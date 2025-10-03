"""Audio ingestion utilities."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class IngestionConfig:
    """Configuration for ingesting audio from a source."""

    source: str = "local"
    path: Optional[Path] = None
    url: Optional[str] = None
    cookies: Optional[Path] = None
    tmp_root: Optional[Path] = None
    cleanup: bool = True
    normalize: bool = True
    sample_rate: int = 16_000
    channels: int = 1
    audio_format: str = "wav"


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""

    audio_path: Path
    workdir: Path
    source_path: Path
    cleanup_enabled: bool = True

    def cleanup(self) -> None:
        """Remove temporary artifacts if configured."""

        if not self.cleanup_enabled:
            return
        try:
            shutil.rmtree(self.workdir)
        except FileNotFoundError:  # pragma: no cover - directory already gone
            logger.debug("Temporary directory already removed: %s", self.workdir)


class IngestionError(RuntimeError):
    """Raised when the ingestion pipeline fails."""


def ingest_audio(config: IngestionConfig) -> IngestionResult:
    """Download and/or normalise audio according to ``config``."""

    workdir = Path(tempfile.mkdtemp(prefix="oratiotranscripta_", dir=config.tmp_root))
    logger.debug("Created temporary workdir at %s", workdir)

    try:
        source_path = _resolve_source(config, workdir)
        audio_path = _normalise_audio(source_path, workdir, config)
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise

    return IngestionResult(
        audio_path=audio_path,
        workdir=workdir,
        source_path=source_path,
        cleanup_enabled=config.cleanup,
    )


def _resolve_source(config: IngestionConfig, workdir: Path) -> Path:
    if config.source == "youtube":
        return _download_from_youtube(config, workdir)
    if config.source == "local":
        if not config.path:
            raise IngestionError("--path is required when --source=local")
        path = Path(config.path).expanduser().resolve()
        if not path.exists():
            raise IngestionError(f"Arquivo local não encontrado: {path}")
        return path
    raise IngestionError(f"Fonte de ingestão desconhecida: {config.source}")


def _download_from_youtube(config: IngestionConfig, workdir: Path) -> Path:
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise IngestionError("yt-dlp não está instalado para downloads do YouTube") from exc

    if not config.url:
        raise IngestionError("--url é obrigatório para downloads do YouTube")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(workdir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "cookiefile": str(config.cookies) if config.cookies else None,
    }
    logger.info("Baixando áudio do YouTube de %s", config.url)
    with YoutubeDL({k: v for k, v in ydl_opts.items() if v is not None}) as ydl:
        info = ydl.extract_info(config.url, download=True)
        if "requested_downloads" in info and info["requested_downloads"]:
            filename = info["requested_downloads"][0]["filepath"]
            return Path(filename)

    candidates = sorted(workdir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise IngestionError("Não foi possível determinar o arquivo baixado")
    return candidates[0]


def _normalise_audio(source_path: Path, workdir: Path, config: IngestionConfig) -> Path:
    if not config.normalize:
        target = workdir / source_path.name
        if source_path != target:
            shutil.copy2(source_path, target)
            return target
        return source_path

    output_path = workdir / f"normalised.{config.audio_format}"
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-ac",
        str(config.channels),
        "-ar",
        str(config.sample_rate),
        "-vn",
        str(output_path),
    ]
    logger.debug("Normalizando áudio com comando: %s", " ".join(command))
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:  # pragma: no cover - depende do ambiente
        raise IngestionError("ffmpeg não encontrado no PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise IngestionError(f"ffmpeg falhou ao processar o áudio: {exc.stderr.decode(errors='ignore')}")
    return output_path


__all__ = [
    "IngestionConfig",
    "IngestionResult",
    "IngestionError",
    "ingest_audio",
]
