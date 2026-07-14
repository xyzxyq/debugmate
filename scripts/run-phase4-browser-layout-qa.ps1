[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

function Test-LoopbackPortClosed {
    param(
        [Parameter(Mandatory)]
        [ValidateRange(1, 65535)]
        [int]$Port
    )

    return @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue).Count -eq 0
}

function Wait-ForLoopbackPortClosed {
    param(
        [Parameter(Mandatory)]
        [ValidateRange(1, 65535)]
        [int]$Port
    )

    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    while ($stopwatch.Elapsed.TotalSeconds -lt 5) {
        if (Test-LoopbackPortClosed -Port $Port) {
            return
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Captured loopback server port $Port remained open after cleanup."
}

function Test-ConfigReady {
    param(
        [Parameter(Mandatory)]
        [string]$BaseUrl
    )

    try {
        $config = Invoke-RestMethod -Uri "$BaseUrl/config" -TimeoutSec 1
        if ($config -is [string]) {
            return $config -match '"components"\s*:\s*\['
        }
        return $null -ne $config.PSObject.Properties['components'] -and `
            $config.components -is [System.Collections.IList]
    }
    catch {
        return $false
    }
}

function Assert-CapturedServerOwnership {
    param(
        [Parameter(Mandatory)]
        [System.Diagnostics.Process]$Process,
        [Parameter(Mandatory)]
        [string]$Python,
        [Parameter(Mandatory)]
        [ValidateRange(1, 65535)]
        [int]$Port
    )

    $processInfo = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $($Process.Id)"
    if ($null -eq $processInfo) {
        throw "Cannot verify captured server PID $($Process.Id) ownership."
    }
    $commandLine = [string]$processInfo.CommandLine
    foreach ($fragment in @(
            [regex]::Escape($Python),
            [regex]::Escape('-m'),
            [regex]::Escape('debugmate.ui.serve'),
            [regex]::Escape('--host'),
            [regex]::Escape('127.0.0.1'),
            [regex]::Escape('--port'),
            "(?<![0-9])$Port(?![0-9])"
        )) {
        if ($commandLine -notmatch $fragment) {
            throw "Captured server PID $($Process.Id) command line does not match the requested loopback server."
        }
    }
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python environment not found at $python. Create .venv and install .[dev] first."
}

$listener = $null
$serverProcess = $null
$serverProcessVerified = $false
$port = $null
$hadBaseUrl = Test-Path -LiteralPath Env:DEBUGMATE_UI_BASE_URL
$priorBaseUrl = $env:DEBUGMATE_UI_BASE_URL

Push-Location -LiteralPath $projectRoot
try {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
    $listener.Stop()
    $listener = $null

    $serverProcess = Start-Process `
        -FilePath $python `
        -ArgumentList @('-m', 'debugmate.ui.serve', '--host', '127.0.0.1', '--port', "$port") `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -PassThru
    Assert-CapturedServerOwnership -Process $serverProcess -Python $python -Port $port
    $serverProcessVerified = $true

    $baseUrl = "http://127.0.0.1:$port"
    $readyTimer = [System.Diagnostics.Stopwatch]::StartNew()
    $ready = $false
    while ($readyTimer.Elapsed.TotalSeconds -lt 30) {
        $serverProcess.Refresh()
        if ($serverProcess.HasExited) {
            throw "Captured loopback Gradio process exited before /config became ready."
        }
        if (Test-ConfigReady -BaseUrl $baseUrl) {
            $ready = $true
            break
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not $ready) {
        throw 'Captured loopback Gradio /config did not become ready in 30 seconds.'
    }

    $env:DEBUGMATE_UI_BASE_URL = $baseUrl
    & $python -m pytest tests/ui/test_browser.py -m browser -q
    if ($LASTEXITCODE -ne 0) {
        throw "Browser layout tests failed with exit code $LASTEXITCODE."
    }
}
finally {
    if ($null -ne $listener) {
        $listener.Stop()
    }
    if ($null -ne $serverProcess) {
        $serverProcess.Refresh()
        if (-not $serverProcess.HasExited) {
            if (-not $serverProcessVerified) {
                throw "Refusing to stop unverified captured server PID $($serverProcess.Id)."
            }
            Stop-Process -Id $serverProcess.Id -ErrorAction Stop
            [void]$serverProcess.WaitForExit(10000)
        }
    }
    if ($null -ne $port) {
        Wait-ForLoopbackPortClosed -Port $port
        Write-Host "Captured loopback server stopped; port $port is closed."
    }
    if ($hadBaseUrl) {
        $env:DEBUGMATE_UI_BASE_URL = $priorBaseUrl
    }
    else {
        Remove-Item -LiteralPath Env:DEBUGMATE_UI_BASE_URL -ErrorAction SilentlyContinue
    }
    Pop-Location
}
