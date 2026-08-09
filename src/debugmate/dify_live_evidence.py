from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import httpx
import yaml
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

TARGET_TEXT = "ModuleNotFoundError: No module named 'debugmate_demo_pkg'"
LOCKED_C06_WORKFLOW_RUN_ID_SHA256 = (
    "94a89d3fe4e77fa0a1255e39dbfd565f184076a12d6248c93fd314f09cb3531f"
)
LOCKED_C06_SOURCE_URL = "https://docs.python.org/3/library/exceptions.html"
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
PERSONAL_PATH_RE = re.compile(r"(?i)\b[A-Z]:\\+Users\\+")
SECRET_RE = re.compile(
    r"(?i)(?:bearer\s+[A-Za-z0-9._-]{8,}|authorization\s*[:=]|"
    r"api[_ -]?key\s*[:=]\s*[\"'][^\"']+|csrf|session[_ -]?token|cookie\s*[:=])"
)
PREBUILT_KEYS = {"observed_facts", "evidence", "routing", "facts", "prebuilt_facts"}
ALLOWED_NON_IMAGE_INPUTS = {
    "case_id",
    "file_id",
    "error_text",
    "code",
    "environment",
    "generation_request",
    "request_kind",
    "schema_version",
    "issues",
    "candidate",
}


class _StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class RetrievalHit(_StrictModel):
    chunk_id: str = Field(min_length=1, max_length=256)
    content_summary: str = Field(min_length=1, max_length=500)
    source_id: str = Field(min_length=1, max_length=256)
    source_title: str = Field(min_length=1, max_length=300)
    source_url: HttpUrl | None
    locator: str = Field(min_length=1, max_length=300)
    relevance_score: float | None


class RetrieverResource(_StrictModel):
    source_kind: Literal[
        "knowledge_retrieval_node_resource", "knowledge_retrieval_console_log"
    ]
    workflow_run_id_sha256: str
    node_run_id_sha256: str
    hits: list[RetrievalHit] = Field(min_length=1)


class C03Record(_StrictModel):
    capability_id: Literal["C03"]
    status: Literal["pass", "fail", "blocked", "not-tested"]
    attempted_at_utc: str
    input_image: str | None = None
    request_manifest: str | None = None
    request_sha256: str | None = None
    upload_id_sha256: str | None = None
    workflow_run_id_sha256: str | None = None
    source_kind: str | None = None
    extracted_text: str | None = None
    extracted_facts: list[str] = Field(default_factory=list)
    extraction_match_kind: Literal["single_exact", "ordered_exact_coverage"] | None = None
    target_text_sha256: str | None = None
    reason_code: str | None = None


class C04Record(_StrictModel):
    capability_id: Literal["C04"]
    status: Literal["pass", "fail", "blocked", "not-tested"]
    attempted_at_utc: str
    retriever_resource: str | None = None
    retriever_resource_sha256: str | None = None
    reason_code: str | None = None


class C06Record(_StrictModel):
    capability_id: Literal["C06"]
    status: Literal["pass", "fail", "blocked", "not-tested"]
    attempted_at_utc: str
    completed_at_utc: str | None = None
    import_channel: str | None = None
    source_app_id_sha256: str | None = None
    independent_app_id_sha256: str | None = None
    source_dsl: str | None = None
    source_sha256: str | None = None
    reexport_dsl: str | None = None
    reexport_sha256: str | None = None
    source_normalized_sha256: str | None = None
    reexport_normalized_sha256: str | None = None
    differences: list[str] = Field(default_factory=list)
    reconstructed_output: str | None = None
    reconstructed_output_sha256: str | None = None
    reason_code: str | None = None


