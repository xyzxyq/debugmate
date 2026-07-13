"""Safe deterministic textual result renderers."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from pydantic import Field

from debugmate.hashing import canonical_json_bytes, sha256_bytes
from debugmate.privacy.output_scan import assert_export_safe
from debugmate.results.contracts import ArtifactIdentity, StrictFrozenModel
from debugmate.results.presentation import (
    PresentationCommand,
    PresentationModel,
    _validated_presentation,
)


class ReportRenderError(ValueError):
    """A value-free report boundary error suitable for UI state mapping."""

    def __init__(self) -> None:
        super().__init__("report_render_failed")


class CitationRenderError(ValueError):
    def __init__(self) -> None:
        super().__init__("citation_render_failed")


class RenderedReport(StrictFrozenModel):
    identity: ArtifactIdentity
    markdown: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class CitationRow(StrictFrozenModel):
    evidence_id: str = Field(pattern=r"^evidence_[0-9a-f]{32}$")
    source_label: str
    source_url: str
    source_locator: str
    chunk_id: str
    source_id: str
    knowledge_build_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    supported_candidate_ids: tuple[str, ...]
    supported_fact_ids: tuple[str, ...]


class RenderedCitations(StrictFrozenModel):
    identity: ArtifactIdentity
    rows: tuple[CitationRow, ...]
    json_bytes: bytes
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


_MARKDOWN_ESCAPES = re.compile(r"([\[\]()!#*|])")


def _safe_text(value: str) -> str:
    """Escape structure while leaving ordinary technical literals byte-identical."""

    escaped = value.replace("<", "&lt;").replace(">", "&gt;")
    escaped = escaped.replace("`", "&#96;")
    escaped = re.sub(r"(?i)javascript:", "javascript&#58;", escaped)
    escaped = re.sub(r"(?i)data:", "data&#58;", escaped)
    return _MARKDOWN_ESCAPES.sub(r"\\\1", escaped)


def _items(values: tuple[str, ...], *, empty: str = "无。") -> list[str]:
    return [f"- {_safe_text(value)}" for value in values] or [f"- {empty}"]


def _max_backtick_run(value: str) -> int:
    return max((len(match.group(0)) for match in re.finditer(r"`+", value)), default=0)


def _command_block(index: int, step: PresentationCommand) -> list[str]:
    fence = "`" * max(3, _max_backtick_run(step.command) + 1)
    return [
        f"### {index}",
        f"- 平台：{_safe_text(str(step.platform))}",
        f"- 影响：{_safe_text(step.impact)}",
        f"- 预期结果：{_safe_text(step.expected_result)}",
        f"- 回滚说明：{_safe_text(step.rollback)}",
        f"{fence}text",
        step.command,
        fence,
    ]


def _commands(values: tuple[PresentationCommand, ...]) -> list[str]:
    if not values:
        return ["无。"]
    lines: list[str] = []
    for index, step in enumerate(values, start=1):
        if lines:
            lines.append("")
        lines.extend(_command_block(index, step))
    return lines


def _report_lines(presentation: PresentationModel) -> list[str]:
    identity = presentation.identity
    lines = [
        "# DebugMate 诊断报告",
        "",
        "## 1. 案例与版本摘要",
        f"- 案例 ID：{identity.case_id}",
        f"- 来源运行 ID：{identity.source_run_id}",
        f"- 诊断摘要：{identity.diagnosis_sha256}",
        f"- Schema：{identity.schema_version}",
        f"- 生成版本：{identity.generation_version}",
        f"- 类别：{presentation.category}",
        "",
        "## 2. 已观察事实",
    ]
    lines.extend(
        f"- `{item.fact_id}` · `{_safe_text(item.field_id)}` · {_safe_text(item.value)} "
        f"· 置信度 {item.confidence:.2f} · 来源 {_safe_text(str(item.source_kind))} "
        f"· 定位 {_safe_text(item.locator)}"
        for item in presentation.observed_facts
    )
    if not presentation.observed_facts:
        lines.append("- 无。")

    lines.extend(["", "## 3. 根因候选与证据"])
    for item in presentation.root_causes:
        fact_ids = "、".join(f"`{value}`" for value in item.fact_ids) or "无"
        evidence_ids = "、".join(f"`{value}`" for value in item.evidence_ids) or "无"
        lines.extend(
            [
                f"### {item.claim_label} · `{item.candidate_id}`",
                f"- 原因：{_safe_text(item.cause)}",
                f"- 事实支撑：{fact_ids}",
                f"- 知识支撑：{evidence_ids}",
                f"- 置信度：{item.confidence:.2f}",
                f"- 适用条件：{_safe_text(item.applicability)}",
                f"- 反证或限制：{_safe_text(item.counterevidence_or_limits)}",
            ]
        )
    if not presentation.root_causes:
        lines.append("- 无根因候选；报告未补写诊断结论。")

    for heading, commands in (
        ("## 4. 检查步骤", presentation.checks),
        ("## 5. 修复步骤", presentation.fixes),
        ("## 6. 验证步骤", presentation.verification_steps),
    ):
        lines.extend(["", heading])
        lines.extend(_commands(commands))

    lines.extend(["", "## 7. 缺失信息"])
    lines.extend(_items(presentation.missing_information))
    lines.extend(
        [
            "",
            "## 8. 置信度、适用条件与局限",
            f"- 总体置信度：{presentation.confidence:.2f}",
        ]
    )
    for item in presentation.root_causes:
        lines.append(
            f"- `{item.candidate_id}` 适用条件：{_safe_text(item.applicability)}"
        )
    lines.extend(_items(presentation.limitations, empty="无额外局限。"))
    lines.extend(["", "## 9. 引用清单"])
    for item in presentation.citations:
        lines.append(
            f"- `{item.evidence_id}` · {_safe_text(item.source_id)} · "
            f"{_safe_text(item.source_url)} · 定位 {_safe_text(item.source_locator)} · "
            f"chunk `{_safe_text(item.chunk_id)}` · build `{item.knowledge_build_id}`"
        )
    if not presentation.citations:
        lines.append("- 无。")
    return lines


def _scan_rendered_report(presentation: PresentationModel, markdown: str) -> None:
    """Scan rendered prose while masking only already-verified opaque identities."""

    trusted = {
        presentation.identity.case_id,
        presentation.identity.source_run_id,
        presentation.identity.diagnosis_sha256,
        presentation.identity.generation_version,
        presentation.font_sha256,
        *(item.fact_id for item in presentation.observed_facts),
        *(item.evidence_id for item in presentation.citations),
        *(item.knowledge_build_id for item in presentation.citations),
        *(item.candidate_id for item in presentation.root_causes),
    }
    scan_value = markdown
    for value in sorted(trusted, key=len, reverse=True):
        scan_value = scan_value.replace(value, "VERIFIED_IDENTIFIER")
    assert_export_safe(scan_value)


def _verified_https(value: str) -> bool:
    if (
        not value.startswith("https://")
        or "\\" in value
        or any(ord(char) < 0x20 or char.isspace() for char in value)
    ):
        return False
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        return False
    return bool(
        parsed.scheme == "https"
        and parsed.hostname
        and parsed.username is None
        and parsed.password is None
    )


def _citation_rows(presentation: PresentationModel) -> tuple[CitationRow, ...]:
    fact_ids = [item.fact_id for item in presentation.observed_facts]
    evidence_ids = [item.evidence_id for item in presentation.citations]
    candidate_ids = [item.candidate_id for item in presentation.root_causes]
    if (
        len(fact_ids) != len(set(fact_ids))
        or len(evidence_ids) != len(set(evidence_ids))
        or len(candidate_ids) != len(set(candidate_ids))
    ):
        raise ValueError("duplicate projection identity")
    facts = set(fact_ids)
    evidence = set(evidence_ids)
    for link in presentation.support_links:
        if (
            not link.fact_ids
            or not link.evidence_ids
            or len(link.fact_ids) != len(set(link.fact_ids))
            or len(link.evidence_ids) != len(set(link.evidence_ids))
            or not set(link.fact_ids) <= facts
            or not set(link.evidence_ids) <= evidence
        ):
            raise ValueError("invalid support graph")
    for candidate in presentation.root_causes:
        if not set(candidate.fact_ids) <= facts or not set(candidate.evidence_ids) <= evidence:
            raise ValueError("invalid candidate graph")
        if candidate.claim_label == "有依据":
            has_complete_edge = any(
                set(candidate.fact_ids) == set(link.fact_ids)
                and set(candidate.evidence_ids) == set(link.evidence_ids)
                for link in presentation.support_links
            )
            if not has_complete_edge:
                raise ValueError("grounded candidate requires one complete support edge")

    rows: list[CitationRow] = []
    for item in sorted(presentation.citations, key=lambda value: value.evidence_id):
        if not _verified_https(item.source_url):
            raise ValueError("citation URL is not verified HTTPS")
        supported_facts = sorted(
            {
                fact_id
                for link in presentation.support_links
                if item.evidence_id in link.evidence_ids
                for fact_id in link.fact_ids
            }
        )
        supported_candidates = sorted(
            candidate.candidate_id
            for candidate in presentation.root_causes
            if candidate.claim_label == "有依据"
            and item.evidence_id in candidate.evidence_ids
            and any(
                set(candidate.fact_ids) == set(link.fact_ids)
                and set(candidate.evidence_ids) == set(link.evidence_ids)
                for link in presentation.support_links
            )
        )
        rows.append(
            CitationRow(
                evidence_id=item.evidence_id,
                source_label=item.source_id,
                source_url=item.source_url,
                source_locator=item.source_locator,
                chunk_id=item.chunk_id,
                source_id=item.source_id,
                knowledge_build_id=item.knowledge_build_id,
                supported_candidate_ids=tuple(supported_candidates),
                supported_fact_ids=tuple(supported_facts),
            )
        )
    result = tuple(rows)
    assert_export_safe([item.model_dump(mode="json") for item in result])
    return result


def render_report(presentation: PresentationModel) -> RenderedReport:
    """Render the fixed Chinese report using no provider, filesystem or LLM input."""

    try:
        if not isinstance(presentation, PresentationModel):
            raise TypeError("presentation type")
        strict = _validated_presentation(presentation)
        _citation_rows(strict)
        markdown = "\n".join(_report_lines(strict)) + "\n"
        _scan_rendered_report(strict, markdown)
        return RenderedReport(
            identity=strict.identity,
            markdown=markdown,
            sha256=sha256_bytes(markdown.encode("utf-8")),
        )
    except Exception:
        failure = ReportRenderError()
    raise failure from None


def render_citations(presentation: PresentationModel) -> RenderedCitations:
    """Export only verified evidence metadata in canonical stable-ID order."""

    try:
        if not isinstance(presentation, PresentationModel):
            raise TypeError("presentation type")
        strict = _validated_presentation(presentation)
        rows = _citation_rows(strict)
        payload = {
            "identity": strict.identity.model_dump(mode="json"),
            "rows": [item.model_dump(mode="json") for item in rows],
        }
        json_bytes = canonical_json_bytes(payload)
        return RenderedCitations(
            identity=strict.identity,
            rows=rows,
            json_bytes=json_bytes,
            sha256=sha256_bytes(json_bytes),
        )
    except Exception:
        failure = CitationRenderError()
    raise failure from None
