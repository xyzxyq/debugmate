"""Native Gradio 6 workbench structure for verified DebugMate results."""

from __future__ import annotations

import os
import secrets
import stat
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

import gradio as gr
from fastapi import HTTPException
from fastapi.responses import Response
from starlette.datastructures import URL

from debugmate.contracts import DiagnosisRecord, new_case_id
from debugmate.diagnosis.extraction import FieldId
from debugmate.hashing import sha256_bytes
from debugmate.privacy.approval import approve_preview
from debugmate.privacy.image_models import validate_screenshot
from debugmate.privacy.models import InputEnvelope, PreviewBundle
from debugmate.privacy.text_redactor import redact_input
from debugmate.results.contracts import (
    ArtifactAvailability,
    ResultMode,
    ResultStatus,
    ResultViewState,
    SafeFailure,
)
from debugmate.results.service import (
    CorrectionDraft,
    ResultApplicationService,
    ResultServiceError,
    ServiceStageEvent,
)
from debugmate.ui.local_live import LocalPreviewStore
from debugmate.ui.presentation import (
    ComponentViewModel,
    VerifiedDiagnosisPresentation,
    render_verified_diagnosis,
    render_view_state,
)

WORKBENCH_CSS = "\n".join(
    (
        (
            ":root { --canvas: #f5f7fb; --surface-1: #ffffff; --surface-2: #f8fafc; "
            "--sidebar: #edf2f7; --text: #0f172a; --muted: #5f6b7a; "
            "--border: #d8dee8; --primary: #007aff; --primary-soft: #e9f2ff; "
            "--warning-surface: #fff7ed; --warning: #ff9f0a; "
            "--failure-surface: #fff1f2; --failure: #ff3b30; "
            "--success-surface: #ecfdf3; --success: #34c759; --accent: #007aff; }"
        ),
        "* { box-sizing: border-box; }",
        (
            "body, .gradio-container { background: var(--canvas) !important; "
            "color: var(--text) !important; color-scheme: light; }"
        ),
        (
            ".gradio-container { width: 100% !important; max-width: 1440px !important; "
            "margin: 0 auto; "
            "padding: 14px 16px 18px !important; --body-background-fill: var(--canvas); "
            "--background-fill-primary: var(--surface-1); "
            "--background-fill-secondary: var(--surface-2); "
            "--block-background-fill: var(--surface-1); "
            "--block-border-color: var(--border); --block-label-text-color: var(--muted); "
            "--input-background-fill: var(--surface-2); --input-border-color: var(--border); "
            "--body-text-color: var(--text); --body-text-color-subdued: var(--muted); "
            "--border-color-primary: var(--border); }"
        ),
        (
            ".gradio-container code, .gradio-container pre { background: var(--surface-2) "
            "!important; color: var(--text) !important; border-color: var(--border) !important; }"
        ),
        (
            ".gradio-container .prose, .gradio-container .prose p, .gradio-container .prose li, "
            ".gradio-container .prose strong { color: var(--text) !important; }"
        ),
        (
            ".gradio-container a { color: var(--primary) !important; "
            "text-decoration-color: var(--primary) !important; }"
        ),
        ".command-bar { position: sticky; top: 0; z-index: 20; }",
        (
            ".command-bar > .styler { display: grid; "
            "grid-template-columns: minmax(0, 1fr) minmax(180px, auto); "
            "align-items: center; gap: 16px; "
            "background: transparent !important; border: 0 !important; padding: 0 !important; }"
        ),
        (
            ".command-bar { margin: 0 0 12px !important; padding: 8px 12px !important; "
            "background: var(--surface-1) !important; border: 1px solid var(--border) "
            "!important; border-radius: 8px !important; box-shadow: none; }"
        ),
        ".command-bar .product-title { min-width: 0; }",
        ".command-bar .product-title h1 { margin: 0; color: var(--text); font-size: 18px; }",
        (
            ".command-bar .product-title p { margin: 2px 0 0; color: var(--muted); "
            "font-size: 13px; line-height: 1.35; }"
        ),
        (
            ".command-bar .status-indicator { min-width: 0; display: flex; "
            "flex-direction: column; align-items: center; gap: 6px; }"
        ),
        (
            ".command-bar .status-indicator p { margin: 0; max-width: 100%; "
            "text-align: center; overflow-wrap: anywhere; }"
        ),
        (
            ".command-bar .status-indicator p:first-child { display: inline-flex; "
            "align-items: center; "
            "border: 1px solid var(--border); border-radius: 999px; padding: 6px 12px; "
            "font-weight: 700; }"
        ),
        (
            ".command-bar .status-indicator p:not(:first-child) { color: var(--muted); "
            "font-size: 12px; line-height: 1.35; }"
        ),
        ".command-bar .metadata { margin-left: auto; text-align: right; }",
        (
            ".command-bar .styler, .command-bar .block { background: transparent !important; "
            "border: 0 !important; padding: 0 !important; min-height: 0 !important; }"
        ),
        ".command-bar > .styler > .product-title { grid-column: 1; grid-row: 1 / span 2; }",
        ".command-bar > .styler > #diagnostic-status { grid-column: 2; grid-row: 1; }",
        (
            ".command-bar > .styler > #accessible-status { position: absolute !important; "
            "width: 1px !important; height: 1px !important; overflow: hidden !important; "
            "clip: rect(0 0 0 0) !important; white-space: nowrap !important; }"
        ),
        "#workbench-grid:has(> #workbench-grid) { display: grid; }",
        (
            "#workbench-grid:has(> #workbench-grid) { "
            "grid-template-columns: minmax(320px, 360px) minmax(0, 1fr); gap: 16px; }"
        ),
        (
            "#workbench-grid:has(> #workbench-grid) { width: 100% !important; "
            "max-width: none !important; align-items: start; "
            "background: var(--canvas) !important; border: 0 !important; }"
        ),
        "#workbench-grid:has(> #workbench-grid) > #workbench-grid { display: contents; }",
        (
            "#workbench-grid:has(> #workbench-grid) > #workbench-grid > .styler "
            "{ display: contents; }"
        ),
        (
            "#workbench-grid:has(> #workbench-grid) .region { min-width: 0; "
            "background: var(--surface-1); border: 1px solid var(--border); }"
        ),
        (
            "#workbench-grid:has(> #workbench-grid) .region { border-radius: 8px; "
            "padding: 16px; overflow: hidden; }"
        ),
        ".control-rail { background: var(--sidebar) !important; grid-row: 1 / span 2; }",
        ".diagnosis-canvas, .result-workspace { grid-column: 2; }",
        (
            ".region > .styler, .region .gr-accordion, .region .tabs, .region .tabitem { "
            "background: var(--surface-1) !important; color: var(--text) !important; "
            "border-color: var(--border) !important; }"
        ),
        (
            ".region h2 { margin: 0 0 12px; color: var(--text); font-size: 16px; "
            "font-weight: 700; letter-spacing: 0; }"
        ),
        (
            ".section-kicker p { margin: 12px 0 7px; color: var(--muted); font-size: 12px; "
            "font-weight: 700; letter-spacing: 0; }"
        ),
        (
            ".metadata { color: var(--muted) !important; font-family: Cascadia Mono, "
            "Consolas, monospace; font-size: 12px; }"
        ),
        ".metadata { overflow-wrap: anywhere; }",
        (
            ".region label, .region .label-wrap, .region .block-label { "
            "color: var(--muted) !important; }"
        ),
        (
            ".region input, .region textarea, .region select { background: var(--surface-2) "
            "!important; color: var(--text) !important; border-color: var(--border) !important; }"
        ),
        ".region input::placeholder, .region textarea::placeholder { color: var(--muted); }",
        (
            ".region button { min-height: 40px; border-radius: 8px !important; "
            "font-weight: 700 !important; }"
        ),
        (
            ".region button.primary { background: var(--primary) !important; "
            "color: var(--surface-1) !important; border-color: var(--primary) !important; }"
        ),
        (
            ".region button.primary:hover { background: var(--text) !important; "
            "border-color: var(--text) !important; }"
        ),
        (
            ".region button.secondary { background: var(--surface-1) !important; "
            "color: var(--text) !important; border-color: var(--border) !important; }"
        ),
        (
            ".region button.secondary:hover { border-color: var(--primary) !important; "
            "background: var(--primary-soft) !important; }"
        ),
        (
            ".region button:disabled { background: var(--surface-2) !important; "
            "color: var(--text) !important; border-color: var(--border) !important; "
            "opacity: .84; cursor: not-allowed; }"
        ),
        (
            ".correction-panel { margin-top: 12px !important; background: var(--surface-1) "
            "!important; border: 1px solid var(--border) !important; "
            "border-radius: 8px !important; }"
        ),
        ".correction-panel summary { color: var(--text) !important; font-weight: 700; }",
        (
            ".block.diagnosis-summary { padding: 16px; background: var(--surface-2); "
            "border: 1px solid var(--border); border-left: 4px solid var(--muted); "
            "border-radius: 8px; "
            "color: var(--text) !important; }"
        ),
        (
            ".status-indicator.tone-neutral p:first-child { background: var(--surface-2); "
            "color: var(--muted) !important; }"
        ),
        (
            ".status-indicator.tone-blue p:first-child { background: var(--primary-soft); "
            "color: var(--primary) !important; }"
        ),
        (
            ".status-indicator.tone-green p:first-child { background: var(--success-surface); "
            "color: var(--success) !important; }"
        ),
        (
            ".status-indicator.tone-amber p:first-child { background: var(--warning-surface); "
            "color: var(--warning) !important; }"
        ),
        (
            ".status-indicator.tone-red p:first-child { background: var(--failure-surface); "
            "color: var(--failure) !important; }"
        ),
        (
            ".prose.diagnosis-summary { border: 0 !important; padding: 0 !important; "
            "background: transparent !important; }"
        ),
        (
            ".block.diagnosis-summary.tone-neutral { border: 0; padding: 0; "
            "background: transparent; }"
        ),
        (
            ".block.diagnosis-summary.tone-blue { border-left-color: var(--primary); "
            "background: var(--primary-soft); }"
        ),
        (
            ".block.diagnosis-summary.tone-green { border-left-color: var(--success); "
            "background: var(--success-surface); }"
        ),
        (
            ".block.diagnosis-summary.tone-amber { border-left-color: var(--warning); "
            "background: var(--warning-surface); }"
        ),
        (
            ".block.diagnosis-summary.tone-red { border-left-color: var(--failure); "
            "background: var(--failure-surface); }"
        ),
        ".diagnosis-summary p { margin: 0; }",
        (
            ".block.next-steps { margin-top: 12px; padding: 12px 16px; "
            "background: var(--surface-2); "
            "border: 1px solid var(--border); border-radius: 8px; }"
        ),
        ".next-steps p, .next-steps li { color: var(--text) !important; }",
        (
            ".prose.next-steps, .next-steps > .styler { border: 0 !important; "
            "padding: 0 !important; "
            "background: transparent !important; }"
        ),
        ".evidence-kicker p { margin: 16px 0 8px; color: var(--muted); font-weight: 700; }",
        ".tab-container.visually-hidden[aria-hidden='true'] { display: none !important; }",
        (
            ".result-workspace .tabs { background: var(--surface-1) !important; "
            "border-color: var(--border) !important; }"
        ),
        (
            ".result-workspace .tab-nav { border-bottom-color: var(--border) !important; "
            "gap: 4px; }"
        ),
        (
            ".result-workspace .tab-nav button { color: var(--muted) !important; "
            "background: var(--surface-2) !important; border-radius: 10px !important; }"
        ),
        (
            ".result-workspace .tab-nav button.selected { color: var(--text) !important; "
            "border-color: var(--primary) !important; background: var(--primary-soft) !important; }"
        ),
        (
            ".result-workspace [role='tab'] { color: var(--muted) !important; "
            "background: var(--surface-2) !important; }"
        ),
        (
            ".result-workspace [role='tab'][aria-selected='true'] { color: var(--primary) "
            "!important; border-color: var(--primary) !important; }"
        ),
        ".report-panel { max-height: 560px; max-width: 80ch; overflow: auto; }",
        (
            ".report-summary { margin: 0 0 12px; padding: 12px 16px; "
            "background: var(--success-surface); border: 1px solid var(--border); "
            "border-radius: 8px; }"
        ),
        ".report-panel, #fact-table, #citation-table { color: var(--text) !important; }",
        (
            ".report-panel pre { max-width: 100%; white-space: pre-wrap; "
            "overflow-wrap: anywhere; overflow-x: auto; }"
        ),
        (
            ".diagnosis-summary code, .next-steps code, .report-summary code { "
            "white-space: pre-wrap !important; overflow-wrap: anywhere; "
            "word-break: break-word; }"
        ),
        "#fact-table, #citation-table, #diagnostic-commands { max-width: 100%; overflow: auto; }",
        (
            "#fact-table { max-height: 430px; scrollbar-color: var(--border) "
            "var(--surface-1); }"
        ),
        (
            ".region table { width: 100%; border-collapse: collapse; color: var(--text); "
            "font-size: 12px; background: var(--surface-1); }"
        ),
        (
            ".region th { padding: 8px 9px; background: var(--surface-2); color: var(--muted); "
            "border: 0; border-bottom: 1px solid var(--border); text-align: left; }"
        ),
        (
            ".region td { padding: 8px 9px; border: 0; border-bottom: 1px solid var(--border); "
            "vertical-align: top; overflow-wrap: anywhere; }"
        ),
        "#diagnostic-commands td:nth-child(2) { white-space: pre-wrap; overflow-wrap: anywhere; }",
        "#failure-details:not(:empty) { color: var(--failure); }",
        "#partial-retry { border-color: var(--warning) !important; }",
        (
            "#diagnostic-audio, #diagnostic-audio .wrap, #diagnostic-audio label, "
            "#diagnostic-audio .controls { background: var(--surface-2) !important; "
            "color: var(--text) !important; border-color: var(--border) !important; "
            "color-scheme: light; }"
        ),
        (
            "#diagnostic-card img { display: block; max-width: 100%; "
            "height: auto; object-fit: contain; }"
        ),
        (
            ":focus-visible { outline: 2px solid var(--accent) !important; "
            "outline-offset: 2px !important; }"
        ),
        (
            "footer { background: var(--canvas) !important; color: var(--muted) !important; "
            "border-color: var(--border) !important; }"
        ),
        "footer a, footer button { color: var(--muted) !important; }",
        (
            "@media (max-width: 1099px) { #workbench-grid:has(> #workbench-grid) "
            "{ grid-template-columns: 1fr; } }"
        ),
        (
            "@media (max-width: 1099px) { #workbench-grid:has(> #workbench-grid) "
            ".control-rail { grid-row: auto; } }"
        ),
        (
            "@media (max-width: 1099px) { #workbench-grid:has(> #workbench-grid) "
            ".diagnosis-canvas, #workbench-grid:has(> #workbench-grid) .result-workspace "
            "{ grid-column: auto; } }"
        ),
        (
            "@media (max-width: 899px) { #workbench-grid:has(> #workbench-grid) "
            "{ grid-template-columns: 1fr; } }"
        ),
        (
            "@media (max-width: 899px) { #workbench-grid:has(> #workbench-grid) "
            ".control-rail, #workbench-grid:has(> #workbench-grid) .diagnosis-canvas, "
            "#workbench-grid:has(> #workbench-grid) .result-workspace "
            "{ grid-column: auto; grid-row: auto; } }"
        ),
        (
            "@media (max-width: 899px) { .command-bar { position: static; } "
            ".command-bar > .styler { grid-template-columns: 1fr; } "
            ".command-bar > .styler > .product-title, .command-bar > .styler > #diagnostic-status, "
            ".command-bar > .styler > #accessible-status, "
            ".command-bar > .styler > #result-metadata "
            "{ grid-column: auto; grid-row: auto; } "
            ".command-bar .metadata { margin-left: 0; "
            "text-align: left; } }"
        ),
        "@media (max-width: 899px) { .report-panel { max-height: none; } }",
        "@media (max-width: 639px) { .gradio-container { padding: 8px !important; } }",
    )
)

