"""Deterministic presentation projection for verified diagnoses."""

from __future__ import annotations


class PresentationBuildError(ValueError):
    """Value-free failure at the verified-source presentation boundary."""


def build_presentation(source: object, context: object) -> object:
    """Build the strict renderer input (implemented by the TDD GREEN step)."""

    del source, context
    raise PresentationBuildError("presentation_build_failed")
