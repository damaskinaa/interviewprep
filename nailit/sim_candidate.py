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


def run_rehearse(cards=5, http=None):
    """Rehearsal mode: hear the question and the model answer (TTS), say a paraphrase by voice, check the score.
    A faithful paraphrase should score >= 7; an off-topic answer should score <= 4."""
    http = http or httpx.Client(base_url=BASE, timeout=300)
    problems, rows = [], []
    deck = http.get("/rehearse/deck").json()["cards"][:cards]
    with tempfile.TemporaryDirectory() as folder:
        for index, c in enumerate(deck):
            for part in ("question", "answer"):
                r = http.post("/rehearse/speak", json={"card_id": c["id"], "part": part})
                if r.status_code != 200 or not r.json().get("audio_url"):
                    problems.append(f"card {c['id']}: no {part} audio ({r.status_code})")
                elif http.get(r.json()["audio_url"]).status_code != 200:
                    problems.append(f"card {c['id']}: {part} audio not served")
            good = ask_llm("Paraphrase this interview answer as if rehearsing it from memory: keep its structure, "
                           f"key numbers and trade-off, change the wording, about 80% of the length.\n\n{c['answer']}",
                           max_tokens=500, retries=2, temperature=0.6)
            bad = "I like working with people and I am very hard-working. I think I would be good at this job."
            for label, text, ok in (("paraphrase", good, lambda s: s >= 7), ("off-topic", bad, lambda s: s <= 4)):
                audio = speak_to_file(text, folder, index * 2 + (label == "off-topic"))
                started = time.monotonic()
                with open(audio, "rb") as handle:
                    r = http.post("/rehearse/attempt", data={"card_id": c["id"]}, files={"audio": ("a.aiff", handle, "audio/aiff")})
                wall = round(time.monotonic() - started, 1)
                if r.status_code != 200:
                    problems.append(f"card {c['id']} {label}: /rehearse/attempt {r.status_code} {r.text[:120]}")
                    continue
                score = r.json()["score"]
                rows.append({"card": c["question"][:60], "attempt": label, "score": score, "wall_s": wall})
                if not ok(score):
                    problems.append(f"card {c['id']} {label}: score {score} is outside the expected range")
                if wall > 15:
                    problems.append(f"card {c['id']} {label}: scoring took {wall}s")
    return {"round": "rehearse", "persona": "paraphrase+off-topic", "mode": "-", "mock_id": "-", "minutes": 0,
            "turns": [{"index": i, "wall_s": r["wall_s"], "wer": 0, "kind": r["attempt"], "interviewer": r["card"],
                       "answer_words": 0, "timings": {"score": r["score"]}} for i, r in enumerate(rows)],
            "scores": [{"score": r["score"]} for r in rows], "problems": problems}


def check_end_early(http):
    r = http.post("/interview/start", json={"round_id": "recruiter", "mode": "A"})
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


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--round", default="recruiter")
    parser.add_argument("--persona", default="strong", choices=sorted(PERSONAS))
    parser.add_argument("--mode", default="A")
    parser.add_argument("--tts", default="none", choices=["none", "say", "openai"])
    parser.add_argument("--all", action="store_true", help="recruiter with all personas + one TTS run + end-early check")
    parser.add_argument("--rehearse", type=int, default=0, help="also test rehearsal mode on N cards")
    args = parser.parse_args()
    http = httpx.Client(base_url=BASE, timeout=300)
    if args.all:
        runs = [("recruiter", "strong", "A", "say"), ("recruiter", "nervous", "A", "none"),
                ("hiring_manager", "minimal", "B", "none")]
    else:
        runs = [(args.round, args.persona, args.mode, args.tts)]
    results = [run_one(r, p, m, t, http=http) for r, p, m, t in runs] if not (args.rehearse and not args.all and args.round == "none") else []
    if args.rehearse:
        results.append(run_rehearse(args.rehearse, http=http))
    text, path = report(results, check_end_early(http))
    print(text)
    print(f"\nSaved: {path}")


if __name__ == "__main__":
    main()
