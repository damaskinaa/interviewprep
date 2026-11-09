"""Loads and schema-validates the personal library in ~/NailIt (never committed; see examples/NailIt).

Formats: library files follow SCHEMA.md (schemas in nailit/schemas/); me/ files are parsed from markdown.
"""
import json
import os
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).parent / "schemas"
ME_FILES = ("stories.md", "profile.md", "tmay.md")
LIBRARY_YAML = ("detectors", "phrases", "questions", "followups", "personas")
PROGRAMME_TOKENS = ("weak_list", "all_core", "shuffle")
PROGRAMME_PREFIXES = ("weak_list", "round", "company", "mode", "bank", "count")

FACT_LINE = re.compile(r"^(F\d+)\s*\|\s*(.+?)\s*\|\s*(confirmed|approximate|unconfirmed)\s*\|\s*(.+?)\s*$")
STORY_HEADING = re.compile(r"^##\s+(S[0-9A-Za-z_]+)\b\s*[:—-]?\s*(.*)$")
YAML_BLOCK = re.compile(r"```ya?ml\n(.*?)```", re.S)
FACT_REF = re.compile(r"\bF\d+\b")
RUBRIC_RULE = re.compile(
    r"^\s*(?:[-*]\s+)?\*\*(R(\d+)\.\d+)[.:]?\*\*[.:—–-]?\s*(.+?)\s*(?:\(src:\s*([^)]*)\))?\s*$"
)
RUBRIC_LIKE = re.compile(r"^\s*(?:[-*]\s+)?\**R\d+\.\d+\b")
SNAKE = re.compile(r"^[a-z0-9_]+$")


class LibraryError(ValueError):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


def home():
    return Path(os.getenv("NAILIT_HOME") or Path.home() / "NailIt").expanduser()


def schema_errors(name, data, label):
    schema = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))
    return [f"{label}: {'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message[:200]}" for e in errors]


def _read_yaml(path, errors):
    try:
        return yaml.safe_load(path.read_text(encoding="utf8"))
    except yaml.YAMLError as error:
        errors.append(f"{path.name}: invalid yaml: {error}")
        return None


def _duplicates(ids, label):
    seen, dupes = set(), set()
    for item_id in ids:
        (dupes if item_id in seen else seen).add(item_id)
    return [f"{label}: duplicate id {item_id}" for item_id in sorted(dupes, key=str)]


def _ids(items):
    if not isinstance(items, list):
        return []
    return [item["id"] for item in items if isinstance(item, dict) and "id" in item]


# ---------- me/ ----------

def _sections(text):
    sections, current = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def parse_stories(text):
    """Fact lines `F12 | text | confirmed|approximate|unconfirmed | source`; stories are `## S1 Title` + a yaml block."""
    facts, stories, errors = {}, [], []
    lines = text.splitlines()
    for line in lines:
        stripped = line.strip()
        match = FACT_LINE.match(stripped)
        if match:
            fid, fact, status, source = match.groups()
            if fid in facts:
                errors.append(f"stories.md: duplicate fact {fid}")
            facts[fid] = {"text": fact, "status": status, "source": source}
        elif re.match(r"^F\d+\s*\|", stripped):
            errors.append(f"stories.md: malformed fact line: {stripped[:80]}")
    for index, line in enumerate(lines):
        heading = STORY_HEADING.match(line)
        if not heading:
            continue
        rest = "\n".join(lines[index + 1:])
        next_heading = re.search(r"^##\s", rest, re.M)
        block = YAML_BLOCK.search(rest[: next_heading.start()] if next_heading else rest)
        story_id = heading.group(1)
        if not block:
            errors.append(f"stories.md: {story_id} has no ```yaml block")
            continue
        try:
            fields = yaml.safe_load(block.group(1)) or {}
        except yaml.YAMLError as error:
            errors.append(f"stories.md: {story_id}: invalid yaml: {error}")
            continue
        if not isinstance(fields, dict):
            errors.append(f"stories.md: {story_id}: yaml block must be a mapping")
            continue
        stories.append({"id": story_id, "title": heading.group(2).strip(), **fields})
    return {"facts": facts, "stories": stories}, errors


