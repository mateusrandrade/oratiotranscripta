from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oratiotranscripta.annotate import _load_transcript
from oratiotranscripta.annotate.parsers import (
    EditedUtterance,
    parse_srt,
    parse_txt,
    parse_vtt,
)


def test_parse_txt_merges_consecutive_segments() -> None:
    content = """# language: pt
[00:00:00.000 -> 00:00:02.000] Speaker 1: Olá (conf=0.90)
[00:00:02.000 -> 00:00:04.500] Speaker 1: mundo!
[00:00:04.500 -> 00:00:05.000] Speaker 2: Tchau.
"""

    utterances = parse_txt(content)

    assert len(utterances) == 2
    first, second = utterances
    assert first.start == 0.0
    assert first.end == 4.5
    assert first.speaker == "Speaker 1"
    assert first.text == "Olá mundo!"
    assert first.segments == (1, 2)

    assert second.start == 4.5
    assert second.end == 5.0
    assert second.speaker == "Speaker 2"
    assert second.text == "Tchau."
    assert second.segments == (3,)


def test_parse_srt_extracts_speaker_and_confidence() -> None:
    content = """1
00:00:00,000 --> 00:00:02,500
Speaker 1: Primeira frase (conf=0.81)

2
00:00:02,500 --> 00:00:04,000
Speaker 1: Segunda frase

3
00:00:04,000 --> 00:00:05,500
Speaker 2: Final
"""

    utterances = parse_srt(content)

    assert len(utterances) == 2
    first, second = utterances
    assert first.start == 0.0
    assert first.end == 4.0
    assert first.speaker == "Speaker 1"
    assert first.text == "Primeira frase Segunda frase"
    assert first.segments == (1, 2)

    assert second.start == 4.0
    assert second.end == 5.5
    assert second.speaker == "Speaker 2"
    assert second.text == "Final"
    assert second.segments == (3,)


def test_parse_vtt_handles_header_and_merging() -> None:
    content = """WEBVTT

00:00:00.000 --> 00:00:02.000
Speaker 1: Bom dia (conf=0.77)

00:00:02.000 --> 00:00:03.500
Speaker 1: Tudo bem?

00:00:03.500 --> 00:00:05.000
Speaker 2: Sim!
"""

    utterances = parse_vtt(content)

    assert len(utterances) == 2
    first, second = utterances
    assert first.start == 0.0
    assert first.end == 3.5
    assert first.speaker == "Speaker 1"
    assert first.text == "Bom dia Tudo bem?"
    assert first.segments == (1, 2)

    assert second.start == 3.5
    assert second.end == 5.0
    assert second.speaker == "Speaker 2"
    assert second.text == "Sim!"
    assert second.segments == (3,)


def test_load_transcript_parses_txt_file(tmp_path) -> None:
    path = tmp_path / "edited.txt"
    path.write_text(
        """[00:00:00.000 -> 00:00:02.000] Speaker 1: Olá (conf=0.9)
[00:00:02.000 -> 00:00:04.000] Speaker 1: mundo!
[00:00:04.000 -> 00:00:05.000] Speaker 2: Tchau
""",
        encoding="utf-8",
    )

    segments = _load_transcript(path, format="txt")

    assert [segment["utt_id"] for segment in segments] == ["utt-0001", "utt-0002"]
    first, second = segments
    assert first["speaker"] == "Speaker 1"
    assert first["text"] == "Olá mundo!"
    assert first["segments"] == [1, 2]
    assert second["speaker"] == "Speaker 2"
    assert second["segments"] == [3]


def test_load_transcript_auto_detects_srt(tmp_path) -> None:
    path = tmp_path / "edited.srt"
    path.write_text(
        """1
00:00:00,000 --> 00:00:02,500
Speaker 1: Primeira

2
00:00:02,500 --> 00:00:04,000
Speaker 1: frase

3
00:00:04,000 --> 00:00:05,000
Speaker 2: Final
""",
        encoding="utf-8",
    )

    segments = _load_transcript(path, format="auto")

    assert len(segments) == 2
    assert segments[0]["utt_id"] == "utt-0001"
    assert segments[0]["text"] == "Primeira frase"
    assert segments[0]["segments"] == [1, 2]
    assert segments[1]["speaker"] == "Speaker 2"
