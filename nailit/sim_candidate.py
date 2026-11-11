"""Simulated candidate: runs whole mock interviews against the live app, by voice, and reports every problem.

It plays a persona, writes each answer with the LLM, speaks it with macOS `say`, uploads the audio to
/voice/answer exactly like the browser does (so local transcription, the interviewer and TTS all run for
real), and checks each step. Usage:

    uv run python -m nailit.sim_candidate --round recruiter --persona strong
    uv run python -m nailit.sim_candidate --all

The report is written to ~/NailIt/sim_reports/<timestamp>.md and printed.
"""
import argparse
import difflib
import json
import re
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

import httpx

from nailit import library
from nailit.llm import ask_llm

BASE = "http://127.0.0.1:8000"
PERSONAS = {
    "strong": ("A senior Service Delivery / Operations Manager candidate, about 8 years in tech operations for a "
               "global platform's partner programme, leading about 10 people across three regions. Answers like a top "
               "candidate: result first, says 'I' for decisions, one number with context, the trade-off, the lesson. "
               "75-90 seconds when spoken (about 170-210 words) for main questions, 40-70 words for follow-ups."),
    "nervous": ("The same background, but nervous: starts with context, says 'we' a lot, uses 'um' and 'like', "
                "hedges, forgets numbers, rambles slightly. 120-180 words for main questions."),
    "minimal": ("A tired candidate who gives very short answers of one or two sentences and sometimes says "
                "'I'm not sure'."),
}
TEMPLATE_LEAKS = [r"This one is a", r"\{.*?\}", r"\bNone\b", r"undefined", r"\[.*?\]", r"as an AI", r"I'm an AI"]


def speak_to_file(text, folder, index):
    aiff = Path(folder) / f"answer_{index:02d}.aiff"
    subprocess.run(["say", "-o", str(aiff), "--", text], check=True, timeout=180, capture_output=True)
    return aiff


def wer(ref, hyp):
    norm = lambda s: re.sub(r"[^a-z0-9' ]", " ", s.lower()).split()  # noqa: E731
    r, h = norm(ref), norm(hyp)
    if not r:
        return 0.0
    sm = difflib.SequenceMatcher(None, r, h)
    matched = sum(b.size for b in sm.get_matching_blocks())
    return round(1 - matched / len(r), 3)


def write_answer(persona, history, line, kind):
    convo = "\n".join(f"{who}: {text}" for who, text in history[-8:])
    prompt = (f"You are role-playing a job candidate in a spoken interview.\nPersona: {PERSONAS[persona]}\n"
              f"Never mention that this is a simulation. Do not use real company-confidential details or names.\n"
              f"Conversation so far:\n{convo}\n\nInterviewer ({kind}): {line}\n\n"
              "Reply with only the words you would say out loud.")
    return ask_llm(prompt, max_tokens=500, retries=2, temperature=0.7).strip()


