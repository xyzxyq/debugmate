from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from debugmate.dify_live_evidence import (
    LOCKED_C06_WORKFLOW_RUN_ID_SHA256,
    compare_dsl_files,
    sha256_file,
    validate_c06_record,
)

SOURCE_DSL = """
app:
  name: Original
  mode: workflow
kind: app
version: 0.7.0
workflow:
  graph:
    nodes:
      - id: start-1
        position: {x: 1, y: 2}
        data:
          title: Start
          type: start
          variables:
            - variable: image_input
              type: file
      - id: vision-1
        data:
          title: Vision
          type: llm
          model: {provider: openai, name: gpt-4.1}
          vision: {enabled: true}
          structured_output_enabled: true
      - id: retrieve-1
        data:
          title: Retrieval
          type: knowledge-retrieval
          retrieval_mode: multiple
          multiple_retrieval_config: {top_k: 4}
      - id: end-1
        data:
          title: End
          type: end
          outputs:
            - variable: diagnosis
              value_selector: [vision-1, structured_output]
    edges:
      - id: edge-1
        source: start-1
        target: vision-1
      - id: edge-2
        source: vision-1
        target: retrieve-1
      - id: edge-3
        source: retrieve-1
        target: end-1
"""


REEXPORTED_DSL = SOURCE_DSL.replace("name: Original", "name: Rebuilt").replace(
    "id: start-1", "id: new-start"
).replace("source: start-1", "source: new-start").replace(
    "position: {x: 1, y: 2}", "position: {x: 90, y: 80}"
)

AUTHORITATIVE_DSL = Path("platform/dify/app.dsl.yml")


def _node_by_title(payload: dict[str, object], title: str) -> dict[str, object]:
    workflow = payload["workflow"]
    assert isinstance(workflow, dict)
    graph = workflow["graph"]
    assert isinstance(graph, dict)
    nodes = graph["nodes"]
    assert isinstance(nodes, list)
    for node in nodes:
        if (
            isinstance(node, dict)
            and isinstance(node.get("data"), dict)
            and node["data"].get("title") == title
        ):
            return node
    raise AssertionError(f"missing DSL node: {title}")


def _assert_phase8_same_run_contract(payload: dict[str, object]) -> None:
    retrieval = _node_by_title(payload, "知识检索")
    sanitizer = _node_by_title(payload, "知识证据净化")
    envelope = _node_by_title(payload, "同次运行信封")
    end = _node_by_title(payload, "输出")

    retrieval_data = retrieval["data"]
    sanitizer_data = sanitizer["data"]
    envelope_data = envelope["data"]
    end_data = end["data"]
    assert all(isinstance(value, dict) for value in (
        retrieval_data,
        sanitizer_data,
        envelope_data,
        end_data,
    ))
    assert retrieval_data["multiple_retrieval_config"]["top_k"] == 4
    assert retrieval_data["dataset_ids"] == []

    sanitizer_variables = sanitizer_data["variables"]
    direct_selector = [retrieval["id"], "result"]
    assert any(item.get("value_selector") == direct_selector for item in sanitizer_variables)
    sanitizer_code = sanitizer_data["code"]
    assert "chunk_id_fingerprint" in sanitizer_code
    assert "len(hits) == 4" in sanitizer_code
    assert "[:limit]" in sanitizer_code
    assert "https://" in sanitizer_code

    envelope_code = envelope_data["code"]
    for required in (
        "envelope_version",
        "extraction_facts",
        "retrieval_trace",
        'SCHEMA_VERSION = "1.1.0"',
        "PROMPT_VERSION",
        "KNOWLEDGE_BUILD_ID",
        "DSL_SEMANTIC_SHA256",
    ):
        assert required in envelope_code
    envelope_variables = envelope_data["variables"]
    assert any(
        item.get("value_selector") == [sanitizer["id"], "retrieval_trace"]
        for item in envelope_variables
    )
    assert end_data["outputs"] == [
        {
            "value_selector": [envelope["id"], "run_envelope"],
            "value_type": "object",
            "variable": "run_envelope",
        }
    ]


def test_authoritative_dsl_exports_bounded_same_run_envelope() -> None:
    payload = yaml.safe_load(AUTHORITATIVE_DSL.read_text(encoding="utf-8-sig"))
    assert isinstance(payload, dict)
    _assert_phase8_same_run_contract(payload)


def test_phase8_contract_rejects_diagnosis_without_direct_retrieval_trace() -> None:
    payload = yaml.safe_load(AUTHORITATIVE_DSL.read_text(encoding="utf-8-sig"))
    assert isinstance(payload, dict)
    broken = copy.deepcopy(payload)
    end = _node_by_title(broken, "输出")
    normalizer = _node_by_title(broken, "合同规范化")
    end["data"]["outputs"] = [
        {
            "value_selector": [normalizer["id"], "diagnosis"],
            "value_type": "object",
            "variable": "diagnosis",
        }
    ]

    with pytest.raises(AssertionError):
        _assert_phase8_same_run_contract(broken)


def test_dsl_compare_ignores_ids_layout_and_app_display_name(tmp_path: Path) -> None:
    source = tmp_path / "source.yml"
    reexport = tmp_path / "reexport.yml"
    source.write_text(SOURCE_DSL, encoding="utf-8")
    reexport.write_text(REEXPORTED_DSL, encoding="utf-8")

    result = compare_dsl_files(source, reexport)
    assert result["differences"] == []
    assert result["source_normalized_sha256"] == result["reexport_normalized_sha256"]


