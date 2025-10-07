"""Ferramentas de anotação para OratioTranscripta."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

LOG_FORMAT = "[%(levelname)s] %(message)s"


def build_parser() -> argparse.ArgumentParser:
    """Cria o parser de argumentos para a CLI de anotação."""

    parser = argparse.ArgumentParser(
        description="Gera arquivos de anotação a partir de uma transcrição",
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        required=True,
        help="Arquivo contendo a transcrição a ser anotada (JSON, JSONL ou texto)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "jsonl"],
        default="jsonl",
        help="Formato de saída desejado",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        help="Arquivo JSON opcional com metadados adicionais",
    )
    parser.add_argument(
        "--raw-json",
        type=Path,
        help="Arquivo JSON com a transcrição bruta exportada pela pipeline",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Caminho do arquivo de saída (default: stdout)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Arquivo JSONL onde o manifesto da exportação será registrado",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostra logs detalhados durante a execução",
    )
    return parser


def _load_json_file(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def _load_transcript(path: Path) -> List[Dict[str, Any]]:
    try:
        data = _load_json_file(path)
    except json.JSONDecodeError:
        records: List[Dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                item = json.loads(stripped)
            except json.JSONDecodeError:
                records.append({"text": stripped})
            else:
                records.append(_ensure_mapping(item))
        if not records:
            raise ValueError("Nenhum segmento encontrado na transcrição")
        return records

    if isinstance(data, dict) and "segments" in data:
        segments = data.get("segments", [])
    elif isinstance(data, list):
        segments = data
    else:
        segments = [data]

    if not isinstance(segments, Iterable):
        raise ValueError("Formato de transcrição inválido: esperado lista de segmentos")

    normalised: List[Dict[str, Any]] = []
    for segment in segments:
        if isinstance(segment, dict):
            normalised.append(dict(segment))
        else:
            normalised.append({"text": str(segment)})
    if not normalised:
        raise ValueError("Nenhum segmento encontrado na transcrição")
    return normalised


def _ensure_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {"text": str(value)}


def _load_metadata(path: Optional[Path]) -> Dict[str, Any]:
    if path is None:
        return {}
    data = _load_json_file(path)
    if not isinstance(data, dict):
        raise ValueError("Metadados devem ser um objeto JSON")
    return data


def _load_raw_transcription(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if path is None:
        return None
    data = _load_json_file(path)
    if not isinstance(data, dict):
        raise ValueError("Transcrição bruta deve ser um objeto JSON")
    return data


def _write_json(path: Optional[Path], payload: Dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if path is None:
        print(text)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_jsonl(path: Optional[Path], records: Iterable[Dict[str, Any]]) -> None:
    lines = [json.dumps(record, ensure_ascii=False) for record in records]
    if path is None:
        for line in lines:
            print(line)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_manifest(
    manifest_path: Optional[Path],
    *,
    output_path: Optional[Path],
    transcript_path: Path,
    output_format: str,
    segments: int,
    metadata_path: Optional[Path],
    raw_path: Optional[Path],
) -> None:
    if manifest_path is None:
        return
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "transcript": str(transcript_path),
        "output": str(output_path) if output_path else "-",
        "format": output_format,
        "segments": segments,
    }
    if metadata_path:
        entry["metadata"] = str(metadata_path)
    if raw_path:
        entry["raw_json"] = str(raw_path)
    with manifest_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")



def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format=LOG_FORMAT)
    logger = logging.getLogger("oratiotranscripta.annotate")

    logger.info("Carregando transcrição de %%s", args.transcript)
    try:
        segments = _load_transcript(args.transcript)
    except Exception as exc:
        parser.error(str(exc))
        return

    try:
        metadata = _load_metadata(args.metadata)
        raw_transcription = _load_raw_transcription(args.raw_json)
    except Exception as exc:
        parser.error(str(exc))
        return

    if args.format == "json":
        payload: Dict[str, Any] = {
            "segments": segments,
            "metadata": metadata,
        }
        if raw_transcription is not None:
            payload["raw_transcription"] = raw_transcription
        payload["source"] = str(args.transcript)
        _write_json(args.out, payload)
    else:
        base_record: Dict[str, Any] = {"metadata": metadata}
        if raw_transcription is not None:
            base_record["raw_transcription"] = raw_transcription
        records = []
        for segment in segments:
            record = dict(base_record)
            record["segment"] = segment
            records.append(record)
        _write_jsonl(args.out, records)

    _append_manifest(
        args.manifest,
        output_path=args.out,
        transcript_path=args.transcript,
        output_format=args.format,
        segments=len(segments),
        metadata_path=args.metadata,
        raw_path=args.raw_json,
    )

    logger.info("Exportação concluída (%d segmentos)", len(segments))


__all__ = ["build_parser", "main"]