class C06ReconstructedRun(_StrictModel):
    evidence_schema_version: Literal["1.0.0"]
    started_at_utc: Literal["2026-08-09T05:21:46Z"]
    completed_at_utc: Literal["2026-08-09T05:22:04Z"]
    status: Literal["SUCCESS"]
    duration_seconds: float
    total_tokens: Literal[6019]
    total_steps: Literal[6]
    workflow_run_id_sha256: str
    diagnosis_valid: Literal[True]
    diagnosis_schema_version: Literal["1.1.0"]
    diagnosis_category: Literal["dependency_environment"]
    knowledge_chunk_id: Literal["python-exceptions:module-not-found-error"]
    source_url: HttpUrl


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_request_sha256(request: object) -> str:
    return hashlib.sha256(_canonical_bytes(request)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalized_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def _walk_strings(value: object) -> Sequence[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, Mapping):
        for key, item in value.items():
            found.append(str(key))
            found.extend(_walk_strings(item))
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for item in value:
            found.extend(_walk_strings(item))
    return found


def _validate_non_image_inputs(inputs: Mapping[str, object]) -> None:
    unknown = set(inputs) - ALLOWED_NON_IMAGE_INPUTS
    if unknown & PREBUILT_KEYS:
        raise ValueError("prebuilt facts are forbidden in non-image inputs")
    if PREBUILT_KEYS & set(inputs):
        raise ValueError("prebuilt facts are forbidden in non-image inputs")
    target = _normalized_text(TARGET_TEXT)
    for field, value in inputs.items():
        for candidate in _walk_strings(value):
            if target in _normalized_text(candidate):
                raise ValueError(f"target text found in non-image input: {field}")
    if unknown:
        raise ValueError(f"unallowlisted non-image inputs: {sorted(unknown)}")


def build_request_manifest(
    *, image_path: Path, non_image_inputs: Mapping[str, object], upload_id: str
) -> dict[str, object]:
    if not image_path.is_file() or image_path.suffix.casefold() != ".png":
        raise ValueError("C03 input must be an existing PNG")
    _validate_non_image_inputs(non_image_inputs)
    request = {
        "inputs": dict(non_image_inputs),
        "image_input": {
            "type": "image",
            "transfer_method": "local_file",
            "upload_file_id_sha256": _fingerprint(upload_id),
        },
    }
    return {
        "schema_version": "1.0.0",
        "input_image": image_path.name,
        "input_image_sha256": sha256_file(image_path),
        "upload_id_sha256": _fingerprint(upload_id),
        "target_text_sha256": _fingerprint(TARGET_TEXT),
        "non_image_inputs": dict(non_image_inputs),
        "request": request,
        "request_sha256": canonical_request_sha256(request),
    }


def _resolve_artifact(repository_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError("artifact paths must be repository-relative")
    root = repository_root.resolve()
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("artifact path escapes repository root") from error
    if not resolved.is_file():
        raise ValueError(f"artifact does not exist: {value}")
    return resolved


def _valid_hash(value: str | None, field: str) -> str:
    if value is None or HASH_RE.fullmatch(value) is None:
        raise ValueError(f"{field} must be a SHA-256 fingerprint")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path.name}")
    return value


def validate_c03_record(record: Mapping[str, object], repository_root: Path) -> dict[str, Any]:
    parsed = C03Record.model_validate(record)
    if parsed.status != "pass":
        if not parsed.reason_code:
            raise ValueError("non-pass C03 record requires reason_code")
        return parsed.model_dump(mode="json")
    image = _resolve_artifact(repository_root, parsed.input_image or "")
    manifest_path = _resolve_artifact(repository_root, parsed.request_manifest or "")
    manifest = _load_json(manifest_path)
    if image.suffix.casefold() != ".png" or sha256_file(image) != manifest.get(
        "input_image_sha256"
    ):
        raise ValueError("C03 PNG hash mismatch")
    non_image_inputs = manifest.get("non_image_inputs")
    if not isinstance(non_image_inputs, dict):
        raise ValueError("C03 manifest is missing non-image inputs")
    _validate_non_image_inputs(non_image_inputs)
    request = manifest.get("request")
    expected_request_hash = canonical_request_sha256(request)
    if parsed.request_sha256 != expected_request_hash or manifest.get(
        "request_sha256"
    ) != expected_request_hash:
        raise ValueError("C03 request hash mismatch")
    if parsed.upload_id_sha256 != manifest.get("upload_id_sha256"):
        raise ValueError("C03 upload fingerprint mismatch")
    _valid_hash(parsed.upload_id_sha256, "upload_id_sha256")
    _valid_hash(parsed.workflow_run_id_sha256, "workflow_run_id_sha256")
    if parsed.source_kind != "vlm":
        raise ValueError("C03 pass requires source_kind=vlm")
    match_kind = _vlm_match_kind(
        ([parsed.extracted_text] if parsed.extracted_text else []) + parsed.extracted_facts
    )
    if match_kind is None or parsed.extraction_match_kind not in {None, match_kind}:
        raise ValueError(
            "C03 pass requires exact target extraction or ordered exact target coverage"
        )
    if parsed.target_text_sha256 != _fingerprint(TARGET_TEXT):
        raise ValueError("C03 target hash mismatch")
    return parsed.model_dump(mode="json")


def validate_c04_record(
    record: Mapping[str, object],
    repository_root: Path,
    *,
    publication_repository_root: Path | None = None,
) -> dict[str, Any]:
    parsed = C04Record.model_validate(record)
    if parsed.status != "pass":
        if not parsed.reason_code:
            raise ValueError("non-pass C04 record requires reason_code")
        return parsed.model_dump(mode="json")
    expected_sha256 = parsed.retriever_resource_sha256 or ""
    _valid_hash(expected_sha256, "retriever_resource_sha256")
    resource_path = _resolve_artifact(repository_root, parsed.retriever_resource or "")
    if sha256_file(resource_path) != expected_sha256:
        raise ValueError("C04 retriever resource hash mismatch")
    if publication_repository_root is not None and not _git_tracked(
        publication_repository_root, resource_path
    ):
        raise ValueError("C04 retriever resource must be Git tracked and not ignored")
    try:
        resource = RetrieverResource.model_validate(_load_json(resource_path))
    except Exception as error:
        raise ValueError("C04 pass requires direct Knowledge Retrieval node resource") from error
    _valid_hash(resource.workflow_run_id_sha256, "workflow_run_id_sha256")
    _valid_hash(resource.node_run_id_sha256, "node_run_id_sha256")
    return parsed.model_dump(mode="json")


DISPLAY_KEYS = {
    "id",
    "position",
    "position_absolute",
    "viewport",
    "selected",
    "zindex",
    "width",
    "height",
}


def _replace_node_ids(value: object, node_titles: Mapping[str, str]) -> object:
    if isinstance(value, str):
        return node_titles.get(value, value)
    if isinstance(value, list):
        return [_replace_node_ids(item, node_titles) for item in value]
    if isinstance(value, dict):
        return {
            key: _replace_node_ids(item, node_titles)
            for key, item in sorted(value.items())
            if key.casefold() not in DISPLAY_KEYS
        }
    return value


def normalize_dsl(value: Mapping[str, object]) -> dict[str, object]:
    workflow = value.get("workflow")
    if not isinstance(workflow, dict) or not isinstance(workflow.get("graph"), dict):
        raise ValueError("Dify DSL must contain workflow.graph")
    graph = workflow["graph"]
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("Dify DSL graph must contain nodes and edges")
    node_titles: dict[str, str] = {}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("data"), dict):
            raise ValueError("Dify DSL node is malformed")
        node_id = str(node.get("id", ""))
        title = str(node["data"].get("title", ""))
        if not node_id or not title:
            raise ValueError("Dify DSL node requires id and title")
        if title in node_titles.values():
            raise ValueError(f"duplicate node title: {title}")
        node_titles[node_id] = title
    normalized_nodes = []
    for node in nodes:
        data = _replace_node_ids(node["data"], node_titles)
        normalized_nodes.append(data)
    normalized_nodes.sort(key=lambda item: str(item.get("title", "")))
    topology = []
    for edge in edges:
        if not isinstance(edge, dict):
            raise ValueError("Dify DSL edge is malformed")
        source = node_titles.get(str(edge.get("source", "")), str(edge.get("source", "")))
        target = node_titles.get(str(edge.get("target", "")), str(edge.get("target", "")))
        topology.append(
            {
                "source": source,
                "target": target,
                "source_handle": edge.get("sourceHandle", edge.get("source_handle")),
                "target_handle": edge.get("targetHandle", edge.get("target_handle")),
            }
        )
    topology.sort(key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))
    app = value.get("app") if isinstance(value.get("app"), dict) else {}
    dependencies = _replace_node_ids(value.get("dependencies", []), node_titles)
    return {
        "kind": value.get("kind"),
        "version": value.get("version"),
        "app": {"mode": app.get("mode")},
        "dependencies": dependencies,
        "nodes": normalized_nodes,
        "topology": topology,
    }


