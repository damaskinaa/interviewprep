# NailIt

Personal interview prep and practice tool. It runs only on my Mac and binds to 127.0.0.1.

| Path | What |
|---|---|
| `nailit/api.py` | FastAPI app (`uv run nailit`) |
| `nailit/llm.py` | the one OpenAI-compatible client: fast + strong model, raises on error, logs cost per call |
| `nailit/guards.py` | grounding rules and the invented-number check |
| `nailit/prep/` | `research.py` (company, role, rounds), `me.py` (candidate profile, gap map), `questions.py` (strategy, prep pack), `answers.py` |
| `nailit/coach.py`, `nailit/store.py` | practice coach; SQLite jobs/sessions |
| `frontend/` | Next.js UI; server routes proxy to the backend via `frontend/lib/backend.ts` |

## Keys
Stored in the macOS Keychain under service `nailit`; `.env` is a fallback (see `.env.example`).
```bash
security add-generic-password -s nailit -a OPENAI_API_KEY -w <key>
security add-generic-password -s nailit -a TAVILY_API_KEY -w <key>
```

## Models
`OPENAI_BASE_URL`, `NAILIT_MODEL_FAST`, `NAILIT_MODEL_STRONG` and `NAILIT_PRICE_FAST` / `NAILIT_PRICE_STRONG` (USD per 1M input,output tokens) configure the client.

## Run
```bash
uv run nailit                 # backend on http://127.0.0.1:8000
cd frontend && npm ci && npm run dev   # UI on http://127.0.0.1:3000
uv run --extra dev pytest tests -q
```
