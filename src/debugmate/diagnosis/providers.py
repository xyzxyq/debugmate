"""Approved-input-only production extraction providers."""

from __future__ import annotations

import base64
import hmac
import re
from pathlib import Path
from typing import Protocol, runtime_checkable

import httpx

from debugmate.diagnosis.extraction import (
    ExtractionRecord,
    FactCandidate,
    FieldId,
    OcrLocator,
    SourceKind,
    TextLocator,
    extraction_id_for,
    make_candidate,
)
from debugmate.hashing import (
    UnsafeArtifactPath,
    canonical_json_bytes,
    resolve_artifact_path,
    sha256_bytes,
    sha256_file,
)
from debugmate.privacy.image_models import InvalidScreenshot, validate_screenshot
from debugmate.privacy.models import ApprovedRedactedInput
from debugmate.privacy.ocr import OcrBackend, OcrToken


class ExtractionRejected(ValueError):
    """Safe, value-free failure at an extraction trust boundary."""


@runtime_checkable
class ExtractionProvider(Protocol):
    def extract(self, approved: ApprovedRedactedInput) -> ExtractionRecord: ...


@runtime_checkable
class VlmCandidateProvider(Protocol):
    def extract_candidates(
        self,
        approved: ApprovedRedactedInput,
        *,
        image_path: Path,
        width: int,
        height: int,
    ) -> list[FactCandidate]: ...


_EXCEPTION = re.compile(r"\b([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception))\b")
_PACKAGE = re.compile(
    r"(?:No module named\s+['\"]?([A-Za-z0-9_.-]+)|\bPackage\s*:\s*([A-Za-z0-9_.-]+))",
    re.IGNORECASE,
)
_VERSION = re.compile(r"\bVersion\s*:\s*([^\s,;]+)", re.IGNORECASE)
_DEVICE = re.compile(r"\bDevice\s*:\s*([^\s,;]+)", re.IGNORECASE)
_PATH = re.compile(r"\bPath\s*:\s*(\S+)", re.IGNORECASE)


def _mapped_values(text: str) -> list[tuple[FieldId, str, int, int]]:
    values: list[tuple[FieldId, str, int, int]] = []
    exception = _EXCEPTION.search(text)
    if exception:
        values.append(
            (FieldId.EXCEPTION_TYPE, exception.group(1), exception.start(1), exception.end(1))
        )
        values.append((FieldId.TRACEBACK_KEY_LINE, text, 0, len(text)))
    for field_id, pattern in (
        (FieldId.PACKAGE, _PACKAGE),
        (FieldId.VERSION, _VERSION),
        (FieldId.DEVICE, _DEVICE),
        (FieldId.PATH, _PATH),
    ):
        match = pattern.search(text)
        if match:
            group = next(index for index, value in enumerate(match.groups(), 1) if value)
            values.append((field_id, match.group(group), match.start(group), match.end(group)))
    return values


