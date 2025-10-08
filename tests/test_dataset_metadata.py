from __future__ import annotations

import json
from pathlib import Path

import pytest

from oratiotranscripta.annotate import _compute_metrics
from oratiotranscripta.annotate.metadata import DatasetMetadata


@pytest.fixture()
def metadata_tmp(tmp_path: Path) -> Path:
    content = {
        "project": "Arquivo Histórico",
        "event": "Entrevista",
        "participants": [
            {"name": "Maria", "aliases": ["M."], "role": "Entrevistada"},
            {"name": "João", "aliases": ["J."]},
        ],
        "dates": ["2024-01-20"],
        "coverage": {"spatial": "Brasil"},
        "license": "CC-BY",
        "editors": ["Equipe"],
    }
    path = tmp_path / "metadata.yaml"
    path.write_text(json.dumps(content), encoding="utf-8")
    return path


def test_validate_speakers_accepts_aliases(metadata_tmp: Path) -> None:
    metadata = DatasetMetadata.from_mapping(json.loads(metadata_tmp.read_text(encoding="utf-8")))
    metadata.validate_speakers({"Maria", "J."})


def test_validate_speakers_raises_for_unknown(metadata_tmp: Path) -> None:
    metadata = DatasetMetadata.from_mapping(json.loads(metadata_tmp.read_text(encoding="utf-8")))
    with pytest.raises(ValueError) as excinfo:
        metadata.validate_speakers({"Maria", "José"})
    assert "José" in str(excinfo.value)


def test_compute_metrics_uses_canonical_names(metadata_tmp: Path) -> None:
    metadata = DatasetMetadata.from_mapping(json.loads(metadata_tmp.read_text(encoding="utf-8")))
    segments = [
        {"speaker": {"id": "spk0", "name": "M."}, "start": 0.0, "end": 2.0},
        {
            "speaker": {"id": "spk1"},
            "speaker_name": "João",
            "start": 2.0,
            "end": 4.5,
        },
    ]
    metrics = _compute_metrics(segments, metadata)
    assert metrics["segment_count"] == 2
    assert metrics["utterances_per_participant"] == {"Maria": 1, "João": 1}
    assert metrics["duration_seconds"] == pytest.approx(4.5)