def _load_yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"YAML object required: {path}")
    return payload


def compare_dsl_files(source: Path, reexport: Path) -> dict[str, object]:
    source_normalized = normalize_dsl(_load_yaml(source))
    reexport_normalized = normalize_dsl(_load_yaml(reexport))
    source_hash = canonical_request_sha256(source_normalized)
    reexport_hash = canonical_request_sha256(reexport_normalized)
    differences = [] if source_normalized == reexport_normalized else [
        "normalized Dify workflow structures differ"
    ]
    return {
        "source_normalized_sha256": source_hash,
        "reexport_normalized_sha256": reexport_hash,
        "differences": differences,
    }


def validate_c06_record(record: Mapping[str, object], repository_root: Path) -> dict[str, Any]:
    parsed = C06Record.model_validate(record)
    if parsed.status != "pass":
        if not parsed.reason_code:
            raise ValueError("non-pass C06 record requires reason_code")
        return parsed.model_dump(mode="json")
    source_app = _valid_hash(parsed.source_app_id_sha256, "source_app_id_sha256")
    independent_app = _valid_hash(
        parsed.independent_app_id_sha256, "independent_app_id_sha256"
    )
    if source_app == independent_app:
        raise ValueError("C06 application fingerprints must be distinct")
    source = _resolve_artifact(repository_root, parsed.source_dsl or "")
    reexport = _resolve_artifact(repository_root, parsed.reexport_dsl or "")
    output = _resolve_artifact(repository_root, parsed.reconstructed_output or "")
    source_sha256 = _valid_hash(parsed.source_sha256, "source_sha256")
    reexport_sha256 = _valid_hash(parsed.reexport_sha256, "reexport_sha256")
    output_sha256 = _valid_hash(
        parsed.reconstructed_output_sha256, "reconstructed_output_sha256"
    )
    if sha256_file(source) != source_sha256:
        raise ValueError("C06 source DSL hash mismatch")
    if sha256_file(reexport) != reexport_sha256:
        raise ValueError("C06 re-export DSL hash mismatch")
    if sha256_file(output) != output_sha256:
        raise ValueError("C06 reconstructed output hash mismatch")
    comparison = compare_dsl_files(source, reexport)
    if parsed.differences or comparison["differences"]:
        raise ValueError("C06 normalized structures contain differences")
    if parsed.source_normalized_sha256 != comparison["source_normalized_sha256"]:
        raise ValueError("C06 source normalized hash mismatch")
    if parsed.reexport_normalized_sha256 != comparison["reexport_normalized_sha256"]:
        raise ValueError("C06 re-export normalized hash mismatch")
    try:
        reconstructed = C06ReconstructedRun.model_validate(_load_json(output))
    except Exception as error:
        raise ValueError("C06 requires safe authoritative rerun evidence") from error
    run_fingerprint = _valid_hash(
        reconstructed.workflow_run_id_sha256, "workflow_run_id_sha256"
    )
    if run_fingerprint != LOCKED_C06_WORKFLOW_RUN_ID_SHA256:
        raise ValueError("C06 workflow run fingerprint does not match the locked rerun")
    if reconstructed.duration_seconds != 18.515:
        raise ValueError("C06 rerun duration does not match the locked rerun")
    if str(reconstructed.source_url) != LOCKED_C06_SOURCE_URL:
        raise ValueError("C06 rerun source URL does not match the locked source")
    return parsed.model_dump(mode="json")