_FIELD_LABELS = (
    "异常类型",
    "关键回溯行",
    "包/模块",
    "版本",
    "设备",
    "路径",
)
_FIELD_IDS = tuple(FieldId)
_EMPTY_FIELD_VALUES = ("", "", "", "", "", "")
_CASE_ID = "case_"
_RUN_ID = "run_"
_RESULT_ID = "result_"
_CONTENT_PREFIX = "/debugmate-content/"
_CONTENT_ROUTE = f"{_CONTENT_PREFIX}{{token}}"
_CONTENT_CALLBACKS_ATTR = "_debugmate_content_callbacks"
_FACT_HEADERS = ("事实 ID", "观察或结论", "证据 ID", "来源", "支持关系")
_COMMAND_HEADERS = ("步骤", "命令", "平台", "影响", "预期结果", "回退说明")
_CITATION_HEADERS = ("证据 ID", "标题", "官方来源", "版本范围")


def _markdown_table(title: str, headers: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> str:
    """Render verified scalar rows as a non-interactive accessible Markdown table."""

    def cell(value: object) -> str:
        return (
            str(value)
            .replace("\\", "\\\\")
            .replace("|", "\\|")
            .replace("\r", " ")
            .replace("\n", " ")
        )

    header = "| " + " | ".join(cell(item) for item in headers) + " |"
    separator = "| " + " | ".join("---" for _item in headers) + " |"
    body = ["| " + " | ".join(cell(item) for item in row) + " |" for row in rows]
    return "\n".join((f"### {title}", "", header, separator, *body))


_DEFAULT_CONTENT_ORIGIN = "http://127.0.0.1:7860"


def _loopback_origin(value: object, *, origin_only: bool) -> str:
    """Normalize a loopback HTTP origin without trusting arbitrary Host text."""

    if isinstance(value, URL):
        value = str(value)
    elif not isinstance(value, str):
        raise ResultServiceError("download_invalid")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise ResultServiceError("download_invalid") from None
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.username is not None
        or parsed.password is not None
        or port is None
        or not 1024 <= port <= 65535
        or parsed.query
        or parsed.fragment
        or (origin_only and parsed.path not in {"", "/"})
    ):
        raise ResultServiceError("download_invalid")
    return f"http://127.0.0.1:{port}"


@dataclass(frozen=True, slots=True)
class UiContent:
    """In-memory verified bytes issued to a native component through a token URL."""

    payload: bytes = field(repr=False)
    filename: str
    mime_type: str
    attachment: bool
    sha256: str


@dataclass(frozen=True, slots=True)
class UiContentUrl:
    url: str
    filename: str
    mime_type: str


