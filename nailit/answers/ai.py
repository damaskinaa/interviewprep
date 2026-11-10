"""Model access for the answer engine: Claude (Anthropic SDK) or OpenAI by model name; embeddings run locally.

Claude models are chosen by name (`claude-...`). Anthropic has no embeddings endpoint, so clustering uses a local
sentence-transformers model (free, offline after the first download).
"""
import json
import os
import time

from nailit.llm import parse_json_object

USAGE = {}
EMBED_MODEL = os.getenv("NAILIT_EMBED_MODEL") or "BAAI/bge-small-en-v1.5"
_anthropic = None
_openai = None
_embedder = None


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


def chat(model, prompt, json_mode=False, effort="medium", max_tokens=16000, retries=3):
    """One request. JSON mode asks for a single JSON object and parses it ({} on failure)."""
    if json_mode:
        prompt += "\n\nReply with one JSON object only, no prose before or after it."
    for attempt in range(retries):
        try:
            if model.startswith("claude"):
                import anthropic
                resp = _claude().messages.create(
                    model=model, max_tokens=max_tokens, output_config={"effort": effort},
                    messages=[{"role": "user", "content": prompt}])
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
            if "credit" in str(error).lower() or "quota" in str(error).lower() or "authentication" in str(error).lower():
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
    prices = {"claude-opus-5-5": (4, 20), "claude-sonnet-5-5": (2, 10), "claude-haiku-5-5": (0.10, 0.50)}
    total = 0.0
    lines = []
    for model, (inp, out) in USAGE.items():
        p = prices.get(model)
        cost = (inp * p[0] + out * p[1]) / 1e6 if p else None
        total += cost or 0
        lines.append(f"{model}: {inp:,} in / {out:,} out" + (f" ≈ ${cost:.2f}" if cost is not None else ""))
    return "\n".join(lines + [f"total (Claude) ≈ ${total:.2f}"])


if __name__ == "__main__":
    print(json.dumps(chat(os.getenv("NAILIT_ANSWER_WRITER", "claude-opus-5-5"), "Say OK as JSON {\"ok\": true}", json_mode=True)))
