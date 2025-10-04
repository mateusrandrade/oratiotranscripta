"""Voice activity detection backends."""

from __future__ import annotations

import inspect
import logging
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

logger = logging.getLogger(__name__)

# Pin the Silero VAD torch hub reference to a known-good release so that future
# upstream changes do not silently change the model behaviour or break loading.
SILERO_VAD_REPO_REF = "snakers4/silero-vad:v5.0"


@dataclass
class VADSegment:
    """Time span flagged as speech."""

    start: float
    end: float


class BaseVAD:
    """Base class for VAD backends."""

    def __call__(self, audio_path: Path) -> List[VADSegment]:
        raise NotImplementedError


class BypassVAD(BaseVAD):
    """Return a single full-length segment."""

    def __call__(self, audio_path: Path) -> List[VADSegment]:
        duration = _get_duration(audio_path)
        logger.debug("Bypass VAD returning full duration %.2fs", duration)
        return [VADSegment(0.0, duration)]


class WebRTCVAD(BaseVAD):
    """VAD based on the WebRTC implementation."""

    def __init__(self, aggressiveness: int = 3, frame_ms: int = 30):
        try:
            import webrtcvad  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("webrtcvad não está instalado") from exc

        if not 0 <= aggressiveness <= 3:
            raise ValueError("aggressiveness deve estar entre 0 e 3")
        self._vad = webrtcvad.Vad(aggressiveness)
        self.frame_ms = frame_ms

    def __call__(self, audio_path: Path) -> List[VADSegment]:
        with wave.open(str(audio_path), "rb") as wf:
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            if channels != 1 or sampwidth != 2:
                raise RuntimeError("VAD WebRTC requer áudio PCM mono de 16 bits")
            frame_size = int(sample_rate * self.frame_ms / 1000)
            bytes_per_frame = frame_size * sampwidth
            timestamp = 0.0
            triggered = False
            segments: List[VADSegment] = []
            current_start: Optional[float] = None

            while True:
                frames = wf.readframes(frame_size)
                if len(frames) < bytes_per_frame:
                    break
                is_speech = self._vad.is_speech(frames, sample_rate)
                if is_speech and not triggered:
                    triggered = True
                    current_start = timestamp
                elif not is_speech and triggered:
                    triggered = False
                    if current_start is not None:
                        segments.append(VADSegment(current_start, timestamp))
                        current_start = None
                timestamp += self.frame_ms / 1000.0

            if triggered and current_start is not None:
                duration = _get_duration(audio_path)
                segments.append(VADSegment(current_start, duration))

        merged = _merge_close_segments(segments, gap=0.3)
        logger.debug("WebRTC VAD produced %d segments", len(merged))
        return merged


class SileroVAD(BaseVAD):
    """Silero VAD via torch hub."""

    def __init__(
        self,
        device: Optional[str] = None,
        repo_ref: str = SILERO_VAD_REPO_REF,
    ):
        try:
            import torch
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("torch é necessário para o VAD Silero") from exc

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        try:
            try:
                self.model, utils = torch.hub.load(
                    repo_or_dir=repo_ref,
                    model="silero_vad",
                    force_reload=False,
                    trust_repo=True,
                )
            except TypeError:
                self.model, utils = torch.hub.load(
                    repo_or_dir=repo_ref,
                    model="silero_vad",
                    force_reload=False,
                )
        except Exception as exc:  # pragma: no cover - heavy optional dependency
            raise RuntimeError("Falha ao carregar modelo Silero VAD") from exc
        (
            self.get_speech_timestamps,
            self.save_audio,
            self.read_audio,
            self.vad_iterator,
            self.collect_chunks,
        ) = utils

    def __call__(self, audio_path: Path) -> List[VADSegment]:
        wav = self.read_audio(str(audio_path), sampling_rate=16_000)
        collect_kwargs = {
            "sampling_rate": 16_000,
            "min_speech_duration_ms": 250,
            "max_speech_duration_s": 15,
            "min_silence_duration_ms": 100,
            "speech_pad_ms": 120,
            "device": self.device,
        }

        collect_signature = inspect.signature(self.collect_chunks)
        collect_params = collect_signature.parameters

        if "threshold" in collect_params:
            collect_kwargs["threshold"] = 0.5

        ckw = {
            key: value
            for key, value in collect_kwargs.items()
            if key in collect_params
        }

        try:
            speeches = self.collect_chunks(
                self.model,
                wav,
                **ckw,
            )
        except Exception:
            ts_params = inspect.signature(self.get_speech_timestamps).parameters
            ts_kwargs = {
                key: value
                for key, value in collect_kwargs.items()
                if key in ts_params
            }
            speeches = self.get_speech_timestamps(
                wav,
                self.model,
                **ts_kwargs,
            )
        segments = [VADSegment(s[0] / 1000.0, s[1] / 1000.0) for s in speeches]
        logger.debug("Silero VAD produced %d segments", len(segments))
        return segments


class PyannoteVAD(BaseVAD):
    """pyannote.audio VAD pipeline."""

    def __init__(self, auth_token: Optional[str] = None):
        try:
            from pyannote.audio import Pipeline  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("pyannote.audio não está instalado") from exc

        self.pipeline = Pipeline.from_pretrained(
            "pyannote/voice-activity-detection",
            use_auth_token=auth_token,
        )

    def __call__(self, audio_path: Path) -> List[VADSegment]:
        vad_result = self.pipeline(audio_path)
        segments = [VADSegment(segment.start, segment.end) for segment in vad_result.get_timeline()]
        logger.debug("pyannote VAD produced %d segments", len(segments))
        return segments


def load_vad_backend(name: str, **kwargs) -> BaseVAD:
    """Factory for VAD backends."""

    normalized = (name or "none").lower()
    if normalized in {"none", "off", "disable", "disabled"}:
        return BypassVAD()
    if normalized in {"auto", "default"}:
        try:
            return WebRTCVAD()
        except Exception as exc:  # pragma: no cover
            logger.warning("Falha ao inicializar WebRTC VAD: %s", exc)
            return BypassVAD()
    if normalized == "webrtc":
        return WebRTCVAD(**kwargs)
    if normalized == "silero":
        return SileroVAD(**kwargs)
    if normalized == "pyannote":
        return PyannoteVAD(**kwargs)
    raise ValueError(f"Backend de VAD desconhecido: {name}")


def _get_duration(audio_path: Path) -> float:
    with wave.open(str(audio_path), "rb") as wf:
        frames = wf.getnframes()
        sample_rate = wf.getframerate()
    return frames / float(sample_rate)


def _merge_close_segments(segments: Iterable[VADSegment], gap: float = 0.2) -> List[VADSegment]:
    merged: List[VADSegment] = []
    for segment in sorted(segments, key=lambda s: s.start):
        if not merged:
            merged.append(segment)
            continue
        last = merged[-1]
        if segment.start - last.end <= gap:
            merged[-1] = VADSegment(last.start, max(last.end, segment.end))
        else:
            merged.append(segment)
    return merged


__all__ = [
    "VADSegment",
    "BaseVAD",
    "BypassVAD",
    "WebRTCVAD",
    "SileroVAD",
    "PyannoteVAD",
    "load_vad_backend",
]
