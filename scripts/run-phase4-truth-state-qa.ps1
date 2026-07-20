[CmdletBinding()]
param(
    [ValidateNotNullOrEmpty()]
    [string]$TestExpression = 'vq_02 or vq_03 or vq_06 or vq_07 or vq_08 or vq_09 or vq_10'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$process = $null
$listener = $null
$port = $null
$pushed = $false
$prior = @{}
$names = @(
    'DEBUGMATE_UI_BASE_URL',
    'DEBUGMATE_QA_ENABLED',
    'DEBUGMATE_QA_CAPABILITY',
    'DEBUGMATE_QA_STAGING_DIR'
)
foreach ($name in $names) {
    $item = Get-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
    $prior[$name] = if ($null -eq $item) { $null } else { [string]$item.Value }
}

$bytes = [byte[]]::new(32)
$generator = [Security.Cryptography.RandomNumberGenerator]::Create()
try { $generator.GetBytes($bytes) }
finally { $generator.Dispose() }
$capability = 'qa_' + ([BitConverter]::ToString($bytes) -replace '-', '').ToLowerInvariant()
$runKey = [guid]::NewGuid().ToString('N')
$runtimeRoot = Join-Path $projectRoot ".debugmate-runtime\qa-browser\$runKey"
$stagingRoot = Join-Path $projectRoot "evidence\ui\phase4\staging\$runKey"
$projectFull = [IO.Path]::GetFullPath($projectRoot).TrimEnd([IO.Path]::DirectorySeparatorChar) +
    [IO.Path]::DirectorySeparatorChar
$runtimeFull = [IO.Path]::GetFullPath($runtimeRoot)
if (-not $runtimeFull.StartsWith($projectFull, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'QA runtime root escaped the project workspace.'
}

try {
    Push-Location -LiteralPath $projectRoot
    $pushed = $true
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = ([Net.IPEndPoint]$listener.LocalEndpoint).Port
    $listener.Stop()
    $listener = $null
    New-Item -ItemType Directory -Path $runtimeRoot, $stagingRoot -Force | Out-Null
    $env:DEBUGMATE_QA_ENABLED = '1'
    $env:DEBUGMATE_QA_CAPABILITY = $capability
    $env:DEBUGMATE_QA_STAGING_DIR = $stagingRoot
    $env:DEBUGMATE_UI_BASE_URL = "http://127.0.0.1:$port"
    $process = Start-Process -FilePath $python -ArgumentList @(
        '-m', 'debugmate.ui.qa_serve', '--host', '127.0.0.1', '--port', "$port",
        '--runtime-root', $runtimeRoot
    ) -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
    $timer = [Diagnostics.Stopwatch]::StartNew()
    do {
        if ($process.HasExited) { throw 'QA server exited before readiness.' }
        try {
            $response = Invoke-WebRequest -Uri "$env:DEBUGMATE_UI_BASE_URL/config" `
                -UseBasicParsing -TimeoutSec 1
            $ready = $response.StatusCode -eq 200
        }
        catch { $ready = $false }
        if (-not $ready) { Start-Sleep -Milliseconds 200 }
    } until ($ready -or $timer.Elapsed.TotalSeconds -ge 60)
    if (-not $ready) { throw 'QA server did not become ready.' }
    $routeReady = $false
    $timer.Restart()
    do {
        if ($process.HasExited) { throw 'QA server exited before private route readiness.' }
        $routeStatus = $null
        try {
            $probe = Invoke-WebRequest -Uri "$env:DEBUGMATE_UI_BASE_URL/_debugmate/qa" `
                -UseBasicParsing -Method Get -TimeoutSec 1
            $routeStatus = [int]$probe.StatusCode
        }
        catch {
            if ($null -ne $_.Exception.Response) {
                $routeStatus = [int]$_.Exception.Response.StatusCode
            }
        }
        $routeReady = $routeStatus -eq 405
        if (-not $routeReady) { Start-Sleep -Milliseconds 100 }
    } until ($routeReady -or $timer.Elapsed.TotalSeconds -ge 10)
    if (-not $routeReady) { throw 'QA private route did not become ready.' }
    & $python -m pytest -q -m browser tests\ui\test_browser.py `
        -k $TestExpression
    if ($LASTEXITCODE -ne 0) { throw "Truth-state Edge tests failed: $LASTEXITCODE" }
}
finally {
    $cleanupErrors = [Collections.Generic.List[string]]::new()
    if ($null -ne $listener) {
        try { $listener.Stop() }
        catch { $cleanupErrors.Add("listener: $($_.Exception.Message)") }
    }
    try {
        if ($null -ne $process -and -not $process.HasExited) {
            Stop-Process -InputObject $process -ErrorAction Stop
            if (-not $process.WaitForExit(10000)) { throw 'QA server did not stop.' }
        }
    }
    catch { $cleanupErrors.Add("process: $($_.Exception.Message)") }
    if ($null -ne $port) {
        try {
            $connections = @()
            $timer = [Diagnostics.Stopwatch]::StartNew()
            do {
                $connections = @(Get-NetTCPConnection -State Listen -LocalPort $port `
                    -ErrorAction SilentlyContinue)
                if ($connections.Count -eq 0) { break }
                Start-Sleep -Milliseconds 100
            } until ($timer.Elapsed.TotalSeconds -ge 5)
            if ($connections.Count -ne 0) { throw "QA port $port remained open." }
        }
        catch { $cleanupErrors.Add("port: $($_.Exception.Message)") }
    }
    try {
        if (Test-Path -LiteralPath $runtimeRoot -PathType Container) {
            Remove-Item -LiteralPath $runtimeRoot -Recurse -Force
        }
    }
    catch { $cleanupErrors.Add("runtime: $($_.Exception.Message)") }
    foreach ($name in $names) {
        try {
            if ($null -eq $prior[$name]) {
                Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
            }
            else { Set-Item -LiteralPath "Env:$name" -Value $prior[$name] }
        }
        catch { $cleanupErrors.Add("environment $name`: $($_.Exception.Message)") }
    }
    if ($pushed) {
        try { Pop-Location }
        catch { $cleanupErrors.Add("location: $($_.Exception.Message)") }
    }
    if ($cleanupErrors.Count -gt 0) {
        throw "QA runner cleanup failed: $($cleanupErrors -join '; ')"
    }
}
