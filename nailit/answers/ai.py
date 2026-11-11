"""Model access for the answer engine: Claude (Anthropic SDK) or OpenAI by model name; embeddings run locally.

Claude models are chosen by name (`claude-...`). Anthropic has no embeddings endpoint, so clustering uses a local
sentence-transformers model (free, offline after the first download).
"""
import json
import os
import time

from nailit.llm import parse_json_object

USAGE = {}
PRICES = {"claude-opus-5-5": (4, 20), "claude-sonnet-5-5": (2, 10), "claude-haiku-5-5": (0.10, 0.50)}  # $/M tokens
CAP_USD = float(os.getenv("NAILIT_BUDGET_USD") or 0)  # 0 = no cap; set per run with set_cap()
EMBED_MODEL = os.getenv("NAILIT_EMBED_MODEL") or "BAAI/bge-small-en-v1.5"
_anthropic = None
_openai = None
_embedder = None


class BudgetExceeded(RuntimeError):
    pass


def set_cap(usd):
    global CAP_USD
    CAP_USD = float(usd or 0)


def spent():
    return sum((inp * PRICES[m][0] + out * PRICES[m][1]) / 1e6 for m, (inp, out) in USAGE.items() if m in PRICES)


def _claude():
    global _anthropic
    if _anthropic is None:
        import anthropic
        _anthropic = anthropic.Anthropic(max_retries=4)
    return _anthropic


TENSORX_BASE = os.getenv("TENSORX_BASE_URL") or "https://api.tensorx.ai/v1"
_tensorx = None


def _tx():
    """TensorX: OpenAI-compatible API; models are named "tx:<model id>" in this module."""
    global _tensorx
    if _tensorx is None:
        from openai import OpenAI
        _tensorx = OpenAI(api_key=os.environ["TENSORX_API_KEY"], base_url=TENSORX_BASE, max_retries=4)
    return _tensorx


def _gpt():
    global _openai
    if _openai is None:
        from openai import OpenAI
        _openai = OpenAI()
    return _openai


CLI_MODELS = {"claude-haiku-5-5": "haiku", "claude-sonnet-5-5": "sonnet", "claude-opus-5-5": "opus"}
BACKEND = os.getenv("NAILIT_LLM_BACKEND") or "cli"  # "cli" = Claude Code on your Claude plan (no API key); "api" = SDK


class CLIError(RuntimeError):
    pass


def _cli(model, prompt, effort):
    """One headless Claude Code call (`claude -p`): uses your signed-in Claude plan, no tools, no project context."""
    import subprocess
    import tempfile
    cmd = ["claude", "-p", "--model", CLI_MODELS.get(model, model), "--effort", effort, "--tools", "",
           "--strict-mcp-config", "--no-session-persistence", "--output-format", "json",
           "--system-prompt", "You are a precise assistant. Follow the user's instructions exactly."]
    with tempfile.TemporaryDirectory() as cwd:  # empty folder: no CLAUDE.md or project files leak into the prompt
        run = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=600, cwd=cwd)
    try:
        data = json.loads(run.stdout)
    except json.JSONDecodeError as error:
        raise CLIError(f"claude -p failed: {(run.stderr or run.stdout)[:300]}") from error
    if data.get("is_error"):
        message = str(data.get("result"))
        if any(w in message.lower() for w in ("authenticate", "login", "limit", "credit")):
            raise PermissionError(f"claude -p: {message}")  # not retried: sign in, or wait for the usage limit to reset
        raise CLIError(f"claude -p: {message}")
    usage = data.get("usage") or {}
    _track("cli:" + CLI_MODELS.get(model, model), usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
           + usage.get("cache_creation_input_tokens", 0), usage.get("output_tokens", 0))
    return (data.get("result") or "").strip()


def _track(model, inp, out):
    u = USAGE.setdefault(model, [0, 0])
    u[0] += inp or 0
    u[1] += out or 0


