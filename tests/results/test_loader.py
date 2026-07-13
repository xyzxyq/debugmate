from __future__ import annotations

import json
import shutil
import traceback
from pathlib import Path

import pytest

from debugmate.diagnosis.workflow import WorkflowStatus
from debugmate.results.loader import ResultLoadError, load_verified_outcome
from debugmate.results.outcome_store import DiagnosisOutcomeStore


def test_verified_completed_outcome_loads_with_canonical_diagnosis_identity(
    completed_source_bundle,
) -> None:
    outcome, source = completed_source_bundle
    loaded = load_verified_outcome(outcome, evidence_root=source.parents[1])
    assert loaded.outcome == outcome
    assert loaded.diagnosis == outcome.diagnosis
    assert loaded.case_id == outcome.case_id
    assert loaded.source_run_id == outcome.run_id
    assert len(loaded.diagnosis_sha256) == 64
    assert loaded.source_manifest.case_id == outcome.case_id
    assert not hasattr(loaded, "source_path")


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"status": WorkflowStatus.NEEDS_INFORMATION}, "source_outcome_invalid"),
        ({"diagnosis": None}, "source_outcome_invalid"),
        ({"run_id": "run_" + "f" * 32}, "source_outcome_invalid"),
        ({"idempotency_key": "idem_" + "f" * 32}, "source_outcome_invalid"),
        ({"completed_stages": ["input_approved", "published"]}, "source_outcome_invalid"),
        ({"schema_version": "9.9.9"}, "source_outcome_invalid"),
        ({"revision": "0"}, "source_outcome_invalid"),
    ],
)
def test_outcome_forgery_fails_before_result_root_exists(
    completed_source_bundle, tmp_path: Path, changes: dict[str, object], code: str
) -> None:
    outcome, source = completed_source_bundle
    result_root = tmp_path / "results"
    with pytest.raises(ResultLoadError) as caught:
        load_verified_outcome(outcome.model_copy(update=changes), evidence_root=source.parents[1])
    assert caught.value.code == code
    assert caught.value.stage == "source"
    assert not result_root.exists()
    assert str(source) not in str(caught.value)


