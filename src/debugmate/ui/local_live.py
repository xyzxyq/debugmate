"""Server-owned local preview records for the deliberate live approval path."""

from __future__ import annotations

import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from debugmate.contracts import new_case_id
from debugmate.privacy.approval import APPROVAL_TTL
from debugmate.privacy.models import InputEnvelope, PreviewBundle
from debugmate.privacy.text_redactor import redact_input

LOCAL_RULE_DEMO_ERROR = (
    "Traceback (most recent call last):\n"
    '  File "C:\\Users\\demo-user\\DebugMate\\main.py", line 1, in <module>\n'
    "ModuleNotFoundError: No module named 'fictional_pkg'"
)
LOCAL_RULE_DEMO_CODE = "import fictional_pkg"
LOCAL_RULE_DEMO_ENVIRONMENT = {
    "python": "3.13.5",
    "workspace": r"C:\Users\demo-user\DebugMate",
}


@dataclass(frozen=True, slots=True)
class LocalPreviewRecord:
    preview: PreviewBundle = field(repr=False)
    request_session: str
    expires_at_utc: datetime


@dataclass(frozen=True, slots=True)
class LocalPreviewPresentation:
    token: str = field(repr=False)
    redacted_display: str
    audit_display: str


class LocalPreviewStore:
    """Bounded, session-bound, one-time registry of local redaction previews."""

    def __init__(
        self,
        *,
        ttl: timedelta = APPROVAL_TTL,
        max_entries: int = 64,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if ttl <= timedelta(0) or ttl > APPROVAL_TTL:
            raise ValueError("preview TTL must be positive and within approval TTL")
        if not isinstance(max_entries, int) or isinstance(max_entries, bool) or max_entries < 1:
            raise ValueError("preview store max_entries must be positive")
        self._ttl = ttl
        self._max_entries = max_entries
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = threading.RLock()
        self._records: dict[str, LocalPreviewRecord] = {}

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("preview clock must return a UTC-aware datetime")
        return value

    def _purge_expired(self, now: datetime) -> None:
        for token in tuple(self._records):
            if self._records[token].expires_at_utc <= now:
                self._records.pop(token, None)

    @staticmethod
    def _display(preview: PreviewBundle) -> tuple[str, str]:
        redacted = preview.redacted
        sections = []
        if redacted.error_text:
            sections.append(redacted.error_text)
        if redacted.code:
            sections.append(f"代码：\n{redacted.code}")
        if redacted.environment:
            environment = "\n".join(
                f"{key}={value}" for key, value in sorted(redacted.environment.items())
            )
            sections.append(f"环境：\n{environment}")
        counts = "、".join(
            f"{kind.value}={count}"
            for kind, count in sorted(
                preview.audit.counts_by_kind.items(), key=lambda item: str(item[0])
            )
        )
        audit = f"候选敏感项：{preview.audit.candidate_count}"
        if counts:
            audit = f"{audit}（{counts}）"
        return "\n\n".join(sections), audit

    def create(self, request_session: str) -> LocalPreviewPresentation:
        if not isinstance(request_session, str) or not request_session:
            raise ValueError("request session is required")
        preview = redact_input(
            InputEnvelope(
                case_id=new_case_id(),
                error_text=LOCAL_RULE_DEMO_ERROR,
                code=LOCAL_RULE_DEMO_CODE,
                environment=LOCAL_RULE_DEMO_ENVIRONMENT,
            )
        )
        now = self._now()
        token = secrets.token_urlsafe(32)
        record = LocalPreviewRecord(
            preview=preview,
            request_session=request_session,
            expires_at_utc=now + self._ttl,
        )
        with self._lock:
            self._purge_expired(now)
            self._records[token] = record
            while len(self._records) > self._max_entries:
                self._records.pop(next(iter(self._records)))
        redacted_display, audit_display = self._display(preview)
        return LocalPreviewPresentation(
            token=token,
            redacted_display=redacted_display,
            audit_display=audit_display,
        )

    def consume(
        self, token: str | None, request_session: str
    ) -> LocalPreviewRecord | None:
        if not isinstance(token, str) or not token:
            return None
        if not isinstance(request_session, str) or not request_session:
            return None
        now = self._now()
        with self._lock:
            self._purge_expired(now)
            record = self._records.get(token)
            if record is None or record.request_session != request_session:
                return None
            return self._records.pop(token)
