# NailIt interview prep

| Path | What |
|---|---|
| `/` (root) | FastAPI backend (`api.py`, pipeline in `agent_v2.py`, Lua coach `lua_*.py`) |
| `frontend/` | Next.js UI; server routes proxy to the backend via `frontend/lib/backend.ts` |
| `docs/nmt/` | Next Move Theory research workbench (not shipped in the Docker image) |

## Backend
```bash
cp .env.example .env   # fill in keys
docker compose up      # api on :8000 + rq worker + redis
# or: pip install -r dev-requirements.txt && uvicorn api:app --reload
python -m pytest tests -q
```

## Frontend
```bash
cd frontend
cp .env.example .env.local   # APP_API_KEY, BACKEND_URL=http://localhost:8000
npm ci && npm run dev
```
On Vercel, set the project's **Root Directory** to `frontend`.
