[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

try {
    $repositoryRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
    $python = (Resolve-Path -LiteralPath (Join-Path $repositoryRoot ".venv\Scripts\python.exe")).Path
    $realInputTest = (Resolve-Path -LiteralPath (Join-Path $repositoryRoot "tests\ui\test_real_input.py")).Path
    $privacyTest = (Resolve-Path -LiteralPath (Join-Path $repositoryRoot "tests\privacy\test_preview_integration.py")).Path

    Push-Location -LiteralPath $repositoryRoot
    try {
        $collection = @(
            & $python -m pytest --collect-only -q $realInputTest $privacyTest 2>&1 |
                ForEach-Object { [string]$_ }
        )
        $collectionExit = $LASTEXITCODE
        if ($collectionExit -ne 0) {
            throw "Phase 07 RED tests did not collect cleanly: $($collection -join [Environment]::NewLine)"
        }

        $focused = @(
            & $python -m pytest -q --tb=no $realInputTest $privacyTest -k phase7_contract 2>&1 |
                ForEach-Object { [string]$_ }
        )
        $focusedExit = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    $joined = $focused -join [Environment]::NewLine
    if ($focusedExit -eq 0) { throw "Phase 07 contract tests unexpectedly passed before production implementation." }
    foreach ($forbidden in @(
            "ImportError",
            "ModuleNotFoundError",
            "ERROR collecting",
            "no tests ran",
            "INTERNALERROR",
            "pytest internal error"
        )) {
        if ($joined -match [regex]::Escape($forbidden)) {
            throw "Phase 07 RED run failed for an invalid reason: $forbidden."
        }
    }

    $expected = @(
        "test_phase7_contract_screenshot_audit_hash_binding",
        "test_phase7_contract_revision_atomic_consume",
        "test_phase7_contract_construction_local_only",
        "test_phase7_contract_orthogonal_state"
    )
    $actual = @(
        [regex]::Matches($joined, "FAILED\s+[^\r\n]+::(test_phase7_contract_[A-Za-z0-9_]+)") |
            ForEach-Object { $_.Groups[1].Value } |
            Sort-Object -Unique
    )
    if (@(Compare-Object -ReferenceObject $expected -DifferenceObject $actual -CaseSensitive).Count -ne 0) {
        throw "Phase 07 RED failures did not match the exact expected set. Expected: $($expected -join ', '); actual: $($actual -join ', ')."
    }

    Write-Host "Phase 07 RED semantics verified: clean collection and exactly four expected contract failures."
    exit 0
}
catch {
    [Console]::Error.WriteLine([string]$_.Exception.Message)
    exit 1
}
