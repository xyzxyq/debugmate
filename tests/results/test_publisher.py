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


def _trusted_root(path: Path):
    return publisher_module.TrustedResultRoot.for_testing(path)


def _rewrite_publication_archive_hash(bundle, archive_bytes: bytes) -> None:
    from debugmate.hashing import canonical_json_bytes, sha256_bytes

    archive = bundle.path / bundle.archive_name
    os.chmod(archive, stat.S_IWRITE)
    archive.write_bytes(archive_bytes)
    publication = bundle.path / "publication.json"
    payload = json.loads(publication.read_text(encoding="utf-8"))
    payload["archive_sha256"] = sha256_bytes(archive_bytes)
    os.chmod(publication, stat.S_IWRITE)
    publication.write_bytes(canonical_json_bytes(payload))


def test_publisher_requires_factory_issued_root_and_private_candidate_snapshot(
    candidates, tmp_path: Path
):
    from debugmate.results.consistency import validate_result_candidates

    candidate = validate_result_candidates(*candidates)
    expected_report = candidate.report_bytes
    object.__setattr__(candidate, "report_bytes", b"forged publisher input")

    with pytest.raises(publisher_module.ResultPublishError, match="candidate_invalid"):
        publisher_module.publish_result_bundle(tmp_path / "raw-results", candidate)

    bundle = publisher_module.publish_result_bundle(
        _trusted_root(tmp_path / "results"), candidate
    )
    assert (bundle.path / "report.md").read_bytes() == expected_report


def test_publisher_rejects_a_concurrent_candidate_checkout(candidates, tmp_path: Path):
    from debugmate.results.consistency import (
        checkout_verified_candidate_for_publication,
        release_verified_candidate_checkout,
        validate_result_candidates,
    )

    candidate = validate_result_candidates(*candidates)
    checkout_verified_candidate_for_publication(candidate)
    try:
        with pytest.raises(publisher_module.ResultPublishError, match="candidate_busy"):
            publisher_module.publish_result_bundle(
                _trusted_root(tmp_path / "results"), candidate
            )
    finally:
        release_verified_candidate_checkout(candidate)