def check_stories(data):
    errors = schema_errors("stories", data, "stories.md")
    ids = [s["id"] for s in data["stories"]]
    errors += _duplicates(ids, "stories.md")
    for story in data["stories"]:
        listed = story.get("facts") if isinstance(story.get("facts"), list) else []
        refs = {f for f in listed if isinstance(f, str)} | set(FACT_REF.findall(json.dumps(story.get("stages") or {})))
        errors += [f"stories.md: {story['id']} references unknown fact {ref}" for ref in sorted(refs - set(data["facts"]))]
        fallback = story.get("fallback_story")
        if fallback and fallback not in ids:
            errors.append(f"stories.md: {story['id']} fallback_story {fallback} does not exist")
    return errors


def parse_profile(text):
    """`## People` lines `- Name: role` are private; names are replaced by roles before text goes to an LLM."""
    sections = _sections(text)
    people = {}
    for line in sections.get("People", "").splitlines():
        match = re.match(r"^\s*[-*]\s*(.+?)\s*:\s*(.+?)\s*$", line)
        if match:
            people[match.group(1)] = match.group(2)
    profile = {"sections": sections, "people": people}
    if sections.get("Target line"):
        profile["target_line"] = sections["Target line"]
    return profile


def parse_tmay(text):
    return {"versions": {k.lower(): v for k, v in _sections(text).items() if v}}


def load_me(root=None):
    me_dir = (Path(root) if root else home()) / "me"
    errors, me = [], {}
    for name in ME_FILES:
        path = me_dir / name
        if not path.exists():
            errors.append(f"me/{name}: missing")
            continue
        text = path.read_text(encoding="utf8")
        if name == "stories.md":
            me["stories"], parse_errors = parse_stories(text)
            errors += parse_errors + check_stories(me["stories"])
        elif name == "profile.md":
            me["profile"] = parse_profile(text)
            errors += schema_errors("profile", me["profile"], "profile.md")
        else:
            me["tmay"] = parse_tmay(text)
            errors += schema_errors("tmay", me["tmay"], "tmay.md")
    if errors:
        raise LibraryError(errors)
    return me


def people_map(root=None):
    """Colleague name -> role from me/profile.md; empty when there is no profile yet."""
    path = (Path(root) if root else home()) / "me" / "profile.md"
    return parse_profile(path.read_text(encoding="utf8"))["people"] if path.exists() else {}


# ---------- library/ ----------

def parse_rubric(text):
    """Each rule is a line starting with a bold `R<section>.<n>`, then the text, then `(src: D..)`."""
    rules, errors = [], []
    for number, line in enumerate(text.splitlines(), 1):
        match = RUBRIC_RULE.match(line)
        if match:
            rule_id, section, body, sources = match.groups()
            rule = {"id": rule_id, "section": int(section), "text": body}
            if sources:
                rule["src"] = [s.strip() for s in sources.split(",") if s.strip()]
            rules.append(rule)
        elif RUBRIC_LIKE.match(line):
            errors.append(f"rubric.md: line {number}: rule ID must be bold at the start of the line")
    return {"rules": rules}, errors


def _questions(data):
    if isinstance(data, dict):
        return data.get("questions") or [], data.get("candidate_questions") or []
    return data or [], []