def _scan_text(path: Path) -> None:
    if path.suffix.casefold() in {".png", ".mp3"}:
        return
    text = path.read_text(encoding="utf-8-sig")
    if SECRET_RE.search(text):
        raise ValueError(f"sensitive authentication/session material in {path.name}")
    if PERSONAL_PATH_RE.search(text):
        raise ValueError(f"personal absolute path in {path.name}")


def _record_paths(evidence_root: Path) -> tuple[Path, Path]:
    return (
        evidence_root / "c03-c04" / "vision-retrieval-evidence.json",
        evidence_root / "c06" / "dsl-roundtrip-evidence.json",
    )


def _git_tracked(repository_root: Path, path: Path) -> bool:
    relative = path.resolve().relative_to(repository_root.resolve()).as_posix()
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=repository_root,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        return False
    ignored = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", relative],
        cwd=repository_root,
        check=False,
    )
    return ignored.returncode != 0


def validate_candidate_tree(repository_root: Path, evidence_root: Path) -> dict[str, str]:
    root = repository_root.resolve()
    evidence = evidence_root.resolve()
    try:
        evidence.relative_to(root)
    except ValueError as error:
        raise ValueError("evidence root must be inside repository") from error
    for path in evidence.rglob("*"):
        if path.is_file():
            _scan_text(path)
    c03_c04_path, c06_path = _record_paths(evidence)
    result: dict[str, str] = {}
    if c03_c04_path.is_file():
        combined = _load_json(c03_c04_path)
        result["C03"] = validate_c03_record(combined["c03"], evidence)["status"]
        result["C04"] = validate_c04_record(combined["c04"], evidence)["status"]
    if c06_path.is_file():
        result["C06"] = validate_c06_record(_load_json(c06_path), root)["status"]
    if not result and any(evidence.rglob("*")):
        return result
    if set(result) != {"C03", "C04", "C06"}:
        raise ValueError("candidate evidence must contain C03, C04, and C06 records")
    return result


