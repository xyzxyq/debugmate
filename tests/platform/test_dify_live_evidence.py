from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

import debugmate.dify_live_evidence as live_evidence
from debugmate.dify_live_evidence import (
    TARGET_TEXT,
    build_request_manifest,
    canonical_request_sha256,
    validate_c03_record,
    validate_c04_record,
    validate_candidate_tree,
    validate_published_tree,
)

SAFE_INPUTS: dict[str, object] = {
    "error_text": "",
    "code": "",
    "environment": {},
    "generation_request": {},
    "request_kind": "live_vision_evidence",
    "schema_version": "1.0.0",
    "issues": {},
    "candidate": {},
}


def _png(path: Path) -> Path:
    path.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
    return path


def _c03_record(tmp_path: Path) -> dict[str, object]:
    image = _png(tmp_path / "input-terminal.png")
    manifest = build_request_manifest(
        image_path=image,
        non_image_inputs=SAFE_INPUTS,
        upload_id="uploaded-file-id",
    )
    manifest_path = tmp_path / "workflow-request-manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return {
        "capability_id": "C03",
        "status": "pass",
        "attempted_at_utc": "2026-08-09T00:00:00Z",
        "input_image": image.name,
        "request_manifest": manifest_path.name,
        "request_sha256": canonical_request_sha256(manifest["request"]),
        "upload_id_sha256": manifest["upload_id_sha256"],
        "workflow_run_id_sha256": "a" * 64,
        "source_kind": "vlm",
        "extracted_text": TARGET_TEXT,
        "target_text_sha256": manifest["target_text_sha256"],
        "reason_code": None,
    }


@pytest.mark.parametrize(
    "field",
    [
        "error_text",
        "code",
        "environment",
        "generation_request",
        "issues",
        "candidate",
        "unexpected_new_field",
    ],
)
def test_c03_rejects_target_in_every_non_image_input(tmp_path: Path, field: str) -> None:
    image = _png(tmp_path / "input-terminal.png")
    unsafe = dict(SAFE_INPUTS)
    unsafe[field] = {"nested": TARGET_TEXT.swapcase()}

    with pytest.raises(ValueError, match="target text"):
        build_request_manifest(
            image_path=image,
            non_image_inputs=unsafe,
            upload_id="uploaded-file-id",
        )


@pytest.mark.parametrize("field", ["observed_facts", "evidence", "routing", "facts"])
def test_c03_rejects_prebuilt_fact_fields(tmp_path: Path, field: str) -> None:
    image = _png(tmp_path / "input-terminal.png")
    unsafe = dict(SAFE_INPUTS)
    unsafe[field] = []

    with pytest.raises(ValueError, match="prebuilt"):
        build_request_manifest(
            image_path=image,
            non_image_inputs=unsafe,
            upload_id="uploaded-file-id",
        )


def test_c03_pass_requires_png_manifest_vlm_exact_match_and_real_run(tmp_path: Path) -> None:
    record = _c03_record(tmp_path)
    assert validate_c03_record(record, tmp_path)["status"] == "pass"

    for patch in (
        {"source_kind": "ocr"},
        {"extracted_text": TARGET_TEXT + " extra"},
        {"workflow_run_id_sha256": None},
        {"upload_id_sha256": None},
    ):
        with pytest.raises(ValueError):
            validate_c03_record(record | patch, tmp_path)


def test_c03_accepts_only_ordered_exact_multi_fact_coverage(tmp_path: Path) -> None:
    record = _c03_record(tmp_path) | {
        "extracted_text": None,
        "extracted_facts": [
            "ModuleNotFoundError",
            "No module named 'debugmate_demo_pkg'",
        ],
        "extraction_match_kind": "ordered_exact_coverage",
    }
    assert validate_c03_record(record, tmp_path)["status"] == "pass"

    with pytest.raises(ValueError, match="exact target"):
        validate_c03_record(
            record
            | {
                "extracted_facts": [
                    "ModuleNotFoundError",
                    "unrelated text",
                    "No module named 'debugmate_demo_pkg'",
                ]
            },
            tmp_path,
        )
    with pytest.raises(ValueError, match="exact target"):
        validate_c03_record(
            record
            | {
                "extracted_facts": [
                    "No module named 'debugmate_demo_pkg'",
                    "ModuleNotFoundError",
                ]
            },
            tmp_path,
        )