def _drill_items(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [d for key, value in data.items() if key != "common_end" and isinstance(value, list) for d in value]
    return []


def _resolve(path):
    path = Path(path).expanduser() if path else home() / "library"
    return path / "library" if (path / "library").is_dir() and not (path / "rubric.md").exists() else path


def _load_files(lib_dir, errors):
    lib = {}
    rubric_path = lib_dir / "rubric.md"
    if rubric_path.exists():
        lib["rubric"], parse_errors = parse_rubric(rubric_path.read_text(encoding="utf8"))
        errors += parse_errors + schema_errors("rubric", lib["rubric"], "rubric.md")
    else:
        errors.append("rubric.md: missing")
    for name in LIBRARY_YAML:
        path = lib_dir / f"{name}.yaml"
        if not path.exists():
            errors.append(f"{name}.yaml: missing")
            continue
        before = len(errors)
        lib[name] = _read_yaml(path, errors)
        if len(errors) == before:
            errors += schema_errors(name, lib[name], f"{name}.yaml")
    for folder, schema in (("drills", "drills"), ("programmes", "programme")):
        lib[folder] = {}
        paths = sorted((lib_dir / folder).glob("*.yaml"))
        if not paths:
            errors.append(f"{folder}/: no .yaml files")
        for path in paths:
            before = len(errors)
            data = _read_yaml(path, errors)
            if len(errors) == before:
                errors += schema_errors(schema, data, f"{folder}/{path.name}")
            lib[folder][path.stem] = data
    return lib


def _cross_reference_errors(lib):
    errors = []
    rubric = {r["id"] for r in lib["rubric"]["rules"]}
    detectors, phrases, personas = lib["detectors"], lib["phrases"], lib["personas"]
    questions, candidates = _questions(lib["questions"])
    banks = lib["followups"]["banks"]
    drills = [d for data in lib["drills"].values() for d in _drill_items(data)]

    errors += _duplicates([r["id"] for r in lib["rubric"]["rules"]], "rubric.md")
    errors += _duplicates([i for key in detectors for i in _ids(detectors[key])], "detectors.yaml")
    errors += _duplicates([i for key in phrases for i in _ids(phrases[key])], "phrases.yaml")
    errors += _duplicates(_ids(questions) + _ids(candidates), "questions.yaml")
    errors += _duplicates(_ids(banks), "followups.yaml")
    errors += _duplicates([i for key in personas for i in _ids(personas[key])], "personas.yaml")
    errors += _duplicates(_ids(drills), "drills/")

    question_ids, round_ids = set(_ids(questions)), set(_ids(personas["rounds"]))
    company_ids, bank_ids, drill_ids = set(_ids(personas["companies"])), set(_ids(banks)), set(_ids(drills))
    question_types = {q["type"] for q in questions}

    for check in detectors["structure_checks"]:
        if check["rubric_rule"] not in rubric:
            errors.append(f"detectors.yaml: {check['id']}: unknown rubric rule {check['rubric_rule']}")
    for company in personas["companies"]:
        errors += [f"personas.yaml: {company['id']}: unknown followup bank {b}"
                   for b in company.get("followup_banks") or [] if b not in bank_ids]
    for bank in banks:
        if bank["trigger"].startswith("company:") and bank["trigger"][8:] not in company_ids:
            errors.append(f"followups.yaml: {bank['id']}: unknown company in trigger {bank['trigger']}")
    for round_ in personas["rounds"]:
        errors += [f"personas.yaml: round {round_['id']}: unknown question or round {entry}"
                   for entry in round_["flow"] if SNAKE.match(entry) and entry not in question_ids | round_ids]

    known = {"round": round_ids, "company": company_ids, "bank": bank_ids}
    for name, programme in lib["programmes"].items():
        label = f"programmes/{name}.yaml"
        for gate in programme.get("gates") or []:
            if gate["after_day"] > programme["days"]:
                errors.append(f"{label}: gate after day {gate['after_day']} is beyond {programme['days']} days")
        for day in programme["schedule"]:
            where = f"{label}: day {day['day']}"
            errors += [f"{where}: unknown drill {d}" for d in day["drills"] if d not in drill_ids]
            for entry in day.get("questions") or []:
                prefix, _, value = entry.partition(":")
                if not value:
                    ok = entry in question_ids or entry in question_types or entry in PROGRAMME_TOKENS
                elif prefix in ("weak_list", "count"):
                    ok = value.isdigit()
                elif prefix == "mode":
                    ok = value in ("A", "B", "C")
                else:
                    ok = prefix in known and value in known[prefix]
                if not ok:
                    errors.append(f"{where}: unknown question entry {entry}")
    return errors


def load_library(path=None):
    """Load and validate a library folder (default ~/NailIt/library); raises LibraryError listing every problem."""
    lib_dir = _resolve(path)
    if not lib_dir.is_dir():
        raise LibraryError([f"{lib_dir}: not a directory"])
    errors = []
    lib = _load_files(lib_dir, errors)
    if not errors:
        errors += _cross_reference_errors(lib)
    if errors:
        raise LibraryError(errors)
    return lib


def summary(lib):
    questions, candidates = _questions(lib["questions"])
    detectors = lib["detectors"]
    counts = {
        "rubric rules": len(lib["rubric"]["rules"]),
        **{key.replace("_", " "): len(detectors[key]) for key in detectors},
        "questions": len(questions),
        "candidate questions": len(candidates),
        "followup banks": len(lib["followups"]["banks"]),
        **{key.replace("_", " "): len(value) for key, value in lib["personas"].items()},
        "drills": sum(len(_drill_items(d)) for d in lib["drills"].values()),
        "programmes": len(lib["programmes"]),
    }
    return ", ".join(f"{n} {k}" for k, n in counts.items())