def test_audio_handoff_is_not_consumed_until_after_transaction_begin(
    candidates, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from debugmate.results.audio import AudioHandoff
    from debugmate.results.consistency import validate_result_candidates

    calls: list[str] = []
    original_take = AudioHandoff.take_verified_bytes

    def tracked_take(self, audio):
        calls.append("take")
        return original_take(self, audio)

    monkeypatch.setattr(AudioHandoff, "take_verified_bytes", tracked_take)
    candidate = validate_result_candidates(*candidates)
    assert calls == []

    def transaction_failure(*_arguments, **_kwargs):
        raise publisher_module.ResultPublishError("transaction_failed")

    monkeypatch.setattr(publisher_module, "_begin_transaction", transaction_failure)
    with pytest.raises(publisher_module.ResultPublishError, match="transaction_failed"):
        publisher_module.publish_result_bundle(_trusted_root(tmp_path / "results"), candidate)
    assert calls == []


def test_audio_handoff_consumes_once_after_safe_transaction_starts(
    candidates, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from debugmate.results.audio import AudioHandoff
    from debugmate.results.consistency import validate_result_candidates

    events: list[str] = []
    original_take = AudioHandoff.take_verified_bytes
    original_begin = publisher_module._begin_transaction

    def tracked_take(self, audio):
        events.append("take")
        return original_take(self, audio)

    def tracked_begin(*arguments, **kwargs):
        transaction = original_begin(*arguments, **kwargs)
        events.append("transaction")
        return transaction

    monkeypatch.setattr(AudioHandoff, "take_verified_bytes", tracked_take)
    monkeypatch.setattr(publisher_module, "_begin_transaction", tracked_begin)
    bundle = publisher_module.publish_result_bundle(
        _trusted_root(tmp_path / "results"), validate_result_candidates(*candidates)
    )
    assert events == ["transaction", "take"]
    assert (bundle.path / "recap.mp3").is_file()


def test_temp_directory_reparse_race_never_writes_external_target(
    candidates, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A swap immediately after mkdir must fail before any member write."""

    from debugmate.results.consistency import validate_result_candidates

    external = tmp_path / "external-target"
    external.mkdir()
    real_mkdir = publisher_module.os.mkdir
    raced = False

    def mkdir_with_reparse(path, *args, **kwargs):
        nonlocal raced
        result = real_mkdir(path, *args, **kwargs)
        candidate_path = Path(path)
        if candidate_path.name.startswith(".tmp-result_") and not raced:
            raced = True
            candidate_path.rmdir()
            try:
                candidate_path.symlink_to(external, target_is_directory=True)
            except OSError:
                pytest.skip("this Windows test process cannot create a directory reparse point")
        return result

    monkeypatch.setattr(publisher_module.os, "mkdir", mkdir_with_reparse)
    with pytest.raises(publisher_module.ResultPublishError):
        publisher_module.publish_result_bundle(
            _trusted_root(tmp_path / "results"), validate_result_candidates(*candidates)
        )
    assert raced is True
    assert list(external.iterdir()) == []
    result_root = tmp_path / "results"
    assert not list(result_root.rglob(".tmp-result_*")) if result_root.exists() else True


def test_publish_full_bundle_is_atomic_deterministic_and_freshly_downloadable(
    candidates, tmp_path: Path
):
    from debugmate.results.consistency import validate_result_candidates

    validated = validate_result_candidates(*candidates)
    root = _trusted_root(tmp_path / "results")
    first = publisher_module.publish_result_bundle(root, validated)
    second = publisher_module.publish_result_bundle(root, validated)

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
        _trusted_root(tmp_path / "results"), validate_result_candidates(*candidates)
    )
    result_root = tmp_path / "results"
    download = verifier_module.resolve_verified_download(
        result_root, bundle.manifest.identity.case_id, bundle.manifest.result_id, "report"
    )
    assert download.member_id == "report"
    assert download.read_bytes() == (bundle.path / "report.md").read_bytes()
    assert not hasattr(download, "path")
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


def test_download_is_opaque_one_shot_bytes_not_a_reopenable_path(candidates, tmp_path: Path):
    from debugmate.results.consistency import validate_result_candidates

    root = tmp_path / "results"
    bundle = publisher_module.publish_result_bundle(
        _trusted_root(root), validate_result_candidates(*candidates)
    )
    download = verifier_module.resolve_verified_download(
        root, bundle.manifest.identity.case_id, bundle.manifest.result_id, "report"
    )
    assert not hasattr(download, "path")
    assert download.filename == "report.md"
    assert download.read_bytes() == (bundle.path / "report.md").read_bytes()
    with pytest.raises(verifier_module.ResultVerificationError, match="download_invalid"):
        download.read_bytes()
    with pytest.raises(TypeError):
        verifier_module.VerifiedDownload()


def test_disk_verifier_rederives_citation_url_and_support_graph(candidates, tmp_path: Path):
    """A well-shaped, rehashed citation row still needs diagnosis support."""

    from debugmate.hashing import canonical_json_bytes, sha256_bytes
    from debugmate.results.consistency import validate_result_candidates

    bundle = publisher_module.publish_result_bundle(
        _trusted_root(tmp_path / "results"), validate_result_candidates(*candidates)
    )
    citation_path = bundle.path / "citations.json"
    payload = json.loads(citation_path.read_text(encoding="utf-8"))
    payload["rows"][0]["source_url"] = "https://forged.example.invalid/claim"
    forged_bytes = canonical_json_bytes(payload)
    os.chmod(citation_path, stat.S_IWRITE)
    citation_path.write_bytes(forged_bytes)
    forged_records = tuple(
        record.model_copy(
            update={"bytes": len(forged_bytes), "sha256": sha256_bytes(forged_bytes)}
        )
        if record.kind == "citations"
        else record
        for record in bundle.manifest.artifacts
    )
    forged_manifest = bundle.manifest.model_copy(update={"artifacts": forged_records})

    with pytest.raises(verifier_module.ResultVerificationError, match="citation_verify_failed"):
        verifier_module._validate_business_payloads(bundle.path, forged_manifest)


def test_verifier_rejects_manifest_hash_cycles_and_zip_slip(candidates, tmp_path: Path):
    from debugmate.results.consistency import validate_result_candidates

    bundle = publisher_module.publish_result_bundle(
        _trusted_root(tmp_path / "results"), validate_result_candidates(*candidates)
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
        _trusted_root(tmp_path / "results"),
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
            _trusted_root(tmp_path / "results"), replace(valid, _token=object())
        )


def test_result_verify_cli_accepts_only_root_and_strict_identifiers(
    candidates, tmp_path: Path, capsys
):
    from debugmate.results.consistency import validate_result_candidates

    root = tmp_path / "results"
    bundle = publisher_module.publish_result_bundle(
        _trusted_root(root), validate_result_candidates(*candidates)
    )

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
        _trusted_root(tmp_path / "first"), validate_result_candidates(*candidates)
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
        _trusted_root(tmp_path / "second"),
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
        _trusted_root(tmp_path / "published"), validate_result_candidates(*candidates)
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
            _trusted_root(tmp_path / "failed"),
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
        _trusted_root(tmp_path / "results"), validate_result_candidates(*candidates)
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
        _trusted_root(tmp_path / "second"),
        validate_result_candidates(
            source, presentation, report, citations, card, recap, fresh_audio
        ),
    )
    archive_path = fresh.path / "debugmate-result.zip"
    rewrite("report.md", b"0" * (publisher_module.MAX_MEMBER_BYTES + 1))
    with pytest.raises(verifier_module.ResultVerificationError):
        verifier_module.verify_result_bundle(fresh.path)


def test_zip_bomb_metadata_rejects_before_any_member_open(
    candidates, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Central-directory caps must run before a bomb can be decompressed."""

    from debugmate.results.consistency import validate_result_candidates

    bundle = publisher_module.publish_result_bundle(
        _trusted_root(tmp_path / "results"), validate_result_candidates(*candidates)
    )
    archive_path = bundle.path / "debugmate-result.zip"
    original_infolist = zipfile.ZipFile.infolist
    original_open = zipfile.ZipFile.open
    opened = False

    def forged_infolist(archive: zipfile.ZipFile):
        infos = original_infolist(archive)
        if Path(archive.filename) == archive_path:
            infos[0].file_size = publisher_module.MAX_MEMBER_BYTES + 1
        return infos

    def tracked_open(archive: zipfile.ZipFile, *args, **kwargs):
        nonlocal opened
        if Path(archive.filename) == archive_path:
            opened = True
        return original_open(archive, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "infolist", forged_infolist)
    monkeypatch.setattr(zipfile.ZipFile, "open", tracked_open)
    with pytest.raises(verifier_module.ResultVerificationError, match="archive_verify_failed"):
        verifier_module.verify_result_bundle(bundle.path)
    assert opened is False


@pytest.mark.parametrize(
    ("prefix", "suffix"),
    [
        (b"SFX", b""),
        (b"PK\x03\x04" + b"JUNK" * 200, b""),
        (b"", b"unexpected trailing bytes"),
    ],
)
def test_verifier_rejects_rehashed_zip_preamble_and_trailing_bytes(
    candidates, tmp_path: Path, prefix: bytes, suffix: bytes
):
    from debugmate.results.consistency import validate_result_candidates

    bundle = publisher_module.publish_result_bundle(
        _trusted_root(tmp_path / "results"), validate_result_candidates(*candidates)
    )
    archive = (bundle.path / bundle.archive_name).read_bytes()
    _rewrite_publication_archive_hash(bundle, prefix + archive + suffix)

    with pytest.raises(verifier_module.ResultVerificationError, match="archive_verify_failed"):
        verifier_module.verify_result_bundle(bundle.path)


def test_verifier_rejects_rehashed_oversize_archive_before_hash_or_zip_open(
    candidates, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from debugmate.results.consistency import validate_result_candidates

    bundle = publisher_module.publish_result_bundle(
        _trusted_root(tmp_path / "results"), validate_result_candidates(*candidates)
    )
    archive = (bundle.path / bundle.archive_name).read_bytes()
    oversized = b"P" * (publisher_module.MAX_TOTAL_BYTES + 1) + archive
    _rewrite_publication_archive_hash(bundle, oversized)

    def unexpected_zip_open(*_arguments, **_kwargs):
        raise AssertionError("ZipFile must not open an oversized raw archive")

    monkeypatch.setattr(verifier_module.zipfile, "ZipFile", unexpected_zip_open)
    with pytest.raises(verifier_module.ResultVerificationError, match="archive_verify_failed"):
        verifier_module.verify_result_bundle(bundle.path)


def test_verifier_rejects_stale_version_and_download_file_swap(candidates, tmp_path: Path):
    from tests.results.conftest import _AudioAdapter, _FailAdapter

    from debugmate.results.audio import TrustedCandidateRoot, TtsFallbackChain
    from debugmate.results.consistency import validate_result_candidates
    from debugmate.results.tts.base import TtsRequestIdentity

    result_root = tmp_path / "results"
    bundle = publisher_module.publish_result_bundle(
        _trusted_root(result_root), validate_result_candidates(*candidates)
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
        _trusted_root(tmp_path / "swap"),
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
