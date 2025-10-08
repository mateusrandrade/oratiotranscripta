"""Utilities for building structured export manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

try:  # pragma: no cover - exercised in fallback path depending on environment
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled when PyYAML missing
    yaml = None

from .metadata import DatasetMetadata


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _describe_file(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if path is None or not path.exists():
        return None
    stat = path.stat()
    return {
        "path": str(path),
        "sha256": _sha256_of(path),
        "size": stat.st_size,
    }


def build_normalised_metadata(
    metadata: DatasetMetadata,
    *,
    metrics: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    payload = metadata.to_dict()
    payload["dates"] = sorted(payload.get("dates", []))
    payload["participant_count"] = len(metadata.participants)
    payload["participants"] = sorted(
        (dict(participant.to_dict()) for participant in metadata.participants),
        key=lambda item: item.get("name", ""),
    )
    if metrics:
        payload.setdefault("statistics", {}).update(dict(metrics))
    return payload


def build_manifest(
    *,
    metadata: Optional[DatasetMetadata],
    metrics: Mapping[str, Any],
    tei_path: Optional[Path],
    jsonl_path: Optional[Path],
    metadata_path: Optional[Path],
    raw_path: Optional[Path],
    pipeline: Optional[Mapping[str, Any]] = None,
    editing: Optional[Mapping[str, Any]] = None,
    checks: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    manifest: Dict[str, Any] = {
        "dataset": {},
        "files": {},
        "pipeline": dict(pipeline or {}),
        "editing": dict(editing or {}),
        "checks": dict(checks or {}),
    }

    if metadata is not None:
        manifest["dataset"]["metadata"] = build_normalised_metadata(
            metadata, metrics=metrics
        )
    if metrics:
        manifest["dataset"].setdefault("metrics", {}).update(dict(metrics))

    files_section: Dict[str, Any] = {}
    raw_key = "raw_segments" if raw_path and raw_path.suffix.lower() == ".jsonl" else "raw"
    file_entries = {
        "tei": _describe_file(tei_path),
        "jsonl": _describe_file(jsonl_path),
        "metadata": _describe_file(metadata_path),
        raw_key: _describe_file(raw_path),
    }
    for key, description in file_entries.items():
        if description:
            files_section[key] = description
    manifest["files"] = files_section

    return manifest


def write_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


def write_metadata_yaml(path: Path, metadata: Mapping[str, Any]) -> Path:
    """Serialise metadata to YAML when available, with JSON fallback.

    Parameters
    ----------
    path:
        Desired output path. When PyYAML is not installed the final file will
        use a ``.json`` suffix irrespective of the provided value.
    metadata:
        Mapping to serialise.

    Returns
    -------
    Path
        The actual path that was written.
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    if yaml is not None:
        if path.suffix.lower() not in {".yml", ".yaml"}:
            path = path.with_suffix(".yml")
        text = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False)
        if not text.endswith("\n"):
            text += "\n"
        path.write_text(text, encoding="utf-8")
        return path

    json_path = path if path.suffix.lower() == ".json" else path.with_suffix(".json")
    text = json.dumps(metadata, ensure_ascii=False, indent=2)
    json_path.write_text(text + "\n", encoding="utf-8")
    return json_path


__all__ = [
    "build_manifest",
    "build_normalised_metadata",
    "write_manifest",
    "write_metadata_yaml",
]

