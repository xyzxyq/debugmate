"""Value-free prompt-injection marking and recursive export safety scans."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from debugmate.hashing import sha256_bytes
from debugmate.privacy.models import SecretCandidate
from debugmate.privacy.text_redactor import scan_text


class StrictScanModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class InjectionFinding(StrictScanModel):
    """A suspicious instruction span represented without its matched text."""

    rule_id: str
    start: Annotated[int, Field(strict=True, ge=0)]
    end: Annotated[int, Field(strict=True, ge=1)]
    match_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class SafetyScanResult(StrictScanModel):
    safe: bool
    injection_findings: list[InjectionFinding]
    secret_findings: list[SecretCandidate]

    @model_validator(mode="after")
    def require_truthful_safe_flag(self) -> Self:
        expected = not self.injection_findings and not self.secret_findings
        if self.safe is not expected:
            raise ValueError("safe must reflect all findings")
        return self


@dataclass(frozen=True, slots=True)
class _InjectionRule:
    rule_id: str
    pattern: re.Pattern[str]


def _rule(rule_id: str, english: str, chinese: str) -> _InjectionRule:
    return _InjectionRule(rule_id, re.compile(f"(?:{english})|(?:{chinese})", re.IGNORECASE))


INJECTION_RULES: tuple[_InjectionRule, ...] = (
    _rule(
        "INJECT_IGNORE",
        r"\b(?:ignore|disregard|forget|override|bypass)\b.{0,48}"
        r"\b(?:previous|prior|above|system|developer)?\s*(?:instructions?|rules?|prompt)\b",
        r"(?:忽略|无视|绕过|覆盖).{0,24}(?:此前|之前|以上|系统|开发者)?(?:指令|规则|提示词)",
    ),
    _rule(
        "INJECT_POLICY",
        r"\b(?:reveal|show|print|output|disclose)\b.{0,48}"
        r"\b(?:system|developer|hidden|internal)\s*(?:prompt|policy|instructions?|rules?)\b",
        r"(?:泄露|显示|输出|公开).{0,24}(?:系统|开发者|隐藏|内部)(?:提示词|策略|指令|规则)",
    ),
    _rule(
        "INJECT_SECRET",
        r"\b(?:print|show|reveal|output|expose|leak|send)\b.{0,48}"
        r"\b(?:api[_ -]?key|tokens?|passwords?|secrets?|credentials?)\b",
        r"(?:输出|显示|泄露|发送|打印).{0,24}(?:API密钥|密钥|令牌|密码|凭据|秘密)",
    ),
    _rule(
        "INJECT_TOOL",
        r"\b(?:call|invoke|use)\s+(?:the\s+)?(?:tool|shell|powershell|cmd)\b"
        r"|\bexecute\s+(?:this\s+)?(?:shell|powershell|cmd)(?:\s+command)?\b",
        r"(?:调用|使用)(?:外部)?工具|执行\s*(?:shell|powershell|cmd)(?:\s*命令)?",
    ),
    _rule(
        "INJECT_ENCODED",
        r"\b(?:decode|execute|follow)\b.{0,32}\b(?:base64|encoded|payload)\b"
        r"|\bbase64\b.{0,32}\b(?:decode|execute|follow)\b",
        r"(?:解码|执行|遵循).{0,20}(?:base64|编码载荷|编码内容)",
    ),
)


@dataclass(frozen=True, slots=True)
class ExportFinding:
    path: str
    rule_ids: tuple[str, ...]


class UnsafeExport(ValueError):
    """Describe unsafe locations and rule IDs without echoing their values."""

    def __init__(self, findings: Sequence[ExportFinding]) -> None:
        self.findings = tuple(findings)
        rendered = "; ".join(
            f"{item.path} [{','.join(item.rule_ids)}]" for item in self.findings
        )
        super().__init__(f"unsafe export: {rendered}")


def scan_untrusted_text(text: str) -> SafetyScanResult:
    """Mark injection and secret patterns while retaining only hashes and spans."""

    injection_findings: list[InjectionFinding] = []
    for rule in INJECTION_RULES:
        for match in rule.pattern.finditer(text):
            injection_findings.append(
                InjectionFinding(
                    rule_id=rule.rule_id,
                    start=match.start(),
                    end=match.end(),
                    match_sha256=sha256_bytes(match.group(0).encode("utf-8")),
                )
            )
    injection_findings.sort(key=lambda item: (item.start, item.end, item.rule_id))
    secret_findings = scan_text("export", text)
    return SafetyScanResult(
        safe=not injection_findings and not secret_findings,
        injection_findings=injection_findings,
        secret_findings=secret_findings,
    )


_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
def _path_for_key(parent: str, key: object) -> tuple[str, SafetyScanResult]:
    text = str(key)
    scanned = scan_untrusted_text(text)
    if _SAFE_IDENTIFIER.fullmatch(text) and scanned.safe:
        return f"{parent}.{text}", scanned
    opaque = sha256_bytes(text.encode("utf-8"))[:12]
    return f'{parent}["key#{opaque}"]', scanned


def _ignored_secret_rules(key: object | None, value: str) -> set[str]:
    if key is None:
        return set()
    normalized = str(key).lower()
    if normalized == "case_id" and re.fullmatch(r"case_[0-9a-f]{32}", value):
        return {item.rule_id for item in scan_text("metadata", value)}
    if normalized in {"knowledge_build_id"} and re.fullmatch(r"[0-9a-f]{64}", value):
        return {item.rule_id for item in scan_text("metadata", value)}
    if normalized.endswith("sha256") and re.fullmatch(r"[0-9a-f]{64}", value):
        return {item.rule_id for item in scan_text("metadata", value)}
    if normalized in {"run_id", "file_id"}:
        return {"HIGH_ENTROPY_TOKEN"}
    return set()


def _rule_ids(
    result: SafetyScanResult, *, ignored_secret_rules: set[str] | None = None
) -> tuple[str, ...]:
    rules = {item.rule_id for item in result.injection_findings}
    ignored = set() if ignored_secret_rules is None else ignored_secret_rules
    rules.update(item.rule_id for item in result.secret_findings if item.rule_id not in ignored)
    return tuple(sorted(rules))


def assert_export_safe(value: Any) -> None:
    """Recursively reject unsafe strings and report only opaque JSON locations."""

    findings: list[ExportFinding] = []

    def visit(current: Any, path: str, *, metadata_key: object | None = None) -> None:
        if isinstance(current, str):
            result = scan_untrusted_text(current)
            rules = _rule_ids(
                result,
                ignored_secret_rules=_ignored_secret_rules(metadata_key, current),
            )
            if rules:
                findings.append(ExportFinding(path=path, rule_ids=rules))
            return
        if isinstance(current, Mapping):
            for key, nested in current.items():
                child_path, key_scan = _path_for_key(path, key)
                key_rules = _rule_ids(key_scan)
                if key_rules:
                    findings.append(ExportFinding(path=child_path, rule_ids=key_rules))
                visit(nested, child_path, metadata_key=key)
            return
        if isinstance(current, Sequence) and not isinstance(current, (bytes, bytearray)):
            for index, nested in enumerate(current):
                visit(nested, f"{path}[{index}]")

    visit(value, "$")
    unique = sorted(set(findings), key=lambda item: (item.path, item.rule_ids))
    if unique:
        raise UnsafeExport(unique)
