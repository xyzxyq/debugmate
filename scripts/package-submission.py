"""Build and verify a safe, self-contained DebugMate source submission package.

The package is intentionally built from Git-tracked project assets plus this
script. It excludes machine-local state, credentials, caches, and temporary
preview material while retaining everything needed to rebuild and run the
course deliverable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "DebugMate-V0.1-source"
ARCHIVE_PATH = ROOT / "deliverables" / f"{PACKAGE_NAME}.zip"
EXTERNAL_MANIFEST_PATH = ROOT / "deliverables" / "source-package-manifest.json"
INTERNAL_MANIFEST_PATH = f"{PACKAGE_NAME}/PACKAGE_MANIFEST.json"
PACKAGE_SCRIPT = Path(__file__).resolve()

ALLOWED_PREFIXES = (
    "README.md",
    ".env.example",
    ".gitattributes",
    ".gitignore",
    "pyproject.toml",
    "contracts/",
    "docs/",
    "evaluation/",
    "evidence/dify-live/",
    "fixtures/",
    "knowledge/",
    "platform/",
    "prompts/",
    "scripts/",
    "src/",
    "tests/",
    "video/",
    "deliverables/",
    "projects/debugmate-defense-ppt_ppt169_20260901/",
)

FORBIDDEN_PARTS = {
    ".git",
    ".venv",
    ".planning",
    ".artifacts",
    ".debugmate-runtime",
    ".playwright-cli",
    ".playwright-mcp",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "backup",
    "live_preview",
}

SECRET_PATTERNS = (
    re.compile(
        r"-----BEGIN (?:RSA|OPENSSH|EC|DSA|PRIVATE) KEY-----\s*\n"
        r"[A-Za-z0-9+/=\r\n]{32,}\s*\n-----END"
    ),
    re.compile(r"\bsk-[A-Za-z0-9]{24,}\b"),
    re.compile(
        r"(?i)\bBearer\s+(?!SECRET_SENTINEL|REDACTED|PLACEHOLDER)"
        r"[A-Za-z0-9._-]{24,}"
    ),
    re.compile(
        r"(?i)(?:api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]\s*[\"']"
        r"(?!(?:[^\"']*@example\.com)|app-abcdefghijklmnop|\$\{|<|your|example|test|change|replace|none|null)"
        r"[^\"']{16,}[\"']"
    ),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    paths = [Path(item) for item in result.stdout.decode("utf-8").split("\0") if item]
    selected: set[Path] = set()
    for relative in paths:
        normalized = relative.as_posix()
        if not any(
            normalized == prefix or normalized.startswith(prefix)
            for prefix in ALLOWED_PREFIXES
        ):
            continue
        if is_forbidden(relative):
            continue
        selected.add(relative)

    # The script is created immediately before the first package build, so it
    # may not yet be tracked. Include it explicitly and let the later commit
    # make it part of the repository as well.
    selected.add(PACKAGE_SCRIPT.relative_to(ROOT))
    return sorted(selected, key=lambda item: item.as_posix().lower())


def is_forbidden(relative: Path) -> bool:
    parts = {part.lower() for part in relative.parts}
    lower = relative.as_posix().lower()
    name = relative.name.lower()
    if parts & {part.lower() for part in FORBIDDEN_PARTS}:
        return True
    if lower.startswith("output/") or lower.startswith("evidence/course-"):
        return True
    if name == "agents.md":
        return True
    if name == ".env" or name.endswith(".env"):
        return True
    if name.endswith((".pyc", ".pyo")):
        return True
    if lower.endswith("debugmate-v0.1-source.zip"):
        return True
    return lower.endswith("source-package-manifest.json")


def validate_source_file(relative: Path) -> None:
    path = ROOT / relative
    if not path.is_file():
        raise RuntimeError(f"Selected package file is missing: {relative}")
    if is_forbidden(relative):
        raise RuntimeError(f"Forbidden package file selected: {relative}")
    binary_suffixes = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".mp4", ".pptx", ".zip"}
    if path.suffix.lower() in binary_suffixes:
        return
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return
    for pattern in SECRET_PATTERNS:
        if pattern.search(content):
            raise RuntimeError(f"Possible secret detected in package source: {relative}")


def make_manifest(relative_files: list[Path], created_on: str) -> dict[str, object]:
    files = []
    for relative in relative_files:
        validate_source_file(relative)
        source = ROOT / relative
        files.append(
            {
                "path": relative.as_posix(),
                "bytes": source.stat().st_size,
                "sha256": sha256_file(source),
            }
        )
    return {
        "package_schema": "debugmate-source-package-1.0",
        "project": "DebugMate",
        "version": "V0.1",
        "created_on": created_on,
        "source_root": "Git-tracked project assets plus scripts/package-submission.py",
        "entrypoints": {
            "install": "python -m pip install -e \".[dev]\"",
            "ui": "python -m debugmate.ui.serve",
            "tests": "python -m pytest -q",
        },
        "runtime": {
            "python": ">=3.13,<3.14",
            "configuration": (
                ".env.example; DIFY_API_KEY is optional for local replay and "
                "required only for live Dify calls"
            ),
            "dify_assets": ["platform/dify/app.dsl.yml", "knowledge/", "prompts/"],
        },
        "included_roots": list(ALLOWED_PREFIXES),
        "excluded_categories": [
            "Git metadata and worktrees",
            "virtual environments and caches",
            "local .env files and credentials",
            "GSD/agent instructions and planning internals",
            "temporary browser previews, backups, and generated output caches",
        ],
        "files": files,
    }


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_package() -> tuple[Path, dict[str, object], str]:
    relative_files = tracked_files()
    created_on = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    manifest = make_manifest(relative_files, created_on)
    ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE_PATH.unlink(missing_ok=True)

    with ZipFile(ARCHIVE_PATH, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in relative_files:
            archive.write(ROOT / relative, f"{PACKAGE_NAME}/{relative.as_posix()}")
        archive.writestr(
            INTERNAL_MANIFEST_PATH,
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )

    package_sha256 = sha256_file(ARCHIVE_PATH)
    external_manifest = {
        **manifest,
        "archive": {
            "path": f"deliverables/{ARCHIVE_PATH.name}",
            "bytes": ARCHIVE_PATH.stat().st_size,
            "sha256": package_sha256,
        },
        "internal_manifest": INTERNAL_MANIFEST_PATH,
    }
    write_json(EXTERNAL_MANIFEST_PATH, external_manifest)
    return ARCHIVE_PATH, external_manifest, package_sha256


def verify_package(archive_path: Path, run_smoke: bool = True) -> dict[str, object]:
    if not archive_path.is_file():
        raise RuntimeError(f"Archive not found: {archive_path}")
    with ZipFile(archive_path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise RuntimeError(f"ZIP CRC check failed: {bad_member}")
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise RuntimeError("ZIP contains duplicate member names")
        forbidden_members = [
            name
            for name in names
            if is_forbidden(Path(name.removeprefix(f"{PACKAGE_NAME}/")))
            or name.startswith(".git/")
        ]
        if forbidden_members:
            raise RuntimeError(f"Forbidden ZIP members: {forbidden_members[:5]}")
        if INTERNAL_MANIFEST_PATH not in names:
            raise RuntimeError("ZIP is missing PACKAGE_MANIFEST.json")
        manifest = json.loads(archive.read(INTERNAL_MANIFEST_PATH).decode("utf-8"))
        listed = {entry["path"]: entry for entry in manifest["files"]}
        missing = [path for path in listed if f"{PACKAGE_NAME}/{path}" not in names]
        if missing:
            raise RuntimeError(f"Manifest files missing from ZIP: {missing[:5]}")
        hash_failures = []
        for path, entry in listed.items():
            actual = hashlib.sha256(archive.read(f"{PACKAGE_NAME}/{path}")).hexdigest()
            if actual != entry["sha256"]:
                hash_failures.append(path)
        if hash_failures:
            raise RuntimeError(f"Manifest SHA-256 mismatch: {hash_failures[:5]}")
        required = {
            "README.md",
            ".env.example",
            "pyproject.toml",
            "src/debugmate/__init__.py",
            "src/debugmate/ui/serve.py",
            "platform/dify/app.dsl.yml",
            "knowledge/",
            "tests/",
            "deliverables/DebugMate-V0.1.pptx",
        }
        available = set(listed)
        missing_required = [
            item
            for item in required
            if not any(path == item or path.startswith(item) for path in available)
        ]
        if missing_required:
            raise RuntimeError(f"Required delivery assets missing: {missing_required}")

        file_count = len(listed)
        extracted_root: Path | None = None
        if run_smoke:
            extracted_root = Path(tempfile.mkdtemp(prefix="debugmate-source-package-"))
            archive.extractall(extracted_root)

    if run_smoke and extracted_root is not None:
        project_root = extracted_root / PACKAGE_NAME
        compile_result = subprocess.run(
            [sys.executable, "-m", "compileall", "-q", str(project_root / "src")],
            capture_output=True,
            text=True,
        )
        if compile_result.returncode:
            raise RuntimeError(f"Extracted source compile failed: {compile_result.stderr}")
        smoke_env = os.environ.copy()
        smoke_env["PYTHONPATH"] = (
            str(project_root / "src")
            + os.pathsep
            + smoke_env.get("PYTHONPATH", "")
        )
        smoke_result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import debugmate; import debugmate.contracts; print(debugmate.__name__)",
            ],
            cwd=project_root,
            env=smoke_env,
            capture_output=True,
            text=True,
        )
        if smoke_result.returncode:
            raise RuntimeError(f"Extracted source import failed: {smoke_result.stderr}")
        shutil.rmtree(extracted_root, ignore_errors=True)

    return {
        "archive": str(archive_path),
        "archive_sha256": sha256_file(archive_path),
        "file_count": file_count,
        "zip_integrity": "passed",
        "manifest_hashes": "passed",
        "extracted_compile": "passed" if run_smoke else "skipped",
        "extracted_import": "passed" if run_smoke else "skipped",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path, help="Verify an existing source package")
    parser.add_argument(
        "--no-smoke",
        action="store_true",
        help="Skip extracted source smoke checks",
    )
    args = parser.parse_args()

    if args.verify:
        result = verify_package(args.verify.resolve(), run_smoke=not args.no_smoke)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    archive_path, manifest, package_sha256 = build_package()
    verification = verify_package(archive_path, run_smoke=not args.no_smoke)
    print(
        json.dumps(
            {
                "package": str(archive_path),
                "manifest": str(EXTERNAL_MANIFEST_PATH),
                "package_sha256": package_sha256,
                "file_count": len(manifest["files"]),
                "verification": verification,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
