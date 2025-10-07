"""Helpers for generating JSONL exports with stable identifiers."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Mapping, MutableMapping, Optional, Sequence


def _normalise_segment(segment: Mapping[str, Any]) -> Dict[str, Any]:
    if isinstance(segment, MutableMapping):
        return dict(segment)
    return {"text": str(segment)}


def _sort_key(item: Dict[str, Any]) -> tuple:
    start = item.get("start")
    if isinstance(start, (int, float)):
        return (0, float(start), item["_source_index"])
    return (1, item["_source_index"])


def iter_records(
    segments: Sequence[Mapping[str, Any]],
    *,
    metadata: Optional[Mapping[str, Any]] = None,
    raw_transcription: Optional[Mapping[str, Any]] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield JSONL records ordered by time with stable IDs."""

    normalised: List[Dict[str, Any]] = []
    for index, segment in enumerate(segments, start=1):
        payload = _normalise_segment(segment)
        payload["_source_index"] = index
        normalised.append(payload)

    normalised.sort(key=_sort_key)

    base: Dict[str, Any] = {}
    if metadata is not None:
        base["metadata"] = dict(metadata)
    if raw_transcription is not None:
        base["raw_transcription"] = dict(raw_transcription)

    for position, segment in enumerate(normalised, start=1):
        record = dict(base)
        record.update(
            {
                "id": f"utt-{position:04d}",
                "segment_index": segment.pop("_source_index"),
                "segment": segment,
            }
        )
        record.setdefault("start", segment.get("start"))
        record.setdefault("end", segment.get("end"))
        record.setdefault("speaker", segment.get("speaker", ""))
        yield record


def build_records(
    segments: Sequence[Mapping[str, Any]],
    *,
    metadata: Optional[Mapping[str, Any]] = None,
    raw_transcription: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Return a list with all JSONL records."""

    return list(
        iter_records(
            segments,
            metadata=metadata,
            raw_transcription=raw_transcription,
        )
    )


__all__ = ["build_records", "iter_records"]

