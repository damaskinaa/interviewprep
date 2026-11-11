"""VOX: delivery metrics from word timestamps and, when there is audio, pitch and loudness (praat-parselmouth).

`measure_answer()` returns {metric_name: value} using the metric names detectors.yaml refers to, plus
`baselines` ({metric_name: calm value}) so a rule like "> baseline * 1.2" can be evaluated, and the
details the debrief shows (result sentences with their final pitch slope, pauses, filled pauses).
All times are seconds on the answer recording's clock; a metric that cannot be measured is None.
"""
import logging
import math
import re
import shutil
import statistics
import subprocess
import tempfile
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)
FILLED_PAUSES = {"um", "umm", "uh", "uhh", "er", "erm", "hmm", "mm", "ah"}
NUMBER_WORDS = ("one two three four five six seven eight nine ten eleven twelve fifteen twenty thirty forty fifty "
                "sixty seventy eighty ninety hundred thousand million billion percent half double twice triple")
CLAIM = re.compile(r"\d|%|\b(" + "|".join(NUMBER_WORDS.split()) + r")\b", re.I)
SENTENCE_END = re.compile(r"[.?!]$")
BEHAVIOURAL_TYPES = {"behavioural", "failure"}
TMAY_TYPES = {"opening"}
PAUSE_S = 0.5            # "rush" = a stretch with no pause longer than this
SLOPE_TAIL_S = 0.6       # final pitch slope is fitted over the last 0.6 s of a sentence
SLOPE_FLAT_ST_S = 1.5    # |slope| below this (semitones per second) counts as flat


def _bare(word):
    return re.sub(r"[^\w%']", "", word.lower())


def _content(words):
    return [w for w in words if _bare(w["word"]) and _bare(w["word"]) not in FILLED_PAUSES]


def sentences(words):
    """Group words into sentences on . ? ! (Whisper keeps punctuation on the word)."""
    out, current = [], []
    for w in words:
        current.append(w)
        if SENTENCE_END.search(w["word"].strip()):
            out.append(current)
            current = []
    if current:
        out.append(current)
    return [{"text": " ".join(w["word"].strip() for w in s), "start": s[0]["start"], "end": s[-1]["end"], "words": s}
            for s in out]


def is_result_sentence(text):
    """A RESULT sentence carries a number or a claim word (percent, double, ...)."""
    return bool(CLAIM.search(text))


def filled_pauses(words):
    return sum(1 for w in words if _bare(w["word"]) in FILLED_PAUSES)


def answer_seconds(words):
    return round(words[-1]["end"] - words[0]["start"], 2) if words else None


def wpm(words):
    content, span = _content(words), answer_seconds(words)
    return round(len(content) / span * 60, 1) if content and span else None


def wpm_by_10s(words, bin_s=10.0):
    """Words per minute in consecutive 10 s windows; a final window shorter than 5 s is dropped."""
    if not words:
        return []
    start, end = words[0]["start"], words[-1]["end"]
    rates, t = [], start
    while t < end:
        width = min(bin_s, end - t)
        if width < bin_s / 2:
            break
        count = sum(1 for w in _content(words) if t <= w["start"] < t + width)
        rates.append(count / width * 60)
        t += bin_s
    return [round(r, 1) for r in rates]


def gaps(words):
    """(time, length) of the silence after each word."""
    return [(words[i]["end"], round(words[i + 1]["start"] - words[i]["end"], 2)) for i in range(len(words) - 1)]


def pauses(words, min_s=0.25):
    return [{"at": at, "s": s} for at, s in gaps(words) if s >= min_s]


def longest_stretch_without_pause(words, pause_s=PAUSE_S):
    if not words:
        return None
    longest, stretch_start = 0.0, words[0]["start"]
    for i in range(len(words) - 1):
        if words[i + 1]["start"] - words[i]["end"] > pause_s:
            longest = max(longest, words[i]["end"] - stretch_start)
            stretch_start = words[i + 1]["start"]
    return round(max(longest, words[-1]["end"] - stretch_start), 2)


def pause_after_number_sentences(words):
    """The silence after every RESULT sentence that is followed by more speech."""
    sents = sentences(words)
    return [round(sents[i + 1]["start"] - s["end"], 2) for i, s in enumerate(sents[:-1]) if is_result_sentence(s["text"])]


def _norm(text):
    return " ".join(_bare(t) for t in text.split() if _bare(t))


def is_answering(text, bridges=()):
    """Not a buying-time line: at least 4 content words and not one of the library's bridge phrases."""
    norm = _norm(text)
    content = [t for t in norm.split() if t not in FILLED_PAUSES]
    if len(content) < 4:
        return False
    return not any(_norm(b) and (_norm(b) in norm or norm in _norm(b)) for b in bridges)


