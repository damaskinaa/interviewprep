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

## Voice mock (N3b)

On the Mac: `brew install ffmpeg`, then `uv sync --extra voice` (installs mlx-whisper; Apple silicon only), then
`uv run nailit` and open http://127.0.0.1:8000/mock in Chrome.
- **Input:** click Answer or press Space to start and again to stop, hands-free (Silero VAD in the page; it stops recording after the set
  seconds of silence), or text.
- **Transcription:** runs locally with mlx-whisper (`NAILIT_WHISPER_MODEL`, default
  `mlx-community/whisper-small.en-mlx`). It keeps word timestamps, and its prompt keeps fillers (um/uh/like).
- **Interviewer voice:** OpenAI TTS (`OPENAI_TTS_API_KEY` in the Keychain, or `OPENAI_API_KEY`;
  `NAILIT_TTS_VOICE`, default `alloy`), macOS `say` (`NAILIT_SAY_VOICE`), or none. If OpenAI fails, it uses
  `say`, then text.
- **Saved files:** answers, interviewer audio and the optional webcam video go to `~/NailIt/recordings/<mock_id>/`.
- **Latency:** the time from your last word to the interviewer's audio starting is logged per turn;
  `GET /voice/latency` shows it with the median.
- **Needs internet:** the VAD script loads from jsDelivr (pinned with SRI hashes), and OpenAI TTS is online.
- **Uploads:** capped at 50 MB each.

### Measuring (N4)

`nailit.measure.vox.measure_answer(words, audio, baseline, question_type, events)` computes every
`measured_detectors` metric from word timestamps and, with audio, pitch and loudness (praat-parselmouth):
pace vs your calm baseline (`baseline_from()` on a relaxed recording), pace stability per 10 s, the final pitch
slope of RESULT sentences (sentences with a number or claim), energy vs baseline (1.0 = calm), pauses after
number sentences, the longest stretch with no pause over 0.5 s, time to the first answering sentence (bridges
from phrases.yaml don't count), answer length, filled pauses, and the barge-in / silence-gap / freeze /
recall timers (from words, or from audio onsets when there is no transcript).

`nailit.measure.detectors.run(lib, words, ...)` runs every detector in `detectors.yaml` on an answer:
phrase detectors (`phrase` / `regex` / `names_from_profile`, with scope, `except_context` and `per_answer`
threshold) and measured detectors, whose `rule` is a comparison over the metric and its `baseline`
(`"> baseline * 1.2"`, `"< 1 or > 3"`). Each mock answer is measured after the interviewer's reply has gone
out and stored on the turn for the debrief; nothing is shown during the round. `check-library` reports
unknown metric names, rules the engine can't evaluate and broken regexes.

### Simulated candidate

`uv run python -m nailit.sim_candidate --all` (app running, on the Mac) plays strong, nervous and minimal
candidates through full voice mocks with `say` + local Whisper and reports template leaks, repeated questions,
missing hints, transcription errors, slow turns and early endings. `--fake` runs the same checks in-process with
fake STT/TTS/LLM against the example library; CI runs it and fails on any problem.
