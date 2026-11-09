"""One OpenAI-compatible client. Raises on failure and logs the cost of every call."""
import json
import logging
import os
import re
import time
from contextvars import ContextVar

from openai import OpenAI

from nailit.config import llm_settings

logger = logging.getLogger("nailit.llm")

SETTINGS = llm_settings()
MODEL_FAST = SETTINGS["model_fast"]
MODEL_STRONG = SETTINGS["model_strong"]

SYSTEM_PROMPT = (
    "You are Nailit, a private interview strategist. "
    "You are evidence led, specific, practical, honest, and direct. "
    "Never invent facts, numbers, timelines or stakes. Separate official evidence from directional public themes. "
    "Use only the candidate's own evidence for claims about the candidate."
)

_cost_log = ContextVar("nailit_cost_log", default=None)
_client = None


class LLMError(RuntimeError):
    """Raised when the LLM call cannot produce output, so failures never leak into artifacts as text."""


def client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY") or "missing", base_url=SETTINGS["base_url"] or None)
    return _client


def call_cost(model, prompt_tokens, completion_tokens):
    role = "strong" if model == MODEL_STRONG and model != MODEL_FAST else "fast"
    prices = SETTINGS["prices"][role]
    return round((prompt_tokens * prices[0] + completion_tokens * prices[1]) / 1_000_000, 6)


def start_cost_log():
    """Collect per-call cost records for the current job/context."""
    records = []
    _cost_log.set(records)
    return records


def record_call(model, usage, seconds):
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    record = {
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": call_cost(model, prompt_tokens, completion_tokens),
        "seconds": round(seconds, 3),
    }
    logger.info("llm call %s", json.dumps(record))
    records = _cost_log.get()
    if records is not None:
        records.append(record)
    return record


def ask_llm(prompt, model=None, max_tokens=2400, retries=3, temperature=0.25):
    model = model or MODEL_FAST
    if not os.getenv("OPENAI_API_KEY"):
        raise LLMError("OPENAI_API_KEY is not set (Keychain service 'nailit' or .env).")
    last_error = None
    for attempt in range(1, retries + 1):
        started = time.monotonic()
        try:
            response = client().chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt.strip()}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=150,
            )
            record_call(model, response.usage, time.monotonic() - started)
            return response.choices[0].message.content or ""
        except Exception as error:
            last_error = error
            if attempt < retries:
                time.sleep(3 * attempt)
    raise LLMError(f"LLM call failed after {retries} attempts: {last_error}")


JSON_PARSE_ERROR = "Could not parse model output as valid JSON"
JSON_PARSE_ERROR_KEY = "__nailit_parse_error__"


def extract_json(text):
    text = text or "{}"
    cleaned = text.strip()
    cleaned = re.sub(r"^```json", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"^```", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first != -1 and last != -1 and last > first:
        cleaned = cleaned[first:last + 1]
    try:
        return json.dumps(json.loads(cleaned), indent=2)
    except Exception:
        return json.dumps({JSON_PARSE_ERROR_KEY: True, "error": JSON_PARSE_ERROR, "raw_output": text[:6000]}, indent=2)


def parse_json_object(text, fallback=None):
    fallback = fallback if fallback is not None else {}
    try:
        parsed = json.loads(extract_json(text))
    except Exception:
        return fallback
    if isinstance(parsed, dict) and parsed.get(JSON_PARSE_ERROR_KEY) is True:
        return fallback
    return parsed


def json_dumps(data):
    return json.dumps(data or {}, indent=2, ensure_ascii=False)


def ask_json(prompt, model=None, max_tokens=3000, retries=3, fallback=None):
    output = ask_llm(prompt, model=model, max_tokens=max_tokens, retries=retries)
    return parse_json_object(output, fallback=fallback if fallback is not None else {})