class _UiContentStore:
    """Bounded server-owned content registry with no caller-visible server path."""

    def __init__(self, content_origin: str) -> None:
        self._content_origin = _loopback_origin(content_origin, origin_only=True)
        self._lock = threading.RLock()
        self._values: dict[str, UiContent] = {}

    @property
    def content_origin(self) -> str:
        return self._content_origin

    @staticmethod
    def _token_from_url(value: object, *, content_origin: str) -> str:
        raw = value.url if isinstance(value, UiContentUrl) else value
        if not isinstance(raw, str):
            raise ResultServiceError("download_invalid")
        if raw.startswith(content_origin):
            raw = raw.removeprefix(content_origin)
        if not raw.startswith(_CONTENT_PREFIX):
            raise ResultServiceError("download_invalid")
        token = raw.removeprefix(_CONTENT_PREFIX)
        if len(token) != 32 or any(character not in "0123456789abcdef" for character in token):
            raise ResultServiceError("download_invalid")
        return token

    def issue(self, download, *, attachment: bool) -> UiContentUrl:
        filename = download.filename
        mime_type = download.mime_type
        if (
            not isinstance(filename, str)
            or not filename
            or "/" in filename
            or "\\" in filename
            or ":" in filename
            or "\x00" in filename
        ):
            raise ResultServiceError("download_invalid")
        payload = download.read_bytes()
        return self.issue_bytes(
            payload,
            filename=filename,
            mime_type=mime_type,
            attachment=attachment,
        )

    def issue_bytes(
        self, payload: bytes, *, filename: str, mime_type: str, attachment: bool
    ) -> UiContentUrl:
        """Issue already-verified bytes without exposing their server path."""

        if not isinstance(payload, bytes):
            raise ResultServiceError("download_invalid")
        if (
            not isinstance(filename, str)
            or not filename
            or "/" in filename
            or "\\" in filename
            or ":" in filename
            or "\x00" in filename
            or not isinstance(mime_type, str)
            or not mime_type
        ):
            raise ResultServiceError("download_invalid")
        content = UiContent(
            payload=payload,
            filename=filename,
            mime_type=mime_type,
            attachment=attachment,
            sha256=sha256_bytes(payload),
        )
        token = secrets.token_hex(16)
        with self._lock:
            self._values[token] = content
            while len(self._values) > 64:
                self._values.pop(next(iter(self._values)))
        return UiContentUrl(
            url=f"{self._content_origin}{_CONTENT_PREFIX}{token}",
            filename=filename,
            mime_type=mime_type,
        )

    def resolve(self, url: object) -> UiContent:
        token = self._token_from_url(url, content_origin=self._content_origin)
        with self._lock:
            content = self._values.get(token)
        if content is None or sha256_bytes(content.payload) != content.sha256:
            raise ResultServiceError("download_invalid")
        return content


class _UiSessionStateStore:
    """Bounded server-only registry of one strict result state per UI session."""

    def __init__(self, *, max_sessions: int = 64) -> None:
        if not isinstance(max_sessions, int) or isinstance(max_sessions, bool) or max_sessions < 1:
            raise ValueError("max_sessions must be a positive integer")
        self._max_sessions = max_sessions
        self._values: dict[str, ResultViewState] = {}
        self._lease_by_session: dict[str, str] = {}
        self._session_by_lease: dict[str, str] = {}
        self._lease_sources: dict[str, str] = {}
        self._session_order: dict[str, None] = {}
        self._audit_events: list[dict[str, str | bool | None]] = []
        self._lock = threading.RLock()

    def _record_event(
        self,
        operation: str,
        key: str,
        state: ResultViewState | None,
        *,
        success: bool,
    ) -> None:
        self._audit_events.append(
            {
                "operation": operation,
                "session_sha256_prefix": sha256_bytes(key.encode("utf-8"))[:12],
                "status": None if state is None else state.status.value,
                "source_run_id": (
                    None
                    if state is None or state.identity is None
                    else state.identity.source_run_id
                ),
                "success": success,
            }
        )
        del self._audit_events[:-32]

    @staticmethod
    def _key(request: object | None) -> str | None:
        value = getattr(request, "session_hash", None)
        if (
            not isinstance(value, str)
            or not 8 <= len(value) <= 128
            or any(
                not (character.isascii() and (character.isalnum() or character in "-_"))
                for character in value
            )
        ):
            return None
        return value

    @staticmethod
    def _checked_state(state: object) -> ResultViewState | None:
        if not isinstance(state, ResultViewState):
            return None
        try:
            return ResultViewState.model_validate_json(state.model_dump_json(), strict=True)
        except (TypeError, ValueError):
            return None

    def _drop_session(self, key: str) -> None:
        self._values.pop(key, None)
        self._session_order.pop(key, None)
        lease = self._lease_by_session.pop(key, None)
        if lease is not None:
            self._session_by_lease.pop(lease, None)
            self._lease_sources.pop(lease, None)

    def _touch_session(self, key: str) -> None:
        self._session_order.pop(key, None)
        self._session_order[key] = None
        while len(self._session_order) > self._max_sessions:
            self._drop_session(next(iter(self._session_order)))

    def _store(self, key: str, checked: ResultViewState) -> None:
        self._values[key] = checked
        lease = self._lease_by_session.get(key)
        if lease is not None and checked.identity is not None:
            self._lease_sources[lease] = checked.identity.source_run_id
        self._touch_session(key)

    def issue_lease(self, request: object) -> str | None:
        key = self._key(request)
        if key is None:
            return None
        with self._lock:
            lease = self._lease_by_session.get(key)
            if lease is None:
                lease = "lease_" + secrets.token_hex(16)
                self._lease_by_session[key] = lease
                self._session_by_lease[lease] = key
            self._touch_session(key)
            self._record_event("issue_lease", key, self._values.get(key), success=True)
            return lease

    def publish(self, request: object, state: object) -> bool:
        key = self._key(request)
        checked = self._checked_state(state)
        if key is None or checked is None:
            return False
        with self._lock:
            self._store(key, checked)
            self._record_event("publish_request", key, checked, success=True)
        return True

    def publish_lease(self, lease: object, state: object, expected_source_run_id: object) -> bool:
        checked = self._checked_state(state)
        if (
            not isinstance(lease, str)
            or len(lease) != 38
            or not lease.startswith("lease_")
            or any(character not in "0123456789abcdef" for character in lease[6:])
            or not isinstance(expected_source_run_id, str)
            or not self._strict_run_id(expected_source_run_id)
            or checked is None
        ):
            return False
        with self._lock:
            key = self._session_by_lease.get(lease)
            if key is None:
                return False
            if self._lease_sources.get(lease) != expected_source_run_id:
                self._record_event("publish_lease", key, checked, success=False)
                return False
            self._store(key, checked)
            self._record_event("publish_lease", key, checked, success=True)
        return True

    def clear_lease(self, lease: object) -> bool:
        if not isinstance(lease, str):
            return False
        with self._lock:
            key = self._session_by_lease.get(lease)
            if key is None:
                return False
            self._record_event("clear_lease", key, self._values.get(key), success=True)
            self._drop_session(key)
        return True

    @staticmethod
    def _strict_run_id(value: str) -> bool:
        return (
            value.startswith(_RUN_ID)
            and len(value) == len(_RUN_ID) + 32
            and all(character in "0123456789abcdef" for character in value[len(_RUN_ID) :])
        )

    def read(self, request: object | None) -> ResultViewState | None:
        key = self._key(request)
        if key is None:
            return None
        with self._lock:
            value = self._values.get(key)
        if value is None:
            return None
        return ResultViewState.model_validate_json(value.model_dump_json(), strict=True)

    def clear(self, request: object | None) -> bool:
        key = self._key(request)
        if key is None:
            return False
        with self._lock:
            existed = key in self._values or key in self._lease_by_session
            self._drop_session(key)
            return existed

    def __len__(self) -> int:
        with self._lock:
            return len(self._values)

    def audit_snapshot(self) -> tuple[dict[str, str | None], ...]:
        """Return hashed identity-only diagnostics; never raw session keys or capabilities."""

        with self._lock:
            values = tuple(self._values.items())
        return tuple(
            {
                "session_sha256_prefix": sha256_bytes(key.encode("utf-8"))[:12],
                "status": state.status.value,
                "source_run_id": (None if state.identity is None else state.identity.source_run_id),
            }
            for key, state in values
        )

    def audit_events(self) -> tuple[dict[str, str | bool | None], ...]:
        with self._lock:
            return tuple(dict(item) for item in self._audit_events)


@dataclass(frozen=True, slots=True)
class CallbackPayload:
    """Strict UI state plus server-owned component outputs, never input paths."""

    state: ResultViewState
    view: ComponentViewModel
    report_markdown: str | None
    card_url: UiContentUrl | None
    audio_url: UiContentUrl | None
    download_url: UiContentUrl | None
    field_values: tuple[str, str, str, str, str, str]
    redacted_input: str = ""
    category: str = "等待诊断"
    confidence: str = "暂无"
    fact_rows: tuple[tuple[str, str, str, str, str], ...] = ()
    citation_rows: tuple[tuple[str, str, str, str], ...] = ()
    command_rows: tuple[tuple[str, str, str, str, str, str], ...] = ()
    recap_text: str = ""
    failure_details: tuple[tuple[str, str], ...] = ()
    diagnosis: VerifiedDiagnosisPresentation | None = None


def _capability_file_data(value: UiContentUrl | None) -> dict[str, object] | None:
    """Serialize a verified loopback capability without a filesystem handoff."""

    if value is None:
        return None
    return {
        "path": value.url,
        "url": value.url,
        "orig_name": value.filename,
        "mime_type": value.mime_type,
        "is_stream": False,
        "meta": {"_type": "gradio.FileData"},
    }


