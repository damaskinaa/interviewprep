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

## Mock interviews (text, N3a)

`POST /interview/start {"round_id", "mode": "A|B|C", "company_id"?, "temperament_id"?}` starts a mock from
`personas.yaml`. Then send each answer to `POST /interview/answer {"mock_id", "text", "seconds"?, "pre_answer_silence_s"?}`.
`GET /interview/options` lists rounds, companies, temperaments and modes; mode C stays locked until you've done
5 freeze drills and your week-2 average is at least 3.5. `GET /interview/get?mock_id=` returns the transcript,
per-question scores, the stories you used, repeated errors and the pressure events that fired.

## Voice mock (N3b, Pipecat)

On the Mac: `brew install ffmpeg`, then `uv sync --extra voice` (Pipecat, Silero VAD, and on Apple silicon
mlx-whisper + mlx-audio), then `uv run nailit` and open http://127.0.0.1:8000/mock in Chrome.
- **Pipeline** (`nailit/interview/pipeline.py`): page mic → localhost websocket (16 kHz PCM) → turn gate → local
  Whisper → interviewer engine (fast LLM from config) → Kokoro-82M → page speaker (24 kHz PCM).
- **Input:** push-to-talk (default; hold Space), hands-free (Silero VAD; talking over the interviewer interrupts it;
  `NAILIT_VAD_STOP_S`, default 1.5 s of silence ends an answer), or text. The interviewer's interrupt and 90-s
  cut-off events stop your turn.
- **STT:** mlx-whisper with word timestamps; its prompt keeps fillers (um/uh/like). `NAILIT_WHISPER_MODEL`, default
  `mlx-community/whisper-large-v3-turbo`.
- **TTS:** Kokoro-82M through mlx-audio (`NAILIT_KOKORO_VOICE`, default `af_heart`); macOS `say` if Kokoro can't
  run, or with `NAILIT_TTS=say` (`NAILIT_SAY_VOICE`). If both fail, the line is shown as text.
- **Saved files:** each answer (WAV) and the optional webcam video go to `~/NailIt/recordings/<mock_id>/`.
- **Latency:** each turn logs STT, LLM time to first token and total, TTS to first audio, and end-to-end (your last
  word → the interviewer's audio). `GET /voice/latency` lists them with the median.
- **Pressure mode** (`NAILIT_VOICE_PROVIDER=realtime`, pay per use): OpenAI Realtime transcribes and speaks instead of
  Whisper + the interviewer LLM + Kokoro. Turns stay local (push-to-talk or Silero), and the engine still picks every
  line as plain text; the realtime model only voices it. Key: `OPENAI_REALTIME_API_KEY` in the Keychain (or
  `OPENAI_API_KEY`); optional `NAILIT_REALTIME_MODEL`, `NAILIT_REALTIME_VOICE`, `NAILIT_REALTIME_TRANSCRIBE`. Target median < 1 s.
  Its default transcriber (`gpt-realtime-whisper`) takes no prompt, so fillers may be dropped in this mode.
- First run downloads the Whisper (about 1.6 GB) and Kokoro models; after that it runs offline except the LLM.
