"""Detector runner: phrase and measured detectors, driven entirely by library/detectors.yaml."""
import ast
import operator
import re

from nailit.measure import vox

METRICS = (
    "wpm_vs_baseline", "wpm_stddev_by_10s", "final_pitch_slope_result_sentences",
    "pitch_range_and_loudness_var_vs_baseline", "pause_after_number_sentence_s",
    "longest_stretch_without_pause_gt_0_5s", "pre_answer_silence_s", "seconds_to_first_answering_sentence",
    "answer_seconds", "answer_seconds_tmay", "answer_seconds_behavioural", "overlap_user_over_tts_s",
    "gap_after_interviewer_silence_s", "freeze_recovery_s", "trigger_recall_s", "distinct_facts_per_minute",
)
EDGE_SENTENCES = 2  # answer_start / answer_end look at this many sentences
OPS = re.compile(r"^\s*(>=|<=|==|!=|>|<)")


# ---- phrase detectors ----

def _sentences(words, text):
    if words:
        return vox.sentences(words)
    parts = [p.strip() for p in re.split(r"(?<=[.?!])\s+", text or "") if p.strip()]
    return [{"text": p, "start": None, "end": None} for p in parts]


def _scoped(detector, sents, question_type):
    scope = detector.get("scope", "all")
    if scope == "result_sentences":
        return [s for s in sents if vox.is_result_sentence(s["text"])]
    if scope == "answer_start":
        return sents[:EDGE_SENTENCES]
    if scope == "answer_end":
        return sents[-EDGE_SENTENCES:]
    if scope == "failure_answers":
        return sents if question_type == "failure" else []
    return sents


def _patterns(detector, people):
    kind = detector.get("kind", "phrase")
    if kind == "regex":
        return [re.compile(p, re.I) for p in detector.get("patterns") or []]
    if kind == "names_from_profile":
        names = {n for full in people for n in (full, full.split()[0]) if n}
        return [re.compile(rf"\b{re.escape(n)}\b") for n in sorted(names, key=len, reverse=True)]
    return [re.compile(rf"(?<!\w){re.escape(p)}(?!\w)", re.I) for p in detector.get("patterns") or []]


def phrase_hits(detectors, words=None, text=None, question_type=None, people=None):
    """One hit per phrase detector whose matches reach its per-answer threshold, with timestamps when known."""
    sents = _sentences(words, text)
    hits = []
    for detector in detectors:
        patterns = _patterns(detector, people or {})
        cancel = [re.compile(p, re.I) for p in detector.get("except_context") or []]
        matches = []
        for sentence in _scoped(detector, sents, question_type):
            if any(c.search(sentence["text"]) for c in cancel):
                continue
            for pattern in patterns:
                matches += [{"text": m.group(0), "sentence": sentence["text"], "start": sentence["start"]}
                            for m in pattern.finditer(sentence["text"])]
                if detector.get("kind") == "names_from_profile" and matches:
                    break  # "Alex Sample" and "Alex" are one mention
        if len(matches) >= (detector.get("threshold") or {}).get("per_answer", 1):
            hits.append(_hit(detector, "phrase", matches=matches, count=len(matches)))
    return hits


# ---- measured detectors ----

def _expression(rule):
    """'> baseline * 1.2', '< 1 or > 3', 'value > 120 and value < 600' -> a python expression over value/baseline."""
    parts = re.split(r"\s+\b(and|or)\b\s+", rule.strip())
    return " ".join(f"value {p}" if OPS.match(p) else p for p in parts)


BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
CMP = {ast.Gt: operator.gt, ast.GtE: operator.ge, ast.Lt: operator.lt, ast.LtE: operator.le,
       ast.Eq: operator.eq, ast.NotEq: operator.ne}
ALLOWED = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.Compare, ast.BinOp, ast.UnaryOp, ast.USub,
           ast.Name, ast.Load, ast.Constant, *BIN, *CMP)


