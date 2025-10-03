"""Automatic speech recognition interfaces."""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from ..vad import VADSegment

logger = logging.getLogger(__name__)


@dataclass
class WordMetadata:
    """Metadata for a recognised word."""

    word: str
    start: Optional[float]
    end: Optional[float]
    confidence: Optional[float] = None


@dataclass
class TranscriptionSegment:
    """Segment of recognised speech."""

    start: float
    end: float
    text: str
    confidence: Optional[float] = None
    speaker: Optional[str] = None
    words: List[WordMetadata] = field(default_factory=list)


@dataclass
class TranscriptionResult:
    segments: List[TranscriptionSegment]
    language: Optional[str]
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "language": self.language,
            "segments": [
                {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "confidence": segment.confidence,
                    "speaker": segment.speaker,
                    "words": [
                        {
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "confidence": word.confidence,
                        }
                        for word in segment.words
                    ],
                }
                for segment in self.segments
            ],
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class BaseASREngine:
    def transcribe(
        self,
        audio_path: Path,
        *,
        language: Optional[str] = None,
        vad_segments: Optional[Sequence[VADSegment]] = None,
        word_timestamps: bool = False,
    ) -> TranscriptionResult:
        raise NotImplementedError


def load_asr_engine(
    engine: str,
    model: str,
    *,
    device: Optional[str] = None,
) -> BaseASREngine:
    normalized = engine.lower()
    if normalized in {"whisper", "openai"}:
        return WhisperEngine(model=model, device=device)
    if normalized in {"faster-whisper", "ctranslate2", "faster"}:
        return FasterWhisperEngine(model=model, device=device)
    raise ValueError(f"Engine ASR desconhecido: {engine}")


def _detect_device(preferred: Optional[str] = None) -> str:
    if preferred:
        return preferred
    try:
        import torch

        if torch.cuda.is_available():  # pragma: no cover - depends on environment
            return "cuda"
    except Exception:  # pragma: no cover - torch optional
        logger.debug("Torch indisponível para detecção automática de GPU")
    return "cpu"


class WhisperEngine(BaseASREngine):
    def __init__(self, model: str, device: Optional[str] = None):
        try:
            import whisper
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("whisper não está instalado") from exc

        self._whisper = whisper
        self.model_name = model
        self.model = whisper.load_model(model, device=_detect_device(device))

    def transcribe(
        self,
        audio_path: Path,
        *,
        language: Optional[str] = None,
        vad_segments: Optional[Sequence[VADSegment]] = None,
        word_timestamps: bool = False,
    ) -> TranscriptionResult:
        options = {
            "language": language,
            "word_timestamps": word_timestamps,
            "condition_on_previous_text": False,
            "task": "transcribe",
        }
        logger.info("Iniciando transcrição com Whisper (%s)", self.model.device)
        result = self.model.transcribe(str(audio_path), **options)
        segments = _parse_whisper_segments(result, vad_segments)
        metadata = {
            "engine": "whisper",
            "model": self.model_name,
            "device": str(self.model.device),
        }
        return TranscriptionResult(segments=segments, language=result.get("language"), metadata=metadata)


def _parse_whisper_segments(result: Dict[str, object], vad_segments: Optional[Sequence[VADSegment]]) -> List[TranscriptionSegment]:
    segments: List[TranscriptionSegment] = []
    for seg in result.get("segments", []):  # type: ignore[assignment]
        start = float(seg["start"])
        end = float(seg["end"])
        if vad_segments and not _overlaps_vad(start, end, vad_segments):
            continue
        words = [
            WordMetadata(
                word=w.get("word", ""),
                start=w.get("start"),
                end=w.get("end"),
                confidence=w.get("probability"),
            )
            for w in seg.get("words", [])  # type: ignore[attr-defined]
        ]
        confidence = None
        if seg.get("avg_logprob") is not None:
            confidence = math.exp(float(seg["avg_logprob"]))
        segments.append(
            TranscriptionSegment(
                start=start,
                end=end,
                text=seg.get("text", "").strip(),
                confidence=confidence,
                words=words,
            )
        )
    return segments


class FasterWhisperEngine(BaseASREngine):
    def __init__(self, model: str, device: Optional[str] = None):
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("faster-whisper não está instalado") from exc

        device = _detect_device(device)
        compute_type = "float16" if device == "cuda" else "int8"
        self.model_path = model
        self.model = WhisperModel(model, device=device, compute_type=compute_type)
        self._device = device

    def transcribe(
        self,
        audio_path: Path,
        *,
        language: Optional[str] = None,
        vad_segments: Optional[Sequence[VADSegment]] = None,
        word_timestamps: bool = False,
    ) -> TranscriptionResult:
        logger.info("Iniciando transcrição com Faster-Whisper (%s)", self._device)
        segments_iter, info = self.model.transcribe(
            str(audio_path),
            language=language,
            word_timestamps=word_timestamps,
        )
        segments = _parse_faster_whisper_segments(segments_iter, vad_segments)
        metadata = {
            "engine": "faster-whisper",
            "model": self.model_path,
            "device": self._device,
            "language_probability": getattr(info, "language_probability", None),
        }
        return TranscriptionResult(segments=segments, language=info.language, metadata=metadata)


def _parse_faster_whisper_segments(
    segments_iter: Iterable[object], vad_segments: Optional[Sequence[VADSegment]]
) -> List[TranscriptionSegment]:
    segments: List[TranscriptionSegment] = []
    for segment in segments_iter:
        start = float(segment.start)
        end = float(segment.end)
        if vad_segments and not _overlaps_vad(start, end, vad_segments):
            continue
        words = [
            WordMetadata(
                word=word.word,
                start=word.start,
                end=word.end,
                confidence=getattr(word, "probability", None),
            )
            for word in getattr(segment, "words", []) or []
        ]
        confidence_logprob = getattr(segment, "avg_logprob", None)
        confidence_value = None
        if isinstance(confidence_logprob, (int, float)):
            confidence_value = math.exp(confidence_logprob)
        segments.append(
            TranscriptionSegment(
                start=start,
                end=end,
                text=str(segment.text).strip(),
                confidence=confidence_value,
                words=words,
            )
        )
    return segments


def _overlaps_vad(start: float, end: float, vad_segments: Sequence[VADSegment]) -> bool:
    for vad in vad_segments:
        if start < vad.end and end > vad.start:
            return True
    return False


__all__ = [
    "WordMetadata",
    "TranscriptionSegment",
    "TranscriptionResult",
    "BaseASREngine",
    "load_asr_engine",
]
