from __future__ import annotations

import json
import os
import stat
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from debugmate.cli import main
from debugmate.results import publisher as publisher_module
from debugmate.results import verifier as verifier_module


def test_publish_full_bundle_is_atomic_deterministic_and_freshly_downloadable(
    candidates, tmp_path: Path
):
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


def test_verifier_and_download_resolver_reject_tamper_and_path_like_member(
    candidates, tmp_path: Path
):
    from debugmate.results.consistency import validate_result_candidates

    bundle = publisher_module.publish_result_bundle(
        tmp_path / "results", validate_result_candidates(*candidates)
    )
    result_root = tmp_path / "results"
    assert (
        verifier_module.resolve_verified_download(
            result_root, bundle.manifest.identity.case_id, bundle.manifest.result_id, "report"
        ).name
        == "report.md"
    )
    with pytest.raises(verifier_module.ResultVerificationError):
        verifier_module.resolve_verified_download(
            result_root, bundle.manifest.identity.case_id, bundle.manifest.result_id, "../report.md"
        )
    report = bundle.path / "report.md"
    os.chmod(report, stat.S_IWRITE)
    report.write_text("tampered", encoding="utf-8")
    with pytest.raises(verifier_module.ResultVerificationError):
        verifier_module.resolve_verified_download(
            result_root, bundle.manifest.identity.case_id, bundle.manifest.result_id, "report"
        )


def test_verifier_rejects_manifest_hash_cycles_and_zip_slip(candidates, tmp_path: Path):
    from debugmate.results.consistency import validate_result_candidates

    bundle = publisher_module.publish_result_bundle(
        tmp_path / "results", validate_result_candidates(*candidates)
    )
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
    os.chmod(manifest_path, stat.S_IWRITE)
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(verifier_module.ResultVerificationError):
        verifier_module.verify_result_bundle(bundle.path)


def test_publish_audio_partial_uses_only_the_partial_archive_and_safe_tts_retry(
    candidates, tmp_path: Path
):
    from tests.results.conftest import _FailAdapter

    from debugmate.results.audio import TrustedCandidateRoot, TtsFallbackChain
    from debugmate.results.consistency import validate_result_candidates
    from debugmate.results.tts.base import TtsRequestIdentity

    source, presentation, report, citations, card, recap, _audio = candidates
    unavailable = TtsFallbackChain(
        (_FailAdapter("dify"), _FailAdapter("edge_tts"), _FailAdapter("sapi"))
    ).synthesize(
        recap,
        TtsRequestIdentity(
            case_id=recap.identity.case_id,
            source_run_id=recap.identity.source_run_id,
            diagnosis_sha256=recap.identity.diagnosis_sha256,
            generation_version=recap.identity.generation_version,
            recap_sha256=recap.sha256,
        ),
        TrustedCandidateRoot.for_testing(tmp_path / "partial-private"),
    )

    bundle = publisher_module.publish_result_bundle(
        tmp_path / "results",
        validate_result_candidates(
            source, presentation, report, citations, card, recap, unavailable
        ),
    )

    assert bundle.manifest.status.value == "partial"
    assert bundle.manifest.failure.retry_scope == "tts"
    assert (bundle.path / "debugmate-result-partial.zip").is_file()
    assert not (bundle.path / "recap.mp3").exists()


def test_publisher_rejects_a_handcrafted_partial_candidate(candidates, tmp_path: Path):
    from tests.results.conftest import _FailAdapter

    from debugmate.results.audio import TrustedCandidateRoot, TtsFallbackChain
    from debugmate.results.consistency import validate_result_candidates
    from debugmate.results.tts.base import TtsRequestIdentity

    source, presentation, report, citations, card, recap, _audio = candidates
    unavailable = TtsFallbackChain(
        (_FailAdapter("dify"), _FailAdapter("edge_tts"), _FailAdapter("sapi"))
    ).synthesize(
        recap,
        TtsRequestIdentity(
            case_id=recap.identity.case_id,
            source_run_id=recap.identity.source_run_id,
            diagnosis_sha256=recap.identity.diagnosis_sha256,
            generation_version=recap.identity.generation_version,
            recap_sha256=recap.sha256,
        ),
        TrustedCandidateRoot.for_testing(tmp_path / "forged-private"),
    )
    valid = validate_result_candidates(
        source, presentation, report, citations, card, recap, unavailable
    )

    with pytest.raises(publisher_module.ResultPublishError, match="candidate_invalid"):
        publisher_module.publish_result_bundle(
            tmp_path / "results", replace(valid, _token=object())
        )


