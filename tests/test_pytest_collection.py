from __future__ import annotations

from collections import defaultdict
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent


def test_non_package_test_module_basenames_are_unique() -> None:
    """Prevent pytest's default import mode from aliasing standalone test modules."""

    paths_by_name: dict[str, list[Path]] = defaultdict(list)
    for path in TESTS_ROOT.rglob("test_*.py"):
        if not (path.parent / "__init__.py").is_file():
            paths_by_name[path.name].append(path.relative_to(TESTS_ROOT))

    duplicates = {
        name: sorted(path.as_posix() for path in paths)
        for name, paths in paths_by_name.items()
        if len(paths) > 1
    }

    assert duplicates == {}, (
        "pytest's default import mode requires unique basenames for test modules "
        f"outside packages: {duplicates}"
    )
