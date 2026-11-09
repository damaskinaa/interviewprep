"""Pipecat voice loop for a mock: browser mic over a localhost websocket → turn gate (push-to-talk or Silero VAD)
→ local Whisper (fillers kept) → interviewer engine (fast LLM) → Kokoro / `say` → browser speaker.

Wire format: binary messages are 16-bit mono PCM (16 kHz in, 24 kHz out); text messages are JSON events.
"""
import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    EndFrame,
    ErrorFrame,
    InputAudioRawFrame,
    InputTransportMessageFrame,
    InterruptionFrame,
    OutputAudioRawFrame,
    OutputTransportMessageFrame,
    OutputTransportMessageUrgentFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
    TTSSpeakFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.serializers.base_serializer import FrameSerializer
from pipecat.services.settings import STTSettings, TTSSettings
from pipecat.services.stt_service import SegmentedSTTService
from pipecat.services.tts_service import TTSService

from nailit import llm
from nailit.interview import interviewer, voice
from nailit.store import log_voice, save_mock

logger = logging.getLogger(__name__)

IN_RATE, OUT_RATE = 16000, 24000
TRAILING_PAD_S = 0.5


@dataclass
class Turn:
    """Clock shared by the gate and the interviewer processor (time.monotonic seconds). The bot counts as speaking
    until the page reports its playback ended, since the server sends audio faster than real time."""
    input: str = "ptt"
    bot_speaking: bool = False
    bot_stopped_at: float | None = None
    user_started_at: float | None = None
    user_stopped_at: float | None = None
    limit_s: float | None = None
    segment: int = 0
    marks: dict = field(default_factory=dict)


def message(payload, urgent=True):
    return (OutputTransportMessageUrgentFrame if urgent else OutputTransportMessageFrame)(message=payload)


class PcmJsonSerializer(FrameSerializer):
    async def serialize(self, frame):
        if isinstance(frame, OutputAudioRawFrame):
            return frame.audio
        if isinstance(frame, (OutputTransportMessageFrame, OutputTransportMessageUrgentFrame)):
            return json.dumps(frame.message)
        if isinstance(frame, InterruptionFrame):
            return json.dumps({"type": "clear"})
        return None

    async def deserialize(self, data):
        if isinstance(data, bytes):
            return InputAudioRawFrame(audio=data, sample_rate=IN_RATE, num_channels=1)
        try:
            return InputTransportMessageFrame(message=json.loads(data))
        except ValueError:
            return None


class TurnGate(FrameProcessor):
    """Turns push-to-talk key events (or Silero VAD) into speech segments, handles barge-in and the interviewer's
    interrupt / 90-s cut-off timers."""

    def __init__(self, turn, **kwargs):
        super().__init__(**kwargs)
        self.turn, self._timer = turn, None

    async def _start(self):
        self.turn.user_started_at, self.turn.segment = time.monotonic(), self.turn.segment + 1
        if self.turn.bot_speaking:
            await self.broadcast_interruption()
        if self.turn.limit_s:
            self._timer = self.create_task(self._cut(self.turn.segment, self.turn.limit_s))
        await self.push_frame(VADUserStartedSpeakingFrame())

    async def _stop(self, reason="end"):
        if self._timer:
            await self.cancel_task(self._timer)
            self._timer = None
        self.turn.user_stopped_at = time.monotonic()
        self.turn.limit_s = None
        await self.push_frame(VADUserStoppedSpeakingFrame())
        await self.push_frame(message({"type": "listening", "on": False, "reason": reason}))

    async def _cut(self, segment, limit_s):
        await asyncio.sleep(limit_s)
        if segment == self.turn.segment and self.turn.user_stopped_at < self.turn.user_started_at:
            self._timer = None
            await self._stop("cut")

    def _speaking(self):
        return self.turn.user_started_at and (self.turn.user_stopped_at or 0) < self.turn.user_started_at

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if isinstance(frame, InputTransportMessageFrame) and frame.message.get("type") == "ptt":
            if self.turn.input == "ptt":
                down = bool(frame.message.get("down"))
                if down and not self._speaking():
                    await self._start()
                elif not down and self._speaking():
                    await self._stop()
            return
        if isinstance(frame, InputTransportMessageFrame) and frame.message.get("type") == "played":
            self.turn.bot_speaking, self.turn.bot_stopped_at = False, time.monotonic()
            return
        if isinstance(frame, VADUserStartedSpeakingFrame):
            if self.turn.input == "vad" and not self._speaking():
                await self._start()
            return
        if isinstance(frame, VADUserStoppedSpeakingFrame):
            if self.turn.input == "vad" and self._speaking():
                await self._stop()
            return
        if isinstance(frame, BotStartedSpeakingFrame):
            self.turn.bot_speaking = True
        await self.push_frame(frame, direction)