def seconds_to_first_answering_sentence(words, bridges=(), start_s=0.0):
    for s in sentences(words):
        if is_answering(s["text"], bridges):
            return round(s["start"] - start_s, 2)
    return None


def distinct_facts_per_minute(words):
    """Distinct numbers/claim tokens per minute of speech (N4c refines this against stories.md facts)."""
    span = answer_seconds(words)
    facts = {_bare(w["word"]) for w in words if CLAIM.search(w["word"])}
    return round(len(facts) / span * 60, 2) if span else None


# ---- timers (barge-in, silences, freeze, recall) ----

def speech_segments(samples, sample_rate, frame_s=0.02, floor_db=-30.0, min_gap_s=0.25, min_len_s=0.1):
    """Energy-based speech segments [(start, end)] from raw audio, for timers when words are missing."""
    samples = np.asarray(samples, dtype=np.float64)
    hop = max(1, int(frame_s * sample_rate))
    frames = len(samples) // hop
    if not frames:
        return []
    rms = np.sqrt(np.mean(samples[: frames * hop].reshape(frames, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    noise = np.percentile(db, 10)
    voiced = db > max(db.max() + floor_db, noise + 10.0)  # relative to the peak and above the room's noise floor
    segments, start = [], None
    for i, on in enumerate(voiced):
        if on and start is None:
            start = i
        elif not on and start is not None:
            segments.append([start * frame_s, i * frame_s])
            start = None
    if start is not None:
        segments.append([start * frame_s, frames * frame_s])
    merged = []
    for seg in segments:
        if merged and seg[0] - merged[-1][1] < min_gap_s:
            merged[-1][1] = seg[1]
        else:
            merged.append(seg)
    return [(round(a, 2), round(b, 2)) for a, b in merged if b - a >= min_len_s]


def speech_after(t, words=None, segments=None):
    """When speech (not a filled pause) next starts at or after t: from words if given, else audio segments."""
    if words:
        starts = [w["start"] for w in _content(words) if w["start"] >= t - 0.05]
    else:
        starts = [a for a, _ in segments or [] if a >= t - 0.05]
    return min(starts) if starts else None


def _since(t, words, segments):
    if t is None:
        return None
    resumed = speech_after(t, words, segments)
    return None if resumed is None else round(max(0.0, resumed - t), 2)


def overlap_user_over_tts_s(tts_end_s, words=None, segments=None, tts_start_s=0.0):
    """Barge-in: how long you spoke over the interviewer's audio (0 if you waited); onsets before it began don't count."""
    if tts_end_s is None:
        return None
    first = speech_after(tts_start_s or 0.0, words, segments)
    return None if first is None else round(max(0.0, tts_end_s - max(first, tts_start_s or 0.0)), 2)


# ---- audio: pitch and loudness ----

def load_sound(path):
    """A parselmouth Sound; formats Praat can't read (webm, mp4) go through ffmpeg first."""
    import parselmouth
    try:
        return parselmouth.Sound(str(path))
    except parselmouth.PraatError:
        if not shutil.which("ffmpeg"):
            raise
        with tempfile.TemporaryDirectory() as folder:
            wav = Path(folder) / "a.wav"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", "16000", str(wav)],
                           check=True, timeout=120)
            return parselmouth.Sound(str(wav))


def as_sound(audio, sample_rate=16000):
    if audio is None:
        return None
    if isinstance(audio, (str, Path)):
        return load_sound(audio)
    if hasattr(audio, "to_pitch"):
        return audio
    import parselmouth
    return parselmouth.Sound(np.asarray(audio, dtype=np.float64), sampling_frequency=sample_rate)


def pitch_track(sound):
    """(times, semitones re 100 Hz) of voiced frames."""
    pitch = sound.to_pitch(time_step=0.01, pitch_floor=75.0, pitch_ceiling=500.0)
    f0 = pitch.selected_array["frequency"]
    times = pitch.xs()
    voiced = f0 > 0
    return times[voiced], 12 * np.log2(f0[voiced] / 100.0)


def final_slope(track, start, end, tail_s=SLOPE_TAIL_S):
    """Least-squares pitch slope (semitones/second) over the last `tail_s` of [start, end]."""
    times, st = track
    mask = (times >= max(start, end - tail_s)) & (times <= end)
    if mask.sum() < 5:
        return None
    return round(float(np.polyfit(times[mask], st[mask], 1)[0]), 2)


def contour(slope):
    if slope is None:
        return None
    return "rising" if slope > SLOPE_FLAT_ST_S else "falling" if slope < -SLOPE_FLAT_ST_S else "flat"


def pitch_range_st(track):
    _, st = track
    return round(float(np.percentile(st, 90) - np.percentile(st, 10)), 2) if len(st) >= 10 else None


def loudness_var_db(sound):
    values = sound.to_intensity(minimum_pitch=75.0).values.flatten()
    values = values[values > values.max() - 30]
    return round(float(np.std(values)), 2) if len(values) >= 10 else None


def baseline_from(words, audio=None, sample_rate=16000):
    """Calm baseline from a relaxed recording: wpm, pitch range and loudness variation."""
    sound = as_sound(audio, sample_rate)
    track = pitch_track(sound) if sound is not None else None
    return {"wpm": wpm(words),
            "pitch_range_st": pitch_range_st(track) if track is not None else None,
            "loudness_var_db": loudness_var_db(sound) if sound is not None else None}


def _ratio(value, base):
    return value / base if value is not None and base else None


def measure_answer(words, audio=None, sample_rate=16000, baseline=None, question_type=None,
                   pre_answer_silence_s=None, bridges=(), events=None):
    """All N4 delivery metrics for one answer. `events` (answer-clock seconds, all optional):
    tts_start_s / tts_end_s (interviewer audio playing), silence_start_s (interviewer went deliberately quiet),
    freeze_cue_s, trigger_s (flash-card shown)."""
    baseline, events = baseline or {}, events or {}
    try:
        sound = as_sound(audio, sample_rate)
    except Exception as error:  # unreadable audio: keep the timestamp metrics
        logger.warning("audio not measured: %s", error)
        sound = None
    track = pitch_track(sound) if sound is not None else None
    segments = speech_segments(sound.values[0], sound.sampling_frequency) if sound is not None else None
    timer_words = words or None
    result_sentences = []
    for s in sentences(words):
        if is_result_sentence(s["text"]):
            slope = final_slope(track, s["start"], s["end"]) if track is not None else None
            result_sentences.append({"text": s["text"], "start": s["start"], "end": s["end"],
                                     "slope_st_s": slope, "contour": contour(slope)})
    slopes = [r["slope_st_s"] for r in result_sentences if r["slope_st_s"] is not None]
    after_numbers = pause_after_number_sentences(words)
    rates = wpm_by_10s(words)
    length = answer_seconds(words)
    energy = None
    if track is not None:
        ratios = [r for r in (_ratio(pitch_range_st(track), baseline.get("pitch_range_st")),
                              _ratio(loudness_var_db(sound), baseline.get("loudness_var_db"))) if r is not None]
        energy = round(math.prod(ratios) ** (1 / len(ratios)), 2) if ratios else None
    metrics = {
        "wpm_vs_baseline": wpm(words),
        "wpm_stddev_by_10s": round(statistics.pstdev(rates), 1) if len(rates) >= 2 else None,
        "final_pitch_slope_result_sentences": round(statistics.mean(slopes), 2) if slopes else None,
        "pitch_range_and_loudness_var_vs_baseline": energy,
        "pause_after_number_sentence_s": round(min(after_numbers), 2) if after_numbers else None,
        "longest_stretch_without_pause_gt_0_5s": longest_stretch_without_pause(words),
        "pre_answer_silence_s": pre_answer_silence_s,
        "seconds_to_first_answering_sentence": seconds_to_first_answering_sentence(words, bridges),
        "answer_seconds": length,
        "answer_seconds_tmay": length if question_type in TMAY_TYPES else None,
        "answer_seconds_behavioural": length if question_type in BEHAVIOURAL_TYPES else None,
        "overlap_user_over_tts_s": overlap_user_over_tts_s(events.get("tts_end_s"), timer_words, segments,
                                                           events.get("tts_start_s", 0.0)),
        "gap_after_interviewer_silence_s": _since(events.get("silence_start_s"), timer_words, segments),
        "freeze_recovery_s": _since(events.get("freeze_cue_s"), timer_words, segments),
        "trigger_recall_s": _since(events.get("trigger_s"), timer_words, segments),
        "distinct_facts_per_minute": distinct_facts_per_minute(words),
    }
    return {
        "metrics": metrics,
        # Rules say "baseline * 1.2": the calm value for a metric. The energy metric is already a ratio to calm.
        "baselines": {"wpm_vs_baseline": baseline.get("wpm"), "pitch_range_and_loudness_var_vs_baseline": 1.0},
        "result_sentences": result_sentences,
        "pauses": pauses(words),
        "filled_pauses": filled_pauses(words),
        "speech_segments": segments,
    }
