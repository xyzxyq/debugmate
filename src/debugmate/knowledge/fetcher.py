"""Allowlisted HTTP fetching for curated official documentation."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit

import httpx
from pydantic import Field

from debugmate.knowledge.models import KnowledgeSource, StrictKnowledgeModel

FETCH_TIMEOUT_SECONDS = 20.0
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class SourceFetchError(RuntimeError):
    """Base class for rejected or failed official-source responses."""


class SourceDomainViolation(SourceFetchError):
    """A response or redirect attempted to leave the allowlisted domain."""


class SourceRedirectRejected(SourceFetchError):
    """A redirect attempted to fetch a URL absent from the strict registry."""


class SourceStatusError(SourceFetchError):
    """The official source returned a status other than 200."""


class SourceContentTypeRejected(SourceFetchError):
    """The official source did not return HTML."""


class SourceResponseTooLarge(SourceFetchError):
    """The official source exceeded the bounded response size."""


class FetchedSource(StrictKnowledgeModel):
    """In-memory HTML plus the audit metadata needed by later build stages."""

    source_id: str
    final_url: str
    status_code: int
    etag: str | None
    last_modified: str | None
    retrieved_at: datetime
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    html: str


def _hostname(url: str) -> str | None:
    return urlsplit(url).hostname


def _validate_exact_response_url(source: KnowledgeSource, final_url: str) -> None:
    parsed = urlsplit(final_url)
    if parsed.scheme != "https" or parsed.hostname != source.allowed_domain:
        raise SourceDomainViolation(
            f"source {source.source_id!r} left allowlisted domain: {final_url}"
        )
    if final_url != source.url:
        raise SourceRedirectRejected(
            f"source {source.source_id!r} resolved to an unregistered URL: {final_url}"
        )


def _reject_redirect(source: KnowledgeSource, response: httpx.Response) -> None:
    location = response.headers.get("location")
    if not location:
        raise SourceStatusError(
            f"source {source.source_id!r} returned redirect without Location"
        )
    redirect_url = urljoin(source.url, location)
    if _hostname(redirect_url) != source.allowed_domain or urlsplit(redirect_url).scheme != "https":
        raise SourceDomainViolation(
            f"source {source.source_id!r} redirected outside allowlist: {redirect_url}"
        )
    raise SourceRedirectRejected(
        f"source {source.source_id!r} redirected to unregistered URL: {redirect_url}"
    )


def _read_bounded_html(source: KnowledgeSource, response: httpx.Response) -> bytes:
    content_type = response.headers.get("content-type", "")
    if content_type.split(";", 1)[0].strip().lower() != "text/html":
        raise SourceContentTypeRejected(
            f"source {source.source_id!r} returned unsupported Content-Type: {content_type!r}"
        )

    content_length = response.headers.get("content-length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError as exc:
            raise SourceFetchError("invalid Content-Length response header") from exc
        if declared_size > MAX_RESPONSE_BYTES:
            raise SourceResponseTooLarge(
                f"source {source.source_id!r} exceeds {MAX_RESPONSE_BYTES} bytes"
            )

    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            raise SourceResponseTooLarge(
                f"source {source.source_id!r} exceeds {MAX_RESPONSE_BYTES} bytes"
            )
        chunks.append(chunk)
    return b"".join(chunks)


def fetch_source(source: KnowledgeSource, client: httpx.Client) -> FetchedSource:
    """Fetch one exact allowlisted URL with bounded, auditable behavior.

    The supplied client makes transport behavior testable. Redirect behavior and
    timeout are nevertheless overridden per request so a permissive caller cannot
    weaken the registry boundary.
    """

    _validate_exact_response_url(source, source.url)
    for attempt in range(2):
        try:
            with client.stream(
                "GET",
                source.url,
                follow_redirects=False,
                timeout=FETCH_TIMEOUT_SECONDS,
            ) as response:
                final_url = str(response.url)
                _validate_exact_response_url(source, final_url)
                if response.status_code in _REDIRECT_STATUSES:
                    _reject_redirect(source, response)
                if response.status_code != 200:
                    raise SourceStatusError(
                        f"source {source.source_id!r} returned HTTP {response.status_code}"
                    )
                raw = _read_bounded_html(source, response)
                encoding = response.encoding or "utf-8"
                return FetchedSource(
                    source_id=source.source_id,
                    final_url=final_url,
                    status_code=response.status_code,
                    etag=response.headers.get("etag"),
                    last_modified=response.headers.get("last-modified"),
                    retrieved_at=datetime.now(UTC),
                    sha256=hashlib.sha256(raw).hexdigest(),
                    html=raw.decode(encoding),
                )
        except (httpx.ConnectError, httpx.TimeoutException):
            if attempt == 1:
                raise

    raise AssertionError("two-attempt fetch loop terminated unexpectedly")


__all__ = [
    "FetchedSource",
    "SourceContentTypeRejected",
    "SourceDomainViolation",
    "SourceFetchError",
    "SourceRedirectRejected",
    "SourceResponseTooLarge",
    "SourceStatusError",
    "fetch_source",
]
