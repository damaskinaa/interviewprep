"""N4a VOX metrics. E9 (rising vs falling result sentences) and E10 (timers within ±0.3 s) use synthetic audio."""
import unittest

import numpy as np

from nailit.measure import vox

SR = 16000


def _words(text, start, step=0.3, length=0.25):
    return [{"word": w, "start": round(start + i * step, 2), "end": round(start + i * step + length, 2)}
            for i, w in enumerate(text.split())]


def _voice(f0, sr=SR):
    """A voiced, harmonic signal following the f0 contour (Hz per sample)."""
    phase = 2 * np.pi * np.cumsum(f0) / sr
    return sum(np.sin(k * phase) / k for k in range(1, 6)) * 0.2


def _labelled_result_sentences(n=20, seed=7):
    """n sentences, each ending in a 0.6 s pitch glide of ±3-6 semitones; returns audio, words, labels."""
    rng = np.random.default_rng(seed)
    audio, words, labels, t = [], [], [], 0.0
    for i in range(n):
        label = "rising" if i % 2 else "falling"
        base = rng.uniform(110, 230)
        glide = rng.uniform(3, 6) * (1 if label == "rising" else -1)
        body, tail = rng.uniform(1.2, 2.0), 0.6
        steady = base * (1 + 0.01 * np.sin(np.linspace(0, 6 * np.pi, int(body * SR))))
        f0 = np.concatenate([steady, base * 2 ** (np.linspace(0, glide, int(tail * SR)) / 12)])
        audio += [_voice(f0) + rng.normal(0, 0.003, len(f0)), np.zeros(int(0.4 * SR))]
        span = body + tail
        sentence = f"we grew revenue by {10 + i} percent."
        step = span / len(sentence.split())
        words += _words(sentence, t, step=step, length=step * 0.9)
        words[-1]["end"] = round(t + span, 2)
        labels.append(label)
        t += span + 0.4
    return np.concatenate(audio), words, labels


class TimestampMetricsTest(unittest.TestCase):
    def test_pace_pauses_and_lengths(self):
        words = (_words("Um, I cut the queue by 40 percent.", 0.0) + _words("Then I trained the team.", 3.5)
                 + _words("That took about three weeks.", 6.0))
        m = vox.measure_answer(words, question_type="behavioural", pre_answer_silence_s=1.8)["metrics"]
        self.assertEqual(m["answer_seconds"], 7.45)
        self.assertEqual(m["answer_seconds_behavioural"], 7.45)
        self.assertIsNone(m["answer_seconds_tmay"])
        self.assertEqual(m["pause_after_number_sentence_s"], 1.15)
        self.assertEqual(m["longest_stretch_without_pause_gt_0_5s"], 2.35)
        self.assertEqual(m["wpm_vs_baseline"], round(17 / 7.45 * 60, 1))
        self.assertEqual(m["pre_answer_silence_s"], 1.8)
        self.assertEqual(vox.filled_pauses(words), 1)

    def test_rush_and_pace_stability(self):
        steady = _words(" ".join(["word"] * 100), 0.0, step=0.25, length=0.2)
        self.assertEqual(vox.longest_stretch_without_pause(steady), 24.95)
        self.assertEqual(vox.measure_answer(steady)["metrics"]["wpm_stddev_by_10s"], 0.0)
        uneven = _words(" ".join(["word"] * 20), 0.0, step=0.5) + _words(" ".join(["word"] * 50), 10.0, step=0.2)
        self.assertGreater(vox.measure_answer(uneven)["metrics"]["wpm_stddev_by_10s"], 50)

    def test_first_answering_sentence_skips_bridges_and_fillers(self):
        words = _words("Um. That's a great question.", 0.5) + _words("I rebuilt the escalation process last year.", 3.0)
        got = vox.seconds_to_first_answering_sentence(words, bridges=["That's a great question"])
        self.assertEqual(got, 3.0)

    def test_bridge_and_answer_in_one_sentence(self):
        words = _words("Good question, I rebuilt the escalation process last year.", 1.0)
        self.assertEqual(vox.seconds_to_first_answering_sentence(words, bridges=["Good question"]), 1.6)

    def test_shortened_and_repeated_bridges_are_not_answers(self):
        bridge = ["Let me take a moment to think about that"]
        self.assertFalse(vox.is_answering("Let me take a moment.", bridge))
        self.assertFalse(vox.is_answering("Let me take a moment to think about that, let me take a moment.", bridge))
        self.assertTrue(vox.is_answering("Let me take a moment. I would start with the data.", bridge))
        self.assertTrue(vox.is_answering("That's a great performance improvement.", ["That's a great question"]))
        self.assertFalse(vox.is_answering("Let me take a moment, let me take a moment.", bridge))

    def test_tmay_and_facts_per_minute(self):
        words = _words("I run ops for 12 markets and 3 teams.", 0.0, step=1.0)
        m = vox.measure_answer(words, question_type="opening")["metrics"]
        self.assertEqual(m["answer_seconds_tmay"], m["answer_seconds"])
        self.assertEqual(m["distinct_facts_per_minute"], round(2 / m["answer_seconds"] * 60, 2))