def chat(model, prompt, json_mode=False, effort="medium", max_tokens=16000, retries=3, thinking=True):
    """One request. JSON mode asks for a single JSON object and parses it ({} on failure).

    thinking=False switches thinking off where the model allows it (Haiku 5.5: disabled; Sonnet 5.5: between_tools);
    Opus 5.5 always thinks, so effort is its only cost control. Raises BudgetExceeded once the run's cap is spent, and
    re-raises request errors (bad parameter, auth, no credit) instead of quietly returning empty results.
    """
    if CAP_USD and spent() >= CAP_USD:
        raise BudgetExceeded(f"spending cap ${CAP_USD:.2f} reached (spent ${spent():.2f})")
    if json_mode:
        prompt += "\n\nReply with one JSON object only, no prose before or after it."
    for attempt in range(retries):
        try:
            if model.startswith("tx:"):
                kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
                resp = _tx().chat.completions.create(model=model[3:], messages=[{"role": "user", "content": prompt}],
                                                     max_tokens=max_tokens, **kwargs)
                _track(model, resp.usage.prompt_tokens, resp.usage.completion_tokens)
                text = (resp.choices[0].message.content or "").strip()
                text = text.split("</think>")[-1].strip()  # reasoning models may inline their thinking
                if resp.choices[0].finish_reason == "length" or (json_mode and not parse_json_object(text, {})):
                    # long thinking ran out of room, or the JSON came back broken: retry with more room
                    max_tokens = min(max_tokens * 2, 64000)
                    raise ValueError("truncated or invalid JSON reply")
            elif model.startswith("claude") and BACKEND == "cli":
                text = _cli(model, prompt, effort)
            elif model.startswith("claude"):
                extra = {}
                if not thinking and "haiku" in model:
                    extra["thinking"] = {"type": "disabled"}
                elif not thinking and "sonnet-5-5" in model:
                    extra["thinking"] = {"type": "between_tools"}
                resp = _claude().messages.create(
                    model=model, max_tokens=max_tokens, output_config={"effort": effort},
                    messages=[{"role": "user", "content": prompt}], **extra)
                _track(model, resp.usage.input_tokens, resp.usage.output_tokens)
                if resp.stop_reason == "refusal":
                    return {} if json_mode else ""
                text = "".join(b.text for b in resp.content if b.type == "text").strip()
            else:
                kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
                resp = _gpt().chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], **kwargs)
                _track(model, resp.usage.prompt_tokens, resp.usage.completion_tokens)
                text = (resp.choices[0].message.content or "").strip()
            return parse_json_object(text, {}) if json_mode else text
        except Exception as error:  # noqa: BLE001 - SDKs already retry 429/5xx; this covers parse and transient errors
            status = getattr(error, "status_code", None)
            if isinstance(error, PermissionError) or status in (400, 401, 402, 403, 404) or any(w in str(error).lower() for w in ("credit", "quota", "authentication")):
                raise
            time.sleep(3 * (attempt + 1))
    return {} if json_mode else ""


def embed(texts):
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder.encode(list(texts), batch_size=64, normalize_embeddings=True, show_progress_bar=False).tolist()


def usage_report():
    lines = []
    for model, (inp, out) in USAGE.items():
        p = PRICES.get(model)
        cost = (inp * p[0] + out * p[1]) / 1e6 if p else None
        lines.append(f"{model}: {inp:,} in / {out:,} out" + (f" ≈ ${cost:.2f}" if cost is not None else ""))
    cap = f" of ${CAP_USD:.2f} cap" if CAP_USD else ""
    if BACKEND == "cli":
        return "\n".join(lines + ["backend: Claude Code on your Claude plan (no API charges; counts toward your plan's usage limits)"])
    return "\n".join(lines + [f"total (Claude) ≈ ${spent():.2f}{cap}"])


if __name__ == "__main__":  # smoke test: one tiny call per model, about $0.01 in all
    from nailit.config import load_secrets
    load_secrets()
    import sys
    if "--tensorx-models" in sys.argv:  # list the models your TensorX key can use
        for m in sorted(x.id for x in _tx().models.list().data):
            print(m)
        raise SystemExit
    print("backend:", BACKEND)
    for name in ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"):
        print(name, json.dumps(chat(name, 'Reply {"ok": true}', json_mode=True, effort="low", max_tokens=2000,
                                    thinking=False)))
    print(usage_report())
