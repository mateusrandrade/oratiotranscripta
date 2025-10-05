"""Diarization utilities."""

from __future__ import annotations

import audioop
import logging
import os
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

MODEL_ID = "pyannote/speaker-diarization-3.1"

from ..asr import TranscriptionResult, TranscriptionSegment

logger = logging.getLogger(__name__)


@dataclass
class DiarizationConfig:
    mode: str = "none"
    pyannote_token: Optional[str] = None


def apply_diarization(
    result: TranscriptionResult,
    audio_path: Path,
    config: DiarizationConfig,
) -> TranscriptionResult:
    mode = (config.mode or "none").lower()
    if mode in {"none", "off"}:
        return result
    if mode == "basic":
        _basic_diarization(result, audio_path)
        result.metadata["diarization"] = {"mode": "basic"}
        return result
    if mode == "pyannote":
        _pyannote_diarization(result, audio_path, config)
        result.metadata["diarization"] = {"mode": "pyannote"}
        return result
    raise ValueError(f"Modo de diarização desconhecido: {config.mode}")


def _basic_diarization(result: TranscriptionResult, audio_path: Path) -> None:
    energies = _segment_energies(audio_path, result.segments)
    speaker_index = 0
    last_end = None
    last_energy = None
    for segment, energy in zip(result.segments, energies):
        if last_end is not None and segment.start - last_end > 1.5:
            speaker_index += 1
        elif last_energy is not None and energy is not None:
            ratio = abs(energy - last_energy) / max(last_energy, 1e-3)
            if ratio > 0.3:
                speaker_index += 1
        segment.speaker = f"SPK{speaker_index + 1}"
        last_end = segment.end
        last_energy = energy
    logger.debug("Basic diarization assigned %d speaker(s)", speaker_index + 1)


def _segment_energies(audio_path: Path, segments: List[TranscriptionSegment]) -> List[float]:
    energies: List[float] = []
    with wave.open(str(audio_path), "rb") as wf:
        sample_rate = wf.getframerate()
        width = wf.getsampwidth()
        total_frames = wf.getnframes()
        for segment in segments:
            start_frame = min(int(segment.start * sample_rate), total_frames)
            end_frame = min(int(segment.end * sample_rate), total_frames)
            wf.setpos(start_frame)
            frames = wf.readframes(max(end_frame - start_frame, 1))
            try:
                rms = audioop.rms(frames, width)
            except audioop.error:  # pragma: no cover - occurs on malformed data
                rms = 0
            energies.append(float(rms))
    return energies


def _resolve_hf_token(config: DiarizationConfig) -> str:
    token = (
        config.pyannote_token
        or os.getenv("HUGGINGFACE_TOKEN")
        or os.getenv("PYANNOTE_TOKEN")
    )
    if not token:
        raise RuntimeError(
            "Token Hugging Face não encontrado. Informe --pyannote-token, "
            "ou defina as variáveis HUGGINGFACE_TOKEN/PYANNOTE_TOKEN. Gere "
            "um token em https://huggingface.co/settings/tokens e aceite os "
            "termos do modelo em https://huggingface.co/pyannote/speaker-diarization-3.1."
        )
    return token


def _pyannote_diarization(result: TranscriptionResult, audio_path: Path, config: DiarizationConfig) -> None:
    try:
        from pyannote.audio import Pipeline  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("pyannote.audio não está instalado") from exc

    token = _resolve_hf_token(config)

    try:
        try:
            pipeline = Pipeline.from_pretrained(MODEL_ID, use_auth_token=token)
        except TypeError:
            pipeline = Pipeline.from_pretrained(MODEL_ID, token=token)
    except Exception as exc:  # pragma: no cover - network/auth errors
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code in {401, 403}:
            raise RuntimeError(
                "Falha na autenticação com o modelo pyannote. Verifique se o "
                "token está correto e se você aceitou os termos em "
                "https://huggingface.co/pyannote/speaker-diarization-3.1."
            ) from exc
        raise

    diarization = pipeline(audio_path)
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        _assign_speaker(result.segments, turn.start, turn.end, speaker)


def _assign_speaker(segments: List[TranscriptionSegment], start: float, end: float, speaker: str) -> None:
    for segment in segments:
        overlap = min(segment.end, end) - max(segment.start, start)
        if overlap > 0:
            segment.speaker = speaker


__all__ = ["DiarizationConfig", "apply_diarization"]