class LocalWhisperSTT(SegmentedSTTService):
    """mlx-whisper on each segment: word timestamps, fillers kept; each answer is saved as WAV."""

    def __init__(self, mock_id, **kwargs):
        super().__init__(sample_rate=IN_RATE, trailing_silence_secs=TRAILING_PAD_S,
                         settings=STTSettings(model=None, language=None), **kwargs)
        self.mock_id, self.count = mock_id, 0

    async def run_stt(self, audio):
        self.count += 1
        name = f"answer_{self.count:03d}_{int(time.time())}.wav"
        path = voice.save_upload(self.mock_id, name, audio)
        try:
            result = await asyncio.to_thread(voice.transcribe, path)
        except voice.VoiceUnavailable as error:
            yield ErrorFrame(error=str(error))
            return
        if result["text"]:
            yield TranscriptionFrame(text=result["text"], user_id="me", timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
                                     result={**result, "audio": name})


class KokoroTTS(TTSService):
    """Kokoro-82M through mlx-audio; falls back to macOS `say` if Kokoro can't run."""

    def __init__(self, engine="kokoro", **kwargs):
        super().__init__(push_start_frame=True, push_stop_frames=True, sample_rate=OUT_RATE,
                         settings=TTSSettings(model=None, voice=None, language=None), **kwargs)
        self.engine = engine

    def can_generate_metrics(self):
        return True

    async def run_tts(self, text, context_id):
        chunks = None
        if self.engine == "kokoro":
            try:
                chunks = await asyncio.to_thread(lambda: list(voice.kokoro_pcm(text)))
            except Exception as error:
                logger.warning("Kokoro failed, using say: %s", error)
                self.engine = "say"
        if chunks is None:
            try:
                chunks = [(await asyncio.to_thread(voice.say_pcm, text, OUT_RATE), OUT_RATE)]
            except Exception as error:
                yield ErrorFrame(error=f"no TTS available ({error}); the line is shown as text")
                return
        for pcm, rate in chunks:
            if rate != OUT_RATE:
                pcm = await self._resampler.resample(pcm, rate, OUT_RATE)
            yield TTSAudioRawFrame(audio=pcm, sample_rate=OUT_RATE, num_channels=1, context_id=context_id)