class UiCallbacks:
    """Thin adapter that resolves every displayed member through the service."""

    def __init__(
        self, service: ResultApplicationService, *, content_origin: str = _DEFAULT_CONTENT_ORIGIN
    ) -> None:
        self._service = service
        self._content = _UiContentStore(content_origin)
        self._sessions = _UiSessionStateStore()

    def _require_loopback_request(self, request: object | None) -> None:
        """Require the queued event source to match the configured loopback server."""

        if request is None:
            return
        observed = _loopback_origin(getattr(request, "url", None), origin_only=False)
        if observed != self._content.content_origin:
            raise ResultServiceError("download_invalid")

    @staticmethod
    def _failure(state: ResultViewState, code: str) -> ResultViewState:
        safe_code = (
            code
            if code in {"download_invalid", "result_bundle_invalid"}
            else "result_bundle_invalid"
        )
        return ResultViewState(
            mode=state.mode,
            status=ResultStatus.FAILED,
            fixture_id=state.fixture_id,
            fixture_name=state.fixture_name,
            availability=ArtifactAvailability(),
            failure=SafeFailure(code=safe_code, failed_stage="download", retry_scope="download"),
        )

    @staticmethod
    def _strict_id(value: object, prefix: str) -> bool:
        return (
            isinstance(value, str)
            and value.startswith(prefix)
            and len(value) == len(prefix) + 32
            and all(character in "0123456789abcdef" for character in value[len(prefix) :])
        )

    def resolve_content(self, url: object) -> UiContent:
        """Route-only content handoff; it never accepts or returns a file path."""

        return self._content.resolve(url)

    def publish_session_state(self, request: object, state: object) -> bool:
        """Publish one strict server result state for this local Gradio session."""

        return self._sessions.publish(request, state)

    def issue_session_lease(self, request: object) -> str | None:
        return self._sessions.issue_lease(request)

    def publish_session_state_lease(
        self, lease: object, state: object, expected_source_run_id: object
    ) -> bool:
        return self._sessions.publish_lease(lease, state, expected_source_run_id)

    def clear_session_lease(self, lease: object) -> bool:
        return self._sessions.clear_lease(lease)

    def session_audit_snapshot(self) -> tuple[dict[str, str | None], ...]:
        return self._sessions.audit_snapshot()

    def session_audit_events(self) -> tuple[dict[str, str | bool | None], ...]:
        return self._sessions.audit_events()

    def download_surface(
        self, *, request: object | None = None
    ) -> tuple[str, UiContentUrl | None, str | None]:
        """Re-verify and issue only a terminal bundle from server session state."""

        state = self._sessions.read(request)
        if (
            not isinstance(state, ResultViewState)
            or state.status not in {ResultStatus.COMPLETED, ResultStatus.PARTIAL}
            or state.identity is None
            or state.result_id is None
        ):
            return "", None, None
        try:
            self._require_loopback_request(request)
            view = render_view_state(state)
            bundle_url = self._content.issue(self._member(state, "bundle"), attachment=True)
            return view.download_metadata, bundle_url, view.download_label
        except (ResultServiceError, OSError, TypeError, ValueError):
            return "", None, None

    def _member(self, state: ResultViewState, member_id: str):
        if state.identity is None or state.result_id is None:
            raise ResultServiceError("download_invalid")
        return self._service.resolve_download(state.identity.case_id, state.result_id, member_id)

    def _correction_fields(self, state: ResultViewState) -> tuple[str, str, str, str, str, str]:
        """Read six values only from the verified server-side run record."""

        if state.identity is None or state.status not in {
            ResultStatus.COMPLETED,
            ResultStatus.PARTIAL,
        }:
            return _EMPTY_FIELD_VALUES
        try:
            fields = self._service.correction_fields(state.identity.source_run_id)
            if fields.source_run_id != state.identity.source_run_id:
                raise ResultServiceError("correction_invalid")
            return fields.values
        except (AttributeError, ResultServiceError, TypeError, ValueError):
            return _EMPTY_FIELD_VALUES

    def _details(
        self, state: ResultViewState
    ) -> tuple[
        str,
        str,
        str,
        tuple[tuple[str, str, str, str, str], ...],
        tuple[tuple[str, str, str, str], ...],
        tuple[tuple[str, str, str, str, str, str], ...],
        str,
        VerifiedDiagnosisPresentation,
    ]:
        """Derive UI facts only from freshly verified public result members."""

        diagnosis = DiagnosisRecord.model_validate_json(
            self._member(state, "diagnosis").read_bytes(), strict=True
        )
        recap = self._member(state, "recap_text").read_bytes().decode("utf-8")
        summary = "\n".join(f"{fact.field_id}：{fact.value}" for fact in diagnosis.observed_facts)
        evidence_by_fact = {
            fact_id: evidence_id
            for link in diagnosis.support_links
            for fact_id in link.fact_ids
            for evidence_id in link.evidence_ids[:1]
        }
        facts = tuple(
            (
                fact.fact_id,
                fact.value,
                evidence_by_fact.get(fact.fact_id, ""),
                str(fact.source_kind),
                "有依据" if fact.fact_id in evidence_by_fact else "观察",
            )
            for fact in diagnosis.observed_facts
        )
        citations = tuple(
            (item.evidence_id, item.source_id, item.source_url, item.locator)
            for item in diagnosis.evidence
        )
        commands = tuple(
            (
                section,
                item.command,
                str(item.platform),
                item.impact,
                item.expected_result,
                item.rollback,
            )
            for section, items in (
                ("检查", diagnosis.checks),
                ("修复", diagnosis.fixes),
                ("验证", diagnosis.verification_steps),
            )
            for item in items
        )
        return (
            summary,
            str(diagnosis.category),
            f"{diagnosis.confidence:.2f}",
            facts,
            citations,
            commands,
            recap,
            render_verified_diagnosis(diagnosis),
        )

    def _render(self, state: ResultViewState) -> CallbackPayload:
        if state.status not in {ResultStatus.COMPLETED, ResultStatus.PARTIAL}:
            return CallbackPayload(
                state=state,
                view=render_view_state(state),
                report_markdown=None,
                card_url=None,
                audio_url=None,
                download_url=None,
                field_values=_EMPTY_FIELD_VALUES,
                failure_details=render_view_state(state).failure_details,
            )
        try:
            report = self._member(state, "report").read_bytes().decode("utf-8")
            card_url = None
            if state.availability.card:
                card_url = self._content.issue(self._member(state, "card"), attachment=False)
            audio_url = None
            if state.availability.audio:
                audio_url = self._content.issue(self._member(state, "audio"), attachment=False)
            download_url = self._content.issue(self._member(state, "bundle"), attachment=True)
            details = self._details(state)
            return CallbackPayload(
                state=state,
                view=render_view_state(state),
                report_markdown=report,
                card_url=card_url,
                audio_url=audio_url,
                download_url=download_url,
                field_values=self._correction_fields(state),
                redacted_input=details[0],
                category=details[1],
                confidence=details[2],
                fact_rows=details[3],
                citation_rows=details[4],
                command_rows=details[5],
                recap_text=details[6],
                failure_details=render_view_state(state).failure_details,
                diagnosis=details[7],
            )
        except (KeyError, ResultServiceError, TypeError, UnicodeError, OSError, ValueError):
            failed = self._failure(state, "download_invalid")
            return CallbackPayload(
                state=failed,
                view=render_view_state(failed),
                report_markdown=None,
                card_url=None,
                audio_url=None,
                download_url=None,
                field_values=_EMPTY_FIELD_VALUES,
                failure_details=render_view_state(failed).failure_details,
            )

    def load_replay(self, fixture_id: object, *, request: object | None = None) -> CallbackPayload:
        if (
            not isinstance(fixture_id, str)
            or not fixture_id
            or "/" in fixture_id
            or "\\" in fixture_id
        ):
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))
        try:
            self._require_loopback_request(request)
            return self._render(self._service.load_replay(fixture_id))
        except Exception:
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))

    def load_replay_events(self, fixture_id: object, *, request: object | None = None):
        """Yield replay progress only from the service's strict stage stream."""

        if (
            not isinstance(fixture_id, str)
            or not fixture_id
            or "/" in fixture_id
            or "\\" in fixture_id
        ):
            yield self._render(self._failure(_idle_view(), "result_bundle_invalid"))
            return
        try:
            self._require_loopback_request(request)
            for event in self._service.load_replay_events(fixture_id):
                if not isinstance(event, ServiceStageEvent):
                    raise ResultServiceError("result_bundle_invalid")
                yield self._render(event.state)
        except Exception:
            yield self._render(self._failure(_idle_view(), "result_bundle_invalid"))

    def diagnose(
        self, approved_payload: object, *, request: object | None = None
    ) -> CallbackPayload:
        try:
            self._require_loopback_request(request)
            return self._render(self._service.diagnose_and_compose(approved_payload))
        except Exception:
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))

    def diagnose_events(self, approved_payload: object, *, request: object | None = None):
        """Yield strict UI payloads as the service completes actual result stages."""

        try:
            self._require_loopback_request(request)
            for event in self._service.diagnose_and_compose_events(approved_payload):
                if not isinstance(event, ServiceStageEvent):
                    raise ResultServiceError("result_bundle_invalid")
                yield self._render(event.state)
        except Exception:
            yield self._render(self._failure(_idle_view(), "result_bundle_invalid"))

    def refresh(
        self, case_id: object, result_id: object, *, request: object | None = None
    ) -> CallbackPayload:
        if not self._strict_id(case_id, _CASE_ID) or not self._strict_id(result_id, _RESULT_ID):
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))
        try:
            self._require_loopback_request(request)
            return self._render(self._service.restore_result(case_id, result_id))
        except Exception:
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))

    def retry(
        self, case_id: object, result_id: object, *, request: object | None = None
    ) -> CallbackPayload:
        if not self._strict_id(case_id, _CASE_ID) or not self._strict_id(result_id, _RESULT_ID):
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))
        try:
            self._require_loopback_request(request)
            return self._render(self._service.retry_stage(case_id, result_id))
        except Exception:
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))

    def correct(
        self,
        previous_run_id: object,
        draft: CorrectionDraft | str,
        *,
        confirmed: object,
        request: object | None = None,
    ) -> CallbackPayload:
        if not self._strict_id(previous_run_id, _RUN_ID) or not isinstance(confirmed, bool):
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))
        try:
            self._require_loopback_request(request)
            return self._render(
                self._service.correct_and_compose(previous_run_id, draft, confirmed)
            )
        except Exception:
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))


