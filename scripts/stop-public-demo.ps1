[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $projectRoot ".debugmate-runtime\public-demo"
$statusPath = Join-Path $runtimeRoot "status.json"

if (-not (Test-Path -LiteralPath $statusPath)) {
    Write-Output "No public demo status file found; nothing to stop."
    exit 0
}

$status = Get-Content -LiteralPath $statusPath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($property in @("app_pid", "tunnel_pid")) {
    $processId = [int]$status.$property
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) {
        taskkill.exe /PID $processId /T /F | Out-Null
        Write-Output "Stopped $property=$processId"
    }
}
Remove-Item -LiteralPath $statusPath -Force
Write-Output "DebugMate public demo stopped."
