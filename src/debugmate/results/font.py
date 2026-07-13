"""Resolve one verified font and bind it to the generation profile."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from debugmate.hashing import sha256_file
from debugmate.results.contracts import (
    GenerationProfile,
    PreparedGenerationContext,
    ResolvedFont,
)


def _has_link_between(root: Path, target: Path) -> bool:
    current = target
    while current != root:
        if current.is_symlink():
            return True
        current = current.parent
    return root.is_symlink()


def _project_candidate(root: Path, value: str) -> Path:
    relative = PurePosixPath(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError("project font candidate is unsafe")
    unresolved = root / Path(*relative.parts)
    if _has_link_between(root, unresolved):
        raise ValueError("project font candidate contains a link")
    target = unresolved.resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("project font candidate escapes the project") from exc
    return target


def prepare_generation_context(
    *,
    project_root: Path,
    project_font_candidates: tuple[str, ...] = ("assets/fonts/NotoSansSC-Regular.otf",),
    windows_font_candidates: tuple[Path, ...] = (
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
    ),
    report_contract_version: str = "report-v1",
    card_contract_version: str = "card-v1",
    recap_contract_version: str = "recap-v1",
) -> PreparedGenerationContext:
    """Resolve exactly once, project-first, and return an indivisible frozen context."""

    root = Path(project_root).resolve()
    if not root.is_dir() or root.is_symlink():
        raise ValueError("project font root is unavailable or unsafe")
    chosen: tuple[Path, str] | None = None
    for value in project_font_candidates:
        candidate = _project_candidate(root, value)
        if candidate.is_file():
            chosen = (candidate, "project")
            break
    if chosen is None:
        for raw in windows_font_candidates:
            candidate = Path(raw)
            if not candidate.is_absolute():
                raise ValueError("Windows font allowlist entries must be absolute")
            resolved = candidate.resolve()
            if candidate.is_symlink() or resolved != candidate.absolute():
                raise ValueError("Windows font allowlist entry is a link")
            if resolved.is_file():
                chosen = (resolved, "windows")
                break
    if chosen is None:
        raise ValueError("no approved font is available")

    path, source = chosen
    resolved = ResolvedFont(
        name=path.name,
        path=path,
        sha256=sha256_file(path),
        source=source,
    )
    profile = GenerationProfile.create(
        report_contract_version=report_contract_version,
        card_contract_version=card_contract_version,
        recap_contract_version=recap_contract_version,
        font_name=resolved.name,
        font_sha256=resolved.sha256,
    )
    return PreparedGenerationContext(generation_profile=profile, resolved_font=resolved)
