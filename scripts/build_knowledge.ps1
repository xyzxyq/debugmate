[CmdletBinding()]
param(
    [switch]$Online,
    [string]$OutputRoot
)

$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$registry = Join-Path $projectRoot 'knowledge\sources.json'
$evalQueries = Join-Path $projectRoot 'knowledge\eval_queries.json'
$fixture = Join-Path $projectRoot 'tests\fixtures\knowledge\python-errors.html'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Python environment not found. Create .venv and install .[dev] first.'
}
if (-not (Test-Path -LiteralPath $registry -PathType Leaf)) {
    throw 'Knowledge source registry is missing.'
}
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $projectRoot '.artifacts\knowledge-build'
}

Push-Location -LiteralPath $projectRoot
try {
    $buildArguments = @(
        '-m', 'debugmate.cli', 'knowledge-build',
        '--registry', $registry,
        '--output', $OutputRoot
    )
    if ($Online) {
        $buildArguments += '--online'
    }
    else {
        $buildArguments += @('--source-id', 'python-errors', '--fixture', $fixture)
    }

    $buildJson = & $python @buildArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Knowledge build failed with exit code $LASTEXITCODE"
    }
    Write-Output $buildJson
    $build = $buildJson | ConvertFrom-Json
    $buildPath = $build.build_path

    $retrievalOutput = Join-Path $OutputRoot (Join-Path 'retrieval-evidence' $build.build_id)
    $retrievalJson = & $python -m debugmate.cli knowledge-retrieval-eval $buildPath `
        --eval-queries $evalQueries --output $retrievalOutput
    if ($LASTEXITCODE -ne 0) {
        throw "Offline retrieval evaluation failed with exit code $LASTEXITCODE"
    }
    Write-Output $retrievalJson
    $retrieval = $retrievalJson | ConvertFrom-Json
    if ($retrieval.backend -ne 'offline_fixture') {
        throw 'Offline retrieval evidence has an unexpected backend label.'
    }

    & $python -m debugmate.cli knowledge-coverage $buildPath `
        --eval-queries $evalQueries --retrieval-traces $retrieval.traces_path
    if ($LASTEXITCODE -ne 0) {
        throw "Coverage report failed with exit code $LASTEXITCODE"
    }

    & $python -m debugmate.cli knowledge-sync $buildPath --dry-run
    if ($LASTEXITCODE -ne 0) {
        throw "Dify dry-run plan failed with exit code $LASTEXITCODE"
    }

    & $python -m pytest -q tests/knowledge -m 'not cloud and not ocr'
    if ($LASTEXITCODE -ne 0) {
        throw "Offline knowledge tests failed with exit code $LASTEXITCODE"
    }

    & $python -m ruff check src tests
    if ($LASTEXITCODE -ne 0) {
        throw "Ruff failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