def mount_content_endpoint(application, callbacks: UiCallbacks) -> None:
    """Serve a token's re-hashed in-memory bytes; no component path is exposed."""

    @application.get(_CONTENT_ROUTE, include_in_schema=False)
    def content(token: str) -> Response:
        try:
            value = callbacks.resolve_content(f"{_CONTENT_PREFIX}{token}")
        except ResultServiceError:
            raise HTTPException(status_code=404, detail="content unavailable") from None
        headers = {}
        if value.attachment:
            headers["Content-Disposition"] = f'attachment; filename="{value.filename}"'
        return Response(content=value.payload, media_type=value.mime_type, headers=headers)


def ensure_content_endpoint(app: gr.Blocks) -> None:
    """Reattach the private content route after Gradio rebuilds its ASGI app."""

    callbacks = getattr(app, _CONTENT_CALLBACKS_ATTR, None)
    if not isinstance(callbacks, UiCallbacks):
        raise TypeError("DebugMate content callbacks are unavailable")
    if _CONTENT_ROUTE not in {getattr(route, "path", "") for route in app.app.routes}:
        mount_content_endpoint(app.app, callbacks)


def _idle_view() -> ResultViewState:
    return ResultViewState(
        mode=ResultMode.LIVE,
        status=ResultStatus.IDLE,
        availability=ArtifactAvailability(),
    )


def correction_draft_from_fields(
    original: object, current: object, previous_run_id: object
) -> tuple[CorrectionDraft | None, str]:
    """Make a local single-field draft; this helper never calls the service."""

    if (
        not isinstance(original, (tuple, list))
        or not isinstance(current, (tuple, list))
        or len(original) != len(_FIELD_IDS)
        or len(current) != len(_FIELD_IDS)
        or not isinstance(previous_run_id, str)
        or not UiCallbacks._strict_id(previous_run_id, _RUN_ID)
        or not all(isinstance(value, str) for value in (*original, *current))
    ):
        return None, "请先修改至少一个抽取字段。"
    changed = [
        (index, before, after)
        for index, (before, after) in enumerate(zip(original, current, strict=True))
        if before != after
    ]
    if not changed:
        return None, "请先修改至少一个抽取字段。"
    count = len(changed)
    summary_lines = [f"有 {count} 项未确认修改。"]
    summary_lines.extend(
        f"{_FIELD_LABELS[index]}：{before} → {after}" for index, before, after in changed
    )
    if count != 1:
        summary_lines.append("请一次确认一项修改，避免混合多个字段的证据变更。")
        return None, "\n".join(summary_lines)
    index, _before, replacement = changed[0]
    if not replacement.strip():
        summary_lines.append("修改后的字段不能为空。")
        return None, "\n".join(summary_lines)
    try:
        draft = CorrectionDraft(
            field_id=_FIELD_IDS[index],
            replacement=replacement,
            reason="用户确认的已脱敏字段修正。",
        )
    except (TypeError, ValueError):
        return None, "请先修改至少一个抽取字段。"
    return draft, "\n".join(summary_lines)


def _status_text(view: ComponentViewModel) -> str:
    status_badge = view.status_badge
    return "\n\n".join((f"### {status_badge}", view.mode_badge))


def _overview_text(payload: CallbackPayload) -> str:
    """Compose state truth with diagnosis facts only when strict parsing succeeded."""

    view = payload.view
    diagnosis = payload.diagnosis
    rows = [f"### {view.overview_heading}", view.overview_body]
    if diagnosis is not None:
        rows = [
            "### 发生了什么",
            diagnosis.what_happened,
            "### 最可能原因",
            diagnosis.most_likely_reason,
            "### 先做什么",
            diagnosis.first_action_summary,
            "### 如何验证",
            f"`{diagnosis.how_to_verify}`",
        ]
    if view.fallback_badge:
        rows.extend(("### 语音状态", view.fallback_badge))
    return "\n\n".join(rows)


def _next_action_text(payload: CallbackPayload) -> str:
    diagnosis = payload.diagnosis
    if diagnosis is None or diagnosis.next_action is None:
        return "### 现在就做这一步\n\n完成诊断后，这里会显示唯一的建议行动。"
    return (
        "### 现在就做这一步\n\n"
        f"**完整命令（可选择复制）：** `{diagnosis.first_action}`\n\n"
        "命令仅供查看，DebugMate 不会自动执行或安装软件。"
    )


def _report_summary_text(payload: CallbackPayload) -> str:
    diagnosis = payload.diagnosis
    if diagnosis is None:
        return "### 结论速览\n\n完成诊断后显示学生可读结论。"
    return "\n\n".join(
        (
            "### 结论速览",
            f"**发生了什么：** {diagnosis.what_happened}",
            f"**最可能原因：** {diagnosis.most_likely_reason}",
            f"**先做什么：** `{diagnosis.first_action}`",
            f"**如何验证：** `{diagnosis.how_to_verify}`",
        )
    )


def _component_updates(payload: CallbackPayload) -> tuple[object, ...]:
    """Convert one already verified callback payload into atomic native updates."""

    view = payload.view
    failure = ""
    if payload.failure_details:
        failure = "\n\n".join(
            (
                "#### 运行详情",
                *(f"**{label}：** {value}" for label, value in payload.failure_details),
                view.safe_failure_copy or "",
            )
        )
    return (
        gr.update(
            value=_status_text(view),
            elem_classes=["status-indicator", f"tone-{view.state_tone}"],
        ),
        view.result_metadata,
        failure,
        gr.update(value=payload.report_markdown or "尚未生成诊断结果"),
        gr.update(
            value=_capability_file_data(payload.card_url),
            visible=payload.card_url is not None,
        ),
        gr.update(
            value=_capability_file_data(payload.audio_url),
            visible=payload.audio_url is not None,
        ),
        gr.update(
            value=_capability_file_data(payload.download_url),
            label=view.download_label or "下载结果包",
            visible=payload.download_url is not None,
            interactive=payload.download_url is not None,
        ),
        # A correction becomes actionable only after a local, explicit draft
        # exists; terminal state alone must never submit a rerun.
        gr.update(interactive=False),
        payload.state,
    )


def _retry_control_updates(payload: CallbackPayload) -> tuple[object, str | None, str | None]:
    """Expose retry authority only for a verified partial terminal result."""

    state = payload.state
    view = payload.view
    if (
        state.status is ResultStatus.PARTIAL
        and state.identity is not None
        and state.result_id is not None
        and view.retry_label is not None
    ):
        return (
            gr.update(value=view.retry_label, visible=True, interactive=True),
            state.identity.case_id,
            state.result_id,
        )
    return gr.update(value="安全重试", visible=False, interactive=False), None, None


_ENVIRONMENT_KEYS = {
    "python": "python",
    "python版本": "python",
    "os": "os",
    "操作系统": "os",
    "system": "os",
    "cuda": "cuda",
    "pytorch": "pytorch",
    "torch": "pytorch",
    "gpu": "gpu",
}


def _parse_environment(value: object) -> dict[str, str]:
    """Parse optional environment notes without guessing or dropping details."""

    if not isinstance(value, str) or not value.strip():
        return {}
    result: dict[str, str] = {}
    detail_index = 1
    for raw_line in value.replace("；", "\n").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        colon = line.find(":")
        equals = line.find("=")
        positions = [position for position in (colon, equals) if position >= 0]
        split_at = min(positions) if positions else -1
        if split_at > 0:
            raw_key = line[:split_at].strip()
            parsed_value = line[split_at + 1 :].strip()
            normalized = _ENVIRONMENT_KEYS.get(raw_key.casefold())
            if normalized is not None and parsed_value and normalized not in result:
                result[normalized] = parsed_value
                continue
        result[f"detail_{detail_index:03d}"] = line
        detail_index += 1
    return result


def _has_reparse_attribute(path: Path) -> bool:
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse)


