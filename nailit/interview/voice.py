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
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
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


def save_upload(mock_id, name, data):
    if not SAFE_NAME.match(name):
        raise ValueError("bad file name")
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
    filled = [w for w in words if re.sub(r"[^a-z]", "", w["word"].lower()) in FILLED_PAUSES]
    return {
        "text": text,
        "words": words,
        "language": result.get("language"),
        "duration_s": round(duration_s, 2),
        "first_word_s": words[0]["start"] if words else None,
        "speech_s": round(words[-1]["end"] - words[0]["start"], 2) if words else 0.0,
        "trailing_silence_s": round(max(0.0, duration_s - words[-1]["end"]), 2) if words else round(duration_s, 2),
        "filled_pauses": len(filled),
    }


def transcribe(path, model=None):
    try:
        import mlx_whisper
        from mlx_whisper.audio import load_audio
    except ImportError as error:
        raise VoiceUnavailable("mlx-whisper is not installed (Apple silicon only): uv sync --extra voice") from error
    if not shutil.which("ffmpeg"):
        raise VoiceUnavailable("ffmpeg is needed to decode audio: brew install ffmpeg")
    audio = load_audio(str(path))
    result = mlx_whisper.transcribe(
        audio,
        path_or_hf_repo=model or os.getenv("NAILIT_WHISPER_MODEL") or WHISPER_MODEL,
        word_timestamps=True,
        initial_prompt=FILLER_PROMPT,
        condition_on_previous_text=False,
    )
    return words_result(result, len(audio) / SAMPLE_RATE)


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
