"""Revision-aware server authority for deliberate local preview approval."""

from __future__ import annotations

import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from debugmate.privacy.approval import APPROVAL_TTL
from debugmate.privacy.models import PreviewBundle


@dataclass(frozen=True, slots=True)
class LocalPreviewRecord:
    """Server-only preview authority bound to one session revision and TTL."""

    preview: PreviewBundle = field(repr=False)
    request_session: str
    revision: int
    expires_at_utc: datetime


@dataclass(frozen=True, slots=True)
class LocalPreviewPresentation:
    """Redacted browser presentation plus an opaque one-time authority token."""

    token: str = field(repr=False)
    revision: int
    redacted_display: str
    audit_display: str
    screenshot_provided: bool


class LocalPreviewStore:
    """Bounded session/revision/TTL registry with atomic compare-and-consume."""

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
        self._revisions: dict[str, int] = {}
        self._records: dict[str, LocalPreviewRecord] = {}

    @staticmethod
    def _require_session(request_session: str) -> str:
        if not isinstance(request_session, str) or not request_session:
            raise ValueError("request session is required")
        return request_session

    @staticmethod
    def _require_revision(revision: int) -> int:
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
            raise ValueError("preview revision must be a non-negative integer")
        return revision

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("preview clock must return a UTC-aware datetime")
        return value

    def _purge_expired(self, now: datetime) -> None:
        for token in tuple(self._records):
            if self._records[token].expires_at_utc <= now:
                self._records.pop(token, None)

    def _remove_session_tokens(self, request_session: str) -> None:
        for token, record in tuple(self._records.items()):
            if record.request_session == request_session:
                self._records.pop(token, None)

    def _ensure_session(self, request_session: str) -> int:
        revision = self._revisions.get(request_session)
        if revision is not None:
            return revision
        while len(self._revisions) >= self._max_entries:
            evicted_session = next(iter(self._revisions))
            self._revisions.pop(evicted_session)
            self._remove_session_tokens(evicted_session)
        self._revisions[request_session] = 0
        return 0

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
        text_counts = "、".join(
            f"{kind.value}={count}"
            for kind, count in sorted(
                preview.audit.counts_by_kind.items(), key=lambda item: item[0].value
            )
        )
        audit = f"候选敏感项：{preview.audit.candidate_count}"
        if text_counts:
            audit = f"{audit}（{text_counts}）"
        screenshot = preview.screenshot_audit
        audit = (
            f"{audit}；截图：{screenshot.ocr_status.value}，"
            f"遮挡项={screenshot.finding_count}"
        )
        return "\n\n".join(sections), audit

    def current_revision(self, request_session: str) -> int:
        """Return the current server-owned revision, creating the session at zero."""

        session = self._require_session(request_session)
        with self._lock:
            self._purge_expired(self._now())
            return self._ensure_session(session)

    def snapshot_revision(self, request_session: str) -> int:
        """Capture the revision before performing expensive preview work."""

        return self.current_revision(request_session)

    def invalidate_and_increment(self, request_session: str) -> int:
        """Invalidate every authority for the session and monotonically advance it."""

        session = self._require_session(request_session)
        with self._lock:
            self._purge_expired(self._now())
            revision = self._ensure_session(session) + 1
            self._revisions[session] = revision
            self._remove_session_tokens(session)
            return revision

    def publish_if_current(
        self,
        request_session: str,
        revision: int,
        preview: PreviewBundle,
    ) -> LocalPreviewPresentation | None:
        """Publish a completed preview only if its captured revision is still current."""

        session = self._require_session(request_session)
        captured_revision = self._require_revision(revision)
        if not isinstance(preview, PreviewBundle):
            raise TypeError("preview must be PreviewBundle")
        strict_preview = PreviewBundle.model_validate(preview.model_dump())
        redacted_display, audit_display = self._display(strict_preview)
        with self._lock:
            now = self._now()
            self._purge_expired(now)
            if self._ensure_session(session) != captured_revision:
                return None
            self._remove_session_tokens(session)
            token = secrets.token_urlsafe(32)
            self._records[token] = LocalPreviewRecord(
                preview=strict_preview,
                request_session=session,
                revision=captured_revision,
                expires_at_utc=now + self._ttl,
            )
            while len(self._records) > self._max_entries:
                self._records.pop(next(iter(self._records)))
        return LocalPreviewPresentation(
            token=token,
            revision=captured_revision,
            redacted_display=redacted_display,
            audit_display=audit_display,
            screenshot_provided=strict_preview.screenshot_audit.provided,
        )

    def consume_current(
        self, token: str | None, request_session: str
    ) -> LocalPreviewRecord | None:
        """Atomically compare session/revision/TTL and pop one current authority."""

        if not isinstance(token, str) or not token:
            return None
        if not isinstance(request_session, str) or not request_session:
            return None
        with self._lock:
            now = self._now()
            self._purge_expired(now)
            record = self._records.get(token)
            if record is None or record.request_session != request_session:
                return None
            current = self._revisions.get(request_session)
            if current is None or record.revision != current:
                self._records.pop(token, None)
                return None
            return self._records.pop(token)

    def invalidate_current(self, request_session: str) -> None:
        """Remove outstanding live authority before switching to replay mode."""

        session = self._require_session(request_session)
        with self._lock:
            self._purge_expired(self._now())
            self._ensure_session(session)
            self._remove_session_tokens(session)
