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

## Your library (content as data)

The engine loads your private content from `~/NailIt/` (override with `NAILIT_HOME`). Nothing in it is ever committed.

- `~/NailIt/me/`: `stories.md`, `profile.md` and `tmay.md`. These are your facts.
- `~/NailIt/library/`: `rubric.md`, `detectors.yaml`, `phrases.yaml`, `questions.yaml`, `followups.yaml`, `personas.yaml`, `drills/*.yaml` and `programmes/*.yaml`.

`examples/NailIt/` is a tiny synthetic library in the same format; the JSON schemas live in `nailit/schemas/`.

```bash
uv run nailit check-library               # validates ~/NailIt/library
uv run nailit check-library path/to/lib   # or any folder
```

It reports schema errors and unknown cross-references (rubric rules, follow-up banks, drills, questions, rounds, companies), and exits non-zero if anything fails.

**stories.md**:
- Fact lines take the form `F12 | text | confirmed|approximate|unconfirmed | source`.
- Each story is a `## S1 Title` heading followed by a fenced yaml block. The block references fact IDs and holds the story fields: `trigger`, `stages` (HOOK … LESSON), `compressed` (`3_words`, `1_sentence`, `30s`, `90s`), and the rest. See `examples/NailIt/me/stories.md`.

**profile.md**: a `## People` section lists `- Name: role`, and those names are replaced by roles before any text goes to an LLM.
