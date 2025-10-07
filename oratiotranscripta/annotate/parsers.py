"""Utilities for parsing edited transcript files."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, List, Sequence, Tuple


_CONFIDENCE_RE = re.compile(r"\s*\(conf=[^)]+\)\s*$", flags=re.IGNORECASE)


@dataclass
class EditedUtterance:
    """Represents an utterance after human editing."""

    start: float
    end: float
    speaker: str
    text: str
    segments: Tuple[int, ...]


def parse_txt(content: str) -> List[EditedUtterance]:
    """Parse the content of a TXT export into utterances."""

    utterances: List[EditedUtterance] = []
    segment_index = 0
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^\[(?P<start>[^\]]+?)\s*->\s*(?P<end>[^\]]+)]\s*(?P<body>.+)$", line)
        if not match:
            continue
        segment_index += 1
        start = _timestamp_to_seconds(match.group("start"))
        end = _timestamp_to_seconds(match.group("end"))
        speaker, text = _parse_body(match.group("body"))
        _append_utterance(
            utterances,
            EditedUtterance(
                start=start,
                end=end,
                speaker=speaker,
                text=text,
                segments=(segment_index,),
            ),
        )
    return utterances


def parse_srt(content: str) -> List[EditedUtterance]:
    """Parse an SRT transcript into utterances."""

    utterances: List[EditedUtterance] = []
    next_index = 1
    for block in _split_blocks(content):
        if not block:
            continue
        block_iter = iter(block)
        first_line = next(block_iter)
        if _is_timestamp_line(first_line):
            segment_id = next_index
            next_index += 1
            times_line = first_line
        else:
            segment_id = _safe_int(first_line, default=next_index)
            next_index = segment_id + 1
            times_line = next(block_iter, "")
        start, end = _parse_timespan(times_line)
        text_lines = list(block_iter)
        if not text_lines:
            continue
        speaker, text = _parse_caption_text(text_lines)
        _append_utterance(
            utterances,
            EditedUtterance(
                start=start,
                end=end,
                speaker=speaker,
                text=text,
                segments=(segment_id,),
            ),
        )
    return utterances


def parse_vtt(content: str) -> List[EditedUtterance]:
    """Parse a VTT transcript into utterances."""

    utterances: List[EditedUtterance] = []
    segment_index = 0
    for block in _split_blocks(content):
        if not block:
            continue
        cue = list(block)
        if cue[0].strip().upper() == "WEBVTT":
            continue
        if cue[0].strip().lower().startswith("note"):
            continue
        if _is_timestamp_line(cue[0]):
            times_line = cue[0]
            text_lines = cue[1:]
        else:
            if len(cue) < 2:
                continue
            times_line = cue[1]
            text_lines = cue[2:]
        if not text_lines:
            continue
        start, end = _parse_timespan(times_line)
        speaker, text = _parse_caption_text(text_lines)
        segment_index += 1
        _append_utterance(
            utterances,
            EditedUtterance(
                start=start,
                end=end,
                speaker=speaker,
                text=text,
                segments=(segment_index,),
            ),
        )
    return utterances


def _append_utterance(collection: List[EditedUtterance], current: EditedUtterance) -> None:
    if collection and collection[-1].speaker == current.speaker:
        previous = collection[-1]
        merged_text = _merge_text(previous.text, current.text)
        collection[-1] = EditedUtterance(
            start=previous.start,
            end=current.end,
            speaker=previous.speaker,
            text=merged_text,
            segments=previous.segments + current.segments,
        )
        return
    collection.append(current)


def _merge_text(first: str, second: str) -> str:
    if not first:
        return second
    if not second:
        return first
    return " ".join(part for part in (first.strip(), second.strip()) if part).strip()


def _parse_body(body: str) -> Tuple[str, str]:
    cleaned = _CONFIDENCE_RE.sub("", body).strip()
    speaker, text = _split_speaker(cleaned)
    return speaker, text


def _parse_caption_text(lines: Sequence[str]) -> Tuple[str, str]:
    joined = " ".join(line.strip() for line in lines if line.strip())
    cleaned = _CONFIDENCE_RE.sub("", joined).strip()
    return _split_speaker(cleaned)


def _split_speaker(text: str) -> Tuple[str, str]:
    if ":" in text:
        possible_speaker, remainder = text.split(":", 1)
        if possible_speaker.strip() and remainder.strip():
            return possible_speaker.strip(), remainder.strip()
    return "", text.strip()


def _split_blocks(content: str) -> Iterable[List[str]]:
    block: List[str] = []
    for raw_line in content.splitlines():
        line = raw_line.rstrip("\n")
        if not line.strip():
            if block:
                yield block
                block = []
            continue
        block.append(line)
    if block:
        yield block


def _is_timestamp_line(line: str) -> bool:
    return "-->" in line


def _parse_timespan(line: str) -> Tuple[float, float]:
    if "-->" not in line:
        raise ValueError("Linha de tempo inválida")
    start_str, end_str = line.split("-->", 1)
    start = _timestamp_to_seconds(start_str)
    end = _timestamp_to_seconds(end_str)
    return start, end


def _timestamp_to_seconds(value: str) -> float:
    text = value.strip().replace(",", ".")
    if not text:
        raise ValueError("Timestamp vazio")
    parts = text.split(":")
    if len(parts) == 1:
        hours = 0
        minutes = 0
        seconds = float(parts[0])
    elif len(parts) == 2:
        hours = 0
        minutes = int(parts[0])
        seconds = float(parts[1])
    else:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def _safe_int(value: str, default: int) -> int:
    value = value.strip()
    try:
        return int(value)
    except ValueError:
        return default


__all__ = [
    "EditedUtterance",
    "parse_txt",
    "parse_srt",
    "parse_vtt",
]