def test_c04_pass_requires_direct_node_resource_and_source_metadata(tmp_path: Path) -> None:
    resource = {
        "source_kind": "knowledge_retrieval_node_resource",
        "workflow_run_id_sha256": "b" * 64,
        "node_run_id_sha256": "c" * 64,
        "hits": [
            {
                "chunk_id": "chunk-1",
                "content_summary": "Python import resolution guidance.",
                "source_id": "python-errors",
                "source_title": "Python Errors and Exceptions",
                "source_url": "https://docs.python.org/3/tutorial/errors.html",
                "locator": "#exceptions",
                "relevance_score": None,
            }
        ],
    }
    resource_path = tmp_path / "retriever-resource.json"
    resource_path.write_text(json.dumps(resource), encoding="utf-8")
    record = {
        "capability_id": "C04",
        "status": "pass",
        "attempted_at_utc": "2026-08-09T00:00:00Z",
        "retriever_resource": resource_path.name,
        "retriever_resource_sha256": hashlib.sha256(resource_path.read_bytes()).hexdigest(),
        "reason_code": None,
    }

    assert validate_c04_record(record, tmp_path)["status"] == "pass"
    resource["source_kind"] = "diagnosis.evidence"
    resource_path.write_text(json.dumps(resource), encoding="utf-8")
    record["retriever_resource_sha256"] = hashlib.sha256(
        resource_path.read_bytes()
    ).hexdigest()
    with pytest.raises(ValueError, match="direct Knowledge Retrieval"):
        validate_c04_record(record, tmp_path)


def test_c04_rejects_structurally_valid_resource_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resource_path = tmp_path / "retriever-resource.json"
    resource = {
        "source_kind": "knowledge_retrieval_node_resource",
        "workflow_run_id_sha256": "b" * 64,
        "node_run_id_sha256": "c" * 64,
        "hits": [
            {
                "chunk_id": "chunk-1",
                "content_summary": "Original direct retrieval evidence.",
                "source_id": "python-errors",
                "source_title": "Python Errors and Exceptions",
                "source_url": "https://docs.python.org/3/tutorial/errors.html",
                "locator": "#exceptions",
                "relevance_score": None,
            }
        ],
    }
    resource_path.write_text(json.dumps(resource), encoding="utf-8")
    record = {
        "capability_id": "C04",
        "status": "pass",
        "attempted_at_utc": "2026-08-09T00:00:00Z",
        "retriever_resource": resource_path.name,
        "retriever_resource_sha256": hashlib.sha256(resource_path.read_bytes()).hexdigest(),
        "reason_code": None,
    }

    assert validate_c04_record(record, tmp_path)["status"] == "pass"
    resource["hits"][0]["content_summary"] = "Valid structure, replaced content."
    resource_path.write_text(json.dumps(resource), encoding="utf-8")

    with pytest.raises(ValueError, match="retriever resource hash mismatch"):
        validate_c04_record(record, tmp_path)
    monkeypatch.setattr("debugmate.dify_live_evidence._git_tracked", lambda *_: True)
    with pytest.raises(ValueError, match="retriever resource hash mismatch"):
        validate_c04_record(
            record, tmp_path, publication_repository_root=tmp_path
        )


