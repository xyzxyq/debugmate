"""Deterministic, privacy-scanned transcript for every TTS backend."""

from __future__ import annotations

import re
from typing import ClassVar

from pydantic import ConfigDict, Field, model_validator

from debugmate.hashing import sha256_bytes
from debugmate.privacy.output_scan import assert_export_safe
from debugmate.results.contracts import ArtifactIdentity, StrictFrozenModel
from debugmate.results.presentation import PresentationModel, _validated_presentation


class RecapComposeError(ValueError):
    """Value-free failure at the recap privacy and provenance boundary."""

    def __init__(self) -> None:
        super().__init__("recap_unsafe")


class SafeRecapText(StrictFrozenModel):
    """Identity-bound text that is safe to hand to a speech adapter."""

    model_config = ConfigDict(**StrictFrozenModel.model_config, hide_input_in_errors=True)
    MAX_UTF8_BYTES: ClassVar[int] = 2400
    identity: ArtifactIdentity
    text: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    units: tuple[str, str, str, str, str, str]
    word_budget_version: str = Field(pattern=r"^recap_budget_v[0-9]+$")

    @model_validator(mode="after")
    def canonical_text_and_hash(self) -> SafeRecapText:
        try:
            assert_export_safe(self.text)
        except Exception:
            raise ValueError("recap text is unsafe") from None
        if self.text != "\n".join(self.units):
            raise ValueError("recap text does not match its semantic units")
        if len(self.text.encode("utf-8")) > self.MAX_UTF8_BYTES:
            raise ValueError("recap exceeds its byte budget")
        if self.sha256 != sha256_bytes(self.text.encode("utf-8")):
            raise ValueError("recap hash does not match its text")
        return self


_SPACE = re.compile(r"\s+")
_UNIT_CHARACTER_LIMIT = 240
_CONTENT_CHARACTER_LIMIT = 205


def _bounded(value: str, *, fallback: str) -> str:
    """Normalize prose and truncate on a stable character boundary."""

    normalized = _SPACE.sub(" ", value).strip() or fallback
    if len(normalized) <= _CONTENT_CHARACTER_LIMIT:
        return normalized
    return f"{normalized[: _CONTENT_CHARACTER_LIMIT - 1].rstrip()}…"


def _first_fact(presentation: PresentationModel) -> str:
    priorities = ("traceback_key_line", "exception_type", "package")
    by_field = {item.field_id: item.value for item in presentation.observed_facts}
    selected = next((by_field[key] for key in priorities if key in by_field), None)
    if selected is None and presentation.observed_facts:
        selected = presentation.observed_facts[0].value
    return _bounded(selected or "当前未提供可复述的报错现象", fallback="当前未提供可复述的报错现象")


def _cause(presentation: PresentationModel) -> str:
    if presentation.root_causes:
        leading = presentation.root_causes[0]
        label = "有依据" if str(leading.claim_kind) == "grounded" else "推断"
        source = f"{leading.cause}（{label}）；仍需通过检查确认"
    else:
        source = f"{presentation.recap_text}；当前没有已确认的根因候选，仍需通过检查确认"
    return _bounded(source, fallback="当前没有已确认的根因候选，仍需通过检查确认")


def _step_summary(values: tuple[object, ...], *, fallback: str) -> str:
    if not values:
        return fallback
    expected = getattr(values[0], "expected_result", "")
    return _bounded(str(expected), fallback=fallback)


def compose_recap(presentation: PresentationModel) -> SafeRecapText:
    """Compose the fixed six-unit transcript without network or duration guesses."""

    try:
        source = _validated_presentation(presentation)
        check = _step_summary(
            source.checks, fallback="先确认当前运行环境与关键依赖状态"
        )
        fix = _step_summary(
            source.fixes, fallback="当前没有可安全复述的修复动作"
        )
        verification = _step_summary(
            source.verification_steps,
            fallback="重新执行最小验证并观察原报错是否消失",
        )
        limitation = _bounded(
            source.limitations[0]
            if source.limitations
            else "仍需在真实环境中复核结果",
            fallback="仍需在真实环境中复核结果",
        )
        units = (
            f"现象：{_first_fact(source)}",
            f"首要原因与不确定性：{_cause(source)}",
            f"首次检查：{check}",
            f"首次修复：{fix}",
            f"验证：{verification}",
            f"剩余局限：{limitation}",
        )
        if any(len(unit) > _UNIT_CHARACTER_LIMIT for unit in units):
            raise ValueError("unit budget")
        text = "\n".join(units)
        assert_export_safe(text)
        return SafeRecapText(
            identity=source.identity,
            text=text,
            sha256=sha256_bytes(text.encode("utf-8")),
            units=units,
            word_budget_version="recap_budget_v1",
        )
    except Exception:
        failure = RecapComposeError()
    raise failure from None
