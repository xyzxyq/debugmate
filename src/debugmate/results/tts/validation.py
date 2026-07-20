"""Strict, value-free validation shared by all speech adapters."""

from __future__ import annotations

from debugmate.results.recap import SafeRecapText
from debugmate.results.tts.base import TtsAdapterError, TtsRequestIdentity


def validate_tts_request(
    recap: SafeRecapText, request: TtsRequestIdentity
) -> tuple[SafeRecapText, TtsRequestIdentity]:
    """Revalidate constructed instances and bind the request to the recap identity."""

    try:
        # ``model_validate(existing_model)`` may trust the already-constructed
        # object and skip model validators. Reparse its raw field payload so a
        # forged ``model_construct`` instance must pass the complete contract.
        validated_recap = SafeRecapText.model_validate(dict(recap.__dict__), strict=True)
        validated_request = TtsRequestIdentity.model_validate(dict(request.__dict__), strict=True)
        expected = (
            validated_recap.identity.case_id,
            validated_recap.identity.source_run_id,
            validated_recap.identity.diagnosis_sha256,
            validated_recap.identity.generation_version,
            validated_recap.sha256,
        )
        actual = (
            validated_request.case_id,
            validated_request.source_run_id,
            validated_request.diagnosis_sha256,
            validated_request.generation_version,
            validated_request.recap_sha256,
        )
        if actual != expected:
            raise ValueError("request identity does not match recap")
    except Exception:
        raise TtsAdapterError() from None
    return validated_recap, validated_request
