"""Optional alignment utilities using WhisperX."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..asr import TranscriptionResult, WordMetadata

logger = logging.getLogger(__name__)


@dataclass
class AlignmentConfig:
    enabled: bool = False
    model: str = "WAV2VEC2_ASR_LARGE_LV60K_960H"
    device: Optional[str] = None
    language: Optional[str] = None


class AlignmentError(RuntimeError):
    """Raised when alignment cannot be completed."""


def align_transcription(
    result: TranscriptionResult,
    audio_path: Path,
    config: AlignmentConfig,
) -> TranscriptionResult:
    """Apply WhisperX alignment to an existing transcription result."""

    if not config.enabled:
        return result

    try:
        import whisperx  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise AlignmentError("whisperx não está instalado") from exc

    device = config.device or ("cuda" if whisperx.is_cuda_available() else "cpu")
    logger.info("Iniciando alinhamento WhisperX (%s)", device)
    align_model, metadata = whisperx.load_align_model(
        language=config.language or result.language,
        device=device,
        model_name=config.model,
    )
    audio = whisperx.load_audio(str(audio_path))

    whisperx_result = {
        "language": result.language,
        "segments": [
            {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
            }
            for segment in result.segments
        ],
    }

    aligned = whisperx.align(whisperx_result["segments"], align_model, metadata, audio, device)
    words_by_segment = aligned["segments"]

    for segment, aligned_segment in zip(result.segments, words_by_segment):
        words = []
        for word in aligned_segment.get("words", []):
            words.append(
                WordMetadata(
                    word=word.get("word", ""),
                    start=word.get("start"),
                    end=word.get("end"),
                    confidence=word.get("score"),
                )
            )
        segment.words = words

    result.metadata["alignment"] = {
        "model": config.model,
        "device": device,
    }
    return result


__all__ = ["AlignmentConfig", "AlignmentError", "align_transcription"]
