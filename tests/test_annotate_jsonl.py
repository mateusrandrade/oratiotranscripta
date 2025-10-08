from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oratiotranscripta.annotate import _load_raw_transcription
from oratiotranscripta.annotate.jsonl import build_records


def test_build_records_orders_segments_and_adds_ids():
    segments = [
        {
            "start": 5.0,
            "end": 7.0,
            "text": "later",
            "speaker": "B",
            "segments": [2],
            "spk_ids": ["spk-002"],
        },
        {
            "start": 2.0,
            "end": 3.5,
            "text": "early",
            "speaker": {"id": "spkA", "name": "Speaker A"},
            "segments": [1],
        },
        {
            "text": "no timing",
            "segments": [3, 4],
            "orig": {"spk_ids": ["x1"]},
        },
    ]

    records = build_records(
        segments,
        metadata={"project": "X"},
        raw_transcription={"segments": {}},
    )

    assert [record["utt_id"] for record in records] == ["utt-0001", "utt-0002", "utt-0003"]
    assert [record["text"] for record in records] == ["early", "later", "no timing"]
    assert all("metadata" not in record for record in records)
    assert all("segment_index" not in record for record in records)

    first = records[0]
    assert first["start"] == pytest.approx(2.0)
    assert first["end"] == pytest.approx(3.5)
    assert first["duration_sec"] == pytest.approx(1.5)
    assert first["speaker"] == {"id": "spkA", "name": "Speaker A"}
    assert first["orig"]["segment_ids"] == [1]
    assert "spk_ids" not in first["orig"]

    second = records[1]
    assert second["speaker"] == {"id": None, "name": "B"}
    assert second["orig"] == {"segment_ids": [2], "spk_ids": ["spk-002"]}

    third = records[2]
    assert "start" not in third
    assert "speaker" not in third
    assert third["orig"] == {"segment_ids": [3, 4], "spk_ids": ["x1"]}


def test_load_raw_transcription_from_jsonl(tmp_path):
    raw_path = tmp_path / "sample.raw_segments.jsonl"
    raw_path.write_text(
        """
{"segment_id": 0, "text": "hi"}
{"segment_id": 1, "text": "bye"}
        """.strip(),
        encoding="utf-8",
    )

    loaded = _load_raw_transcription(raw_path)

    assert loaded is not None
    assert set(loaded["segments"].keys()) == {"0", "1"}
    assert loaded["segments"]["0"]["text"] == "hi"
