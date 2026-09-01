[CmdletBinding()]
param(
    [int]$Port = 7860
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $projectRoot ".debugmate-runtime\public-demo"
$statusPath = Join-Path $runtimeRoot "status.json"
$tunnelOut = Join-Path $runtimeRoot "cloudflared.stdout.log"
$tunnelErr = Join-Path $runtimeRoot "cloudflared.stderr.log"
$appOut = Join-Path $runtimeRoot "app.stdout.log"
$appErr = Join-Path $runtimeRoot "app.stderr.log"
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Python environment not found: $pythonPath"
}
$cloudflaredCommand = Get-Command cloudflared.exe -ErrorAction SilentlyContinue
if ($null -eq $cloudflaredCommand) {
    throw "cloudflared.exe is not installed or is not on PATH"
}
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    throw "Port $Port is already in use"
}

New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
Remove-Item -LiteralPath $tunnelOut, $tunnelErr, $appOut, $appErr -Force -ErrorAction SilentlyContinue

$tunnel = Start-Process `
    -FilePath $cloudflaredCommand.Source `
    -ArgumentList @("tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:$Port") `
    -RedirectStandardOutput $tunnelOut `
    -RedirectStandardError $tunnelErr `
    -PassThru `
    -WindowStyle Hidden

$publicOrigin = $null
for ($attempt = 0; $attempt -lt 60 -and $null -eq $publicOrigin; $attempt++) {
    Start-Sleep -Seconds 1
    $tunnelText = ""
    foreach ($log in @($tunnelOut, $tunnelErr)) {
        if (Test-Path -LiteralPath $log) {
            $tunnelText += "`n" + (Get-Content -LiteralPath $log -Raw -ErrorAction SilentlyContinue)
        }
    }
    $match = [regex]::Match($tunnelText, "https://[a-z0-9-]+\.trycloudflare\.com")
    if ($match.Success) {
        $publicOrigin = $match.Value
    }
    if ($tunnel.HasExited) {
        throw "cloudflared exited before publishing a URL. See $tunnelErr"
    }
}
if ($null -eq $publicOrigin) {
    Stop-Process -Id $tunnel.Id -Force -ErrorAction SilentlyContinue
    throw "Timed out waiting for a Cloudflare Quick Tunnel URL. See $tunnelErr"
}

$app = Start-Process `
    -FilePath $pythonPath `
    -ArgumentList @("-m", "debugmate.ui.serve", "--host", "127.0.0.1", "--port", "$Port") `
    -WorkingDirectory $projectRoot `
    -Environment @{
        PYTHONPATH = Join-Path $projectRoot "src"
        DEBUGMATE_PUBLIC_ORIGIN = $publicOrigin
    } `
    -RedirectStandardOutput $appOut `
    -RedirectStandardError $appErr `
    -PassThru `
    -WindowStyle Hidden
if ($null -eq $app) {
    Stop-Process -Id $tunnel.Id -Force -ErrorAction SilentlyContinue
    throw "Failed to start DebugMate"
}

$localOrigin = "http://127.0.0.1:$Port"
$ready = $false
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri $localOrigin -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
            $ready = $true
            break
        }
    } catch {
        if ($app.HasExited) {
            throw "DebugMate exited during startup. See $appErr"
        }
    }
}
if (-not $ready) {
    Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $tunnel.Id -Force -ErrorAction SilentlyContinue
    throw "Timed out waiting for local DebugMate UI. See $appErr"
}

$status = [ordered]@{
    started_at = (Get-Date).ToUniversalTime().ToString("o")
    public_origin = $publicOrigin
    local_origin = $localOrigin
    app_pid = $app.Id
    tunnel_pid = $tunnel.Id
    app_stdout = $appOut.Substring($projectRoot.Length + 1).Replace("\", "/")
    app_stderr = $appErr.Substring($projectRoot.Length + 1).Replace("\", "/")
    tunnel_stderr = $tunnelErr.Substring($projectRoot.Length + 1).Replace("\", "/")
}
$status | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8

Write-Output "DebugMate public demo is ready: $publicOrigin"
Write-Output "Local UI: $localOrigin"
Write-Output "Status: $($statusPath.Substring($projectRoot.Length + 1))"
Write-Output "Stop: .\scripts\stop-public-demo.ps1"
