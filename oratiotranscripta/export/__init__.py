"""Transcription exporters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from ..asr import TranscriptionResult, TranscriptionSegment


def export_transcription(
    result: TranscriptionResult,
    destination: Path,
    formats: Iterable[str],
) -> List[Path]:
    base_path = Path(destination)
    if base_path.suffix:
        base_dir = base_path.parent
        stem = base_path.stem
    else:
        base_dir = base_path
        stem = base_path.name or "transcript"
    base_dir.mkdir(parents=True, exist_ok=True)

    exported: List[Path] = []
    for fmt in formats:
        fmt_lower = fmt.lower()
        if fmt_lower == "txt":
            path = base_dir / f"{stem}.txt"
            _export_txt(result, path)
        elif fmt_lower == "srt":
            path = base_dir / f"{stem}.srt"
            _export_srt(result, path)
        elif fmt_lower == "vtt":
            path = base_dir / f"{stem}.vtt"
            _export_vtt(result, path)
        elif fmt_lower == "json":
            path = base_dir / f"{stem}.json"
            _export_json(result, path)
        else:
            raise ValueError(f"Formato de exportação desconhecido: {fmt}")
        exported.append(path)
    return exported


def export_json_file(result: TranscriptionResult, path: Path) -> Path:
    """Export ``result`` to ``path`` as JSON."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _export_json(result, target)
    return target


def _export_txt(result: TranscriptionResult, path: Path) -> None:
    lines = [f"# language: {result.language or 'unknown'}"]
    for key, value in sorted(result.metadata.items()):
        lines.append(f"# {key}: {value}")
    for segment in result.segments:
        start = _format_timestamp(segment.start)
        end = _format_timestamp(segment.end)
        speaker = f"{segment.speaker}: " if segment.speaker else ""
        confidence = f" (conf={segment.confidence:.2f})" if segment.confidence is not None else ""
        lines.append(f"[{start} -> {end}] {speaker}{segment.text}{confidence}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _export_srt(result: TranscriptionResult, path: Path) -> None:
    lines: List[str] = []
    for index, segment in enumerate(result.segments, start=1):
        start = _format_timestamp(segment.start, for_srt=True)
        end = _format_timestamp(segment.end, for_srt=True)
        lines.append(str(index))
        lines.append(f"{start} --> {end}")
        text = _format_caption_text(segment)
        lines.append(text)
        lines.append("")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _export_vtt(result: TranscriptionResult, path: Path) -> None:
    lines: List[str] = ["WEBVTT", ""]
    for segment in result.segments:
        start = _format_timestamp(segment.start, for_vtt=True)
        end = _format_timestamp(segment.end, for_vtt=True)
        lines.append(f"{start} --> {end}")
        lines.append(_format_caption_text(segment))
        lines.append("")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _export_json(result: TranscriptionResult, path: Path) -> None:
    data = result.to_dict()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _format_caption_text(segment: TranscriptionSegment) -> str:
    speaker = f"{segment.speaker}: " if segment.speaker else ""
    confidence = ""
    if segment.confidence is not None:
        confidence = f" (conf={segment.confidence:.2f})"
    lines = [speaker + segment.text.strip() + confidence]
    return "\n".join(lines)


def _format_timestamp(seconds: float, *, for_srt: bool = False, for_vtt: bool = False) -> str:
    millis = int(round(seconds * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    if for_srt:
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"
    if for_vtt:
        return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"
    return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"


__all__ = ["export_transcription", "export_json_file"]
