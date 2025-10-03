"""Aggregation of transcription segments."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from ..asr import TranscriptionSegment, WordMetadata


@dataclass
class AggregationConfig:
    window: Optional[float] = None


def aggregate_segments(
    segments: Iterable[TranscriptionSegment],
    config: AggregationConfig,
) -> List[TranscriptionSegment]:
    segment_list = [s for s in segments]
    if not segment_list:
        return []
    if not config.window:
        return [
            TranscriptionSegment(
                start=segment.start,
                end=segment.end,
                text=segment.text,
                confidence=segment.confidence,
                speaker=segment.speaker,
                words=[WordMetadata(**vars(word)) for word in segment.words],
            )
            for segment in segment_list
        ]

    window = float(config.window)
    base_start = math.floor(segment_list[0].start / window) * window
    grouped: Dict[int, List[TranscriptionSegment]] = defaultdict(list)
    for segment in segment_list:
        index = int((segment.start - base_start) // window)
        grouped[index].append(segment)

    aggregated: List[TranscriptionSegment] = []
    for index in sorted(grouped):
        group = grouped[index]
        start = base_start + index * window
        end = min(start + window, group[-1].end)
        text_lines: List[str] = []
        current_speaker = None
        combined_words: List[WordMetadata] = []
        confidences: List[float] = []

        for seg in group:
            prefix = f"{seg.speaker}: " if seg.speaker else ""
            if current_speaker == seg.speaker and text_lines:
                text_lines[-1] += " " + seg.text.strip()
            else:
                text_lines.append(prefix + seg.text.strip())
            current_speaker = seg.speaker
            combined_words.extend(seg.words)
            if seg.confidence is not None:
                confidences.append(seg.confidence)
        text = "\n".join(filter(None, text_lines))
        confidence = sum(confidences) / len(confidences) if confidences else None
        speaker = group[0].speaker if all(seg.speaker == group[0].speaker for seg in group) else None
        aggregated.append(
            TranscriptionSegment(
                start=start,
                end=end,
                text=text,
                confidence=confidence,
                speaker=speaker,
                words=[WordMetadata(**vars(word)) for word in combined_words],
            )
        )

    return aggregated


__all__ = ["AggregationConfig", "aggregate_segments"]
