[CmdletBinding()]
param(
    [string]$OutputRoot
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python environment not found. Create .venv and install .[dev] first."
}

if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $projectRoot '.artifacts\phase1-probe'
}

Push-Location -LiteralPath $projectRoot
try {
    & $python -m debugmate.cli fixture-probe --output $OutputRoot
    if ($LASTEXITCODE -ne 0) { throw "Fixture probe failed with exit code $LASTEXITCODE" }

    if (-not [string]::IsNullOrWhiteSpace($env:DIFY_API_KEY)) {
        & $python -m debugmate.cli cloud-probe --output $OutputRoot
        if ($LASTEXITCODE -ne 0) { throw "Cloud probe did not pass; exit code $LASTEXITCODE" }
    }
    else {
        Write-Host 'DIFY_API_KEY is absent; cloud probe remains not-tested and no network call was made.'
    }

    & $python -m pytest -q -m 'not cloud'
    if ($LASTEXITCODE -ne 0) { throw "Offline tests failed with exit code $LASTEXITCODE" }

    & $python -m ruff check src tests
    if ($LASTEXITCODE -ne 0) { throw "Ruff failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}