def test_result_verify_cli_accepts_only_root_and_strict_identifiers(
    candidates, tmp_path: Path, capsys
):
    from debugmate.results.consistency import validate_result_candidates

    root = tmp_path / "results"
    bundle = publisher_module.publish_result_bundle(root, validate_result_candidates(*candidates))

    assert (
        main(
            [
                "result-verify",
                "--root",
                str(root),
                "--case-id",
                bundle.manifest.identity.case_id,
                "--result-id",
                bundle.manifest.result_id,
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert "path" not in payload


def test_independent_full_rebuilds_have_identical_fixed_archive_metadata(
    candidates, tmp_path: Path
):
    from tests.results.conftest import _AudioAdapter, _FailAdapter

    from debugmate.results.audio import TrustedCandidateRoot, TtsFallbackChain
    from debugmate.results.consistency import validate_result_candidates
    from debugmate.results.tts.base import TtsRequestIdentity

    source, presentation, report, citations, card, recap, audio = candidates
    first = publisher_module.publish_result_bundle(
        tmp_path / "first", validate_result_candidates(*candidates)
    )
    request = TtsRequestIdentity(
        case_id=recap.identity.case_id,
        source_run_id=recap.identity.source_run_id,
        diagnosis_sha256=recap.identity.diagnosis_sha256,
        generation_version=recap.identity.generation_version,
        recap_sha256=recap.sha256,
    )
    rebuilt_audio = TtsFallbackChain(
        (_AudioAdapter(), _FailAdapter("edge_tts"), _FailAdapter("sapi"))
    ).synthesize(recap, request, TrustedCandidateRoot.for_testing(tmp_path / "second-private"))
    second = publisher_module.publish_result_bundle(
        tmp_path / "second",
        validate_result_candidates(
            source, presentation, report, citations, card, recap, rebuilt_audio
        ),
    )

    assert (first.path / "debugmate-result.zip").read_bytes() == (
        second.path / "debugmate-result.zip"
    ).read_bytes()
    with zipfile.ZipFile(first.path / "debugmate-result.zip") as archive:
        for info in archive.infolist():
            assert info.create_system == 3
            assert info.external_attr == 0o100444 << 16
            assert info.extra == b"" and info.comment == b""
            assert info.date_time == (1980, 1, 1, 0, 0, 0)


def test_verifier_rejects_extra_file_and_atomic_failure_leaves_no_temp_or_final(
    candidates, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from debugmate.results.consistency import validate_result_candidates

    first = publisher_module.publish_result_bundle(
        tmp_path / "published", validate_result_candidates(*candidates)
    )
    (first.path / "unexpected.txt").write_text("not allowed", encoding="utf-8")
    with pytest.raises(verifier_module.ResultVerificationError):
        verifier_module.verify_result_bundle(first.path)

    from tests.results.conftest import _AudioAdapter, _FailAdapter

    from debugmate.results.audio import TrustedCandidateRoot, TtsFallbackChain
    from debugmate.results.tts.base import TtsRequestIdentity

    source, presentation, report, citations, card, recap, _audio = candidates
    request = TtsRequestIdentity(
        case_id=recap.identity.case_id,
        source_run_id=recap.identity.source_run_id,
        diagnosis_sha256=recap.identity.diagnosis_sha256,
        generation_version=recap.identity.generation_version,
        recap_sha256=recap.sha256,
    )
    fresh_audio = TtsFallbackChain(
        (_AudioAdapter(), _FailAdapter("edge_tts"), _FailAdapter("sapi"))
    ).synthesize(recap, request, TrustedCandidateRoot.for_testing(tmp_path / "failed-private"))

    def interrupted(*_args, **_kwargs):
        raise verifier_module.ResultVerificationError("interrupted")

    monkeypatch.setattr(verifier_module, "verify_result_bundle", interrupted)
    with pytest.raises(publisher_module.ResultPublishError):
        publisher_module.publish_result_bundle(
            tmp_path / "failed",
            validate_result_candidates(
                source, presentation, report, citations, card, recap, fresh_audio
            ),
        )
    failed_root = tmp_path / "failed"
    assert not list(failed_root.rglob(".tmp-result_*")) if failed_root.exists() else True
    assert not list(failed_root.rglob("result_*")) if failed_root.exists() else True


def test_verifier_rejects_zip_slip_and_oversized_archive_members(candidates, tmp_path: Path):
    from tests.results.conftest import _AudioAdapter, _FailAdapter

    from debugmate.results.audio import TrustedCandidateRoot, TtsFallbackChain
    from debugmate.results.consistency import validate_result_candidates
    from debugmate.results.tts.base import TtsRequestIdentity

    bundle = publisher_module.publish_result_bundle(
        tmp_path / "results", validate_result_candidates(*candidates)
    )
    archive_path = bundle.path / "debugmate-result.zip"

    def rewrite(extra_name: str, extra_payload: bytes) -> None:
        with zipfile.ZipFile(archive_path) as original:
            members = [(info.filename, original.read(info)) for info in original.infolist()]
        os.chmod(archive_path, stat.S_IWRITE)
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as rewritten:
            for name, payload in members:
                rewritten.writestr(name, extra_payload if name == extra_name else payload)
            if extra_name not in {name for name, _payload in members}:
                rewritten.writestr(extra_name, extra_payload)

    rewrite("../outside.txt", b"escape")
    with pytest.raises(verifier_module.ResultVerificationError):
        verifier_module.verify_result_bundle(bundle.path)

    source, presentation, report, citations, card, recap, _audio = candidates
    request = TtsRequestIdentity(
        case_id=recap.identity.case_id,
        source_run_id=recap.identity.source_run_id,
        diagnosis_sha256=recap.identity.diagnosis_sha256,
        generation_version=recap.identity.generation_version,
        recap_sha256=recap.sha256,
    )
    fresh_audio = TtsFallbackChain(
        (_AudioAdapter(), _FailAdapter("edge_tts"), _FailAdapter("sapi"))
    ).synthesize(recap, request, TrustedCandidateRoot.for_testing(tmp_path / "second-private"))
    fresh = publisher_module.publish_result_bundle(
        tmp_path / "second",
        validate_result_candidates(
            source, presentation, report, citations, card, recap, fresh_audio
        ),
    )
    archive_path = fresh.path / "debugmate-result.zip"
    rewrite("report.md", b"0" * (publisher_module.MAX_MEMBER_BYTES + 1))
    with pytest.raises(verifier_module.ResultVerificationError):
        verifier_module.verify_result_bundle(fresh.path)


def test_verifier_rejects_stale_version_and_download_file_swap(candidates, tmp_path: Path):
    from tests.results.conftest import _AudioAdapter, _FailAdapter

    from debugmate.results.audio import TrustedCandidateRoot, TtsFallbackChain
    from debugmate.results.consistency import validate_result_candidates
    from debugmate.results.tts.base import TtsRequestIdentity

    result_root = tmp_path / "results"
    bundle = publisher_module.publish_result_bundle(
        result_root, validate_result_candidates(*candidates)
    )
    manifest_path = bundle.path / "result-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["manifest_version"] = "2.0.0"
    os.chmod(manifest_path, stat.S_IWRITE)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(verifier_module.ResultVerificationError):
        verifier_module.resolve_verified_download(
            result_root,
            bundle.manifest.identity.case_id,
            bundle.manifest.result_id,
            "bundle",
        )

    source, presentation, report, citations, card, recap, _audio = candidates
    request = TtsRequestIdentity(
        case_id=recap.identity.case_id,
        source_run_id=recap.identity.source_run_id,
        diagnosis_sha256=recap.identity.diagnosis_sha256,
        generation_version=recap.identity.generation_version,
        recap_sha256=recap.sha256,
    )
    fresh_audio = TtsFallbackChain(
        (_AudioAdapter(), _FailAdapter("edge_tts"), _FailAdapter("sapi"))
    ).synthesize(recap, request, TrustedCandidateRoot.for_testing(tmp_path / "swap-private"))
    second = publisher_module.publish_result_bundle(
        tmp_path / "swap",
        validate_result_candidates(
            source, presentation, report, citations, card, recap, fresh_audio
        ),
    )
    report = second.path / "report.md"
    os.chmod(report, stat.S_IWRITE)
    report.unlink()
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    try:
        report.symlink_to(outside)
    except OSError:
        pytest.skip("Windows symlink privilege is not available for this test process")
    with pytest.raises(verifier_module.ResultVerificationError):
        verifier_module.resolve_verified_download(
            tmp_path / "swap",
            second.manifest.identity.case_id,
            second.manifest.result_id,
            "report",
        )
