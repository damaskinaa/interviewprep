import re
from decimal import Decimal

from nailit.prep.common import as_list, count_words, normalize_text

ANSWER_BANNED_OPENINGS = [
    "while my manager was away",
    "in my previous role",
    "in my role as",
    "recognizing the need",
    "i identified that",
    "i faced a situation",
]


WHY_COMPANY_GENERIC_PHRASES = [
    "leader in innovation",
    "google is a leader in innovation",
    "i admire google's culture",
    "i admire google’s culture",
    "dynamic environment",
    "culture of innovation",
    "commitment to innovation",
    "innovation and excellence",
    "innovative practices",
    "collaboration across various teams",
    "enhancing employee experience",
]


def first_sentence(text):
    text = normalize_text(text)
    match = re.search(r"(.+?[.!?])(\s|$)", text)
    return match.group(1).strip() if match else text.split("\n", 1)[0].strip()


def starts_with_banned_opening(answer):
    opening = first_sentence(answer).lower()
    return any(opening.startswith(phrase) for phrase in ANSWER_BANNED_OPENINGS)


def why_company_is_generic(text):
    lowered = normalize_text(text).lower()
    if not lowered:
        return True
    return any(phrase in lowered for phrase in WHY_COMPANY_GENERIC_PHRASES)


def extract_source_numbers(raw_cv, raw_answer_bank):
    """Return the set of digit strings that appear literally in the candidate's own documents."""
    return numbers_in((raw_cv or "") + " " + (raw_answer_bank or ""))


def strip_hallucinated_metrics(answer, raw_cv, raw_answer_bank):
    """
    Scan answer for number+unit patterns.  Replace any that don't appear in
    the candidate's source text with qualitative language.
    Returns (cleaned_answer, list_of_stripped_metrics).
    """
    source_numbers = extract_source_numbers(raw_cv, raw_answer_bank)
    stripped = []

    def _replace(match):
        full = match.group(0)
        if not re.search(r"\d", full):
            return full
        if _is_grounded(_canonical_number(full), source_numbers):
            return full
        # Qualitative replacements by suffix
        low = full.lower()
        stripped.append(full)
        if "%" in full or "percent" in low:
            return "significantly"
        if any(u in low for u in ("hour", "minute", "day", "week", "month")):
            return "meaningfully faster"
        if any(u in low for u in ("$", "dollar", "usd", "gbp", "€")):
            return "meaningfully"
        return "significantly"

    # Pattern: number optionally followed by %, unit words, or currency symbols.
    # Use lookahead/lookbehind instead of \b so the unit suffix is captured in the match.
    pattern = re.compile(
        r"(?<![\d.,])\$?\d+(?:[.,]\d+)*(?:\s*(?:thousand|million|billion|k|m|bn))?(?:\s*(?:%|percent|hours?|minutes?|days?|weeks?|months?))?(?![\d\w])",
        re.IGNORECASE,
    )
    cleaned = pattern.sub(_replace, answer)
    return cleaned, stripped


def answer_word_failures_from_strategy(strategy):
    failures = []
    for round_item in as_list(strategy.get("questions_by_round")):
        for item in as_list(round_item.get("questions") if isinstance(round_item, dict) else []):
            answer = item.get("complete_written_answer", "") if isinstance(item, dict) else ""
            words = count_words(answer)
            if words and words < 180:
                failures.append(item.get("question", "answer")[:120])
    return failures


NUMBER_PATTERN = re.compile(
    r"(?<![\w.])\$?\d+(?:[.,]\d+)*(?:\s*(?:thousand|million|billion|k|m|bn))?(?:\s*(?:%|percent))?(?![\w])", re.IGNORECASE
)


NUMBER_SCALES = {
    "k": Decimal(1_000), "thousand": Decimal(1_000),
    "m": Decimal(1_000_000), "million": Decimal(1_000_000),
    "bn": Decimal(1_000_000_000), "billion": Decimal(1_000_000_000),
}


def _canonical_number(raw):
    """Scaled value as text, with a trailing % for percentages: "$250k" -> "250000", "40 percent" -> "40%"."""
    low = raw.lower().strip()
    value = Decimal(re.search(r"\d+(?:[.,]\d+)*", low).group(0).replace(",", ""))
    scale = re.search(r"\d\s*(thousand|million|billion|bn|k|m)\b", low)
    if scale:
        value *= NUMBER_SCALES[scale.group(1)]
    text = format(value.normalize(), "f")
    return text + "%" if "%" in low or "percent" in low else text


def _is_grounded(value, allowed):
    """A percentage must match a source percentage; a bare number matches the same value in any unit."""
    return value in allowed or (not value.endswith("%") and value in {a.rstrip("%") for a in allowed})


def numbers_in(text):
    """Canonical numeric values mentioned in a text ("1,200", "1200" and "1.2k" are the same number)."""
    return {_canonical_number(m.group(0)) for m in NUMBER_PATTERN.finditer(text or "")}


def invented_numbers(text, *allowed_sources):
    """Numbers in `text` that appear in none of the allowed source texts, in order of first mention."""
    allowed = set().union(*(numbers_in(source) for source in allowed_sources)) if allowed_sources else set()
    seen, invented = set(), []
    for match in NUMBER_PATTERN.finditer(text or ""):
        value = _canonical_number(match.group(0))
        if not _is_grounded(value, allowed) and value not in seen:
            seen.add(value)
            invented.append(match.group(0).strip())
    return invented
