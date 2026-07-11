from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from debugmate.contracts import CapabilityStatus
from debugmate.evidence import (
    MANIFEST_VERSION,
    ArtifactEntry,
    AudioEvidenceNotReady,
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
    interrupted.write_bytes("partial.txt", b"partial", "text/plain")
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
    bundle.write_bytes("artifact.txt", b"original", "text/plain")
    final_path = bundle.finalize(make_manifest(case_id))
    (final_path / "artifact.txt").write_bytes(b"tampered")
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
        bundle.write_bytes(Path("C:/absolute.txt"), b"x", "text/plain")
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


def _png_with_text_metadata(value: str) -> bytes:
    from io import BytesIO

    output = BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Comment", value)
    Image.new("RGB", (2, 2), "white").save(output, format="PNG", pnginfo=metadata)
    return output.getvalue()


def _mp3_frame(payload: bytes = b"\x00" * 32) -> bytes:
    return b"\xff\xfb\x90\x64" + payload


def test_generic_writer_rejects_privacy_sensitive_binary_formats(tmp_path: Path) -> None:
    bundle = EvidenceBundle.begin(tmp_path / "evidence", "case_eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")

    with pytest.raises(UnsafeEvidenceContent, match="write_png"):
        bundle.write_bytes("card.png", _png_with_text_metadata("safe"), "image/png")
    with pytest.raises(UnsafeEvidenceContent, match="not publishable"):
        bundle.write_bytes("recap.mp3", b"ID3\x04\x00\x00safe", "audio/mpeg")

    assert not (bundle.temp_path / "card.png").exists()
    assert not (bundle.temp_path / "recap.mp3").exists()


@pytest.mark.parametrize(
    "payload",
    [_png_with_text_metadata("student@example.com"), _mp3_frame(b"student@example.com")],
)
def test_generic_writer_rejects_binary_magic_disguised_as_octet_stream(
    tmp_path: Path, payload: bytes
) -> None:
    bundle = EvidenceBundle.begin(tmp_path / "evidence", "case_17171717171717171717171717171717")

    with pytest.raises(UnsafeEvidenceContent):
        bundle.write_bytes("artifact.bin", payload, "application/octet-stream")

    assert not (bundle.temp_path / "artifact.bin").exists()


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be"])
def test_generic_writer_scans_artifact_bin_email_before_rejecting_without_echo(
    tmp_path: Path, encoding: str
) -> None:
    sentinel = "student@example.com"
    bundle = EvidenceBundle.begin(tmp_path / "evidence", "case_24242424242424242424242424242424")

    with pytest.raises(UnsafeEvidenceContent) as caught:
        bundle.write_bytes("artifact.bin", sentinel.encode(encoding), "application/octet-stream")

    assert sentinel not in str(caught.value)
    assert "unsupported evidence type" not in str(caught.value)
    assert not (bundle.temp_path / "artifact.bin").exists()


def test_generic_writer_rejects_even_benign_unknown_binary_type(tmp_path: Path) -> None:
    bundle = EvidenceBundle.begin(tmp_path / "evidence", "case_25252525252525252525252525252525")

    with pytest.raises(UnsafeEvidenceContent, match="unsupported evidence type"):
        bundle.write_bytes("artifact.bin", b"benign bytes", "application/octet-stream")

    assert not (bundle.temp_path / "artifact.bin").exists()


def test_png_writer_strips_sensitive_text_metadata_before_publish(tmp_path: Path) -> None:
    case_id = "case_ffffffffffffffffffffffffffffffff"
    sentinel = "student@example.com"
    bundle = EvidenceBundle.begin(tmp_path / "evidence", case_id)

    bundle.write_png("card.png", _png_with_text_metadata(sentinel))
    final_path = bundle.finalize(make_manifest(case_id))

    published = (final_path / "card.png").read_bytes()
    assert sentinel.encode() not in published
    with Image.open(final_path / "card.png") as image:
        assert image.info == {}
    assert verify_bundle(final_path).ok is True


def test_generated_audio_is_deferred_and_never_executes_unrelated_callback(
    tmp_path: Path,
) -> None:
    bundle = EvidenceBundle.begin(tmp_path / "evidence", "case_12121212121212121212121212121212")
    callback_calls: list[str] = []

    with pytest.raises(AudioEvidenceNotReady, match="Phase 4"):
        bundle.write_generated_audio(
            "recap.mp3",
            "fictional safe recap",
            lambda text: (callback_calls.append(text) or (_mp3_frame(), "audio/mpeg")),
        )

    assert callback_calls == []
    assert not (bundle.temp_path / "recap.mp3").exists()


@pytest.mark.parametrize(
    "payload",
    [_png_with_text_metadata("student@example.com"), _mp3_frame(b"student@example.com")],
)
def test_finalize_rejects_binary_magic_hidden_behind_generic_contract(
    tmp_path: Path, payload: bytes
) -> None:
    case_id = "case_20202020202020202020202020202020"
    bundle = EvidenceBundle.begin(tmp_path / "evidence", case_id)
    target = bundle.write_bytes("artifact.txt", b"safe text", "text/plain")
    target.write_bytes(payload)

    with pytest.raises(UnsafeEvidenceContent):
        bundle.finalize(make_manifest(case_id))

    assert not bundle.final_path.exists()


def test_finalize_rejects_unrecognized_binary_hidden_behind_text_contract(
    tmp_path: Path,
) -> None:
    case_id = "case_27272727272727272727272727272727"
    bundle = EvidenceBundle.begin(tmp_path / "evidence", case_id)
    target = bundle.write_bytes("artifact.txt", b"safe text", "text/plain")
    target.write_bytes(b"\x00\xff\x00\xfe\x01\x80")

    with pytest.raises(UnsafeEvidenceContent, match="valid UTF-8"):
        bundle.finalize(make_manifest(case_id))

    assert not bundle.final_path.exists()


@pytest.mark.parametrize(
    "payload",
    [_png_with_text_metadata("student@example.com"), _mp3_frame(b"student@example.com")],
)
def test_verifier_detects_binary_magic_with_generic_name_and_mime(
    tmp_path: Path, payload: bytes
) -> None:
    case_id = "case_22222222222222222222222222222222"
    root = tmp_path / case_id
    root.mkdir()
    artifact = root / "artifact.bin"
    artifact.write_bytes(payload)
    manifest = make_manifest(case_id).model_copy(
        update={
            "artifacts": [
                ArtifactEntry.model_validate(
                    artifact_metadata(root, Path("artifact.bin"), "application/octet-stream")
                )
            ]
        }
    )
    (root / "manifest.json").write_bytes(
        canonical_json_bytes(manifest.model_dump(mode="json")) + b"\n"
    )

    result = verify_bundle(root)

    assert result.ok is False
    assert any(issue.startswith("unsafe ") for issue in result.issues)


def test_finalize_rechecks_png_after_temporary_artifact_tamper(tmp_path: Path) -> None:
    case_id = "case_15151515151515151515151515151515"
    bundle = EvidenceBundle.begin(tmp_path / "evidence", case_id)
    target = bundle.write_png("card.png", _png_with_text_metadata("safe"))
    target.write_bytes(_png_with_text_metadata("student@example.com"))

    with pytest.raises(UnsafeEvidenceContent):
        bundle.finalize(make_manifest(case_id))

    assert not bundle.final_path.exists()
    assert not (bundle.temp_path / "manifest.json").exists()


def test_verifier_rejects_hash_valid_png_with_sensitive_metadata(tmp_path: Path) -> None:
    case_id = "case_14141414141414141414141414141414"
    root = tmp_path / case_id
    root.mkdir()
    artifact = root / "card.png"
    artifact.write_bytes(_png_with_text_metadata("student@example.com"))
    manifest = make_manifest(case_id).model_copy(
        update={
            "artifacts": [
                ArtifactEntry.model_validate(artifact_metadata(root, Path("card.png"), "image/png"))
            ]
        }
    )
    (root / "manifest.json").write_bytes(
        canonical_json_bytes(manifest.model_dump(mode="json")) + b"\n"
    )

    result = verify_bundle(root)

    assert result.ok is False
    assert "unsafe PNG artifact: card.png" in result.issues


def test_verifier_rejects_hash_valid_audio_with_sensitive_bytes(tmp_path: Path) -> None:
    case_id = "case_16161616161616161616161616161616"
    root = tmp_path / case_id
    root.mkdir()
    artifact = root / "recap.mp3"
    artifact.write_bytes(b"ID3\x04\x00\x00student@example.com")
    manifest = make_manifest(case_id).model_copy(
        update={
            "artifacts": [
                ArtifactEntry.model_validate(
                    artifact_metadata(root, Path("recap.mp3"), "audio/mpeg")
                )
            ]
        }
    )
    (root / "manifest.json").write_bytes(
        canonical_json_bytes(manifest.model_dump(mode="json")) + b"\n"
    )

    result = verify_bundle(root)

    assert result.ok is False
    assert "unsafe audio artifact: recap.mp3" in result.issues


def test_verifier_rejects_hash_valid_benign_audio_and_unknown_binary(tmp_path: Path) -> None:
    case_id = "case_26262626262626262626262626262626"
    root = tmp_path / case_id
    root.mkdir()
    audio = root / "recap.mp3"
    binary = root / "artifact.bin"
    audio.write_bytes(_mp3_frame(b"benign"))
    binary.write_bytes(b"benign bytes")
    entries = [
        ArtifactEntry.model_validate(artifact_metadata(root, Path("recap.mp3"), "audio/mpeg")),
        ArtifactEntry.model_validate(
            artifact_metadata(root, Path("artifact.bin"), "application/octet-stream")
        ),
    ]
    manifest = make_manifest(case_id).model_copy(update={"artifacts": entries})
    (root / "manifest.json").write_bytes(
        canonical_json_bytes(manifest.model_dump(mode="json")) + b"\n"
    )

    result = verify_bundle(root)

    assert result.ok is False
    assert "unsafe audio artifact: recap.mp3" in result.issues
    assert "unsupported evidence artifact: artifact.bin" in result.issues


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
