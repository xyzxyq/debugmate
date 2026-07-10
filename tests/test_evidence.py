from __future__ import annotations

import re
from pathlib import Path

import pytest

from debugmate.hashing import (
    UnsafeArtifactPath,
    artifact_metadata,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from debugmate.settings import DebugMateSettings, find_secret_leaks


def test_canonical_json_is_deterministic_and_utf8() -> None:
    first = canonical_json_bytes({"z": 1, "中文": [True, None], "a": "x"})
    second = canonical_json_bytes({"a": "x", "中文": [True, None], "z": 1})

    assert first == second
    assert first == b'{"a":"x","z":1,"\xe4\xb8\xad\xe6\x96\x87":[true,null]}'


def test_sha256_helpers_and_artifact_metadata(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    root.mkdir()
    artifact = root / "nested" / "report.json"
    artifact.parent.mkdir()
    artifact.write_bytes(b'{"ok":true}')

    metadata = artifact_metadata(root, Path("nested/report.json"), "application/json")

    assert sha256_bytes(artifact.read_bytes()) == sha256_file(artifact)
    assert re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"])
    assert metadata == {
        "path": "nested/report.json",
        "mime_type": "application/json",
        "bytes": 11,
        "sha256": sha256_file(artifact),
    }


@pytest.mark.parametrize(
    "path",
    [Path("../escape.txt"), Path("nested/../../escape.txt"), Path("C:/absolute.txt")],
)
def test_artifact_metadata_rejects_unsafe_paths(tmp_path: Path, path: Path) -> None:
    with pytest.raises(UnsafeArtifactPath):
        artifact_metadata(tmp_path, path, "text/plain")


def test_artifact_metadata_rejects_symlink_escape_when_supported(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    target = outside / "secret.txt"
    target.write_text("secret", encoding="utf-8")
    link = root / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable for this Windows account")

    with pytest.raises(UnsafeArtifactPath):
        artifact_metadata(root, Path("link.txt"), "text/plain")


def test_settings_never_serialize_secret_values() -> None:
    sentinel = "SECRET_SENTINEL_DO_NOT_LOG"
    settings = DebugMateSettings.from_env(
        {
            "DIFY_BASE_URL": "https://api.dify.ai/v1",
            "DIFY_API_KEY": sentinel,
            "DIFY_DATASET_API_KEY": f"dataset-{sentinel}",
            "DIFY_USER": "debugmate-test",
        }
    )

    rendered = "\n".join(
        [
            repr(settings),
            str(settings),
            repr(settings.model_dump()),
            settings.model_dump_json(),
            repr(settings.safe_summary()),
        ]
    )
    assert sentinel not in rendered
    assert settings.cloud_configured is True
    assert settings.safe_summary() == {
        "dify_base_url": "https://api.dify.ai/v1",
        "dify_user": "debugmate-test",
        "dify_api_key_configured": True,
        "dify_dataset_api_key_configured": True,
        "cloud_configured": True,
    }


def test_empty_environment_uses_safe_defaults() -> None:
    settings = DebugMateSettings.from_env({})

    assert settings.cloud_configured is False
    assert settings.safe_summary()["dify_base_url"] == "https://api.dify.ai/v1"
    assert settings.safe_summary()["dify_user"] == "debugmate-local"


def test_secret_leak_detector_returns_paths_without_secret_values() -> None:
    sentinel = "SECRET_SENTINEL_DO_NOT_LOG"
    value = {
        "safe": "hello",
        "nested": [{"header": f"Bearer {sentinel}"}, sentinel],
    }

    leaks = find_secret_leaks(value, [sentinel, ""])

    assert leaks == ["$.nested[0].header", "$.nested[1]"]
    assert sentinel not in repr(leaks)
