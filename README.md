# NailIt

Personal interview prep and practice tool. It runs only on my Mac and binds to 127.0.0.1.

| Path | What |
|---|---|
| `/` (root) | FastAPI backend (`api.py`, prep pipeline in `agent_v2.py`, practice coach in `lua_coach.py`) |
| `nailit/` | CLI (`uv run nailit`) and config (Keychain secrets) |
| `frontend/` | Next.js UI; server routes proxy to the backend via `frontend/lib/backend.ts` |

## Keys
Stored in the macOS Keychain under service `nailit`; `.env` is a fallback (see `.env.example`).
```bash
security add-generic-password -s nailit -a OPENAI_API_KEY -w <key>
security add-generic-password -s nailit -a TAVILY_API_KEY -w <key>
```

## Run
```bash
uv run nailit                 # backend on http://127.0.0.1:8000
cd frontend && npm ci && npm run dev   # UI on http://127.0.0.1:3000
uv run --extra dev pytest tests -q
```