def run_one(round_id, persona, mode="A", tts="none", max_turns=40, http=None):
    http = http or httpx.Client(base_url=BASE, timeout=300)
    problems, turns, history = [], [], []
    t0 = time.monotonic()
    r = http.post("/interview/start", json={"round_id": round_id, "mode": mode})
    if r.status_code != 200:
        return {"round": round_id, "persona": persona, "fatal": f"start failed {r.status_code}: {r.text[:200]}"}
    mock_id = r.json()["mock_id"]
    data = http.post("/voice/say", json={"mock_id": mock_id, "engine": tts}).json()
    asked = []
    with tempfile.TemporaryDirectory() as folder:
        for index in range(max_turns):
            turn = data["turn"]
            line = turn["say"]
            for pattern in TEMPLATE_LEAKS:
                if re.search(pattern, line):
                    problems.append(f"turn {index}: interviewer line has a template leak ({pattern}): {line[:120]}")
            if not line.strip():
                problems.append(f"turn {index}: interviewer said nothing")
            if turn.get("kind") == "question":
                if turn.get("question_id") in asked:
                    problems.append(f"turn {index}: question {turn.get('question_id')} asked twice")
                asked.append(turn.get("question_id"))
                if mode == "A" and not turn.get("hint"):
                    problems.append(f"turn {index}: Mode A question without an on-screen hint")
            if tts != "none" and not data.get("audio_url"):
                problems.append(f"turn {index}: no interviewer audio (engine {data.get('tts_engine')})")
            history.append(("Interviewer", line))
            if data.get("done"):
                break
            answer = write_answer(persona, history, line, turn.get("kind", "question"))
            audio = speak_to_file(answer, folder, index)
            if index == 0:
                with open(audio, "rb") as handle:
                    preview = http.post("/voice/preview", data={"mock_id": mock_id},
                                        files={"audio": ("preview.aiff", handle, "audio/aiff")})
                if preview.status_code != 200 or not preview.json().get("text"):
                    problems.append(f"live caption (/voice/preview) failed: {preview.status_code} {preview.text[:120]}")
            started = time.monotonic()
            with open(audio, "rb") as handle:
                resp = http.post("/voice/answer", data={"mock_id": mock_id, "engine": tts, "gap_before_record_s": "1.0"},
                                 files={"audio": ("answer.aiff", handle, "audio/aiff")})
            wall = round(time.monotonic() - started, 2)
            if resp.status_code != 200:
                problems.append(f"turn {index}: /voice/answer {resp.status_code}: {resp.text[:200]}")
                break
            data = resp.json()
            heard = data["transcript"]["text"]
            error_rate = wer(answer, heard)
            if error_rate > 0.15:
                problems.append(f"turn {index}: transcription word error {error_rate:.0%}")
            if wall > 12:
                problems.append(f"turn {index}: slow turn {wall}s (timings {data.get('timings')})")
            turns.append({"index": index, "kind": turn.get("kind"), "interviewer": line, "answer_words": len(answer.split()),
                          "wer": error_rate, "wall_s": wall, "timings": data.get("timings")})
            history.append(("Candidate", answer))
        else:
            problems.append(f"mock did not finish within {max_turns} turns")
    summary = http.get("/interview/get", params={"mock_id": mock_id}).json()
    if summary.get("phase") != "done" and not any("did not finish" in p for p in problems):
        problems.append(f"mock ended in phase {summary.get('phase')}")
    if not summary.get("scores"):
        problems.append("no questions were scored")
    return {"round": round_id, "persona": persona, "mode": mode, "mock_id": mock_id, "minutes": round((time.monotonic() - t0) / 60, 1),
            "turns": turns, "scores": summary.get("scores"), "problems": problems}


def check_end_early(http, round_id="recruiter"):
    r = http.post("/interview/start", json={"round_id": round_id, "mode": "A"})
    if r.status_code != 200:
        return [f"End-early check could not start: {r.status_code} {r.text[:200]}"]
    mock_id = r.json()["mock_id"]
    http.post("/interview/answer", json={"mock_id": mock_id, "text": "I lead operations teams and I fix broken processes."})
    end = http.post("/interview/end", json={"mock_id": mock_id})
    ok = end.status_code == 200 and end.json().get("phase") == "done"
    return [] if ok else [f"End interview failed: {end.status_code} {end.text[:200]}"]


def report(results, extra):
    lines = [f"# Simulated candidate report · {datetime.now():%Y-%m-%d %H:%M}", ""]
    total = sum(len(r.get("problems", [])) for r in results) + len(extra)
    lines += [f"**{len(results)} mocks · {total} problems**", ""]
    for r in results:
        if r.get("fatal"):
            lines += [f"## {r['round']} · {r['persona']}: FATAL", r["fatal"], ""]
            continue
        walls = [t["wall_s"] for t in r["turns"]] or [0]
        wers = [t["wer"] for t in r["turns"]] or [0]
        lines += [f"## {r['round']} · {r['persona']} · mode {r['mode']} · {r['minutes']} min",
                  f"- turns {len(r['turns'])} · median turn {sorted(walls)[len(walls) // 2]}s · max {max(walls)}s · "
                  f"mean transcription error {sum(wers) / len(wers):.1%}",
                  f"- scores: {[s['score'] for s in r.get('scores') or []]}"]
        lines += [f"- PROBLEM: {p}" for p in r["problems"]] or ["- no problems"]
        lines.append("")
    lines += [f"- PROBLEM: {p}" for p in extra]
    text = "\n".join(lines)
    out = library.home() / "sim_reports"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{datetime.now():%Y%m%d_%H%M%S}.md"
    path.write_text(text, encoding="utf8")
    (out / f"{path.stem}.json").write_text(json.dumps(results, indent=1), encoding="utf8")
    return text, path


