from __future__ import annotations

import json
from pathlib import Path

import pytest

from debugmate.dify_live_evidence import (
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


def test_c06_pass_requires_roundtrip_equivalence_and_reconstructed_rerun(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.yml"
    reexport = tmp_path / "reexport.yml"
    output = tmp_path / "reconstructed-output.json"
    source.write_text(SOURCE_DSL, encoding="utf-8")
    reexport.write_text(REEXPORTED_DSL, encoding="utf-8")
    output.write_text(
        json.dumps(
            {
                "workflow_run_id_sha256": "d" * 64,
                "diagnosis_valid": True,
            }
        ),
        encoding="utf-8",
    )
    comparison = compare_dsl_files(source, reexport)
    record = {
        "capability_id": "C06",
        "status": "pass",
        "attempted_at_utc": "2026-08-09T00:00:00Z",
        "import_channel": "dify_console",
        "independent_app_id_sha256": "e" * 64,
        "source_dsl": source.name,
        "source_sha256": sha256_file(source),
        "reexport_dsl": reexport.name,
        "reexport_sha256": sha256_file(reexport),
        "source_normalized_sha256": comparison["source_normalized_sha256"],
        "reexport_normalized_sha256": comparison["reexport_normalized_sha256"],
        "differences": [],
        "reconstructed_output": output.name,
        "reason_code": None,
    }
    assert validate_c06_record(record, tmp_path)["status"] == "pass"

    with pytest.raises(ValueError, match="independent"):
        validate_c06_record(record | {"independent_app_id_sha256": None}, tmp_path)
    with pytest.raises(ValueError, match="differences"):
        validate_c06_record(record | {"differences": ["vision mismatch"]}, tmp_path)
