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


def _gpt():
    global _openai
    if _openai is None:
        from openai import OpenAI
        _openai = OpenAI()
    return _openai


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
            if model.startswith("claude"):
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
            if status in (400, 401, 402, 403, 404) or any(w in str(error).lower() for w in ("credit", "quota", "authentication")):
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
    return "\n".join(lines + [f"total (Claude) ≈ ${spent():.2f}{cap}"])


if __name__ == "__main__":  # smoke test: one tiny call per model, about $0.01 in all
    from nailit.config import load_secrets
    load_secrets()
    for name in ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"):
        print(name, json.dumps(chat(name, 'Reply {"ok": true}', json_mode=True, effort="low", max_tokens=2000,
                                    thinking=False)))
    print(usage_report())
