"""Helpers to export transcription artefacts as JSONL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, MutableMapping, Optional, Sequence

from ..asr import TranscriptionSegment


def _prepare_common_metadata(metadata: Mapping[str, object]) -> MutableMapping[str, object]:
    pipeline = metadata.get("pipeline", {}) if isinstance(metadata, Mapping) else {}
    ingestion = metadata.get("ingestion", {}) if isinstance(metadata, Mapping) else {}

    def _from_mapping(data: object, key: str) -> Optional[object]:
        if isinstance(data, Mapping):
            return data.get(key)
        return None

    common: MutableMapping[str, object] = {
        "engine": metadata.get("engine"),
        "run_id": _from_mapping(pipeline, "run_id"),
        "source": _from_mapping(pipeline, "source"),
        "source_path": _from_mapping(ingestion, "source_path"),
        "audio_path": _from_mapping(ingestion, "audio_path"),
        "output_dir": _from_mapping(pipeline, "output_dir"),
    }
    return common


def write_raw_segments_jsonl(
    path: Path,
    segments: Sequence[TranscriptionSegment],
    *,
    metadata: Mapping[str, object],
    language: Optional[str],
) -> Path:
    """Persista ``segments`` como um arquivo JSONL."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    common = _prepare_common_metadata(metadata)

    with target.open("w", encoding="utf-8") as fh:
        for index, segment in enumerate(segments):
            record = {
                "segment_id": index,
                "start_sec": segment.start,
                "end_sec": segment.end,
                "duration_sec": max(segment.end - segment.start, 0.0),
                "text": segment.text,
                "confidence": segment.confidence,
                "speaker": segment.speaker,
                "language": language,
            }
            record.update(common)
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return target


def write_raw_words_jsonl(
    path: Path,
    segments: Sequence[TranscriptionSegment],
    *,
    metadata: Mapping[str, object],
    language: Optional[str],
) -> Optional[Path]:
    """Persista palavras reconhecidas como JSONL.

    Retorna ``None`` quando não houver palavras a exportar.
    """

    target = Path(path)
    has_words = any(segment.words for segment in segments)
    if not has_words:
        return None

    target.parent.mkdir(parents=True, exist_ok=True)
    common = _prepare_common_metadata(metadata)

    with target.open("w", encoding="utf-8") as fh:
        for segment_id, segment in enumerate(segments):
            for word_id, word in enumerate(segment.words):
                record = {
                    "segment_id": segment_id,
                    "word_id": word_id,
                    "word": word.word,
                    "start_sec": word.start,
                    "end_sec": word.end,
                    "duration_sec": (word.end - word.start) if None not in (word.start, word.end) else None,
                    "confidence": word.confidence,
                    "speaker": segment.speaker,
                    "language": language,
                }
                record.update(common)
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return target


__all__ = ["write_raw_segments_jsonl", "write_raw_words_jsonl"]
