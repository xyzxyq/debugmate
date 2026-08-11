param(
    [string]$PythonPath,
    [string]$StagingRoot = ".artifacts\dify-c03-c04-c06-capture"
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $PythonPath = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
}
$pythonItem = Get-Item -LiteralPath $PythonPath -Force -ErrorAction Stop
if ($pythonItem.PSIsContainer -or -not [System.IO.File]::Exists($pythonItem.FullName)) {
    throw "PythonPath must resolve to a regular file"
}
$python = $pythonItem.FullName
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
$inventoryPath = $staging + "-tracked-inventory.json"
$candidatePaths = @(
    Get-ChildItem -LiteralPath $staging -Recurse -File -Force |
        ForEach-Object { $_.FullName }
)
& (Join-Path $PSScriptRoot "export-phase8-tracked-inventory.ps1") `
    -RepositoryRoot $repositoryRoot `
    -CandidatePath $candidatePaths `
    -OutputPath $inventoryPath
if ($LASTEXITCODE) {
    throw "Dify live evidence inventory export failed"
}
& $python -m debugmate.dify_live_evidence validate-candidate `
    --repository-root $repositoryRoot `
    --evidence-root $staging `
    --tracked-inventory $inventoryPath
if ($LASTEXITCODE) {
    throw "Dify live evidence candidate validation failed"
}
