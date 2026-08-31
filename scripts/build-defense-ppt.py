"""Rebuild the defense-level DebugMate PPTX from the versioned SVG source.

This is intentionally separate from the legacy course-media builder. The deck
is authored as slide-local SVG, checked by ppt-master, then exported to an
editable DrawingML PPTX. No secrets or runtime credentials are read here.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "debugmate-defense-ppt_ppt169_20260901"
DELIVERABLE = ROOT / "deliverables" / "DebugMate-V0.1.pptx"
MANIFEST = ROOT / "deliverables" / "asset-manifest.json"
PPT_MASTER = Path(r"C:\Users\20795\.codex\skills\ppt-master\scripts")


def run(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    run("scripts/author_defense_ppt_svg.py")
    run(
        str(PPT_MASTER / "svg_quality_checker.py"),
        str(PROJECT),
        "--canonical-authoring",
        "--stage",
        "final",
        "--format",
        "ppt169",
    )
    run(str(PPT_MASTER / "finalize_svg.py"), str(PROJECT))
    run(str(PPT_MASTER / "svg_to_pptx.py"), str(PROJECT), "--no-notes")

    exports = sorted((PROJECT / "exports").glob("*.pptx"), key=lambda path: path.stat().st_mtime)
    if not exports:
        raise FileNotFoundError("ppt-master did not produce an export")
    shutil.copyfile(exports[-1], DELIVERABLE)

    image_paths = [
        "projects/debugmate-defense-ppt_ppt169_20260901/images/cover-concept.png",
        "projects/debugmate-defense-ppt_ppt169_20260901/images/01-completed-overview.png",
        "projects/debugmate-defense-ppt_ppt169_20260901/images/02-tts-partial.png",
        "projects/debugmate-defense-ppt_ppt169_20260901/images/03-card-partial.png",
        "projects/debugmate-defense-ppt_ppt169_20260901/images/terminal-module-not-found-redacted.png",
        "projects/debugmate-defense-ppt_ppt169_20260901/images/card.png",
    ]
    assets = []
    for relative in image_paths:
        path = ROOT / relative
        assets.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})

    payload = {
        "schema_version": "debugmate-defense-deck-assets-1.0",
        "generated_on": date.today().isoformat(),
        "pptx": {
            "path": "deliverables/DebugMate-V0.1.pptx",
            "sha256": sha256(DELIVERABLE),
            "slides": 15,
            "authoring_project": "projects/debugmate-defense-ppt_ppt169_20260901",
        },
        "outline": "docs/course/presentation-outline.md",
        "assets": assets,
        "quality_gate": (
            "projects/debugmate-defense-ppt_ppt169_20260901/validation/"
            "svg_quality_report.json"
        ),
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {DELIVERABLE} ({DELIVERABLE.stat().st_size} bytes)")
    print(f"wrote {MANIFEST}")


if __name__ == "__main__":
    main()
