"""Voice loop: local mlx-whisper transcription (word timestamps, fillers kept) and interviewer TTS.

Endpointing happens in the browser page (push-to-talk, or hands-free with Silero VAD). The page uploads one
recording per answer; this module saves it under ~/NailIt/recordings/<mock_id>/, transcribes it locally,
and turns the interviewer's reply into audio with OpenAI TTS or the free macOS `say`.
"""
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from nailit import library

logger = logging.getLogger("nailit.voice")

SAMPLE_RATE = 16000
WHISPER_MODEL = "mlx-community/whisper-small.en-mlx"  # ~10x real time on an M4 with word timestamps; set NAILIT_WHISPER_MODEL for large-v3-turbo
# Whisper drops disfluencies unless the prompt shows them; this prompt makes it transcribe them verbatim.
FILLER_PROMPT = "Um, so, uh, I mean, like, we, um, we kind of, uh, started with the, like, the first step."
FILLED_PAUSES = {"um", "umm", "uh", "uhh", "er", "erm", "ah", "hmm", "mm"}
TTS_ENGINES = ("openai", "say", "none")
OPENAI_TTS_MODEL = "gpt-4o-mini-tts"
SAFE_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$")


class VoiceUnavailable(RuntimeError):
    """Raised when a voice dependency (mlx-whisper, ffmpeg, say, a TTS key) is missing."""


def recordings_dir(mock_id):
    if not SAFE_NAME.match(mock_id or ""):
        raise ValueError("bad mock id")
    root = Path(os.getenv("NAILIT_RECORDINGS") or library.home() / "recordings").expanduser()
    path = root / mock_id
    path.mkdir(parents=True, exist_ok=True)
    return path


MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # about 50 minutes of opus audio, or one 10 s webcam chunk with lots of room


def save_upload(mock_id, name, data):
    if not SAFE_NAME.match(name):
        raise ValueError("bad file name")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("upload too large")
    path = recordings_dir(mock_id) / name
    path.write_bytes(data)
    return path


def words_result(result, duration_s):
    """Flatten mlx-whisper output into words with timestamps; nothing is filtered, fillers included."""
    words = [
        {"word": w["word"].strip(), "start": round(float(w["start"]), 2), "end": round(float(w["end"]), 2)}
        for segment in result.get("segments") or []
        for w in segment.get("words") or []
        if w.get("word", "").strip()
    ]
    text = " ".join(w["word"] for w in words) if words else (result.get("text") or "").strip()
    raw = [w for segment in result.get("segments") or [] for w in segment.get("words") or [] if w.get("word", "").strip()]
    estimated = bool(raw) and raw[0].get("estimated")  # only an estimated first word makes the start unknown
    filled = [w for w in words if re.sub(r"[^a-z]", "", w["word"].lower()) in FILLED_PAUSES]
    return {
        "text": text,
        "words": words,
        "language": result.get("language"),
        "duration_s": round(duration_s, 2),
        "first_word_s": None if not words or estimated else words[0]["start"],  # no invented pre-answer silence
        "speech_s": round(words[-1]["end"] - words[0]["start"], 2) if words else 0.0,
        "trailing_silence_s": round(max(0.0, duration_s - words[-1]["end"]), 2) if words else round(duration_s, 2),
        "filled_pauses": len(filled),
    }


def _load(path):
    try:
        from mlx_whisper.audio import load_audio
    except ImportError as error:
        raise VoiceUnavailable("mlx-whisper is not installed (Apple silicon only): uv sync --extra voice") from error
    if not shutil.which("ffmpeg"):
        raise VoiceUnavailable("ffmpeg is needed to decode audio: brew install ffmpeg")
    return load_audio(str(path))


def _looks_broken(words, seconds):
    """Whisper failure modes seen in testing: a repetition loop ("I, I, I, …") or most of the speech dropped."""
    tokens = [re.sub(r"[^a-z']", "", w["word"].lower()) for w in words]
    run = longest = 1
    for a, b in zip(tokens, tokens[1:]):
        run = run + 1 if a and a == b else 1
        longest = max(longest, run)
    too_sparse = seconds > 8 and len(words) / seconds < 0.9  # normal speech is about 2-3 words a second
    return longest >= 6 or too_sparse


def _words(audio, offset_s=0.0, model=None):
    import mlx_whisper
    if len(audio) < SAMPLE_RATE * 0.3:
        return []
    seconds = len(audio) / SAMPLE_RATE
    attempts = [{"initial_prompt": FILLER_PROMPT}, {"initial_prompt": None, "temperature": (0.0, 0.2, 0.4)}]
    best = None
    for options in attempts:
        result = mlx_whisper.transcribe(
            audio, path_or_hf_repo=model or os.getenv("NAILIT_WHISPER_MODEL") or WHISPER_MODEL,
            word_timestamps=True, condition_on_previous_text=False, **options)
        words = [{"word": w["word"].strip(), "start": round(float(w["start"]) + offset_s, 2),
                  "end": round(float(w["end"]) + offset_s, 2)}
                 for segment in result.get("segments") or [] for w in segment.get("words") or [] if w.get("word", "").strip()]
        text = (result.get("text") or "").split()
        if not words and text:  # recognised but not aligned: spread the words evenly so the answer isn't lost
            step = seconds / len(text)
            words = [{"word": w, "start": round(offset_s + i * step, 2), "end": round(offset_s + (i + 1) * step, 2),
                      "estimated": True} for i, w in enumerate(text)]
        if not _looks_broken(words, seconds):
            return words
        logger.info("transcript looked broken (%d words in %.1fs); retrying without the filler prompt", len(words), seconds)
        best = best if best and len(best) >= len(words) else words
    return best or []


