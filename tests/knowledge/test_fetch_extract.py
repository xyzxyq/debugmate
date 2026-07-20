from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from debugmate.contracts import ErrorCategory
from debugmate.knowledge.extractor import SourceStructureChanged, extract_sections
from debugmate.knowledge.fetcher import (
    SourceContentTypeRejected,
    SourceDomainViolation,
    SourceResponseTooLarge,
    SourceStatusError,
    fetch_source,
)
from debugmate.knowledge.models import KnowledgeSource

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "knowledge" / "python-errors.html"


@pytest.fixture
def source() -> KnowledgeSource:
    return KnowledgeSource(
        source_id="python-errors",
        title="Python Errors and Exceptions",
        url="https://docs.python.org/3/tutorial/errors.html",
        product="python",
        version_scope="Python 3",
        platform="cross-platform",
        allowed_domain="docs.python.org",
        heading_patterns=[r"^Exceptions$", r"^Handling Exceptions$"],
        error_categories=[ErrorCategory.PYTHON_RUNTIME],
        license_or_terms_note="Python documentation license applies.",
        selection_reason="Canonical Python runtime error reference.",
    )


@pytest.fixture
def fixture_html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


def test_fetch_records_auditable_response_metadata(source: KnowledgeSource) -> None:
    raw = b"<html><body><h2>Exceptions</h2></body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == source.url
        return httpx.Response(
            200,
            headers={
                "Content-Type": "text/html; charset=utf-8",
                "ETag": '"python-errors-v1"',
                "Last-Modified": "Fri, 10 Jul 2026 08:00:00 GMT",
            },
            content=raw,
        )

    with _client(handler) as client:
        fetched = fetch_source(source, client)

    assert fetched.source_id == source.source_id
    assert fetched.final_url == source.url
    assert fetched.status_code == 200
    assert fetched.etag == '"python-errors-v1"'
    assert fetched.last_modified == "Fri, 10 Jul 2026 08:00:00 GMT"
    assert fetched.retrieved_at.utcoffset() is not None
    assert fetched.sha256 == hashlib.sha256(raw).hexdigest()
    assert fetched.html == raw.decode()


def test_fetch_disables_client_redirect_following_and_rejects_cross_domain_redirect(
    source: KnowledgeSource,
) -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(302, headers={"Location": "https://example.com/copied"})

    with _client(handler) as client, pytest.raises(SourceDomainViolation):
        fetch_source(source, client)

    assert requests == [source.url]


@pytest.mark.parametrize("failure_type", [httpx.ConnectTimeout, httpx.ReadTimeout])
def test_fetch_retries_connect_and_timeout_failures_once(
    source: KnowledgeSource,
    failure_type: type[httpx.TimeoutException],
) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise failure_type("temporary failure", request=request)
        return httpx.Response(200, headers={"Content-Type": "text/html"}, text="<html />")

    with _client(handler) as client:
        fetch_source(source, client)

    assert attempts == 2


def test_fetch_does_not_retry_http_status_failures(source: KnowledgeSource) -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, headers={"Content-Type": "text/html"})

    with _client(handler) as client, pytest.raises(SourceStatusError):
        fetch_source(source, client)

    assert attempts == 1


def test_fetch_rejects_non_html_response(source: KnowledgeSource) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "application/pdf"}, content=b"PDF")

    with _client(handler) as client, pytest.raises(SourceContentTypeRejected):
        fetch_source(source, client)


def test_fetch_rejects_response_larger_than_two_mibibytes(source: KnowledgeSource) -> None:
    oversized = b"x" * ((2 * 1024 * 1024) + 1)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html"},
            content=oversized,
        )

    with _client(handler) as client, pytest.raises(SourceResponseTooLarge):
        fetch_source(source, client)


def test_selected_headings_and_code_are_normalized(
    fixture_html: str, source: KnowledgeSource
) -> None:
    sections = extract_sections(source, fixture_html)

    assert [section.heading for section in sections] == ["Exceptions", "Handling Exceptions"]
    assert sections[0].source_locator == "#exceptions"
    assert "```\nTraceback (most recent call last):" in sections[0].text
    assert sections[0].text.endswith("The final line identifies the exception type and message.")
    assert "Raising Exceptions" not in sections[1].text
    assert "Copy" not in sections[0].text
    assert "Sidebar" not in sections[0].text


def test_extraction_deduplicates_canonical_text(source: KnowledgeSource) -> None:
    html = """
    <h2 id="one">Exceptions</h2><p>Same   diagnostic fact.</p>
    <h2 id="two">Handling Exceptions</h2><p>Same diagnostic fact.</p>
    """

    sections = extract_sections(source, html)

    assert len(sections) == 1
    assert sections[0].text == "Same diagnostic fact."
    assert sections[0].text_sha256 == hashlib.sha256(b"Same diagnostic fact.").hexdigest()


def test_extraction_stops_at_same_level_heading_nested_in_wrapper(
    source: KnowledgeSource,
) -> None:
    nested_boundary_html = """
    <h2 id="exceptions">Exceptions</h2>
    <div class="content-wrapper">
      <p>Included diagnostic fact.</p>
      <section>
        <h2 id="handling-exceptions">Handling Exceptions</h2>
        <p>Must not leak into the Exceptions section.</p>
      </section>
    </div>
    """

    sections = extract_sections(source, nested_boundary_html)

    assert sections[0].heading == "Exceptions"
    assert sections[0].text == "Included diagnostic fact."
    assert sections[1].heading == "Handling Exceptions"
    assert sections[1].text == "Must not leak into the Exceptions section."


def test_extraction_caps_each_section_at_8000_characters(source: KnowledgeSource) -> None:
    html = f'<h2 id="exceptions">Exceptions</h2><p>{"x" * 9000}</p>'

    [section] = extract_sections(source, html)

    assert len(section.text) <= 8_000


def test_extraction_raises_when_configured_structure_disappears(
    source: KnowledgeSource,
) -> None:
    with pytest.raises(SourceStructureChanged):
        extract_sections(
            source,
            "<html><main><h2>Unrelated</h2><p>Nothing useful.</p></main></html>",
        )