def _require_cached_upload(value: object, cache_root: Path) -> Path:
    """Confine one regular upload to the configured Gradio cache before reading bytes."""

    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("invalid screenshot upload")
    candidate = Path(value)
    root = Path(cache_root)
    if not candidate.is_absolute() or not root.is_absolute():
        raise ValueError("invalid screenshot upload")
    if ".." in candidate.parts:
        raise ValueError("invalid screenshot upload")
    lexical_root = Path(os.path.abspath(root))
    lexical_candidate = Path(os.path.abspath(candidate))
    try:
        if os.path.commonpath((str(lexical_root), str(lexical_candidate))) != str(
            lexical_root
        ):
            raise ValueError("invalid screenshot upload")
    except ValueError:
        raise ValueError("invalid screenshot upload") from None

    root_info = lexical_root.lstat()
    if (
        stat.S_ISLNK(root_info.st_mode)
        or _has_reparse_attribute(lexical_root)
        or not lexical_root.is_dir()
    ):
        raise ValueError("invalid screenshot upload")
    root_resolved = lexical_root.resolve(strict=True)
    relative = lexical_candidate.relative_to(lexical_root)
    current = lexical_root
    for part in relative.parts:
        current = current / part
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or _has_reparse_attribute(current):
            raise ValueError("invalid screenshot upload")
    resolved = lexical_candidate.resolve(strict=True)
    if os.path.commonpath((str(root_resolved), str(resolved))) != str(root_resolved):
        raise ValueError("invalid screenshot upload")
    if not resolved.is_file():
        raise ValueError("invalid screenshot upload")
    validate_screenshot(resolved)
    return resolved


