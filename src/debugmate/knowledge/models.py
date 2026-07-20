"""Strict contracts for the curated official-source registry."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from debugmate.contracts import ErrorCategory

RegistryVersion = Literal["1.0.0"]
ProductFamily = Literal[
    "python",
    "pip",
    "pytorch",
    "cuda",
    "huggingface",
    "ultralytics",
    "windows",
]
NonEmptyText = Annotated[str, Field(min_length=1)]


class StrictKnowledgeModel(BaseModel):
    """Reject undeclared fields and implicit conversion at knowledge boundaries."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class KnowledgeSource(StrictKnowledgeModel):
    """One explicitly approved official documentation source."""

    source_id: Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
    title: NonEmptyText
    url: NonEmptyText
    product: ProductFamily
    version_scope: NonEmptyText
    platform: NonEmptyText
    allowed_domain: Annotated[
        str,
        Field(pattern=r"^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$"),
    ]
    heading_patterns: Annotated[list[NonEmptyText], Field(min_length=1)]
    error_categories: Annotated[list[ErrorCategory], Field(min_length=1)]
    license_or_terms_note: NonEmptyText
    selection_reason: NonEmptyText

    @field_validator(
        "title",
        "version_scope",
        "platform",
        "license_or_terms_note",
        "selection_reason",
    )
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must contain non-whitespace text")
        return value

    @field_validator("heading_patterns")
    @classmethod
    def require_unique_non_blank_patterns(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("heading patterns must contain non-whitespace text")
        if len(values) != len(set(values)):
            raise ValueError("heading patterns must be unique")
        return values

    @field_validator("error_categories")
    @classmethod
    def require_unique_categories(
        cls, values: list[ErrorCategory]
    ) -> list[ErrorCategory]:
        if len(values) != len(set(values)):
            raise ValueError("error categories must be unique")
        return values

    @model_validator(mode="after")
    def require_exact_https_domain(self) -> Self:
        parsed = urlsplit(self.url)
        try:
            port = parsed.port
        except ValueError as exc:
            raise ValueError("source URL has an invalid port") from exc
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or port not in (None, 443)
        ):
            raise ValueError("source URL must be a fragment-free HTTPS URL")
        if self.allowed_domain != parsed.hostname:
            raise ValueError("allowed_domain must equal the source URL host")
        return self


class SourceRegistry(StrictKnowledgeModel):
    """Versioned collection of allowlisted official documentation sources."""

    registry_version: RegistryVersion
    sources: Annotated[list[KnowledgeSource], Field(min_length=1)]

    @model_validator(mode="after")
    def reject_duplicate_sources(self) -> Self:
        source_ids = [source.source_id for source in self.sources]
        urls = [source.url for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source_id values must be unique")
        if len(urls) != len(set(urls)):
            raise ValueError("source URLs must be unique")
        return self


def load_registry(path: Path) -> SourceRegistry:
    """Load and strictly validate a UTF-8 JSON source registry."""

    return SourceRegistry.model_validate_json(path.read_text(encoding="utf-8"), strict=True)
