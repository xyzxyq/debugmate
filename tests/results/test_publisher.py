from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from debugmate.results import publisher as publisher_module
from debugmate.results import verifier as verifier_module


def test_publish_full_bundle_is_atomic_deterministic_and_freshly_downloadable(candidates, tmp_path: Path):
    from debugmate.results.consistency import validate_result_candidates

    validated = validate_result_candidates(*candidates)
    first = publisher_module.publish_result_bundle(tmp_path / "results", validated)
    second = publisher_module.publish_result_bundle(tmp_path / "results", validated)

    assert first.path == second.path
    assert verifier_module.verify_result_bundle(first.path).manifest == first.manifest
    assert (first.path / "debugmate-result.zip").read_bytes() == (
        second.path / "debugmate-result.zip"
    ).read_bytes()
    assert {member.name for member in first.path.iterdir()} == {
        "diagnosis.json",
        "report.md",
        "card.png",
        "recap.txt",
        "recap.mp3",
        "citations.json",
        "source-manifest.json",
        "result-manifest.json",
        "checksums.sha256",
        "debugmate-result.zip",
        "publication.json",
    }
    with zipfile.ZipFile(first.path / "debugmate-result.zip") as archive:
        assert archive.namelist() == sorted(archive.namelist())
        assert "publication.json" not in archive.namelist()
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())


def test_verifier_and_download_resolver_reject_tamper_and_path_like_member(candidates, tmp_path: Path):
    from debugmate.results.consistency import validate_result_candidates

    bundle = publisher_module.publish_result_bundle(tmp_path / "results", validate_result_candidates(*candidates))
    result_root = tmp_path / "results"
    assert verifier_module.resolve_verified_download(
        result_root, bundle.manifest.identity.case_id, bundle.manifest.result_id, "report"
    ).name == "report.md"
    with pytest.raises(verifier_module.ResultVerificationError):
        verifier_module.resolve_verified_download(
            result_root, bundle.manifest.identity.case_id, bundle.manifest.result_id, "../report.md"
        )
    (bundle.path / "report.md").write_text("tampered", encoding="utf-8")
    with pytest.raises(verifier_module.ResultVerificationError):
        verifier_module.resolve_verified_download(
            result_root, bundle.manifest.identity.case_id, bundle.manifest.result_id, "report"
        )


def test_verifier_rejects_manifest_hash_cycles_and_zip_slip(candidates, tmp_path: Path):
    from debugmate.results.consistency import validate_result_candidates

    bundle = publisher_module.publish_result_bundle(tmp_path / "results", validate_result_candidates(*candidates))
    manifest_path = bundle.path / "result-manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["artifacts"].append(
        {
            "kind": "report",
            "path": "result-manifest.json",
            "mime_type": "application/json",
            "bytes": 1,
            "sha256": "0" * 64,
            "identity": data["identity"],
        }
    )
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(verifier_module.ResultVerificationError):
        verifier_module.verify_result_bundle(bundle.path)
