"""One OpenAI-compatible client. Raises on failure and logs the cost of every call."""
import json
import logging
import os
import re
import time
from contextvars import ContextVar

from openai import OpenAI

from nailit.config import llm_settings
from nailit.library import anonymise, people_map

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
_tx_client = None
TENSORX_BASE = os.getenv("TENSORX_BASE_URL") or "https://api.tensorx.ai/v1"
# Live conversation needs speed (interviewer lines); analysis needs strength. Measured on TensorX, Nov 2026:
# MiniMax M3.1 Flash answers in under a second; Kimi K3.1 Pro is the strongest writer on the key.
TX_FAST = os.getenv("NAILIT_TX_FAST") or "minimax/minimax-m3.1-flash"
TX_STRONG = os.getenv("NAILIT_TX_STRONG") or "moonshotai/kimi-k3.1-pro"


ENGINES = {
    "tensorx": {"label": "TensorX", "needs": ["TENSORX_API_KEY"], "cost": "TensorX credit; fractions of a cent per turn",
                "note": "Fastest tested (interviewer replies in 0.4–2 s)."},
    "lua": {"label": "Lua", "needs": ["LUA_API_KEY", "LUA_AGENT_ID"], "cost": "Lua credits",
            "note": "Your Lua agent plays the interviewer through Lua's chat API; hearing and speaking stay on this Mac."},
    "claude": {"label": "Claude (your subscription)", "needs": [], "cost": "No extra cost; counts toward your Claude plan's limits",
               "note": "Runs through Claude Code in the terminal (sign in once with `claude auth login`). Slower: several "
                       "seconds per reply."},
    "gemini": {"label": "Gemini (free key)", "needs": ["GEMINI_API_KEY"], "cost": "Free, with daily limits",
               "note": "A free Google AI Studio key."},
    "openai": {"label": "OpenAI", "needs": ["OPENAI_API_KEY"], "cost": "OpenAI credit", "note": "Needs credit on the account."},
}
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = os.getenv("NAILIT_GEMINI_MODEL") or "gemini-flash-latest"


def settings_path():
    from nailit import library
    return library.home() / "settings.json"


def provider():
    """Who plays the model: NAILIT_PROVIDER, else the engine chosen in settings.json, else TensorX, else OpenAI."""
    forced = (os.getenv("NAILIT_PROVIDER") or "").lower()
    if forced in ENGINES:
        return forced
    try:
        chosen = json.loads(settings_path().read_text()).get("engine")
    except (OSError, ValueError):
        chosen = None
    if chosen in ENGINES:
        return chosen
    return "tensorx" if os.getenv("TENSORX_API_KEY") else "openai"


def engine_ready(name):
    if name == "claude":
        import shutil
        return bool(shutil.which("claude"))
    return all(os.getenv(key) for key in ENGINES[name]["needs"])


def _lua(prompt, max_tokens):
    """One stateless turn on the user's Lua agent. A fresh thread per call keeps Lua from adding its own history."""
    import uuid

    import httpx
    reply = httpx.post(f"https://api.heylua.ai/chat/generate/{os.environ['LUA_AGENT_ID']}", params={"channel": "api"},
                       headers={"Authorization": "Bearer " + os.environ["LUA_API_KEY"]}, timeout=90,
                       json={"messages": [{"type": "text", "text": prompt}], "systemPrompt": SYSTEM_PROMPT,
                             "threadId": "nailit-" + uuid.uuid4().hex[:12]})
    data = reply.json() if reply.headers.get("content-type", "").startswith("application/json") else {}
    if reply.status_code >= 300 or data.get("type") in ("error", "preprocessor_blocked", "governance_blocked"):
        raise LLMError(f"Lua {reply.status_code}: {str(data.get('error') or data.get('message') or reply.text)[:200]}")
    return (data.get("text") or "").strip()


def _other_engine(name, prompt, max_tokens):
    if name == "lua":
        return _lua(prompt, max_tokens)
    if name == "claude":
        from nailit.answers import ai
        return ai._cli("claude-haiku-5-5", SYSTEM_PROMPT + "\n\n" + prompt, "low")
    if name == "gemini":
        response = OpenAI(api_key=os.environ["GEMINI_API_KEY"], base_url=GEMINI_BASE, max_retries=1).chat.completions.create(
            model=GEMINI_MODEL, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            max_tokens=max(max_tokens * 3, 1200), timeout=90)
        return (response.choices[0].message.content or "").strip()
    raise LLMError(f"unknown engine {name}")


KEY_NAMES = ("OPENAI_API_KEY", "TENSORX_API_KEY", "LUA_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY")
KEY_SHAPE = re.compile(r"\b(sk-|AIza)[-_A-Za-z0-9]{16,}")


def redact(text):
    """Provider errors can echo the key that was sent (401 bodies, debug proxies); these messages end up in logs."""
    text = str(text)
    for name in KEY_NAMES:
        value = os.getenv(name) or ""
        if len(value) >= 8:
            text = text.replace(value, "[key]")
    return KEY_SHAPE.sub("[key]", text)


class LLMError(RuntimeError):
    """Raised when the LLM call cannot produce output, so failures never leak into artifacts as text."""

    def __init__(self, message=""):
        super().__init__(redact(message))


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


def log_cost_total(records, label):
    total = round(sum(r["cost_usd"] for r in records), 6)
    logger.info("llm cost %s: %d calls, $%s", label, len(records), total)
    return total


def ask_llm(prompt, model=None, max_tokens=2400, retries=3, temperature=0.25):
    model = model or MODEL_FAST
    engine = provider()
    if engine in ("lua", "claude", "gemini"):
        if not engine_ready(engine):
            raise LLMError(f"{ENGINES[engine]['label']} is selected but not set up: needs {ENGINES[engine]['needs'] or 'the claude command'}.")
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                text = _other_engine(engine, anonymise(prompt.strip(), people_map()), max_tokens)
                if text:
                    return text
                last_error = "empty reply"
            except Exception as error:  # noqa: BLE001
                last_error = error
                if isinstance(error, PermissionError):
                    break
        raise LLMError(f"{ENGINES[engine]['label']} call failed: {last_error}")
    via_tx = engine == "tensorx"
    if via_tx:
        global _tx_client
        if _tx_client is None:
            _tx_client = OpenAI(api_key=os.environ["TENSORX_API_KEY"], base_url=TENSORX_BASE, max_retries=1)
        model = TX_STRONG if model == MODEL_STRONG and MODEL_STRONG != MODEL_FAST else TX_FAST
        max_tokens = max(max_tokens * 3, 1200)  # room for the model's own reasoning before the reply
    elif not os.getenv("OPENAI_API_KEY"):
        raise LLMError("No model key found: add TENSORX_API_KEY or OPENAI_API_KEY (Keychain service 'nailit').")
    user_prompt = anonymise(prompt.strip(), people_map())
    last_error = None
    for attempt in range(1, retries + 1):
        started = time.monotonic()
        try:
            response = (_tx_client if via_tx else client()).chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=150,
            )
            record_call(model, response.usage, time.monotonic() - started)
            text = (response.choices[0].message.content or "").split("</think>")[-1].strip()
            if not text:
                raise LLMError("empty reply")
            return text
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