def test_candidate_tree_rejects_secret_and_personal_path(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    unsafe = evidence / "unsafe.json"
    unsafe.write_text('{"authorization":"Bearer secret-value"}', encoding="utf-8")
    with pytest.raises(ValueError, match="sensitive"):
        validate_candidate_tree(tmp_path, evidence)

    unsafe.write_text('{"path":"C:\\\\Users\\\\student\\\\secret"}', encoding="utf-8")
    with pytest.raises(ValueError, match="personal absolute path"):
        validate_candidate_tree(tmp_path, evidence)


@pytest.mark.parametrize(
    "untracked_name",
    [
        "dsl-roundtrip-evidence.json",
        "source.dsl.yml",
        "reexport.dsl.yml",
        "reconstructed-output.json",
    ],
)
def test_published_c06_requires_record_and_inner_artifacts_tracked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, untracked_name: str
) -> None:
    evidence = tmp_path / "evidence"
    combined_dir = evidence / "c03-c04"
    c06_dir = evidence / "c06"
    combined_dir.mkdir(parents=True)
    c06_dir.mkdir()
    for name in (
        "input.png",
        "manifest.json",
        "retriever.json",
        "source.dsl.yml",
        "reexport.dsl.yml",
        "reconstructed-output.json",
    ):
        (evidence / name).write_text("fixture", encoding="utf-8")
    (combined_dir / "vision-retrieval-evidence.json").write_text(
        json.dumps(
            {
                "c03": {
                    "capability_id": "C03",
                    "status": "pass",
                    "attempted_at_utc": "2026-08-09T00:00:00Z",
                    "input_image": "input.png",
                    "request_manifest": "manifest.json",
                },
                "c04": {
                    "capability_id": "C04",
                    "status": "pass",
                    "attempted_at_utc": "2026-08-09T00:00:00Z",
                    "retriever_resource": "retriever.json",
                },
            }
        ),
        encoding="utf-8",
    )
    (c06_dir / "dsl-roundtrip-evidence.json").write_text(
        json.dumps(
            {
                "capability_id": "C06",
                "status": "pass",
                "attempted_at_utc": "2026-08-09T00:00:00Z",
                "source_dsl": "evidence/source.dsl.yml",
                "reexport_dsl": "evidence/reexport.dsl.yml",
                "reconstructed_output": "evidence/reconstructed-output.json",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(live_evidence, "validate_candidate_tree", lambda *_: {})
    monkeypatch.setattr(live_evidence, "validate_c04_record", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        live_evidence,
        "_git_tracked",
        lambda _root, path: path.name != untracked_name,
    )

    with pytest.raises(ValueError, match="not Git tracked"):
        validate_published_tree(tmp_path, evidence)


def test_published_capability_matrix_matches_independent_live_records() -> None:
    repository = Path.cwd().resolve()
    matrix = json.loads(
        (repository / "platform/dify/capability-matrix.json").read_text(encoding="utf-8")
    )
    expected = {
        "C01": (
            "pass",
            "evidence/dify-live/2026-08-08/cloud-probe/"
            "case_d2c4d21672c14d9bad7f7fe95ee86653/dify-upload.json",
            "608ebdbd5990f3e09f6cafd1682ff25441057768e1c59506e611531831b3cab1",
        ),
        "C02": (
            "pass",
            "evidence/dify-live/2026-08-08/cloud-probe/"
            "case_d2c4d21672c14d9bad7f7fe95ee86653/dify-upload.json",
            "608ebdbd5990f3e09f6cafd1682ff25441057768e1c59506e611531831b3cab1",
        ),
        "C03": (
            "pass",
            "evidence/dify-live/2026-08-09/c03-c04/vision-retrieval-evidence.json",
            "5be859005686b254a7432d3dba3ce93af760be3636db3f3529346bf82d5e9384",
        ),
        "C04": (
            "pass",
            "evidence/dify-live/2026-08-09/c03-c04/vision-retrieval-evidence.json",
            "5be859005686b254a7432d3dba3ce93af760be3636db3f3529346bf82d5e9384",
        ),
        "C05": (
            "pass",
            "evidence/dify-live/2026-08-08/cloud-probe/"
            "case_d2c4d21672c14d9bad7f7fe95ee86653/diagnosis.json",
            "75b2d9a8c2b555418173410592222e8d504fcc7530779ccbae652770658d0d26",
        ),
        "C06": (
            "pass",
            "evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json",
            "cfec6162753ce1496b2a0bf95f93ed442afda2fdb83cdaa675b2ac6be316c114",
        ),
        "C07": (
            "pass",
            "evidence/dify-live/2026-08-09/tts/dify-recap.mp3",
            "a7d7821743b4364e1278b650b80e3d869ce2d06621a0745a4eb5fd45bca02328",
        ),
    }
    actual = {
        item["capability_id"]: (item["status"], item["evidence_path"], item["sha256"])
        for item in matrix["capabilities"]
    }
    assert actual == expected
    for _, evidence_path, expected_hash in expected.values():
        artifact = repository / evidence_path
        assert artifact.is_file()
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == expected_hash
        assert subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", evidence_path],
            cwd=repository,
            capture_output=True,
            check=False,
        ).returncode == 0
        assert subprocess.run(
            ["git", "check-ignore", "--quiet", "--", evidence_path],
            cwd=repository,
            check=False,
        ).returncode != 0

    for doc_path in (
        "README.md",
        "platform/dify/README.md",
        "evidence/dify-live/README.md",
        ".planning/STATE.md",
    ):
        text = (repository / doc_path).read_text(encoding="utf-8")
        assert "C03" in text and "C04" in text and "C06" in text
        assert "C03/C04" in text and "`pass`" in text
        assert "C06" in text and "independent" in text.casefold()
        assert "re-export" in text.casefold() or "重导出" in text
        assert "rerun" in text.casefold() or "复跑" in text