class PitchTest(unittest.TestCase):
    def test_e9_rising_vs_falling_result_sentences(self):
        audio, words, labels = _labelled_result_sentences()
        result = vox.measure_answer(words, audio=audio, sample_rate=SR)
        got = [r["contour"] for r in result["result_sentences"]]
        self.assertEqual(len(got), len(labels))
        accuracy = sum(g == want for g, want in zip(got, labels)) / len(labels)
        self.assertGreaterEqual(accuracy, 0.9, list(zip(got, labels)))

    def test_flat_voice_is_low_energy_vs_baseline(self):
        t = np.arange(int(4 * SR)) / SR
        lively = _voice(150 * 2 ** (6 * np.sin(2 * np.pi * 0.7 * t) / 12)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.5 * t))
        flat = _voice(np.full(len(t), 150.0)) * 0.8
        words = _words(" ".join(["word"] * 12), 0.0)
        baseline = vox.baseline_from(words, lively, SR)
        energy = vox.measure_answer(words, audio=flat, baseline=baseline)["metrics"]["pitch_range_and_loudness_var_vs_baseline"]
        self.assertLess(energy, 0.5)
        self.assertEqual(vox.measure_answer(words, audio=lively, baseline=baseline)["metrics"]
                         ["pitch_range_and_loudness_var_vs_baseline"], 1.0)


class TimerTest(unittest.TestCase):
    """E10: timers from audio onsets (no transcript) land within ±0.3 s of the truth."""

    def _bursts(self, spans, total_s):
        audio = np.zeros(int(total_s * SR))
        for start, end in spans:
            a, b = int(start * SR), int(end * SR)
            audio[a:b] = _voice(np.full(b - a, 140.0))
        return audio + np.random.default_rng(1).normal(0, 0.002, len(audio))

    def test_e10_freeze_recall_barge_in_and_silence_gap(self):
        cases = [
            ("freeze_cue_s", 5.0, [(0.5, 4.8), (7.3, 10.0)], "freeze_recovery_s", 2.3),
            ("trigger_s", 0.0, [(1.7, 4.0)], "trigger_recall_s", 1.7),
            ("tts_end_s", 2.0, [(1.2, 5.0)], "overlap_user_over_tts_s", 0.8),
            ("silence_start_s", 6.0, [(0.3, 5.9), (8.6, 11.0)], "gap_after_interviewer_silence_s", 2.6),
        ]
        for event, at, spans, metric, truth in cases:
            with self.subTest(metric=metric):
                audio = self._bursts(spans, 12.0)
                got = vox.measure_answer([], audio=audio, events={event: at})["metrics"][metric]
                self.assertIsNotNone(got)
                self.assertLessEqual(abs(got - truth), 0.3, (metric, got, truth))

    def test_continuous_speech_is_one_segment(self):
        audio = _voice(np.full(3 * SR, 140.0))
        self.assertEqual(vox.speech_segments(audio, SR), [(0.0, 3.0)])

    def test_silent_audio_has_no_speech(self):
        self.assertEqual(vox.speech_segments(np.zeros(3 * SR), SR), [])

    def test_barge_in_ignores_sound_before_the_interviewer_speaks(self):
        words = _words("hm", 0.1) + _words("Sorry, can I add something?", 2.6)
        self.assertEqual(vox.overlap_user_over_tts_s(3.0, words, tts_start_s=1.0), 0.35)

    def test_brief_interruption_counts_only_while_speaking(self):
        self.assertEqual(vox.overlap_user_over_tts_s(6.0, segments=[(1.0, 1.3), (8.0, 9.0)], tts_start_s=0.0), 0.3)

    def test_unreadable_audio_keeps_timestamp_metrics(self):
        result = vox.measure_answer(_words("I cut costs by 20 percent.", 0.0), audio="/nonexistent.webm")
        self.assertEqual(result["metrics"]["answer_seconds"], 1.75)
        self.assertIsNone(result["metrics"]["final_pitch_slope_result_sentences"])

    def test_timers_prefer_words_and_ignore_filled_pauses(self):
        words = _words("um", 5.2) + _words("So I would start with the data.", 6.4)
        got = vox.measure_answer(words, events={"freeze_cue_s": 5.0})["metrics"]["freeze_recovery_s"]
        self.assertEqual(got, 1.4)


if __name__ == "__main__":
    unittest.main()
