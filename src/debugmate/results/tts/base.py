"""Value-safe contracts shared by all TTS adapters."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import Field

from debugmate.results.contracts import StrictFrozenModel
from debugmate.results.recap import SafeRecapText


class RateProfile(StrEnum):
    NORMAL = "normal"
    FASTER = "faster"


class TtsRequestIdentity(StrictFrozenModel):
    case_id: str = Field(pattern=r"^case_[0-9a-f]{32}$")
    source_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    diagnosis_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generation_version: str = Field(pattern=r"^gen_[0-9a-f]{32}$")
    recap_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class AudioPayload(StrictFrozenModel):
    """Bounded immutable audio returned by an adapter, never a caller path.

    Adapters are deliberately unable to choose a file name or directory.  The
    fallback chain is the sole owner of its private output lease and writes a
    verified canonical payload only after every media check has succeeded.
    """

    backend: str = Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")
    rate_profile: RateProfile
    request_identity: TtsRequestIdentity
    audio_bytes: bytes = Field(min_length=1, max_length=8_000_000)
    voice: str | None = None


class TtsAdapter(Protocol):
    backend: str

    def synthesize(
        self,
        text: SafeRecapText,
        request_identity: TtsRequestIdentity,
        rate_profile: RateProfile,
    ) -> AudioPayload: ...


class TtsAdapterError(RuntimeError):
    def __init__(self, code: str = "tts_backend_failed") -> None:
        self.code = (
            code if code in {"tts_backend_failed", "tts_not_configured"} else "tts_backend_failed"
        )
        super().__init__(self.code)
