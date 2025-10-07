from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oratiotranscripta.annotate.jsonl import build_records


def test_build_records_orders_segments_and_adds_ids():
    segments = [
        {"start": 5.0, "text": "later", "speaker": "B"},
        {"start": 2.0, "text": "early", "speaker": "A"},
        {"text": "no timing"},
    ]

    records = build_records(
        segments,
        metadata={"project": "X"},
        raw_transcription={"segments": []},
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