def _eval(node, names):
    """Interpret a whitelisted rule tree; never calls python's eval."""
    if isinstance(node, ast.Expression):
        return _eval(node.body, names)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return names[node.id]
    if isinstance(node, ast.UnaryOp):
        return -_eval(node.operand, names)
    if isinstance(node, ast.BinOp):
        return BIN[type(node.op)](_eval(node.left, names), _eval(node.right, names))
    if isinstance(node, ast.BoolOp):
        values = (_eval(v, names) for v in node.values)
        return all(values) if isinstance(node.op, ast.And) else any(values)
    left = _eval(node.left, names)
    for op, right_node in zip(node.ops, node.comparators):
        right = _eval(right_node, names)
        if not CMP[type(op)](left, right):
            return False
        left = right
    return True


def compile_rule(rule):
    """Parse a measured-detector rule; raises ValueError if it isn't a comparison over value, baseline and numbers."""
    try:
        tree = ast.parse(_expression(rule), mode="eval")
    except SyntaxError as error:
        raise ValueError(f"cannot parse rule {rule!r}") from error
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED) or (isinstance(node, ast.Name) and node.id not in ("value", "baseline")):
            raise ValueError(f"rule {rule!r}: only comparisons with value, baseline and numbers are allowed")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError(f"rule {rule!r}: only numbers are allowed")
    if not isinstance(tree.body, (ast.Compare, ast.BoolOp)):
        raise ValueError(f"rule {rule!r}: must be a comparison")
    clauses = tree.body.values if isinstance(tree.body, ast.BoolOp) else [tree.body]
    for clause in clauses:
        if "value" not in {n.id for n in ast.walk(clause) if isinstance(n, ast.Name)}:
            raise ValueError(f"rule {rule!r}: every clause must compare the metric")
    return tree, "baseline" in {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}


def evaluate_rule(rule, value, baseline=None):
    """True/False, or None when the metric or a needed baseline is missing."""
    tree, needs_baseline = compile_rule(rule)
    if value is None or (needs_baseline and baseline is None):
        return None
    try:
        return bool(_eval(tree, {"value": value, "baseline": baseline}))
    except ZeroDivisionError:
        return None


def measured_hits(detectors, measurement):
    metrics, baselines = measurement["metrics"], measurement.get("baselines") or {}
    hits = []
    for detector in detectors:
        if not detector.get("metric") or not detector.get("rule"):
            continue
        value = metrics.get(detector["metric"])
        if evaluate_rule(detector["rule"], value, baselines.get(detector["metric"])):
            hits.append(_hit(detector, "measured", metric=detector["metric"], value=value,
                             baseline=baselines.get(detector["metric"])))
    return hits


def _hit(detector, kind, **extra):
    keys = ("id", "label", "severity", "fix", "replacement")
    return {"kind": kind, **{k: detector[k] for k in keys if k in detector}, **extra}


# ---- runner ----

def run(lib, words=None, text=None, audio=None, question_type=None, pre_answer_silence_s=None, baseline=None,
        events=None, people=None):
    """Measure one answer and run every phrase and measured detector from the library on it."""
    detectors = lib["detectors"]
    bridges = [b["text"] for b in (lib.get("phrases") or {}).get("bridges") or []]
    measurement = vox.measure_answer(words or [], audio=audio, baseline=baseline, question_type=question_type,
                                     pre_answer_silence_s=pre_answer_silence_s, bridges=bridges, events=events)
    hits = phrase_hits(detectors["phrase_detectors"], words, text, question_type, people)
    hits += measured_hits(detectors["measured_detectors"], measurement)
    return {"metrics": measurement["metrics"], "baselines": measurement["baselines"], "hits": hits,
            "result_sentences": measurement["result_sentences"], "filled_pauses": measurement["filled_pauses"]}


def library_errors(detectors):
    """check-library: unknown metric names and rules the engine can't evaluate."""
    errors = []
    for detector in detectors.get("measured_detectors") or []:
        if detector["metric"] not in METRICS:
            errors.append(f"detectors.yaml: {detector['id']}: unknown metric {detector['metric']}")
        try:
            compile_rule(detector["rule"])
        except ValueError as error:
            errors.append(f"detectors.yaml: {detector['id']}: {error}")
    for detector in detectors.get("phrase_detectors") or []:
        if detector.get("kind") == "regex":
            for pattern in (detector.get("patterns") or []) + (detector.get("except_context") or []):
                try:
                    re.compile(pattern)
                except re.error as error:
                    errors.append(f"detectors.yaml: {detector['id']}: bad regex {pattern!r}: {error}")
    return errors