@pytest.mark.parametrize("mutation", ["missing", "tampered", "unlisted"])
def test_source_bundle_mutations_fail_closed(
    completed_source_bundle, tmp_path: Path, mutation: str
) -> None:
    outcome, source = completed_source_bundle
    evidence_root = tmp_path / "evidence"
    target = evidence_root / outcome.case_id / outcome.run_id
    shutil.copytree(source, target)
    if mutation == "missing":
        (target / "routing.json").unlink()
    elif mutation == "tampered":
        (target / "diagnosis.json").write_text("{}", encoding="utf-8")
    else:
        (target / "unlisted.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ResultLoadError) as caught:
        load_verified_outcome(outcome, evidence_root=evidence_root)
    assert caught.value.code == "source_bundle_invalid"
    assert caught.value.stage == "source"


def test_diagnosis_identity_mismatch_has_fixed_safe_failure(
    completed_source_bundle, tmp_path: Path
) -> None:
    outcome, source = completed_source_bundle
    evidence_root = tmp_path / "evidence"
    target = evidence_root / outcome.case_id / outcome.run_id
    shutil.copytree(source, target)
    payload = json.loads((target / "diagnosis.json").read_text(encoding="utf-8"))
    payload["recap_text"] = "A different but still safe fictional recap."
    (target / "diagnosis.json").write_text(json.dumps(payload), encoding="utf-8")
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    artifact = next(item for item in manifest["artifacts"] if item["path"] == "diagnosis.json")
    raw = (target / "diagnosis.json").read_bytes()
    import hashlib

    artifact["bytes"] = len(raw)
    artifact["sha256"] = hashlib.sha256(raw).hexdigest()
    (target / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ResultLoadError) as caught:
        load_verified_outcome(outcome, evidence_root=evidence_root)
    assert caught.value.code == "diagnosis_identity_mismatch"
    assert str(caught.value) == "result source validation failed"


def test_outcome_store_atomically_roundtrips_and_rejects_duplicate(
    completed_source_bundle, tmp_path: Path
) -> None:
    outcome, _ = completed_source_bundle
    store = DiagnosisOutcomeStore(tmp_path / "outcomes")
    record = store.write(outcome)
    assert record.name == outcome.run_id
    assert store.read(outcome.run_id) == outcome
    with pytest.raises(ResultLoadError) as caught:
        store.write(outcome)
    assert caught.value.code == "outcome_store_invalid"


def test_outcome_store_rejects_tampered_bytes_and_wrong_run_directory(
    completed_source_bundle, tmp_path: Path
) -> None:
    outcome, _ = completed_source_bundle
    store = DiagnosisOutcomeStore(tmp_path / "outcomes")
    record = store.write(outcome)
    (record / "outcome.json").write_bytes((record / "outcome.json").read_bytes() + b" ")
    with pytest.raises(ResultLoadError) as caught:
        store.read(outcome.run_id)
    assert caught.value.code == "outcome_store_invalid"
    with pytest.raises(ResultLoadError):
        store.read("../arbitrary")


def test_source_and_store_reject_symlink_boundaries(
    completed_source_bundle, tmp_path: Path
) -> None:
    outcome, source = completed_source_bundle
    linked = tmp_path / "linked-evidence"
    try:
        linked.symlink_to(source.parents[1], target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ResultLoadError) as caught:
        load_verified_outcome(outcome, evidence_root=linked)
    assert caught.value.code == "source_bundle_invalid"


def test_outcome_store_rejects_a_reparse_ancestor(
    completed_source_bundle, tmp_path: Path
) -> None:
    outcome, _ = completed_source_bundle
    actual = tmp_path / "actual"
    (actual / "child").mkdir(parents=True)
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(actual, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    store = DiagnosisOutcomeStore(linked / "child" / "outcomes")
    with pytest.raises(ResultLoadError) as caught:
        store.write(outcome)
    assert caught.value.code == "outcome_store_invalid"


def _assert_public_error_is_value_free(error: ResultLoadError, forbidden: tuple[str, ...]) -> None:
    assert error.__cause__ is None
    assert error.__context__ is None
    rendered = "".join(traceback.format_exception(error))
    for value in forbidden:
        assert value not in rendered


@pytest.mark.parametrize(
    ("boundary", "expected_code"),
    [
        ("outcome", "source_outcome_invalid"),
        ("bundle", "source_bundle_invalid"),
        ("identity", "diagnosis_identity_mismatch"),
    ],
)
def test_loader_suppresses_raw_exception_chain_at_every_public_boundary(
    completed_source_bundle,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
    expected_code: str,
) -> None:
    import debugmate.results.loader as loader_module

    outcome, source = completed_source_bundle
    forbidden = ("Bearer SECRET_LEAK", "C:\\Users\\private", "provider response body")

    def explode(_outcome):
        raise RuntimeError(" | ".join(forbidden))

    if boundary == "outcome":
        monkeypatch.setattr(loader_module, "validate_diagnosis_outcome", explode)
    elif boundary == "bundle":
        monkeypatch.setattr(loader_module, "verify_bundle", explode)
    else:
        class ExplodingDiagnosisRecord:
            model_validate_json = staticmethod(explode)

        monkeypatch.setattr(loader_module, "DiagnosisRecord", ExplodingDiagnosisRecord)
    with pytest.raises(ResultLoadError) as caught:
        load_verified_outcome(outcome, evidence_root=source.parents[1])
    assert caught.value.code == expected_code
    _assert_public_error_is_value_free(caught.value, forbidden)


def test_store_suppresses_raw_exception_chain_at_public_boundary(
    completed_source_bundle, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import debugmate.results.outcome_store as store_module

    outcome, _ = completed_source_bundle
    forbidden = ("Bearer SECRET_LEAK", str(tmp_path), "provider response body")

    def explode(_outcome):
        raise RuntimeError(" | ".join(forbidden))

    monkeypatch.setattr(store_module, "_strict_outcome", explode)
    with pytest.raises(ResultLoadError) as caught:
        DiagnosisOutcomeStore(tmp_path / "outcomes").write(outcome)
    _assert_public_error_is_value_free(caught.value, forbidden)


def test_store_read_suppresses_raw_exception_chain_at_public_boundary(
    completed_source_bundle, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import debugmate.results.outcome_store as store_module

    outcome, _ = completed_source_bundle
    store = DiagnosisOutcomeStore(tmp_path / "outcomes")
    store.write(outcome)
    forbidden = ("Bearer SECRET_LEAK", str(tmp_path), "provider response body")

    def explode(_outcome):
        raise RuntimeError(" | ".join(forbidden))

    monkeypatch.setattr(store_module, "_strict_outcome", explode)
    with pytest.raises(ResultLoadError) as caught:
        store.read(outcome.run_id)
    _assert_public_error_is_value_free(caught.value, forbidden)


def test_loaded_source_node_states_are_immutable_and_byte_stable(
    completed_source_bundle,
) -> None:
    from debugmate.hashing import canonical_json_bytes
    from debugmate.results.loader import LoadedDiagnosisSource

    outcome, source = completed_source_bundle
    loaded = load_verified_outcome(outcome, evidence_root=source.parents[1])
    with pytest.raises(AttributeError):
        loaded.source_manifest.node_states.append(("forged", "completed"))
    raw = canonical_json_bytes(loaded.model_dump(mode="json"))
    restored = LoadedDiagnosisSource.model_validate_json(raw, strict=True)
    assert canonical_json_bytes(restored.model_dump(mode="json")) == raw
