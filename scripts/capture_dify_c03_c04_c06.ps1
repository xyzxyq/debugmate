param(
    [string]$PythonPath = "X:\PROJECT\校外实训\.worktrees\phase-1-foundation-platform-gate\.venv\Scripts\python.exe",
    [string]$StagingRoot = ".artifacts\dify-c03-c04-c06-capture"
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$python = (Resolve-Path -LiteralPath $PythonPath).Path
$staging = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot $StagingRoot))
$allowedRoot = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot ".artifacts"))
if (-not $staging.StartsWith($allowedRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "StagingRoot must be below the repository .artifacts directory"
}

$env:PYTHONPATH = (Resolve-Path -LiteralPath (Join-Path $repositoryRoot "src")).Path
& $python -m debugmate.dify_live_evidence capture --output-root $staging
if ($LASTEXITCODE) {
    throw "Dify live evidence capture failed"
}
& $python -m debugmate.dify_live_evidence validate-candidate --repository-root $repositoryRoot --evidence-root $staging
if ($LASTEXITCODE) {
    throw "Dify live evidence candidate validation failed"
}