def build_app(
    service: ResultApplicationService,
    *,
    content_origin: str = _DEFAULT_CONTENT_ORIGIN,
    preview_store: LocalPreviewStore | None = None,
    approval_key: bytes | None = None,
    preview_builder: Callable[[InputEnvelope], PreviewBundle] | None = None,
    upload_root: Path | None = None,
    redacted_root: Path | None = None,
) -> gr.Blocks:
    """Build the compact workbench with a confined local-upload boundary."""

    with gr.Blocks(
        title="DebugMate 学习诊断助手",
        analytics_enabled=False,
        fill_width=True,
    ) as app:
        callbacks = UiCallbacks(service, content_origin=content_origin)
        current_state = gr.State(_idle_view())
        session_lease = gr.State(value=None)
        preview_token_state = gr.State(value=None)
        local_previews = preview_store or LocalPreviewStore()
        local_approval_key = approval_key or secrets.token_bytes(32)
        local_preview_builder = preview_builder or redact_input
        configured_upload_root = Path(
            upload_root
            or os.environ.get("GRADIO_TEMP_DIR", ".debugmate-runtime/gradio-cache")
        ).absolute()
        configured_redacted_root = (
            None if redacted_root is None else Path(redacted_root).absolute()
        )
        correction_original = gr.State(value=_EMPTY_FIELD_VALUES)
        correction_run = gr.State(value=None)
        correction_draft = gr.State(value=None)
        retry_case = gr.State(value=None)
        retry_result = gr.State(value=None)
        with gr.Group(elem_classes=["status-bar", "command-bar"]):
            gr.Markdown(
                "# DebugMate 学习诊断助手\n\n粘贴报错，先看原因与下一步。",
                elem_classes="product-title",
            )
            status = gr.Markdown(
                "● 等待诊断",
                elem_id="diagnostic-status",
                elem_classes=["status-indicator", "tone-neutral"],
            )
            accessible_status = gr.HTML(
                "状态：等待诊断",
                html_template=(
                    '<p role="status" aria-live="polite" aria-atomic="true">${value}</p>'
                ),
                elem_id="accessible-status",
                container=False,
                padding=False,
            )
        with gr.Group(elem_id="workbench-grid"):
            with gr.Column(elem_classes=["region", "control-rail"]):
                gr.Markdown("## 开始诊断")
                gr.Markdown("粘贴报错，获得原因、步骤与复盘材料。")
                error_input = gr.Textbox(
                    label="报错文本（与截图至少填写一项）",
                    lines=6,
                    elem_id="error-input",
                    placeholder="粘贴终端报错、Traceback 或关键日志。",
                )
                screenshot_input = gr.File(
                    label="报错截图（与文本至少填写一项）",
                    type="filepath",
                    file_count="single",
                    file_types=[".png", ".jpg", ".jpeg"],
                    elem_id="screenshot-input",
                )
                with gr.Accordion("可选：代码与环境", open=False):
                    code_input = gr.Textbox(
                        label="相关代码（可选）",
                        lines=6,
                        elem_id="code-input",
                    )
                    environment_input = gr.Textbox(
                        label="环境信息（可选）",
                        lines=4,
                        elem_id="environment-input",
                        placeholder="例如：Python: 3.13；OS=Windows 11",
                    )
                redacted_input = gr.Textbox(
                    label="脱敏后的输入",
                    interactive=False,
                    lines=5,
                    elem_id="preview-error-text",
                    placeholder="已审批的脱敏输入将在此显示。",
                )
                preview_code = gr.Textbox(
                    label="脱敏后的代码",
                    interactive=False,
                    lines=4,
                    elem_id="preview-code",
                )
                preview_environment = gr.JSON(
                    label="脱敏后的环境信息",
                    value={},
                    elem_id="preview-environment",
                )
                preview_screenshot = gr.Image(
                    label="脱敏后的截图",
                    interactive=False,
                    type="filepath",
                    sources=None,
                    buttons=[],
                    elem_id="preview-screenshot",
                )
                preview_audit = gr.Textbox(
                    elem_id="preview-audit",
                    label="脱敏审计摘要",
                    interactive=False,
                    value="请先生成本地脱敏预览。",
                )
                preview_validity = gr.Markdown(
                    "尚未生成脱敏预览。",
                    elem_id="preview-validity",
                )
                ocr_technical_error = gr.Markdown(
                    "",
                    visible=False,
                    elem_id="ocr-technical-error",
                )
                preview_button = gr.Button(
                    "1. 生成脱敏预览",
                    variant="secondary",
                    elem_id="local-preview",
                )
                start_button = gr.Button(
                    "2. 确认并开始诊断",
                    variant="primary",
                    interactive=False,
                    elem_id="local-approve",
                )
                with gr.Accordion("运行与隐私说明", open=False):
                    gr.Markdown("后端：local-rule-v1（本地规则，无云端调用）")
                with gr.Accordion("查看示例", open=False, elem_classes="example-panel"):
                    replay = gr.Dropdown(
                        choices=[
                            ("ModuleNotFoundError：缺少虚构依赖包", "module-not-found"),
                            ("长报告与长命令：布局韧性", "long-content"),
                        ],
                        label="示例案例",
                        value="module-not-found",
                    )
                    replay_button = gr.Button(
                        "加载回放案例", variant="secondary", elem_id="replay-action"
                    )
                with gr.Accordion(
                    "抽取字段与纠错",
                    open=False,
                    visible=False,
                    elem_classes="correction-panel",
                ) as correction_panel:
                    fields = [
                        gr.Textbox(label=label, interactive=False, value="")
                        for label in _FIELD_LABELS
                    ]
                    pending = gr.Textbox(
                        label="修改草稿",
                        interactive=False,
                        lines=4,
                        value="请先修改至少一个抽取字段。",
                    )
                    correction_button = gr.Button("确认修改并重新诊断", interactive=False)
                    with gr.Accordion("确认创建新运行", open=False) as confirmation_panel:
                        gr.Markdown("确认后将创建新的运行和结果；当前证据与结果不会被覆盖。")
                        confirmation_summary = gr.Textbox(
                            label="待确认修改",
                            interactive=False,
                            lines=5,
                        )
                        create_button = gr.Button(
                            "创建新运行", variant="primary", interactive=False
                        )
                        return_button = gr.Button("返回检查")
                gr.Markdown("页面仅展示已验证的脱敏输入与结果。")

            with gr.Column(elem_classes=["region", "diagnosis-canvas"]):
                gr.Markdown("## 诊断结果")
                category_confidence = gr.Markdown(
                    "### 两步开始诊断\n\n先在左侧生成脱敏预览，再确认并开始诊断。",
                    elem_classes=["diagnosis-summary", "tone-neutral"],
                    elem_id="student-overview",
                )
                next_action = gr.Markdown(
                    "### 现在就做这一步\n\n完成诊断后，这里会显示唯一的建议行动。",
                    elem_classes="next-steps",
                    visible=False,
                )
                with gr.Accordion(
                    "技术详情与恢复信息",
                    open=False,
                    visible=False,
                    elem_id="technical-details",
                ) as technical_details:
                    result_metadata = gr.Markdown(
                        "", elem_id="result-metadata", elem_classes="metadata"
                    )
                    fact_table = gr.Markdown(
                        _markdown_table("事实与证据", _FACT_HEADERS, ()),
                        elem_id="fact-table",
                    )
                    gr.Markdown("诊断中的命令仅供查看，DebugMate 不会自动执行命令或安装软件。")
                    command_table = gr.Markdown(
                        _markdown_table("已验证诊断命令", _COMMAND_HEADERS, ()),
                        elem_id="diagnostic-commands",
                    )
                failure = gr.Markdown("", elem_id="failure-details")
                retry_button = gr.Button(
                    "安全重试",
                    variant="secondary",
                    interactive=False,
                    visible=False,
                    elem_id="partial-retry",
                )

            with gr.Column(
                elem_classes=["region", "results-region", "result-workspace"],
                visible=False,
            ) as result_workspace:
                gr.Markdown("## 多模态与完整报告")
                with gr.Tabs(elem_id="result-tabs", visible=False) as result_tabs:
                    with gr.Tab("文字报告", interactive=False) as report_tab:
                        report_summary = gr.Markdown(
                            "### 结论速览\n\n完成诊断后显示学生可读结论。",
                            elem_classes="report-summary",
                        )
                        report = gr.Markdown(
                            "尚未生成诊断结果",
                            elem_id="diagnostic-report",
                            elem_classes="report-panel",
                        )
                    with gr.Tab("诊断卡", interactive=False) as card_tab:
                        card = gr.Image(
                            label="诊断卡",
                            elem_id="diagnostic-card",
                            type="filepath",
                            interactive=False,
                            visible=False,
                            sources=None,
                            buttons=[],
                        )
                    with gr.Tab("语音复盘", interactive=False) as audio_tab:
                        audio = gr.Audio(
                            label="语音复盘",
                            elem_id="diagnostic-audio",
                            type="filepath",
                            interactive=False,
                            visible=False,
                            sources=None,
                            recording=False,
                            buttons=[],
                        )
                        audio_metadata = gr.Markdown(
                            "", elem_id="audio-metadata", elem_classes="metadata"
                        )
                        recap = gr.Textbox(
                            label="已验证复盘稿",
                            elem_id="recap-text",
                            interactive=False,
                            lines=6,
                            value="复盘稿会与语音一并经过验证后显示。",
                        )
                    with gr.Tab("引用与下载", interactive=False) as download_tab:
                        citation_table = gr.Markdown(
                            _markdown_table("引用", _CITATION_HEADERS, ()),
                            elem_id="citation-table",
                        )
                        gr.File(
                            label="已验证单个产物",
                            elem_id="individual-artifacts",
                            interactive=False,
                            visible=False,
                        )
                        download_metadata = gr.Markdown(
                            "", elem_id="download-metadata", elem_classes="metadata"
                        )
                        download = gr.DownloadButton(
                            "下载结果包",
                            visible=False,
                            interactive=False,
                            elem_id="download-result",
                        )
        gr.Markdown("诊断中的命令仅供查看，DebugMate 不会自动执行命令或安装软件。")

        result_outputs = [
            status,
            result_metadata,
            failure,
            report,
            card,
            audio,
            download,
            correction_button,
            current_state,
            *fields,
            correction_original,
            correction_run,
            correction_draft,
            pending,
            confirmation_summary,
            confirmation_panel,
            create_button,
            replay_button,
            start_button,
            preview_button,
            redacted_input,
            preview_audit,
            category_confidence,
            fact_table,
            citation_table,
            recap,
            retry_button,
            retry_case,
            retry_result,
            download_metadata,
            audio_metadata,
            command_table,
            accessible_status,
            correction_panel,
            technical_details,
            next_action,
            report_summary,
            result_workspace,
            result_tabs,
            report_tab,
            card_tab,
            audio_tab,
            download_tab,
        ]

        def apply_payload(
            payload: CallbackPayload,
            *,
            preserved_correction: tuple[object, CorrectionDraft] | None = None,
        ) -> tuple[object, ...]:
            """Reset local correction controls whenever verified result changes."""

            source_run_id = (
                payload.state.identity.source_run_id
                if payload.state.identity is not None
                and payload.state.status in {ResultStatus.COMPLETED, ResultStatus.PARTIAL}
                else None
            )
            values = payload.field_values if source_run_id is not None else _EMPTY_FIELD_VALUES
            fields_enabled = source_run_id is not None
            retry_update, retry_case_id, retry_result_id = _retry_control_updates(payload)
            correction_source = (
                source_run_id if preserved_correction is None else preserved_correction[0]
            )
            correction_value = None if preserved_correction is None else preserved_correction[1]
            component_updates = list(_component_updates(payload))
            # Main result callbacks are clearers, never publishers, for the
            # native download surfaces.  The zero-input session resync below
            # is the sole path that re-verifies and issues a bundle capability.
            component_updates[6] = gr.update(
                value=None,
                label="下载结果包",
                visible=False,
                interactive=False,
            )
            return (
                *component_updates,
                *(gr.update(value=value, interactive=fields_enabled) for value in values),
                values,
                correction_source,
                correction_value,
                gr.update(value="请先修改至少一个抽取字段。"),
                gr.update(value=""),
                gr.update(open=False),
                gr.update(interactive=False),
                gr.update(interactive=payload.state.status is not ResultStatus.RUNNING),
                gr.update(interactive=False),
                gr.update(interactive=payload.state.status is not ResultStatus.RUNNING),
                gr.update(value=payload.redacted_input),
                gr.update(),
                gr.update(
                    value=_overview_text(payload),
                    elem_classes=["diagnosis-summary", f"tone-{payload.view.state_tone}"],
                ),
                gr.update(value=_markdown_table("事实与证据", _FACT_HEADERS, payload.fact_rows)),
                gr.update(value=_markdown_table("引用", _CITATION_HEADERS, payload.citation_rows)),
                gr.update(value=payload.recap_text),
                retry_update,
                retry_case_id,
                retry_result_id,
                gr.update(value=""),
                gr.update(value=payload.view.audio_metadata or ""),
                gr.update(
                    value=_markdown_table("已验证诊断命令", _COMMAND_HEADERS, payload.command_rows)
                ),
                payload.view.accessible_status,
                gr.update(visible=fields_enabled),
                gr.update(visible=payload.view.secondary_disclosure_visible),
                gr.update(
                    value=_next_action_text(payload),
                    visible=payload.state.status
                    in {ResultStatus.COMPLETED, ResultStatus.PARTIAL},
                ),
                gr.update(value=_report_summary_text(payload)),
                gr.update(
                    visible=payload.state.status
                    in {ResultStatus.COMPLETED, ResultStatus.PARTIAL}
                ),
                gr.update(
                    visible=payload.state.status
                    in {ResultStatus.COMPLETED, ResultStatus.PARTIAL}
                ),
                *(
                    gr.update(interactive=payload.view.tabs_enabled)
                    for _tab in (report_tab, card_tab, audio_tab, download_tab)
                ),
            )

        def load_replay_stream(fixture_id: str | None, request: gr.Request):
            if request is not None:
                local_previews.invalidate_current(_request_session(request))
            lease = callbacks.issue_session_lease(request)
            for payload in callbacks.load_replay_events(fixture_id, request=request):
                callbacks.publish_session_state(request, payload.state)
                yield (*apply_payload(payload), lease)

        def replay_button_enabled(fixture_id: object) -> dict[str, bool]:
            return gr.update(interactive=fixture_id in {"module-not-found", "long-content"})

        def _request_session(request: object) -> str:
            session = getattr(request, "session_hash", None)
            if not isinstance(session, str) or not session:
                raise ResultServiceError("result_bundle_invalid")
            return session

        def redacted_screenshot_capability(preview: PreviewBundle) -> object:
            relative = preview.redacted.redacted_screenshot_path
            expected_sha256 = preview.redacted.redacted_screenshot_sha256
            if relative is None or expected_sha256 is None:
                return None
            if configured_redacted_root is None:
                raise ValueError("redacted preview root is unavailable")
            root = configured_redacted_root.resolve(strict=True)
            candidate = root.joinpath(*relative.split("/"))
            current = root
            for part in Path(relative).parts:
                current = current / part
                info = current.lstat()
                if stat.S_ISLNK(info.st_mode) or _has_reparse_attribute(current):
                    raise ValueError("invalid redacted preview")
            resolved = candidate.resolve(strict=True)
            if os.path.commonpath((str(root), str(resolved))) != str(root):
                raise ValueError("invalid redacted preview")
            payload = resolved.read_bytes()
            if sha256_bytes(payload) != expected_sha256:
                raise ValueError("invalid redacted preview")
            issued = callbacks._content.issue_bytes(
                payload,
                filename="redacted.png",
                mime_type="image/png",
                attachment=False,
            )
            return _capability_file_data(issued)

        def prepare_local_preview(
            error_text: object = None,
            screenshot_path: object = None,
            code: object = None,
            environment_text: object = None,
            request: gr.Request | None = None,
        ) -> tuple[object, ...]:
            """Build and publish only a redacted preview for the captured revision."""

            legacy = request is None and hasattr(error_text, "session_hash")
            if legacy:
                request = error_text  # type: ignore[assignment]
                error_text = "ModuleNotFoundError: No module named 'demo_pkg'"
                screenshot_path = None
                code = None
                environment_text = None
            try:
                session = _request_session(request)
                normalized_error = error_text.strip() if isinstance(error_text, str) else None
                normalized_code = code.strip() if isinstance(code, str) else None
                normalized_screenshot = None
                if screenshot_path is not None:
                    normalized_screenshot = str(
                        _require_cached_upload(screenshot_path, configured_upload_root)
                    )
                envelope = InputEnvelope(
                    case_id=new_case_id(),
                    error_text=normalized_error or None,
                    screenshot_path=normalized_screenshot,
                    code=normalized_code or None,
                    environment=_parse_environment(environment_text),
                )
                revision = local_previews.snapshot_revision(session)
                preview = local_preview_builder(envelope)
                prepared = local_previews.publish_if_current(session, revision, preview)
                if prepared is None:
                    raise ValueError("stale preview")
                screenshot_capability = redacted_screenshot_capability(preview)
            except (OSError, TypeError, ValueError):
                if legacy:
                    return None, gr.update(interactive=False), "", "无法生成脱敏预览。"
                return (
                    None,
                    gr.update(interactive=False),
                    "",
                    "",
                    {},
                    None,
                    "未创建可确认的预览。",
                    "请粘贴报错文本或上传报错截图。",
                    gr.update(value="", visible=False),
                )
            if legacy:
                return (
                    prepared.token,
                    gr.update(interactive=True),
                    prepared.redacted_display,
                    prepared.audit_display,
                )
            return (
                prepared.token,
                gr.update(interactive=True),
                preview.redacted.error_text or "",
                preview.redacted.code or "",
                preview.redacted.environment,
                screenshot_capability,
                prepared.audit_display,
                "脱敏预览已就绪，请确认后开始诊断。",
                gr.update(value="", visible=False),
            )

        def invalidate_live_preview(request: gr.Request) -> tuple[object, ...]:
            local_previews.invalidate_and_increment(_request_session(request))
            return (
                None,
                gr.update(interactive=False),
                "",
                "",
                {},
                None,
                "输入已更改；旧预览已失效。",
                "输入已更改，请重新生成脱敏预览。",
                gr.update(value="", visible=False),
            )

        def approve_and_diagnose_stream(preview_token: str | None, request: gr.Request):
            lease = callbacks.issue_session_lease(request)
            try:
                record = local_previews.consume_current(
                    preview_token, _request_session(request)
                )
                if record is None:
                    raise ResultServiceError("result_bundle_invalid")
                approved = approve_preview(record.preview, local_approval_key)
            except (TypeError, ValueError, ResultServiceError):
                payload = callbacks._render(
                    callbacks._failure(_idle_view(), "result_bundle_invalid")
                )
                callbacks.publish_session_state(request, payload.state)
                yield (*apply_payload(payload), lease)
                return
            for payload in callbacks.diagnose_events(approved, request=request):
                callbacks.publish_session_state(request, payload.state)
                yield (*apply_payload(payload), lease)

        def update_correction_draft(
            original: object, previous_run_id: object, *values: object
        ) -> tuple[object, ...]:
            draft, summary = correction_draft_from_fields(original, values, previous_run_id)
            return (
                draft,
                gr.update(value=summary),
                gr.update(interactive=draft is not None),
                gr.update(open=False),
                gr.update(value=""),
                gr.update(interactive=False),
            )

        def open_correction_confirmation(draft: object, summary: object) -> tuple[object, ...]:
            if not isinstance(draft, CorrectionDraft) or not isinstance(summary, str):
                return (
                    gr.update(open=False),
                    gr.update(value=""),
                    gr.update(interactive=False),
                )
            return (
                gr.update(open=True),
                gr.update(
                    value=(f"{summary}\n\n确认后将创建新的运行和结果；当前证据与结果不会被覆盖。")
                ),
                gr.update(interactive=True),
            )

        def return_to_check() -> tuple[object, ...]:
            return (
                gr.update(open=False),
                gr.update(value=""),
                gr.update(interactive=False),
            )

        def create_new_run_stream(
            previous_run_id: object,
            draft: object,
            lease: object,
            request: gr.Request,
        ):
            """Publish running and terminal states under one top-level session."""

            if not callbacks._strict_id(previous_run_id, _RUN_ID) or not isinstance(
                draft, CorrectionDraft
            ):
                callbacks.clear_session_lease(lease)
                payload = callbacks._render(
                    callbacks._failure(_idle_view(), "result_bundle_invalid")
                )
                callbacks.publish_session_state(request, payload.state)
                yield apply_payload(payload)
                return
            running = callbacks._render(
                ResultViewState(
                    mode=ResultMode.LIVE,
                    status=ResultStatus.RUNNING,
                    availability=ArtifactAvailability(),
                    current_stage="correction",
                )
            )
            if not callbacks.publish_session_state_lease(lease, running.state, previous_run_id):
                callbacks.clear_session_lease(lease)
                payload = callbacks._render(
                    callbacks._failure(_idle_view(), "result_bundle_invalid")
                )
                yield apply_payload(payload)
                return
            yield apply_payload(
                running,
                preserved_correction=(previous_run_id, draft),
            )
            terminal = callbacks.correct(previous_run_id, draft, confirmed=True, request=request)
            if not callbacks.publish_session_state_lease(lease, terminal.state, previous_run_id):
                callbacks.clear_session_lease(lease)
                terminal = callbacks._render(
                    callbacks._failure(_idle_view(), "result_bundle_invalid")
                )
            yield apply_payload(terminal)

        def retry_verified_partial(
            case_id: object, result_id: object, request: gr.Request
        ) -> tuple[object, ...]:
            """Retry the server-verified failed stage without a browser stage/path input."""

            payload = callbacks.retry(case_id, result_id, request=request)
            callbacks.publish_session_state(request, payload.state)
            return apply_payload(payload)

        def sync_download_surfaces(request: gr.Request) -> tuple[object, object]:
            """Refresh bundle UI only from the server-held strict result state."""

            metadata, bundle_url, label = callbacks.download_surface(request=request)
            return (
                gr.update(value=metadata),
                gr.update(
                    value=_capability_file_data(bundle_url),
                    label=label or "下载结果包",
                    visible=bundle_url is not None,
                    interactive=bundle_url is not None,
                ),
            )

        replay_completed = replay_button.click(
            load_replay_stream,
            inputs=[replay],
            outputs=[*result_outputs, session_lease],
            api_name=False,
            queue=True,
            trigger_mode="once",
            concurrency_limit=1,
            concurrency_id="debugmate-case",
            postprocess=False,
        )
        replay_completed.then(
            sync_download_surfaces,
            inputs=None,
            outputs=[download_metadata, download],
            api_name=False,
            queue=True,
            trigger_mode="once",
            concurrency_limit=1,
            concurrency_id="debugmate-case",
            postprocess=False,
        )
        replay.change(
            replay_button_enabled,
            inputs=[replay],
            outputs=[replay_button],
            api_name=False,
            queue=False,
        )
        preview_button.click(
            prepare_local_preview,
            inputs=[error_input, screenshot_input, code_input, environment_input],
            outputs=[
                preview_token_state,
                start_button,
                redacted_input,
                preview_code,
                preview_environment,
                preview_screenshot,
                preview_audit,
                preview_validity,
                ocr_technical_error,
            ],
            api_name=False,
            queue=True,
            trigger_mode="once",
            concurrency_limit=1,
            concurrency_id="debugmate-case",
            postprocess=False,
        )
        for live_input in (
            error_input,
            screenshot_input,
            code_input,
            environment_input,
        ):
            live_input.change(
                invalidate_live_preview,
                inputs=None,
                outputs=[
                    preview_token_state,
                    start_button,
                    redacted_input,
                    preview_code,
                    preview_environment,
                    preview_screenshot,
                    preview_audit,
                    preview_validity,
                    ocr_technical_error,
                ],
                api_name=False,
                queue=True,
                trigger_mode="once",
                concurrency_limit=1,
                concurrency_id="debugmate-case",
                postprocess=False,
            )
        # The only browser-held live authority is a one-time opaque token.
        diagnosis_completed = start_button.click(
            approve_and_diagnose_stream,
            inputs=[preview_token_state],
            outputs=[*result_outputs, session_lease],
            api_name=False,
            queue=True,
            trigger_mode="once",
            concurrency_limit=1,
            concurrency_id="debugmate-case",
            postprocess=False,
        )
        diagnosis_completed.then(
            sync_download_surfaces,
            inputs=None,
            outputs=[download_metadata, download],
            api_name=False,
            queue=True,
            trigger_mode="once",
            concurrency_limit=1,
            concurrency_id="debugmate-case",
            postprocess=False,
        )
        for field in fields:
            field.input(
                update_correction_draft,
                inputs=[correction_original, correction_run, *fields],
                outputs=[
                    correction_draft,
                    pending,
                    correction_button,
                    confirmation_panel,
                    confirmation_summary,
                    create_button,
                ],
                api_name=False,
                queue=False,
            )
        correction_button.click(
            open_correction_confirmation,
            inputs=[correction_draft, pending],
            outputs=[confirmation_panel, confirmation_summary, create_button],
            api_name=False,
            queue=False,
        )
        return_button.click(
            return_to_check,
            outputs=[confirmation_panel, confirmation_summary, create_button],
            api_name=False,
            queue=False,
        )
        correction_completed = create_button.click(
            create_new_run_stream,
            inputs=[correction_run, correction_draft, session_lease],
            outputs=result_outputs,
            api_name=False,
            queue=True,
            trigger_mode="once",
            concurrency_limit=1,
            concurrency_id="debugmate-case",
            postprocess=False,
        )
        correction_completed.then(
            sync_download_surfaces,
            inputs=None,
            outputs=[download_metadata, download],
            api_name=False,
            queue=True,
            trigger_mode="once",
            concurrency_limit=1,
            concurrency_id="debugmate-case",
            postprocess=False,
        )
        retry_completed = retry_button.click(
            retry_verified_partial,
            inputs=[retry_case, retry_result],
            outputs=result_outputs,
            api_name=False,
            queue=True,
            trigger_mode="once",
            concurrency_limit=1,
            concurrency_id="debugmate-case",
            postprocess=False,
        )
        retry_completed.then(
            sync_download_surfaces,
            inputs=None,
            outputs=[download_metadata, download],
            api_name=False,
            queue=True,
            trigger_mode="once",
            concurrency_limit=1,
            concurrency_id="debugmate-case",
            postprocess=False,
        )
    # Gradio 6 moved CSS from the constructor to ``launch``.  Retain it on
    # the app for structural inspection; ``serve`` supplies the same string
    # to launch without adding external assets or JavaScript.
    app.css = WORKBENCH_CSS
    # ``Blocks.queue()`` rebuilds ``app.app`` in Gradio 6.  Registering this
    # route before queueing would silently attach it to the discarded ASGI app
    # and leave every otherwise-valid capability URL at 404.
    queued_app = app.queue(default_concurrency_limit=1)
    setattr(queued_app, _CONTENT_CALLBACKS_ATTR, callbacks)
    ensure_content_endpoint(queued_app)
    return queued_app
