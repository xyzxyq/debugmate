from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from debugmate.contracts import ErrorCategory
from debugmate.diagnosis.extraction import (
    CaseFact,
    CaseFacts,
    FieldId,
    SourceKind,
    fact_id_for,
    facts_hash,
)
from debugmate.diagnosis.routing import DecisionStage, route_case
from debugmate.knowledge.local_rule import (
    LocalRuleRetrievalProvider,
    LocalRuleSnapshotError,
    load_local_rule_snapshot,
)

CASE_ID = "case_90909090909090909090909090909090"
SNAPSHOT_RELATIVE_PATH = Path("knowledge/snapshots/local-rule")


def _snapshot_dir(root: Path) -> Path:
    return root / SNAPSHOT_RELATIVE_PATH


def _copy_valid_snapshot_tree(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(SNAPSHOT_RELATIVE_PATH, _snapshot_dir(root))
    return root


def _manifest_path(root: Path) -> Path:
    return _snapshot_dir(root) / "manifest.json"


def _payload_path(root: Path) -> Path:
    return _snapshot_dir(root) / "module-not-found.json"


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _rewrite_manifest(root: Path, *, payload_file: str) -> None:
    manifest = json.loads(_manifest_path(root).read_text(encoding="utf-8"))
    manifest["files"][0]["file"] = payload_file
    _write_json(_manifest_path(root), manifest)


def _rewrite_valid_manifest(root: Path) -> None:
    manifest = json.loads(_manifest_path(root).read_text(encoding="utf-8"))
    payload = _payload_path(root)
    manifest["files"] = [
        {
            "file": payload.name,
            "sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
        }
    ]
    _write_json(_manifest_path(root), manifest)


def _facts(*, exception_type: str) -> CaseFacts:
    fact = CaseFact(
        fact_id=fact_id_for(FieldId.EXCEPTION_TYPE, exception_type),
        field_id=FieldId.EXCEPTION_TYPE,
        value=exception_type,
        provenance_candidate_ids=[],
        source_kinds=[SourceKind.USER],
        confidence=1.0,
    )
    return CaseFacts(
        case_id=CASE_ID,
        revision=0,
        facts_sha256=facts_hash(CASE_ID, 0, [fact], []),
        facts=[fact],
        applied_corrections=[],
    )


def test_local_rule_loader_rejects_missing_or_tampered_payload(tmp_path: Path) -> None:
    root = _copy_valid_snapshot_tree(tmp_path)
    payload = root / "knowledge/snapshots/local-rule/module-not-found.json"
    payload.write_text("{}\n", encoding="utf-8")
    with pytest.raises(LocalRuleSnapshotError, match="sha256"):
        load_local_rule_snapshot(root)

    root = _copy_valid_snapshot_tree(tmp_path / "missing")
    _payload_path(root).unlink()
    with pytest.raises(LocalRuleSnapshotError):
        load_local_rule_snapshot(root)


def test_local_rule_loader_rejects_escape_extra_or_nonofficial_source(tmp_path: Path) -> None:
    root = _copy_valid_snapshot_tree(tmp_path)
    _rewrite_manifest(root, payload_file="../tests/diagnosis.json")
    with pytest.raises(LocalRuleSnapshotError):
        load_local_rule_snapshot(root)
    _rewrite_valid_manifest(root)
    (root / "knowledge/snapshots/local-rule/untracked.json").write_text(
        "{}", encoding="utf-8"
    )
    with pytest.raises(LocalRuleSnapshotError, match="untracked"):
        load_local_rule_snapshot(root)

    root = _copy_valid_snapshot_tree(tmp_path / "source")
    payload = json.loads(_payload_path(root).read_text(encoding="utf-8"))
    payload["retrieval"]["source_url"] = "https://example.com/python-exceptions"
    _write_json(_payload_path(root), payload)
    _rewrite_valid_manifest(root)
    with pytest.raises(LocalRuleSnapshotError):
        load_local_rule_snapshot(root)


def test_local_rule_loader_rejects_unknown_manifest_or_payload_keys(tmp_path: Path) -> None:
    root = _copy_valid_snapshot_tree(tmp_path)
    manifest = json.loads(_manifest_path(root).read_text(encoding="utf-8"))
    manifest["extra"] = "not allowed"
    _write_json(_manifest_path(root), manifest)
    with pytest.raises(LocalRuleSnapshotError):
        load_local_rule_snapshot(root)

    root = _copy_valid_snapshot_tree(tmp_path / "payload")
    payload = json.loads(_payload_path(root).read_text(encoding="utf-8"))
    payload["extra"] = "not allowed"
    _write_json(_payload_path(root), payload)
    _rewrite_valid_manifest(root)
    with pytest.raises(LocalRuleSnapshotError):
        load_local_rule_snapshot(root)


def test_committed_local_rule_snapshot_loads_and_retrieves_one_anchor() -> None:
    snapshot = load_local_rule_snapshot(Path.cwd())

    assert snapshot.version == "local-rule-v1"
    assert (
        snapshot.rule.retrieval.source_url
        == "https://docs.python.org/3/library/exceptions.html"
    )
    assert snapshot.rule.retrieval.locator == "ModuleNotFoundError"

    facts = _facts(exception_type="ModuleNotFoundError")
    routing = route_case(facts, decision_stage=DecisionStage.FINAL)
    assert routing.category is ErrorCategory.DEPENDENCY_ENVIRONMENT

    anchors = LocalRuleRetrievalProvider(snapshot).retrieve(facts, routing)

    assert len(anchors) == 1
    assert anchors[0].knowledge_build_id == snapshot.knowledge_build_id


def test_local_rule_provider_returns_no_data_for_nonmatching_route() -> None:
    snapshot = load_local_rule_snapshot(Path.cwd())
    facts = _facts(exception_type="PermissionError")
    routing = route_case(facts, decision_stage=DecisionStage.FINAL)

    assert LocalRuleRetrievalProvider(snapshot).retrieve(facts, routing) == []