class InterviewerProcessor(FrameProcessor):
    """Feeds each transcribed answer to the interviewer engine, speaks the reply after its scripted silence,
    and logs STT, LLM (time to first token), TTS and end-to-end latency per turn."""

    def __init__(self, state, lib, turn, engine, **kwargs):
        super().__init__(**kwargs)
        self.state, self.lib, self.turn, self.engine = state, lib, turn, engine
        self.pending, self.worker = None, None

    async def _end(self):
        if self.worker:
            await self.worker.queue_frame(EndFrame())

    async def _speak(self, kind="turn", extra=None):
        say = self.state["turns"][-1]
        self.turn.marks["tts_requested_at"] = time.monotonic()
        await self.push_frame(message({"type": kind, "interviewer": say["say"], "event": say.get("event"),
                                       "done": self.state["phase"] == "done", **(extra or {})}))
        if say.get("silence_before_s"):
            await asyncio.sleep(say["silence_before_s"])
            self.turn.marks["tts_requested_at"] = time.monotonic()
        self.turn.limit_s = say.get("interrupt_after_s") or say.get("cut_off_s")
        await self.push_frame(TTSSpeakFrame(text=say["say"], append_to_context=False))

    async def _answer(self, text, result):
        got_at = time.monotonic()
        stopped = self.turn.user_stopped_at
        words = (result or {}).get("words") or []
        last_word_at = stopped - (result["duration_s"] - TRAILING_PAD_S - words[-1]["end"]) if words and stopped else got_at
        silence = None
        if result and self.turn.bot_stopped_at and self.turn.user_started_at:
            silence = round(max(0.0, self.turn.user_started_at - self.turn.bot_stopped_at), 2)
        seconds = result["speech_s"] if result else None

        def run():
            timing = llm.stream_timing()
            turn = interviewer.answer(self.state, text, seconds, silence, lib=self.lib)
            return turn, timing
        try:
            _, timing = await asyncio.to_thread(run)
        except ValueError as error:
            await self.push_frame(message({"type": "error", "error": str(error)}))
            return
        candidate = next(t for t in reversed(self.state["turns"]) if t.get("role") == "candidate")
        if result:
            candidate.update(audio=result["audio"], words=words, filled_pauses=result["filled_pauses"])
        save_mock(self.state)
        self.pending = {"turn": len(self.state["turns"]) - 1, "last_word_at": last_word_at,
                        "stt_s": round(got_at - stopped, 3) if result and stopped else None,
                        "llm_ttft_s": timing.get("ttft_s"), "llm_s": round(time.monotonic() - got_at, 3)}
        await self._speak(extra={"candidate": text, "filled_pauses": (result or {}).get("filled_pauses")})

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame):
            await self._answer(frame.text, frame.result)
            return
        if isinstance(frame, InputTransportMessageFrame):
            kind = frame.message.get("type")
            if kind == "ready":
                await self._speak("question")
            elif kind == "text" and (frame.message.get("text") or "").strip():
                await self._answer(frame.message["text"].strip(), None)
            elif kind == "end":
                await self._end()
            elif kind == "input" and frame.message.get("mode") in ("ptt", "vad", "text"):
                self.turn.input = frame.message["mode"]
            return
        if isinstance(frame, BotStartedSpeakingFrame) and self.pending:
            now, p = time.monotonic(), self.pending
            self.pending = None
            row = {"stt_s": p["stt_s"], "llm_ttft_s": p["llm_ttft_s"], "llm_s": p["llm_s"],
                   "tts_s": round(now - self.turn.marks["tts_requested_at"], 3),
                   "latency_s": round(now - p["last_word_at"], 3)}
            log_voice(self.state["id"], p["turn"], engine=self.engine, **row)
            await self.push_frame(message({"type": "latency", **row}))
        if isinstance(frame, BotStoppedSpeakingFrame) and self.state["phase"] == "done":
            await self.push_frame(message({"type": "done"}))
            await self._end()
        await self.push_frame(frame, direction)


def settings():
    return {
        "input": os.getenv("NAILIT_VOICE_INPUT") or "ptt",
        "tts": os.getenv("NAILIT_TTS") or "kokoro",
        "vad_stop_s": float(os.getenv("NAILIT_VAD_STOP_S") or 1.5),
    }


async def run(websocket, state, lib, input_mode=None, stt=None, tts=None, vad=None):
    """Run one mock's voice session on an accepted FastAPI websocket until the mock ends or the page closes."""
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.worker import PipelineParams, PipelineWorker
    from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport

    config = settings()
    turn = Turn(input=input_mode or config["input"])
    transport = FastAPIWebsocketTransport(websocket, FastAPIWebsocketParams(
        audio_in_enabled=True, audio_in_sample_rate=IN_RATE, audio_out_enabled=True, audio_out_sample_rate=OUT_RATE,
        serializer=PcmJsonSerializer()))
    if vad is None:
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        from pipecat.audio.vad.vad_analyzer import VADParams
        from pipecat.processors.audio.vad_processor import VADProcessor
        vad = VADProcessor(vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=config["vad_stop_s"])))
    tts = tts or KokoroTTS(config["tts"])
    brain = InterviewerProcessor(state, lib, turn, getattr(tts, "engine", config["tts"]))
    steps = [transport.input(), vad, TurnGate(turn), stt or LocalWhisperSTT(state["id"]), brain, tts, transport.output()]
    task = PipelineWorker(Pipeline([s for s in steps if s is not None]), idle_timeout_secs=None, params=PipelineParams(
        audio_in_sample_rate=IN_RATE, audio_out_sample_rate=OUT_RATE, enable_metrics=True))
    brain.worker = task

    @transport.event_handler("on_client_disconnected")
    async def _closed(_transport, _client):
        await task.cancel()

    try:
        await PipelineRunner(handle_sigint=False).run(task)
    except asyncio.CancelledError:
        # The page closing cancels the pipeline; only re-raise if this request itself is being cancelled.
        if asyncio.current_task().cancelling():
            raise