def validate_published_tree(repository_root: Path, evidence_root: Path) -> dict[str, str]:
    result = validate_candidate_tree(repository_root, evidence_root)
    referenced: set[Path] = set(_record_paths(evidence_root))
    combined = _load_json(evidence_root / "c03-c04" / "vision-retrieval-evidence.json")
    c03 = C03Record.model_validate(combined["c03"])
    c04 = C04Record.model_validate(combined["c04"])
    validate_c04_record(
        combined["c04"],
        evidence_root,
        publication_repository_root=repository_root,
    )
    c06 = C06Record.model_validate(
        _load_json(evidence_root / "c06" / "dsl-roundtrip-evidence.json")
    )
    for value in (
        c03.input_image,
        c03.request_manifest,
        c04.retriever_resource,
    ):
        if value:
            referenced.add(_resolve_artifact(evidence_root, value))
    for value in (c06.source_dsl, c06.reexport_dsl, c06.reconstructed_output):
        if value:
            referenced.add(_resolve_artifact(repository_root, value))
    untracked = [path for path in referenced if not _git_tracked(repository_root, path)]
    if untracked:
        names = [
            path.resolve().relative_to(repository_root.resolve()).as_posix()
            for path in untracked
        ]
        raise ValueError(f"published evidence is not Git tracked/not ignored: {sorted(names)}")
    return result


def generate_terminal_png(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1280, 420), "#10151c")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=26)
    lines = [
        "PS C:\\demo> python run_demo.py",
        "Traceback (most recent call last):",
        '  File "C:\\demo\\run_demo.py", line 1, in <module>',
        "    import debugmate_demo_pkg",
        TARGET_TEXT,
    ]
    draw.multiline_text((48, 48), "\n".join(lines), fill="#e8edf2", font=font, spacing=18)
    image.save(path, format="PNG", optimize=False)
    return path


def _safe_vlm_facts(outputs: object) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []

    def visit(value: object) -> None:
        if isinstance(value, dict):
            source = value.get("source_kind")
            candidate = value.get("text", value.get("value", value.get("fact")))
            if source == "vlm" and isinstance(candidate, str):
                facts.append({"source_kind": "vlm", "text": candidate[:500]})
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, str) and len(value) <= 100_000:
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return
            visit(decoded)

    visit(outputs)
    return facts


def _vlm_match_kind(facts: Sequence[str]) -> str | None:
    if TARGET_TEXT in facts:
        return "single_exact"
    for index in range(len(facts) - 1):
        combined = f"{facts[index]}: {facts[index + 1]}"
        if _normalized_text(combined) == _normalized_text(TARGET_TEXT):
            return "ordered_exact_coverage"
    return None


