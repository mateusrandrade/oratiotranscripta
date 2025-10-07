"""Command line interface for OratioTranscripta."""

from __future__ import annotations

import argparse
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, List, Optional

from .aggregation import AggregationConfig, aggregate_segments
from .alignment import AlignmentConfig, align_transcription
from .asr import TranscriptionResult, load_asr_engine
from .diarization import DiarizationConfig, apply_diarization
from .export import export_json_file, export_transcription
from .ingest import IngestionConfig, IngestionError, ingest_audio
from .vad import load_vad_backend
from . import __version__

LOG_FORMAT = "[%(levelname)s] %(message)s"


def _serialise_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_serialise_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_serialise_value(item) for item in value)
    if isinstance(value, dict):
        return {key: _serialise_value(val) for key, val in value.items()}
    return value


def _resolve_output_base(destination: Path) -> tuple[Path, str]:
    base_path = Path(destination)
    if base_path.suffix:
        return base_path.parent, base_path.stem
    stem = base_path.name or "transcript"
    return base_path, stem


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pipeline completo de transcrição de áudio")
    parser.add_argument("--source", choices=["local", "youtube"], default="local", help="Origem do áudio")
    parser.add_argument("--path", type=Path, help="Caminho para arquivo local quando --source=local")
    parser.add_argument("--url", help="URL do vídeo quando --source=youtube")
    parser.add_argument("--out", type=Path, default=Path("output"), help="Caminho base para os arquivos de saída")
    parser.add_argument("--model", default="small", help="Modelo Whisper/Faster-Whisper a ser utilizado")
    parser.add_argument("--engine", choices=["whisper", "faster-whisper"], default="whisper", help="Backend de ASR")
    parser.add_argument("--lang", help="Idioma forçado para reconhecimento")
    parser.add_argument("--device", help="Dispositivo (cpu/cuda)")
    parser.add_argument("--cookies", type=Path, help="Arquivo de cookies para yt-dlp")
    parser.add_argument(
        "--export",
        nargs="+",
        default=["txt"],
        help="Formatos de exportação desejados (txt, srt, vtt, json)",
    )
    parser.add_argument("--window", type=float, help="Janela fixa em segundos para agregação de legendas")
    parser.add_argument("--vad", default="auto", help="Backend de VAD: auto, webrtc, silero, pyannote, none")
    parser.add_argument("--diarize", choices=["none", "basic", "pyannote"], default="none", help="Modo de diarização")
    parser.add_argument(
        "--pyannote-token",
        help=(
            "Token de autenticação da Hugging Face para pipelines pyannote. "
            "Caso omitido, serão utilizadas as variáveis HUGGINGFACE_TOKEN ou "
            "PYANNOTE_TOKEN. É necessário aceitar os termos dos modelos pyannote"
        ),
    )
    parser.add_argument("--align", action="store_true", help="Habilita alinhamento de palavras com WhisperX")
    parser.add_argument("--words", action="store_true", help="Exporta metadados de palavras quando suportado")
    parser.add_argument("--keep-temp", action="store_true", help="Mantém diretórios temporários gerados")
    parser.add_argument("--verbose", action="store_true", help="Mostra logs detalhados")
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format=LOG_FORMAT)
    logger = logging.getLogger("oratiotranscripta")
    logger.info("Iniciando pipeline de transcrição")

    ingestion_config = IngestionConfig(
        source=args.source,
        path=args.path,
        url=args.url,
        cookies=args.cookies,
        cleanup=not args.keep_temp,
    )

    try:
        ingestion_result = ingest_audio(ingestion_config)
    except IngestionError as exc:
        parser.error(str(exc))
        return

    try:
        vad_kwargs = {}
        if args.vad == "pyannote":
            vad_kwargs["auth_token"] = args.pyannote_token
        vad_backend = load_vad_backend(args.vad, **vad_kwargs)
        vad_segments = vad_backend(ingestion_result.audio_path)
        logger.info("VAD gerou %d segmentos", len(vad_segments))

        asr_engine = load_asr_engine(args.engine, args.model, device=args.device)
        word_timestamps = bool(args.words or args.align)
        transcription: TranscriptionResult = asr_engine.transcribe(
            ingestion_result.audio_path,
            language=args.lang,
            vad_segments=vad_segments,
            word_timestamps=word_timestamps,
        )
        logger.info("Reconhecimento retornou %d segmentos", len(transcription.segments))

        alignment_config = AlignmentConfig(
            enabled=args.align,
            device=args.device,
            language=args.lang,
        )
        transcription = align_transcription(transcription, ingestion_result.audio_path, alignment_config)

        diarization_config = DiarizationConfig(mode=args.diarize, pyannote_token=args.pyannote_token)
        transcription = apply_diarization(transcription, ingestion_result.audio_path, diarization_config)

        raw_transcription = deepcopy(transcription)

        pipeline_metadata = {key: _serialise_value(value) for key, value in vars(args).items()}
        ingestion_metadata = {
            "audio_path": str(ingestion_result.audio_path),
            "source_path": str(ingestion_result.source_path),
            "workdir": str(ingestion_result.workdir),
            "cleanup_enabled": ingestion_result.cleanup_enabled,
        }
        software_metadata = {"oratiotranscripta": __version__}

        for result in (transcription, raw_transcription):
            metadata = dict(result.metadata)
            metadata.update(
                {
                    "pipeline": pipeline_metadata,
                    "ingestion": ingestion_metadata,
                    "software": software_metadata,
                }
            )
            result.metadata = metadata

        aggregation_config = AggregationConfig(window=args.window)
        transcription.segments = aggregate_segments(transcription.segments, aggregation_config)

        exported = export_transcription(transcription, args.out, args.export)

        base_dir, stem = _resolve_output_base(args.out)
        raw_json_path = export_json_file(raw_transcription, base_dir / f"{stem}.raw.json")
        exported.append(raw_json_path)

        for path in exported:
            logger.info("Arquivo exportado: %s", path)
    finally:
        if not args.keep_temp:
            ingestion_result.cleanup()


if __name__ == "__main__":
    main()
