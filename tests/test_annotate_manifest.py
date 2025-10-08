import hashlib
import importlib.util
import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oratiotranscripta.annotate.manifest import (
    build_manifest,
    build_normalised_metadata,
    write_manifest,
    write_metadata_yaml,
)
from oratiotranscripta.annotate.metadata import DatasetMetadata, Participant


def _make_metadata() -> DatasetMetadata:
    return DatasetMetadata(
        project="Coleção Teste",
        event="Sessão Zero",
        participants=[
            Participant(name="Bruno", role="convidado"),
            Participant(name="Ana", role="mediadora", aliases=["A."]),
        ],
        dates=["2024-03-01", "2024-02-28"],
        coverage={"location": "Online"},
        license="CC-BY-4.0",
        editors=["Equipe"],
    )


def test_build_manifest_and_metadata_bundle(tmp_path):
    metadata = _make_metadata()
    metrics = {"segment_count": 2, "duration_seconds": 3.5}

    tei_path = tmp_path / "transcript.tei.xml"
    tei_path.write_text("<TEI></TEI>", encoding="utf-8")

    jsonl_path = tmp_path / "transcript.jsonl"
    jsonl_path.write_text("{}\n", encoding="utf-8")

    raw_path = tmp_path / "raw_segments.jsonl"
    raw_path.write_text("{}\n", encoding="utf-8")

    metadata_payload = build_normalised_metadata(metadata, metrics=metrics)
    metadata_file = tmp_path / "metadata.yml"
    metadata_file = write_metadata_yaml(metadata_file, metadata_payload)

    manifest = build_manifest(
        metadata=metadata,
        metrics=metrics,
        tei_path=tei_path,
        jsonl_path=jsonl_path,
        metadata_path=metadata_file,
        raw_path=raw_path,
        pipeline={"step": "annotate", "format": "jsonl"},
        editing={"editors": metadata.editors},
        checks={"status": "ok"},
    )

    manifest_path = tmp_path / "manifest.json"
    write_manifest(manifest_path, manifest)

    written_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert set(written_manifest) == {"dataset", "files", "pipeline", "editing", "checks"}
    assert "metadata" in written_manifest["dataset"]
    assert written_manifest["dataset"]["metadata"]["participant_count"] == 2
    assert written_manifest["dataset"]["metadata"]["participants"][0]["name"] == "Ana"
    assert written_manifest["dataset"]["metrics"] == metrics

    files = written_manifest["files"]
    for key in ("tei", "jsonl", "metadata", "raw_segments"):
        assert key in files
        described = files[key]
        expected_path = {
            "tei": tei_path,
            "jsonl": jsonl_path,
            "metadata": metadata_file,
            "raw_segments": raw_path,
        }[key]
        assert described["path"] == str(expected_path)
        assert described["size"] == expected_path.stat().st_size
        expected_hash = hashlib.sha256(expected_path.read_bytes()).hexdigest()
        assert described["sha256"] == expected_hash

    metadata_text = metadata_file.read_text(encoding="utf-8")
    assert "Coleção Teste" in metadata_text

    if importlib.util.find_spec("yaml") is not None:
        import yaml  # type: ignore

        assert metadata_file.suffix == ".yml"
        loaded_metadata = yaml.safe_load(metadata_text)
    else:
        assert metadata_file.suffix == ".json"
        loaded_metadata = json.loads(metadata_text)

    assert loaded_metadata["participant_count"] == 2
    assert loaded_metadata["statistics"]["duration_seconds"] == 3.5
    assert loaded_metadata["dates"] == ["2024-02-28", "2024-03-01"]
