"""Tests for Silero VAD compatibility helpers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oratiotranscripta.vad import SileroVAD, VADSegment


def _make_vad(collect_fn):
    vad = SileroVAD.__new__(SileroVAD)
    vad.model = object()
    vad.device = "cpu"
    vad.read_audio = lambda path, sampling_rate: b"fake-wav"
    vad.collect_chunks = collect_fn
    return vad


def test_silero_vad_collect_chunks_with_threshold(tmp_path):
    captured = {}

    def collect_chunks(model, wav, *, sampling_rate, threshold, **kwargs):
        captured["model"] = model
        captured["wav"] = wav
        captured["threshold"] = threshold
        captured["kwargs"] = kwargs
        return [(0, 1000)]

    vad = _make_vad(collect_chunks)
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"00")

    segments = vad(audio_path)

    assert segments == [VADSegment(0.0, 1.0)]
    assert captured["threshold"] == 0.5
    assert captured["kwargs"]["min_speech_duration_ms"] == 250
    assert captured["kwargs"]["device"] == "cpu"


def test_silero_vad_collect_chunks_without_threshold(tmp_path):
    captured = {}

    def collect_chunks(model, wav, *, sampling_rate, min_speech_duration_ms, **kwargs):
        captured["kwargs"] = kwargs
        captured["min_speech_duration_ms"] = min_speech_duration_ms
        return [(100, 1200)]

    vad = _make_vad(collect_chunks)
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"00")

    segments = vad(audio_path)

    assert segments == [VADSegment(0.1, 1.2)]
    assert captured["min_speech_duration_ms"] == 250
    assert "threshold" not in captured["kwargs"]
    assert captured["kwargs"]["speech_pad_ms"] == 120
