"""Utilities for collecting provenance for a transcription run."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Optional, Sequence


def _compute_sha256(path: Path) -> Optional[str]:
    try:
        with path.open("rb") as fh:
            hasher = hashlib.sha256()
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                hasher.update(chunk)
    except OSError:
        return None
    return hasher.hexdigest()


def _collect_environment() -> Mapping[str, str]:
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
        "cwd": os.getcwd(),
    }


def _collect_git_metadata() -> Optional[Mapping[str, object]]:
    repo_dir = Path(__file__).resolve().parent
    try:
        commit = (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_dir, text=True)
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    try:
        status = (
            subprocess.check_output(["git", "status", "--short"], cwd=repo_dir, text=True)
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        status = ""

    return {"commit": commit, "dirty": bool(status)}


def _normalise_path(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _describe_artifacts(paths: Iterable[Path], base: Path) -> Sequence[Mapping[str, object]]:
    artifacts: list[Mapping[str, object]] = []
    for item in paths:
        candidate = Path(item)
        if not candidate.exists():
            artifacts.append({"path": _normalise_path(candidate, base), "exists": False})
            continue
        artifacts.append(
            {
                "path": _normalise_path(candidate, base),
                "exists": True,
                "sha256": _compute_sha256(candidate),
                "size_bytes": candidate.stat().st_size,
            }
        )
    return artifacts


def write_run_manifest(
    out_dir: Path,
    *,
    run_id: str,
    pipeline: Mapping[str, object],
    ingestion: Mapping[str, object],
    software: Mapping[str, object],
    artifacts: Sequence[Path],
    log_files: Sequence[Path] | None = None,
) -> Path:
    """Write a ``run_manifest.json`` file describing the execution provenance."""

    destination_dir = Path(out_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)

    manifest: MutableMapping[str, object] = {
        "run_id": run_id,
        "pipeline": dict(pipeline),
        "ingestion": dict(ingestion),
        "software": dict(software),
        "environment": dict(_collect_environment()),
    }

    git_info = _collect_git_metadata()
    if git_info:
        manifest["source_control"] = git_info

    artifact_entries = _describe_artifacts(artifacts, destination_dir)
    manifest["artifacts"] = artifact_entries

    if log_files:
        manifest["logs"] = _describe_artifacts(log_files, destination_dir)

    hashes: MutableMapping[str, object] = {}
    for key in ("audio_path", "source_path"):
        raw_path = ingestion.get(key)
        if not raw_path:
            continue
        path_obj = Path(str(raw_path))
        digest = _compute_sha256(path_obj)
        if digest:
            hashes[key] = {"sha256": digest, "size_bytes": path_obj.stat().st_size}
    if hashes:
        manifest["hashes"] = hashes

    manifest_path = destination_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


__all__ = ["write_run_manifest"]
