from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oratiotranscripta.annotate import _load_raw_transcription
from oratiotranscripta.annotate.jsonl import build_records


def test_build_records_orders_segments_and_adds_ids():
    segments = [
        {"start": 5.0, "text": "later", "speaker": "B", "segments": [2]},
        {"start": 2.0, "text": "early", "speaker": "A", "segments": [1]},
        {"text": "no timing", "segments": [3, 4]},
    ]

    raw_index = {
        "segments": {
            "1": {"segment_id": 1, "text": "first"},
            "2": {"segment_id": 2, "text": "second"},
            "3": {"segment_id": 3, "text": "third"},
            "4": {"segment_id": 4, "text": "fourth"},
        }
    }

    records = build_records(
        segments,
        metadata={"project": "X"},
        raw_transcription=raw_index,
    )

    assert [record["id"] for record in records] == ["utt-0001", "utt-0002", "utt-0003"]
    assert [record["segment_index"] for record in records] == [2, 1, 3]
    assert [record["segment"]["text"] for record in records] == [
        "early",
        "later",
        "no timing",
    ]
    assert records[0]["metadata"]["project"] == "X"
    assert "raw_transcription" in records[0]
    first_orig = records[0]["segment"]["orig"]
    assert first_orig["segment_ids"] == [1]
    assert first_orig["segments"][0]["text"] == "first"
    assert "segments" not in records[0]["segment"]


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
