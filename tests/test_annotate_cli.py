from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oratiotranscripta.annotate import build_parser
from oratiotranscripta.annotate import _resolve_manifest_path, SENTINEL


def _parse_args(tmp_path: Path, *extra: str):
    parser = build_parser()
    transcript = tmp_path / "edited.srt"
    transcript.write_text("", encoding="utf-8")
    argv = ["--transcript", str(transcript), *extra]
    return parser.parse_args(argv)


def test_manifest_absent_returns_none(tmp_path):
    args = _parse_args(tmp_path)
    assert _resolve_manifest_path(args) is None


def test_manifest_explicit_path(tmp_path):
    args = _parse_args(tmp_path, "--manifest", str(tmp_path / "custom.json"))
    resolved = _resolve_manifest_path(args)
    assert resolved == tmp_path / "custom.json"


def test_manifest_auto_from_out_file(tmp_path):
    out_file = tmp_path / "publish" / "mesa.annotated.jsonl"
    args = _parse_args(tmp_path, "--out", str(out_file), "--manifest")
    assert args.manifest is SENTINEL
    resolved = _resolve_manifest_path(args)
    assert resolved == out_file.with_suffix(".manifest.json")


def test_manifest_auto_from_out_directory(tmp_path):
    out_dir = tmp_path / "publish"
    out_dir.mkdir()
    args = _parse_args(tmp_path, "--out", str(out_dir), "--manifest")
    resolved = _resolve_manifest_path(args)
    assert resolved == out_dir / "manifest.json"


def test_manifest_auto_uses_transcript_when_out_missing(tmp_path, monkeypatch):
    args = _parse_args(tmp_path, "--manifest")
    resolved = _resolve_manifest_path(args)
    expected = (tmp_path / "edited.srt").with_suffix(".manifest.json")
    assert resolved == expected


def test_manifest_auto_prefers_transcript_when_out_stdout(tmp_path):
    args = _parse_args(tmp_path, "--out", "-", "--manifest")
    resolved = _resolve_manifest_path(args)
    expected = (tmp_path / "edited.srt").with_suffix(".manifest.json")
    assert resolved == expected


def test_manifest_auto_falls_back_to_cwd_when_everything_stdout(tmp_path, monkeypatch):
    parser = build_parser()
    args = parser.parse_args(["--transcript", "-", "--out", "-", "--manifest"])
    cwd = tmp_path / "work"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    resolved = _resolve_manifest_path(args)
    assert resolved == cwd / "manifest.json"