class ProductionExtractionProvider:
    """Resolve approved artifacts, invoke injected engines, and return candidates only."""

    def __init__(
        self,
        *,
        redacted_root: Path,
        ocr_backend: OcrBackend,
        vlm_candidate_provider: VlmCandidateProvider | None = None,
    ) -> None:
        self._redacted_root = Path(redacted_root)
        self._ocr_backend = ocr_backend
        self._vlm_candidate_provider = vlm_candidate_provider

    def extract(self, approved: ApprovedRedactedInput) -> ExtractionRecord:
        if not isinstance(approved, ApprovedRedactedInput):
            raise TypeError("ProductionExtractionProvider accepts only ApprovedRedactedInput")
        candidates = self._text_candidates(approved)
        source_hashes: dict[str, str] = {}
        redacted = approved.redacted
        if redacted.error_text is not None:
            source_hashes["error_text"] = sha256_bytes(redacted.error_text.encode("utf-8"))
        if redacted.code is not None:
            source_hashes["code"] = sha256_bytes(redacted.code.encode("utf-8"))
        if redacted.environment:
            source_hashes["environment"] = sha256_bytes(
                canonical_json_bytes(dict(sorted(redacted.environment.items())))
            )

        screenshot = self._verified_screenshot(approved)
        if screenshot is not None:
            path, width, height, image_hash = screenshot
            source_hashes["screenshot"] = image_hash
            try:
                tokens = self._ocr_backend.recognize(path)
            except Exception:
                raise ExtractionRejected("OCR unavailable") from None
            candidates.extend(self._ocr_candidates(tokens, image_hash, width, height))
            if self._vlm_candidate_provider is not None:
                try:
                    vlm_candidates = self._vlm_candidate_provider.extract_candidates(
                        approved, image_path=path, width=width, height=height
                    )
                except Exception:
                    raise ExtractionRejected("VLM unavailable") from None
                candidates.extend(
                    self._validated_vlm_candidates(
                        vlm_candidates, image_hash=image_hash, width=width, height=height
                    )
                )

        candidates = sorted(
            {item.candidate_id: item for item in candidates}.values(),
            key=lambda item: item.candidate_id,
        )
        source_hashes = dict(sorted(source_hashes.items()))
        extraction_id = extraction_id_for(approved.case_id, source_hashes, candidates)
        return ExtractionRecord(
            case_id=approved.case_id,
            extraction_id=extraction_id,
            source_hashes=source_hashes,
            candidates=candidates,
        )

    def _verified_screenshot(
        self, approved: ApprovedRedactedInput
    ) -> tuple[Path, int, int, str] | None:
        redacted = approved.redacted
        if redacted.redacted_screenshot_path is None:
            return None
        expected_hash = redacted.redacted_screenshot_sha256
        if expected_hash is None:
            raise ExtractionRejected("approved screenshot hash is missing")
        try:
            path = resolve_artifact_path(
                self._redacted_root, Path(redacted.redacted_screenshot_path)
            )
        except UnsafeArtifactPath:
            raise ExtractionRejected("approved screenshot path is unsafe") from None
        if not path.is_file():
            raise ExtractionRejected("approved screenshot is unavailable")
        actual_hash = sha256_file(path)
        if not hmac.compare_digest(actual_hash, expected_hash):
            raise ExtractionRejected("approved screenshot hash mismatch")
        try:
            image = validate_screenshot(path)
        except InvalidScreenshot:
            raise ExtractionRejected("approved screenshot is invalid") from None
        return path, image.width, image.height, actual_hash

    @staticmethod
    def _text_candidates(approved: ApprovedRedactedInput) -> list[FactCandidate]:
        candidates: list[FactCandidate] = []
        fields = (
            ("error_text", approved.redacted.error_text),
            ("code", approved.redacted.code),
            (
                "environment",
                "\n".join(
                    value for _, value in sorted(approved.redacted.environment.items())
                )
                or None,
            ),
        )
        for input_field, content in fields:
            if content is None:
                continue
            for match in re.finditer(r"[^\r\n]+", content):
                line = match.group(0)
                for field_id, value, start, end in _mapped_values(line):
                    candidates.append(
                        make_candidate(
                            field_id=field_id,
                            value=value,
                            source_kind=SourceKind.TEXT,
                            confidence=1.0,
                            locator=TextLocator(
                                input_field=input_field,
                                start=match.start() + start,
                                end=match.start() + end,
                            ),
                        )
                    )
        return candidates

    @staticmethod
    def _ocr_candidates(
        tokens: list[OcrToken], image_hash: str, width: int, height: int
    ) -> list[FactCandidate]:
        candidates: list[FactCandidate] = []
        for token in tokens:
            try:
                locator = OcrLocator(
                    image_sha256=image_hash,
                    box=token.box,
                    image_width=width,
                    image_height=height,
                )
                for field_id, value, _, _ in _mapped_values(token.text):
                    candidates.append(
                        make_candidate(
                            field_id=field_id,
                            value=value,
                            source_kind=SourceKind.OCR,
                            confidence=token.score,
                            locator=locator,
                        )
                    )
            except (TypeError, ValueError):
                raise ExtractionRejected("OCR candidate locator is invalid") from None
        return candidates

    @staticmethod
    def _validated_vlm_candidates(
        values: list[FactCandidate], *, image_hash: str, width: int, height: int
    ) -> list[FactCandidate]:
        validated: list[FactCandidate] = []
        for value in values:
            try:
                candidate = FactCandidate.model_validate(value.model_dump(), strict=True)
            except Exception:
                raise ExtractionRejected("VLM candidate contract is invalid") from None
            locator = candidate.locator
            if (
                candidate.source_kind is not SourceKind.VLM
                or locator.kind != "vlm"
                or locator.image_sha256 != image_hash
                or locator.image_width != width
                or locator.image_height != height
            ):
                raise ExtractionRejected("VLM candidate locator is invalid")
            validated.append(candidate)
        return validated


class DifyVlmCandidateProvider:
    """Narrow live VLM port for an explicitly configured Dify-compatible endpoint."""

    backend_name = "dify-vlm"

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._timeout = timeout
        self._transport = transport

    def extract_candidates(
        self,
        approved: ApprovedRedactedInput,
        *,
        image_path: Path,
        width: int,
        height: int,
    ) -> list[FactCandidate]:
        if not isinstance(approved, ApprovedRedactedInput):
            raise TypeError("Dify VLM accepts only ApprovedRedactedInput")
        payload = {
            "case_id": approved.case_id,
            "error_text": approved.redacted.error_text,
            "code": approved.redacted.code,
            "environment": approved.redacted.environment,
            "image_base64": base64.b64encode(image_path.read_bytes()).decode("ascii"),
            "image_sha256": approved.redacted.redacted_screenshot_sha256,
            "image_width": width,
            "image_height": height,
            "allowed_fields": [field.value for field in FieldId],
        }
        try:
            with httpx.Client(transport=self._transport, timeout=self._timeout) as client:
                response = client.post(
                    self._endpoint,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            raw_candidates = data["candidates"]
            if not isinstance(raw_candidates, list):
                raise TypeError
            return [FactCandidate.model_validate(item, strict=True) for item in raw_candidates]
        except Exception:
            raise ExtractionRejected("live VLM candidate request failed") from None