def _safe_retriever_resource(
    data: Mapping[str, object], run_fingerprint: str
) -> dict[str, object] | None:
    resources = data.get("retriever_resources")
    if not isinstance(resources, list) or not resources:
        return None
    hits: list[dict[str, object]] = []
    node_id = ""
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        node_id = str(resource.get("position", resource.get("node_id", "retrieval-node")))
        metadata = resource.get("metadata") if isinstance(resource.get("metadata"), dict) else {}
        content = resource.get("content")
        summary = " ".join(str(content or "").split())[:500]
        source_title = str(
            resource.get("document_name")
            or metadata.get("document_name")
            or metadata.get("title")
            or "Dify knowledge source"
        )[:300]
        source_id = str(
            resource.get("document_id") or metadata.get("document_id") or source_title
        )[:256]
        chunk_id = str(resource.get("segment_id") or metadata.get("segment_id") or "")[:256]
        locator = str(metadata.get("position") or metadata.get("page") or chunk_id)[:300]
        source_url = metadata.get("source_url") or metadata.get("url")
        score = resource.get("score")
        if not chunk_id or not summary or not source_id or not locator:
            continue
        hits.append(
            {
                "chunk_id": chunk_id,
                "content_summary": summary,
                "source_id": source_id,
                "source_title": source_title,
                "source_url": source_url if isinstance(source_url, str) else None,
                "locator": locator,
                "relevance_score": float(score) if isinstance(score, (float, int)) else None,
            }
        )
    if not hits:
        return None
    return {
        "source_kind": "knowledge_retrieval_node_resource",
        "workflow_run_id_sha256": run_fingerprint,
        "node_run_id_sha256": _fingerprint(node_id),
        "hits": hits,
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def capture_c03_c04(output_root: Path) -> dict[str, str]:
    attempted = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    target_dir = output_root / "c03-c04"
    image = generate_terminal_png(target_dir / "input-terminal.png")
    safe_inputs: dict[str, object] = {
        "case_id": "c03-c04-live-20260809",
        "file_id": "",
        "error_text": "",
        "code": "",
        "environment": {},
        "generation_request": {},
        "request_kind": "live_vision_evidence",
        "schema_version": "1.0.0",
        "issues": {},
        "candidate": {},
    }
    _validate_non_image_inputs(safe_inputs)
    base_url = os.environ.get("DIFY_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("DIFY_API_KEY", "")
    user = os.environ.get("DIFY_USER", "debugmate-live-evidence")
    if not base_url or not api_key:
        reason = "missing_dify_application_api_environment"
        combined = {
            "schema_version": "1.0.0",
            "c03": C03Record(
                capability_id="C03",
                status="blocked",
                attempted_at_utc=attempted,
                reason_code=reason,
            ).model_dump(mode="json"),
            "c04": C04Record(
                capability_id="C04",
                status="blocked",
                attempted_at_utc=attempted,
                reason_code=reason,
            ).model_dump(mode="json"),
        }
        _write_json(target_dir / "vision-retrieval-evidence.json", combined)
        return {"C03": "blocked", "C04": "blocked"}
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        with httpx.Client(base_url=base_url, headers=headers, timeout=90.0) as client:
            with image.open("rb") as stream:
                upload_response = client.post(
                    "/files/upload",
                    data={"user": user},
                    files={"file": (image.name, stream, "image/png")},
                )
            upload_response.raise_for_status()
            upload_payload = upload_response.json()
            upload_id = upload_payload.get("id")
            if not isinstance(upload_id, str) or not upload_id:
                raise ValueError("upload response omitted file id")
            manifest = build_request_manifest(
                image_path=image, non_image_inputs=safe_inputs, upload_id=upload_id
            )
            _write_json(target_dir / "workflow-request-manifest.json", manifest)
            workflow_inputs = dict(safe_inputs)
            workflow_inputs["image_input"] = {
                "type": "image",
                "transfer_method": "local_file",
                "upload_file_id": upload_id,
            }
            response = client.post(
                "/workflows/run",
                json={"inputs": workflow_inputs, "response_mode": "blocking", "user": user},
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as error:
        reason = f"workflow_api_{type(error).__name__.casefold()}"
        combined = {
            "schema_version": "1.0.0",
            "c03": C03Record(
                capability_id="C03",
                status="blocked",
                attempted_at_utc=attempted,
                reason_code=reason,
            ).model_dump(mode="json"),
            "c04": C04Record(
                capability_id="C04",
                status="blocked",
                attempted_at_utc=attempted,
                reason_code=reason,
            ).model_dump(mode="json"),
        }
        _write_json(target_dir / "vision-retrieval-evidence.json", combined)
        return {"C03": "blocked", "C04": "blocked"}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    run_id = payload.get("workflow_run_id") or data.get("workflow_run_id") or data.get("id")
    run_fingerprint = _fingerprint(str(run_id)) if run_id else ""
    outputs = data.get("outputs", {})
    facts = _safe_vlm_facts(outputs)
    fact_texts = [fact["text"] for fact in facts]
    match_kind = _vlm_match_kind(fact_texts)
    exact_fact = next((fact for fact in facts if fact["text"] == TARGET_TEXT), None)
    workflow_output = {
        "status": str(data.get("status", "unknown")),
        "workflow_run_id_sha256": run_fingerprint or None,
        "vlm_facts": facts,
    }
    _write_json(target_dir / "workflow-output.json", workflow_output)
    resource = _safe_retriever_resource(data, run_fingerprint) if run_fingerprint else None
    resource_path = target_dir / "retriever-resource.json"
    if resource:
        _write_json(resource_path, resource)
    c03_status = "pass" if match_kind and run_fingerprint else "fail"
    c03 = C03Record(
        capability_id="C03",
        status=c03_status,
        attempted_at_utc=attempted,
        input_image=image.relative_to(output_root.parent.parent).as_posix()
        if "evidence" in output_root.parts
        else image.relative_to(output_root).as_posix(),
        request_manifest=(target_dir / "workflow-request-manifest.json")
        .relative_to(output_root)
        .as_posix(),
        request_sha256=manifest["request_sha256"],
        upload_id_sha256=manifest["upload_id_sha256"],
        workflow_run_id_sha256=run_fingerprint or None,
        source_kind="vlm" if match_kind else None,
        extracted_text=exact_fact["text"] if exact_fact else None,
        extracted_facts=fact_texts if match_kind == "ordered_exact_coverage" else [],
        extraction_match_kind=match_kind,
        target_text_sha256=manifest["target_text_sha256"],
        reason_code=None if c03_status == "pass" else "no_exact_vlm_fact_in_workflow_output",
    )
    c04_status = "pass" if resource else "blocked"
    c04 = C04Record(
        capability_id="C04",
        status=c04_status,
        attempted_at_utc=attempted,
        retriever_resource=resource_path.relative_to(output_root).as_posix() if resource else None,
        retriever_resource_sha256=sha256_file(resource_path) if resource else None,
        reason_code=None if resource else "workflow_response_omitted_direct_retriever_resource",
    )
    combined = {
        "schema_version": "1.0.0",
        "c03": c03.model_dump(mode="json"),
        "c04": c04.model_dump(mode="json"),
    }
    _write_json(target_dir / "vision-retrieval-evidence.json", combined)
    return {"C03": c03_status, "C04": c04_status}


def write_blocked_c06(output_root: Path, reason_code: str) -> dict[str, str]:
    attempted = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    record = C06Record(
        capability_id="C06",
        status="blocked",
        attempted_at_utc=attempted,
        reason_code=reason_code,
    )
    _write_json(
        output_root / "c06" / "dsl-roundtrip-evidence.json",
        record.model_dump(mode="json"),
    )
    return {"C06": "blocked"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture and validate safe Dify live evidence")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate-candidate", "validate-published"):
        child = subparsers.add_parser(command)
        child.add_argument("--repository-root", type=Path, required=True)
        child.add_argument("--evidence-root", type=Path, required=True)
    capture = subparsers.add_parser("capture")
    capture.add_argument("--output-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "capture":
        output_root = args.output_root.resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        result = capture_c03_c04(output_root)
        result.update(write_blocked_c06(output_root, "console_import_export_not_attempted"))
    elif args.command == "validate-candidate":
        result = validate_candidate_tree(args.repository_root, args.evidence_root)
    else:
        result = validate_published_tree(args.repository_root, args.evidence_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