def fake_mode():
    """CI mode: in-process app with fake STT (the uploaded file holds the answer text), no TTS, canned LLM lines."""
    import os
    import shutil
    from unittest import mock

    from fastapi.testclient import TestClient

    from nailit import api, store
    from nailit.interview import voice
    home = Path(tempfile.mkdtemp()) / "NailIt"  # a copy, so reports never land inside the repo
    shutil.copytree(Path(__file__).resolve().parents[1] / "examples" / "NailIt", home)
    os.environ["NAILIT_HOME"] = str(home)
    os.environ.setdefault("NAILIT_RECORDINGS", tempfile.mkdtemp())
    os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())

    def fake_words(path, **_):
        text = Path(path).read_text()
        words = [{"word": w, "start": 0.4 * i, "end": 0.4 * i + 0.3} for i, w in enumerate(text.split())]
        return voice.words_result({"segments": [{"words": words}]}, 0.4 * len(words) + 0.5)

    def fake_speak(text, folder, index):
        path = Path(folder) / f"answer_{index}.txt"
        path.write_text(text)
        return path

    canned = ("I led the rollout. The result was a shorter queue. I chose a pilot over a big bang because it was "
              "reversible, and the lesson was to test early.")
    patches = [mock.patch.object(store, "DB_PATH", Path(tempfile.mkdtemp()) / "sim.db"),
               mock.patch("nailit.interview.interviewer.ask_llm", return_value="Tell me more about that."),
               mock.patch(f"{__name__}.ask_llm", return_value=canned),
               mock.patch.object(voice, "transcribe", side_effect=fake_words),
               mock.patch.object(voice, "live_update", side_effect=lambda mock_id, take, path: Path(path).read_text()),
               mock.patch(f"{__name__}.speak_to_file", side_effect=fake_speak)]
    for p in patches:
        p.start()
    return TestClient(api.app), patches


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--round", help="default: recruiter (behavioural with --fake)")
    parser.add_argument("--persona", default="strong", choices=sorted(PERSONAS))
    parser.add_argument("--mode", default="A")
    parser.add_argument("--tts", default="none", choices=["none", "say", "openai"])
    parser.add_argument("--all", action="store_true", help="recruiter with all personas + one TTS run + end-early check")
    parser.add_argument("--fake", action="store_true", help="no Mac needed: fake STT/TTS/LLM, in-process app (CI)")
    args = parser.parse_args()
    patches = []
    if args.fake:
        http, patches = fake_mode()
    else:
        http = httpx.Client(base_url=BASE, timeout=300)
    end_round = "behavioural" if args.fake else "recruiter"  # the example library has no recruiter round
    args.round = args.round or end_round
    if args.all and args.fake:  # the example library only has behavioural and loop rounds
        runs = [("behavioural", "strong", "A", "none"), ("behavioural", "nervous", "A", "none"),
                ("behavioural", "minimal", "B", "none")]
    elif args.all:
        runs = [("recruiter", "strong", "A", "say"), ("recruiter", "nervous", "A", "none"),
                ("hiring_manager", "minimal", "B", "none")]
    else:
        runs = [(args.round, args.persona, args.mode, args.tts)]
    try:
        results = [run_one(r, p, m, t, http=http) for r, p, m, t in runs]
        extra = check_end_early(http, end_round)
    finally:
        for p in patches:
            p.stop()
    text, path = report(results, extra)
    print(text)
    print(f"\nSaved: {path}")
    if extra or any(r.get("fatal") or r.get("problems") for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