def _quiet_cut(audio, lo_s, hi_s):
    """The quietest 50 ms point between lo_s and hi_s, so a chunk boundary never splits a word."""
    import numpy as np
    lo, hi, frame = int(lo_s * SAMPLE_RATE), int(hi_s * SAMPLE_RATE), int(0.05 * SAMPLE_RATE)
    if hi - lo < frame * 2:
        return hi_s
    window = np.asarray(audio[lo:hi], dtype="float32")
    energies = [float((window[i:i + frame] ** 2).mean()) for i in range(0, len(window) - frame, frame)]
    return lo_s + energies.index(min(energies)) * 0.05 + 0.025


# Incremental transcription while the candidate is still speaking: each take keeps the words already
# transcribed up to a quiet point, so when the answer ends only the last few seconds are left to do.
LIVE = {}
CHUNK_S, TAIL_KEEP_S = 8.0, 2.0


def live_update(mock_id, take, path):
    """Called by the live caption. Commits finished chunks; returns committed text plus a rough tail."""
    state = LIVE.get(mock_id)
    if not state or state["take"] != take:
        state = LIVE[mock_id] = {"take": take, "words": [], "committed_s": 0.0}
    audio = _load(path)
    duration = len(audio) / SAMPLE_RATE
    while duration - state["committed_s"] >= CHUNK_S + TAIL_KEEP_S:
        cut = _quiet_cut(audio, state["committed_s"] + CHUNK_S - 2.0, state["committed_s"] + CHUNK_S + 1.0)
        start = state["committed_s"]
        state["words"] += _words(audio[int(start * SAMPLE_RATE):int(cut * SAMPLE_RATE)], start)
        state["committed_s"] = cut
    tail = _words(audio[int(state["committed_s"] * SAMPLE_RATE):], state["committed_s"]) if duration - state["committed_s"] > 1.0 else []
    return " ".join(w["word"] for w in state["words"] + tail)


def transcribe(path, model=None, mock_id=None, take=None):
    """Whole-answer transcript with word timings. Reuses the chunks already done live for this take."""
    audio = _load(path)
    duration = len(audio) / SAMPLE_RATE
    state = LIVE.pop(mock_id, None) if mock_id else None
    if state and take and state["take"] == take and state["committed_s"] <= duration:
        start = state["committed_s"]
        words = state["words"] + _words(audio[int(start * SAMPLE_RATE):], start, model)
    else:
        words = _words(audio, 0.0, model)
    return words_result({"segments": [{"words": [{**w} for w in words]}]},
                        duration)




def _openai_tts(text, path):
    key = os.getenv("OPENAI_TTS_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        raise VoiceUnavailable("no OpenAI key for TTS (OPENAI_TTS_API_KEY or OPENAI_API_KEY)")
    from openai import OpenAI

    client = OpenAI(api_key=key, base_url=os.getenv("OPENAI_TTS_BASE_URL") or None)
    with client.audio.speech.with_streaming_response.create(
        model=os.getenv("NAILIT_TTS_MODEL") or OPENAI_TTS_MODEL,
        voice=os.getenv("NAILIT_TTS_VOICE") or "alloy",
        input=text,
        response_format="mp3",
    ) as response:
        response.stream_to_file(path)


def _say_tts(text, path):
    if sys.platform != "darwin" or not shutil.which("say"):
        raise VoiceUnavailable("macOS `say` is not available")
    command = ["say", "-o", str(path), "--file-format=WAVE", "--data-format=LEI16@22050"]
    if os.getenv("NAILIT_SAY_VOICE"):
        command += ["-v", os.environ["NAILIT_SAY_VOICE"]]
    subprocess.run(command + ["--", text], check=True, timeout=60, capture_output=True)


def speak(text, mock_id, name, engine=None):
    """Write the interviewer's line as audio. Returns (path or None, engine used); None means text only."""
    engine = engine or os.getenv("NAILIT_TTS") or "openai"
    if engine not in TTS_ENGINES:
        raise ValueError(f"unknown TTS engine {engine}")
    order = {"openai": ["openai", "say"], "say": ["say"], "none": []}[engine]
    for choice in order:
        path = recordings_dir(mock_id) / f"{name}.{'mp3' if choice == 'openai' else 'wav'}"
        try:
            (_openai_tts if choice == "openai" else _say_tts)(text, path)
            return path, choice
        except Exception as error:  # noqa: BLE001 - any TTS failure falls back to the next engine, then text
            logger.warning("TTS %s failed: %s", choice, error)
    return None, "none"


class Timer:
    def __init__(self):
        self.marks, self._t = {}, time.perf_counter()

    def mark(self, label):
        now = time.perf_counter()
        self.marks[label] = round(now - self._t, 3)
        self._t = now
