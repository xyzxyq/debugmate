from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

import debugmate.knowledge.local_rule as local_rule
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
    payload_sha256 = hashlib.sha256(payload.read_bytes()).hexdigest()
    manifest["files"] = [
        {
            "file": payload.name,
            "sha256": payload_sha256,
        }
    ]
    manifest["knowledge_build_id"] = payload_sha256
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


def test_local_rule_loader_binds_build_id_to_actual_payload_sha256(tmp_path: Path) -> None:
    root = _copy_valid_snapshot_tree(tmp_path)
    manifest = json.loads(_manifest_path(root).read_text(encoding="utf-8"))
    manifest["knowledge_build_id"] = "f" * 64
    _write_json(_manifest_path(root), manifest)

    with pytest.raises(LocalRuleSnapshotError, match="knowledge_build_id|sha256"):
        load_local_rule_snapshot(root)


def _symlink_or_skip(link: Path, target: Path, *, target_is_directory: bool) -> None:
    try:
        link.symlink_to(target, target_is_directory=target_is_directory)
    except OSError:
        pytest.skip("symlinks are unavailable for this Windows account")


@pytest.mark.parametrize("component", ["knowledge", "snapshots", "local-rule"])
def test_local_rule_loader_rejects_symlinked_snapshot_path_component(
    tmp_path: Path, component: str
) -> None:
    root = tmp_path / component / "project"
    root.mkdir(parents=True)
    knowledge = root / "knowledge"
    snapshots = knowledge / "snapshots"
    snapshot = snapshots / "local-rule"
    if component == "knowledge":
        target = root / "real-knowledge"
        shutil.copytree(SNAPSHOT_RELATIVE_PATH, target / "snapshots/local-rule")
        _symlink_or_skip(knowledge, target, target_is_directory=True)
    elif component == "snapshots":
        knowledge.mkdir()
        target = root / "real-snapshots"
        shutil.copytree(SNAPSHOT_RELATIVE_PATH, target / "local-rule")
        _symlink_or_skip(snapshots, target, target_is_directory=True)
    else:
        target = root / "real-local-rule"
        shutil.copytree(SNAPSHOT_RELATIVE_PATH, target)
        snapshots.mkdir(parents=True)
        _symlink_or_skip(snapshot, target, target_is_directory=True)

    with pytest.raises(LocalRuleSnapshotError, match="symlink"):
        load_local_rule_snapshot(root)


@pytest.mark.parametrize("name", ["manifest.json", "module-not-found.json"])
def test_local_rule_loader_rejects_symlinked_snapshot_file(
    tmp_path: Path, name: str
) -> None:
    root = _copy_valid_snapshot_tree(tmp_path)
    path = _snapshot_dir(root) / name
    target = _snapshot_dir(root) / f"{name}.data"
    path.replace(target)
    _symlink_or_skip(path, target, target_is_directory=False)

    with pytest.raises(LocalRuleSnapshotError, match="symlink"):
        load_local_rule_snapshot(root)


@pytest.mark.parametrize("relative", [Path("nested/untracked.json"), Path("extra.txt")])
def test_local_rule_loader_rejects_any_untracked_tree_content(
    tmp_path: Path, relative: Path
) -> None:
    root = _copy_valid_snapshot_tree(tmp_path)
    untracked = _snapshot_dir(root) / relative
    untracked.parent.mkdir(parents=True, exist_ok=True)
    untracked.write_text("{}", encoding="utf-8")

    with pytest.raises(LocalRuleSnapshotError, match="untracked"):
        load_local_rule_snapshot(root)


@pytest.mark.parametrize("escape_kind", ["absolute", "parent"])
def test_payload_escape_is_rejected_before_any_escape_metadata_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, escape_kind: str
) -> None:
    root = _copy_valid_snapshot_tree(tmp_path)
    payload_file = (
        str((tmp_path / "outside.json").resolve())
        if escape_kind == "absolute"
        else "../outside.json"
    )
    _rewrite_manifest(root, payload_file=payload_file)
    probed: list[Path] = []
    original_is_link = local_rule._is_link

    def spy_is_link(path: Path) -> bool:
        probed.append(path)
        return original_is_link(path)

    monkeypatch.setattr(local_rule, "_is_link", spy_is_link)

    with pytest.raises(LocalRuleSnapshotError, match="escapes"):
        load_local_rule_snapshot(root)

    resolved_root = root.resolve()
    snapshot = resolved_root / SNAPSHOT_RELATIVE_PATH
    assert probed == [
        root,
        resolved_root / "knowledge",
        resolved_root / "knowledge/snapshots",
        snapshot,
        snapshot / "manifest.json",
    ]


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
    with pytest.raises(LocalRuleSnapshotError, match="source_url"):
        load_local_rule_snapshot(root)


def test_local_rule_loader_rejects_unknown_manifest_or_payload_keys(tmp_path: Path) -> None:
    root = _copy_valid_snapshot_tree(tmp_path)
    manifest = json.loads(_manifest_path(root).read_text(encoding="utf-8"))
    manifest["extra"] = "not allowed"
    _write_json(_manifest_path(root), manifest)
    with pytest.raises(LocalRuleSnapshotError, match="manifest.*unknown keys"):
        load_local_rule_snapshot(root)

    root = _copy_valid_snapshot_tree(tmp_path / "payload")
    payload = json.loads(_payload_path(root).read_text(encoding="utf-8"))
    payload["extra"] = "not allowed"
    _write_json(_payload_path(root), payload)
    _rewrite_valid_manifest(root)
    with pytest.raises(LocalRuleSnapshotError, match="payload.*unknown keys"):
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
