"""Safe deterministic textual result renderers."""

from __future__ import annotations


class ReportRenderError(ValueError):
    def __init__(self) -> None:
        super().__init__("report_render_failed")


def render_report(presentation: object) -> object:
    del presentation
    raise ReportRenderError()
