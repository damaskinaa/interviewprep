"""Local voice helpers for the Pipecat loop (nailit/interview/pipeline.py): recordings under
~/NailIt/recordings/<mock_id>/, mlx-whisper transcription (word timestamps, fillers kept), Kokoro-82M via mlx-audio,
and macOS `say` as the fallback TTS.
"""
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

from nailit import library

logger = logging.getLogger("nailit.voice")

SAMPLE_RATE = 16000
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
# Whisper drops disfluencies unless the prompt shows them; this prompt makes it transcribe them verbatim.
FILLER_PROMPT = "Um, so, uh, I mean, like, we, um, we kind of, uh, started with the, like, the first step."
FILLED_PAUSES = {"um", "umm", "uh", "uhh", "er", "erm", "ah", "hmm", "mm"}
TTS_ENGINES = ("kokoro", "say")
KOKORO_MODEL = "prince-canuma/Kokoro-82M"
_KOKORO = None
SAFE_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$")


class VoiceUnavailable(RuntimeError):
    """Raised when a voice dependency (mlx-whisper, mlx-audio, ffmpeg, say) is missing."""


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


def say_pcm(text, sample_rate=24000):
    """macOS `say` as 16-bit mono PCM at sample_rate (the free, offline TTS fallback)."""
    if sys.platform != "darwin" or not shutil.which("say"):
        raise VoiceUnavailable("macOS `say` is not available")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "say.wav"
        command = ["say", "-o", str(path), "--file-format=WAVE", f"--data-format=LEI16@{sample_rate}"]
        if os.getenv("NAILIT_SAY_VOICE"):
            command += ["-v", os.environ["NAILIT_SAY_VOICE"]]
        subprocess.run(command + ["--", text], check=True, timeout=60, capture_output=True)
        with wave.open(str(path)) as wav:
            return wav.readframes(wav.getnframes())


def kokoro_model():
    """Kokoro-82M through mlx-audio (Apple silicon), loaded once."""
    global _KOKORO
    if _KOKORO is None:
        try:
            from mlx_audio.tts.utils import load_model
        except ImportError as error:
            raise VoiceUnavailable("mlx-audio is not installed (Apple silicon only): uv sync --extra voice") from error
        _KOKORO = load_model(os.getenv("NAILIT_KOKORO_MODEL") or KOKORO_MODEL)
    return _KOKORO


def kokoro_pcm(text):
    """Yield (16-bit PCM bytes, sample_rate) per sentence chunk, so playback starts before the whole line is done."""
    import numpy as np
    model = kokoro_model()
    for result in model.generate(text=text, voice=os.getenv("NAILIT_KOKORO_VOICE") or "af_heart",
                                 speed=float(os.getenv("NAILIT_KOKORO_SPEED") or 1.0), lang_code="a",
                                 split_pattern=r"(?<=[.!?])\s+"):
        audio = np.clip(np.asarray(result.audio, dtype=np.float32), -1, 1)
        yield (audio * 32767).astype(np.int16).tobytes(), result.sample_rate