@pytest.mark.parametrize(
    "old,new",
    [
        ("enabled: true", "enabled: false"),
        ("top_k: 4", "top_k: 2"),
        ("variable: diagnosis", "variable: summary"),
        ("name: gpt-4.1", "name: another-model"),
    ],
)
def test_dsl_compare_preserves_critical_contracts(
    tmp_path: Path, old: str, new: str
) -> None:
    source = tmp_path / "source.yml"
    changed = tmp_path / "changed.yml"
    source.write_text(SOURCE_DSL, encoding="utf-8")
    changed.write_text(REEXPORTED_DSL.replace(old, new), encoding="utf-8")
    assert compare_dsl_files(source, changed)["differences"]


def _valid_c06_record(tmp_path: Path) -> tuple[dict[str, object], Path]:
    source = tmp_path / "source.yml"
    reexport = tmp_path / "reexport.yml"
    output = tmp_path / "reconstructed-output.json"
    source.write_text(SOURCE_DSL, encoding="utf-8")
    reexport.write_text(REEXPORTED_DSL, encoding="utf-8")
    output.write_text(
        json.dumps(
            {
                "evidence_schema_version": "1.0.0",
                "started_at_utc": "2026-08-09T05:21:46Z",
                "completed_at_utc": "2026-08-09T05:22:04Z",
                "status": "SUCCESS",
                "duration_seconds": 18.515,
                "total_tokens": 6019,
                "total_steps": 6,
                "workflow_run_id_sha256": LOCKED_C06_WORKFLOW_RUN_ID_SHA256,
                "diagnosis_valid": True,
                "diagnosis_schema_version": "1.1.0",
                "diagnosis_category": "dependency_environment",
                "knowledge_chunk_id": "python-exceptions:module-not-found-error",
                "source_url": "https://docs.python.org/3/library/exceptions.html",
            }
        ),
        encoding="utf-8",
    )
    comparison = compare_dsl_files(source, reexport)
    record = {
        "capability_id": "C06",
        "status": "pass",
        "attempted_at_utc": "2026-08-09T00:00:00Z",
        "completed_at_utc": "2026-08-09T05:22:04Z",
        "import_channel": "dify_console",
        "source_app_id_sha256": "d" * 64,
        "independent_app_id_sha256": "e" * 64,
        "source_dsl": source.name,
        "source_sha256": sha256_file(source),
        "reexport_dsl": reexport.name,
        "reexport_sha256": sha256_file(reexport),
        "source_normalized_sha256": comparison["source_normalized_sha256"],
        "reexport_normalized_sha256": comparison["reexport_normalized_sha256"],
        "differences": [],
        "reconstructed_output": output.name,
        "reconstructed_output_sha256": sha256_file(output),
        "reason_code": None,
    }
    return record, output


def test_c06_pass_requires_roundtrip_equivalence_and_reconstructed_rerun(
    tmp_path: Path,
) -> None:
    record, _ = _valid_c06_record(tmp_path)
    assert validate_c06_record(record, tmp_path)["status"] == "pass"

    with pytest.raises(ValueError, match="application fingerprints"):
        validate_c06_record(
            record
            | {"independent_app_id_sha256": record["source_app_id_sha256"]},
            tmp_path,
        )
    with pytest.raises(ValueError, match="differences"):
        validate_c06_record(record | {"differences": ["vision mismatch"]}, tmp_path)


def test_c06_rejects_same_schema_rerun_replacement(tmp_path: Path) -> None:
    record, output = _valid_c06_record(tmp_path)
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["total_tokens"] = 6020
    output.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="reconstructed output hash mismatch"):
        validate_c06_record(record, tmp_path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("workflow_run_id_sha256", "f" * 64),
        ("status", "FAILED"),
        ("duration_seconds", 18.516),
        ("total_tokens", 6020),
        ("total_steps", 7),
        ("diagnosis_valid", False),
        ("diagnosis_schema_version", "1.0.0"),
        ("diagnosis_category", "runtime"),
        ("knowledge_chunk_id", ""),
        ("source_url", "http://example.invalid/source"),
    ],
)
def test_c06_rejects_non_authoritative_rerun_facts(
    tmp_path: Path, field: str, value: object
) -> None:
    record, output = _valid_c06_record(tmp_path)
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload[field] = value
    output.write_text(json.dumps(payload), encoding="utf-8")
    record["reconstructed_output_sha256"] = sha256_file(output)

    with pytest.raises(ValueError):
        validate_c06_record(record, tmp_path)


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_c06_rerun_allowlist_is_exact(tmp_path: Path, mutation: str) -> None:
    record, output = _valid_c06_record(tmp_path)
    payload = json.loads(output.read_text(encoding="utf-8"))
    if mutation == "missing":
        payload.pop("completed_at_utc")
    else:
        payload["raw_run_id"] = "must-not-be-accepted"
    output.write_text(json.dumps(payload), encoding="utf-8")
    record["reconstructed_output_sha256"] = sha256_file(output)

    with pytest.raises(ValueError, match="safe authoritative rerun evidence"):
        validate_c06_record(record, tmp_path)
