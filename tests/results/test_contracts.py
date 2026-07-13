from __future__ import annotations

import importlib.metadata
import json
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_dependency_versions_are_exactly_pinned_and_installed() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = set(config["project"]["dependencies"])
    assert "gradio==6.20.0" in dependencies
    assert "edge-tts==7.2.8" in dependencies
    assert "playwright==1.61.0" in dependencies
    assert importlib.metadata.version("gradio") == "6.20.0"
    assert importlib.metadata.version("edge-tts") == "7.2.8"
    assert importlib.metadata.version("playwright") == "1.61.0"


def test_default_marker_expression_excludes_external_and_real_media_gates() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    addopts = config["tool"]["pytest"]["ini_options"]["addopts"]
    for marker in ("cloud", "ocr", "network", "browser", "tts"):
        assert f"not {marker}" in addopts


def test_unmarked_fake_media_test_is_collected_by_default() -> None:
    assert b"ID3".startswith(b"ID3")


def test_committed_replay_fixture_strictly_validates_and_verifies(
    completed_source_bundle,
) -> None:
    outcome, source = completed_source_bundle
    index = json.loads((ROOT / "fixtures/replay/index.json").read_text(encoding="utf-8"))
    row = index["fixtures"][0]
    assert row["fixture_id"] == "module-not-found"
    assert row["case_id"] == outcome.case_id
    assert row["run_id"] == outcome.run_id
    assert row["outcome_path"] == "module-not-found/outcome.json"
    assert row["source_path"].startswith("module-not-found/source/case_")
    assert ":" not in row["outcome_path"] and ":" not in row["source_path"]
    assert source.name == outcome.run_id


def test_replay_fixture_regeneration_is_canonical(tmp_path: Path) -> None:
    target = tmp_path / "replay"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/generate-replay-fixture.py"), str(target)],
        cwd=ROOT,
        check=True,
    )
    committed = ROOT / "fixtures/replay/module-not-found"
    outcome = json.loads((committed / "outcome.json").read_text(encoding="utf-8"))
    source_prefix = f"source/{outcome['case_id']}/{outcome['run_id']}/"
    for name in (
        "outcome.json",
        source_prefix + "extraction.json",
        source_prefix + "case-facts.json",
        source_prefix + "sufficiency.json",
        source_prefix + "routing.json",
        source_prefix + "retrieval.json",
        source_prefix + "diagnosis.json",
        source_prefix + "manifest.json",
    ):
        assert (target / "module-not-found" / name).read_bytes() == (committed / name).read_bytes()
