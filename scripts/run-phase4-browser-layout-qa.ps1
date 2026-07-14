[CmdletBinding()]
param(
    # This explicit, bounded switch exists only for the repository's lifecycle
    # smoke test. It causes the existing ownership audit to fail after the
    # runner has captured its own child, so cleanup can be verified safely.
    [switch]$FailOwnershipAuditForSmoke
)

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

function Stop-CapturedServer {
    param(
        [Parameter(Mandatory)]
        [System.Diagnostics.Process]$Process,
        [Parameter(Mandatory)]
        [int]$ExpectedProcessId,
        [Parameter(Mandatory)]
        [Int64]$ExpectedStartTicks
    )

    $Process.Refresh()
    if ($Process.Id -ne $ExpectedProcessId) {
        throw "Captured process object changed from PID $ExpectedProcessId to PID $($Process.Id)."
    }
    if ($Process.HasExited) {
        return
    }
    if ($Process.StartTime.ToUniversalTime().Ticks -ne $ExpectedStartTicks) {
        throw "Captured process PID $ExpectedProcessId no longer has its recorded start time."
    }

    Stop-Process -InputObject $Process -ErrorAction Stop
    if (-not $Process.WaitForExit(10000)) {
        throw "Captured server PID $ExpectedProcessId did not exit within 10 seconds."
    }
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python environment not found at $python. Create .venv and install .[dev] first."
}

$listener = $null
$serverProcess = $null
$serverProcessId = $null
$serverProcessStartUtc = $null
$serverProcessStartTicks = $null
$port = $null
$hadBaseUrl = Test-Path -LiteralPath Env:DEBUGMATE_UI_BASE_URL
$priorBaseUrl = $env:DEBUGMATE_UI_BASE_URL
$locationPushed = $false

try {
    Push-Location -LiteralPath $projectRoot
    $locationPushed = $true
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
    $serverProcessId = $serverProcess.Id
    $serverProcessStartUtc = $serverProcess.StartTime.ToUniversalTime()
    $serverProcessStartTicks = $serverProcessStartUtc.Ticks
    $auditPython = $python
    if ($FailOwnershipAuditForSmoke) {
        $auditPython = "$python.controlled-failure"
    }
    Assert-CapturedServerOwnership -Process $serverProcess -Python $auditPython -Port $port

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
    & $python -m pytest tests/ui/test_browser.py -m browser -k 'not runner_' -q
    if ($LASTEXITCODE -ne 0) {
        throw "Browser layout tests failed with exit code $LASTEXITCODE."
    }
}
finally {
    $cleanupErrors = [System.Collections.Generic.List[string]]::new()
    try {
        if ($null -ne $listener) {
            try {
                $listener.Stop()
            }
            catch {
                [void]$cleanupErrors.Add("TcpListener stop: $($_.Exception.Message)")
            }
        }
        if ($null -ne $serverProcess) {
            try {
                Stop-CapturedServer `
                    -Process $serverProcess `
                    -ExpectedProcessId $serverProcessId `
                    -ExpectedStartTicks $serverProcessStartTicks
            }
            catch {
                [void]$cleanupErrors.Add("Captured server stop: $($_.Exception.Message)")
            }
        }
        if ($null -ne $port) {
            try {
                Wait-ForLoopbackPortClosed -Port $port
                Write-Host "Captured loopback server stopped; port $port is closed."
            }
            catch {
                [void]$cleanupErrors.Add("Loopback port $port close check: $($_.Exception.Message)")
            }
        }
    }
    finally {
        try {
            if ($hadBaseUrl) {
                $env:DEBUGMATE_UI_BASE_URL = $priorBaseUrl
            }
            else {
                Remove-Item -LiteralPath Env:DEBUGMATE_UI_BASE_URL -ErrorAction SilentlyContinue
            }
        }
        catch {
            [void]$cleanupErrors.Add("Environment restore: $($_.Exception.Message)")
        }
        finally {
            if ($locationPushed) {
                try {
                    Pop-Location
                }
                catch {
                    [void]$cleanupErrors.Add("Location restore: $($_.Exception.Message)")
                }
            }
        }
    }
    if ($cleanupErrors.Count -gt 0) {
        throw "Runner cleanup errors: $($cleanupErrors -join '; ')"
    }
}
