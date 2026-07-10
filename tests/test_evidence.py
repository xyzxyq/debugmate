from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from debugmate.contracts import CapabilityStatus
from debugmate.evidence import (
    MANIFEST_VERSION,
    ArtifactEntry,
    CapabilityEvidence,
    EvidenceBundle,
    RunManifest,
    RunStatus,
    UnsafeEvidenceContent,
    verify_bundle,
)
from debugmate.hashing import (
    UnsafeArtifactPath,
    artifact_metadata,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from debugmate.settings import DebugMateSettings, find_secret_leaks


def make_manifest(case_id: str, status: RunStatus = RunStatus.PASSED) -> RunManifest:
    now = datetime.now(UTC)
    return RunManifest(
        manifest_version=MANIFEST_VERSION,
        case_id=case_id,
        status=status,
        created_at_utc=now,
        completed_at_utc=now,
        backend="fixture",
        workflow_version="fixture-v1",
        prompt_version="none",
        schema_version="1.0.0",
        knowledge_version="none",
        input_sha256="0" * 64,
        run_id=f"fixture:{case_id}",
        node_states={"fixture": "passed"},
        latency_ms=1,
        token_usage={"input": 0, "output": 0},
        estimated_cost=0.0,
        artifacts=[],
        probe_capabilities=[],
    )


def test_canonical_json_is_deterministic_and_utf8() -> None:
    first = canonical_json_bytes({"z": 1, "中文": [True, None], "a": "x"})
    second = canonical_json_bytes({"a": "x", "中文": [True, None], "z": 1})

    assert first == second
    assert first == b'{"a":"x","z":1,"\xe4\xb8\xad\xe6\x96\x87":[true,null]}'


def test_sha256_helpers_and_artifact_metadata(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    root.mkdir()
    artifact = root / "nested" / "report.json"
    artifact.parent.mkdir()
    artifact.write_bytes(b'{"ok":true}')

    metadata = artifact_metadata(root, Path("nested/report.json"), "application/json")

    assert sha256_bytes(artifact.read_bytes()) == sha256_file(artifact)
    assert re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"])
    assert metadata == {
        "path": "nested/report.json",
        "mime_type": "application/json",
        "bytes": 11,
        "sha256": sha256_file(artifact),
    }


@pytest.mark.parametrize(
    "path",
    [Path("../escape.txt"), Path("nested/../../escape.txt"), Path("C:/absolute.txt")],
)
def test_artifact_metadata_rejects_unsafe_paths(tmp_path: Path, path: Path) -> None:
    with pytest.raises(UnsafeArtifactPath):
        artifact_metadata(tmp_path, path, "text/plain")


def test_artifact_metadata_rejects_symlink_escape_when_supported(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    target = outside / "secret.txt"
    target.write_text("secret", encoding="utf-8")
    link = root / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable for this Windows account")

    with pytest.raises(UnsafeArtifactPath):
        artifact_metadata(root, Path("link.txt"), "text/plain")


def test_settings_never_serialize_secret_values() -> None:
    sentinel = "SECRET_SENTINEL_DO_NOT_LOG"
    settings = DebugMateSettings.from_env(
        {
            "DIFY_BASE_URL": "https://api.dify.ai/v1",
            "DIFY_API_KEY": sentinel,
            "DIFY_DATASET_API_KEY": f"dataset-{sentinel}",
            "DIFY_USER": "debugmate-test",
        }
    )

    rendered = "\n".join(
        [
            repr(settings),
            str(settings),
            repr(settings.model_dump()),
            settings.model_dump_json(),
            repr(settings.safe_summary()),
        ]
    )
    assert sentinel not in rendered
    assert settings.cloud_configured is True
    assert settings.safe_summary() == {
        "dify_base_url": "https://api.dify.ai/v1",
        "dify_user": "debugmate-test",
        "dify_api_key_configured": True,
        "dify_dataset_api_key_configured": True,
        "cloud_configured": True,
    }


def test_empty_environment_uses_safe_defaults() -> None:
    settings = DebugMateSettings.from_env({})

    assert settings.cloud_configured is False
    assert settings.safe_summary()["dify_base_url"] == "https://api.dify.ai/v1"
    assert settings.safe_summary()["dify_user"] == "debugmate-local"


def test_secret_leak_detector_returns_paths_without_secret_values() -> None:
    sentinel = "SECRET_SENTINEL_DO_NOT_LOG"
    value = {
        "safe": "hello",
        "nested": [{"header": f"Bearer {sentinel}"}, sentinel],
    }

    leaks = find_secret_leaks(value, [sentinel, ""])

    assert leaks == ["$.nested[0].header", "$.nested[1]"]
    assert sentinel not in repr(leaks)


def test_passed_bundle_is_atomic_hash_linked_and_verifiable(tmp_path: Path) -> None:
    case_id = "case_11111111111111111111111111111111"
    bundle = EvidenceBundle.begin(tmp_path / "evidence", case_id)
    bundle.write_json("input.redacted.json", {"error": "fictional"})
    bundle.write_json("diagnosis.json", {"case_id": case_id})

    final_path = bundle.finalize(make_manifest(case_id))
    verification = verify_bundle(final_path)

    assert final_path == tmp_path / "evidence" / case_id
    assert not (tmp_path / "evidence" / f".tmp-{case_id}").exists()
    assert (final_path / "manifest.json").is_file()
    assert verification.ok is True
    assert verification.issues == []
    assert verification.manifest is not None
    assert {entry.path for entry in verification.manifest.artifacts} == {
        "input.redacted.json",
        "diagnosis.json",
    }


def test_failed_bundle_has_explicit_safe_manifest(tmp_path: Path) -> None:
    case_id = "case_22222222222222222222222222222222"
    bundle = EvidenceBundle.begin(tmp_path / "evidence", case_id)
    bundle.write_json("input.redacted.json", {"error": "fictional"})

    final_path = bundle.fail("E_FIXTURE", "fixture validation failed safely")
    verification = verify_bundle(final_path)

    assert verification.ok is True
    assert verification.manifest is not None
    assert verification.manifest.status is RunStatus.FAILED
    assert verification.manifest.error_code == "E_FIXTURE"
    manifest_text = (final_path / "manifest.json").read_text(encoding="utf-8")
    assert "Traceback" not in manifest_text
    assert "Authorization" not in manifest_text


def test_duplicate_or_interrupted_bundle_never_looks_successful(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    case_id = "case_33333333333333333333333333333333"
    first = EvidenceBundle.begin(root, case_id)
    first.write_json("input.redacted.json", {"ok": True})
    first.finalize(make_manifest(case_id))

    with pytest.raises(FileExistsError):
        EvidenceBundle.begin(root, case_id)

    interrupted_id = "case_44444444444444444444444444444444"
    interrupted = EvidenceBundle.begin(root, interrupted_id)
    interrupted.write_bytes("partial.bin", b"partial", "application/octet-stream")
    assert not (root / interrupted_id).exists()
    assert not (root / interrupted_id / "manifest.json").exists()


def test_verifier_detects_missing_manifest_tamper_and_unlisted_file(tmp_path: Path) -> None:
    missing = tmp_path / "case_55555555555555555555555555555555"
    missing.mkdir()
    (missing / "orphan.txt").write_text("x", encoding="utf-8")
    assert verify_bundle(missing).ok is False
    assert "manifest.json is missing" in verify_bundle(missing).issues

    case_id = "case_66666666666666666666666666666666"
    bundle = EvidenceBundle.begin(tmp_path / "evidence", case_id)
    bundle.write_bytes("artifact.bin", b"original", "application/octet-stream")
    final_path = bundle.finalize(make_manifest(case_id))
    (final_path / "artifact.bin").write_bytes(b"tampered")
    tampered = verify_bundle(final_path)
    assert tampered.ok is False
    assert any("sha256 mismatch" in issue for issue in tampered.issues)

    other_id = "case_77777777777777777777777777777777"
    other = EvidenceBundle.begin(tmp_path / "evidence", other_id)
    other.write_json("listed.json", {"ok": True})
    other_path = other.finalize(make_manifest(other_id))
    (other_path / "unlisted.txt").write_text("not in manifest", encoding="utf-8")
    unlisted = verify_bundle(other_path)
    assert unlisted.ok is False
    assert any("unlisted artifact" in issue for issue in unlisted.issues)


def test_verifier_detects_case_directory_mismatch(tmp_path: Path) -> None:
    case_id = "case_88888888888888888888888888888888"
    bundle = EvidenceBundle.begin(tmp_path / "evidence", case_id)
    bundle.write_json("artifact.json", {"ok": True})
    final_path = bundle.finalize(make_manifest(case_id))
    renamed = final_path.with_name("case_99999999999999999999999999999999")
    final_path.rename(renamed)

    result = verify_bundle(renamed)

    assert result.ok is False
    assert any("case_id does not match directory" in issue for issue in result.issues)


def test_bundle_rejects_absolute_paths_and_unsafe_failure_text(tmp_path: Path) -> None:
    case_id = "case_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    bundle = EvidenceBundle.begin(tmp_path / "evidence", case_id)

    with pytest.raises(UnsafeArtifactPath):
        bundle.write_bytes(Path("C:/absolute.bin"), b"x", "application/octet-stream")
    with pytest.raises(UnsafeEvidenceContent):
        bundle.fail("E_UNSAFE", "Authorization: Bearer SECRET_SENTINEL_DO_NOT_LOG")


def test_bundle_rejects_local_absolute_path_in_manifest(tmp_path: Path) -> None:
    case_id = "case_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    bundle = EvidenceBundle.begin(tmp_path / "evidence", case_id)
    bundle.write_json("artifact.json", {"ok": True})
    manifest = make_manifest(case_id).model_copy(update={"backend": r"C:\Users\student\demo"})

    with pytest.raises(UnsafeEvidenceContent):
        bundle.finalize(manifest)


def test_artifact_entry_rejects_nonportable_path() -> None:
    with pytest.raises(ValueError):
        ArtifactEntry(
            path="../escape.json",
            mime_type="application/json",
            bytes=1,
            sha256="0" * 64,
        )


@pytest.mark.parametrize(
    ("evidence_path", "evidence_sha"),
    [("missing.json", "1" * 64), ("artifact.json", "2" * 64)],
)
def test_passed_capability_must_link_to_matching_manifest_artifact(
    evidence_path: str, evidence_sha: str
) -> None:
    case_id = "case_dddddddddddddddddddddddddddddddd"
    manifest = make_manifest(case_id)
    payload = manifest.model_dump()
    payload["artifacts"] = [
        ArtifactEntry(
            path="artifact.json",
            mime_type="application/json",
            bytes=2,
            sha256="1" * 64,
        )
    ]
    payload["probe_capabilities"] = [
        CapabilityEvidence(
            capability_id="C01",
            status=CapabilityStatus.PASS,
            evidence_path=evidence_path,
            sha256=evidence_sha,
        )
    ]

    with pytest.raises(ValueError):
        RunManifest.model_validate(payload)
