"""Helpers for generating JSONL exports with stable identifiers."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Mapping, MutableMapping, Optional, Sequence


def _normalise_segment_id(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    return text


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
    raw_index: Optional[Mapping[str, Any]] = None
    if raw_transcription is not None:
        base["raw_transcription"] = dict(raw_transcription)
        if isinstance(raw_transcription, Mapping):
            segments_data = raw_transcription.get("segments")
            if isinstance(segments_data, Mapping):
                raw_index = segments_data
            else:
                raw_index = raw_transcription

    for position, segment in enumerate(normalised, start=1):
        record = dict(base)
        source_index = segment.pop("_source_index")
        _ensure_orig_reference(segment, raw_index)
        record.update(
            {
                "id": f"utt-{position:04d}",
                "segment_index": source_index,
                "segment": segment,
            }
        )
        record.setdefault("start", segment.get("start"))
        record.setdefault("end", segment.get("end"))
        record.setdefault("speaker", segment.get("speaker", ""))
        yield record


def _ensure_orig_reference(
    segment: Dict[str, Any], raw_index: Optional[Mapping[str, Any]]
) -> None:
    orig = {}
    existing_orig = segment.get("orig")
    if isinstance(existing_orig, Mapping):
        orig.update(existing_orig)

    raw_segment_ids: List[Any] = []
    if "segments" in segment:
        raw_values = segment.pop("segments")
        if isinstance(raw_values, Sequence) and not isinstance(raw_values, (str, bytes)):
            for value in raw_values:
                normalised = _normalise_segment_id(value)
                if normalised is not None:
                    raw_segment_ids.append(normalised)
    elif isinstance(orig.get("segment_ids"), Sequence) and not isinstance(
        orig.get("segment_ids"), (str, bytes)
    ):
        for value in orig["segment_ids"]:  # type: ignore[index]
            raw_segment_ids.append(_normalise_segment_id(value))

    if raw_segment_ids:
        orig["segment_ids"] = list(raw_segment_ids)
        if raw_index:
            resolved_segments = []
            for value in raw_segment_ids:
                key = str(_normalise_segment_id(value))
                resolved = raw_index.get(key) if isinstance(raw_index, Mapping) else None
                if resolved is None and isinstance(raw_index, Mapping):
                    resolved = raw_index.get(value)  # type: ignore[index]
                if isinstance(resolved, MutableMapping):
                    resolved_segments.append(dict(resolved))
                elif isinstance(resolved, Mapping):
                    resolved_segments.append(dict(resolved))
            if resolved_segments:
                orig["segments"] = resolved_segments

    if orig:
        segment["orig"] = orig


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

