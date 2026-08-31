[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Import-Module Microsoft.PowerShell.Utility -ErrorAction Stop

function Test-LoopbackPortClosed {
    param([Parameter(Mandatory)][ValidateRange(1, 65535)][int]$Port)
    return @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue).Count -eq 0
}

function Wait-ForLoopbackPortClosed {
    param([Parameter(Mandatory)][ValidateRange(1, 65535)][int]$Port)
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    while ($stopwatch.Elapsed.TotalSeconds -lt 5) {
        if (Test-LoopbackPortClosed -Port $Port) { return }
        Start-Sleep -Milliseconds 100
    }
    throw "Captured loopback server port $Port remained open after cleanup."
}

function Test-ConfigReady {
    param([Parameter(Mandatory)][string]$BaseUrl)
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/config" -TimeoutSec 1 -UseBasicParsing
        if ($response.StatusCode -ne 200) { return $false }
        Add-Type -AssemblyName System.Web.Extensions
        $config = [System.Web.Script.Serialization.JavaScriptSerializer]::new().DeserializeObject(
            [string]$response.Content
        )
        if ($config -is [System.Collections.IDictionary]) {
            return $config.Keys -contains 'components' -and $config['components'] -is [System.Collections.IList]
        }
        return $null -ne $config.PSObject.Properties['components'] -and `
            $config.components -is [System.Collections.IList]
    }
    catch { return $false }
}

function Assert-CapturedServerOwnership {
    param(
        [Parameter(Mandatory)][System.Diagnostics.Process]$Process,
        [Parameter(Mandatory)][string]$Python,
        [Parameter(Mandatory)][ValidateRange(1, 65535)][int]$Port
    )
    $processInfo = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $($Process.Id)"
    if ($null -eq $processInfo) { throw "Cannot verify captured server PID $($Process.Id) ownership." }
    $commandLine = [string]$processInfo.CommandLine
    foreach ($fragment in @(
            [regex]::Escape($Python), [regex]::Escape('-m'),
            [regex]::Escape('debugmate.ui.serve'), [regex]::Escape('--host'),
            [regex]::Escape('127.0.0.1'), [regex]::Escape('--port'),
            "(?<![0-9])$Port(?![0-9])"
        )) {
        if ($commandLine -notmatch $fragment) {
            throw "Captured server PID $($Process.Id) command line does not match the requested loopback server."
        }
    }
}

function Stop-CapturedServer {
    param(
        [Parameter(Mandatory)][System.Diagnostics.Process]$Process,
        [Parameter(Mandatory)][int]$ExpectedProcessId,
        [Parameter(Mandatory)][Int64]$ExpectedStartTicks
    )
    $Process.Refresh()
    if ($Process.Id -ne $ExpectedProcessId) { throw "Captured process object changed PID." }
    if ($Process.HasExited) { return }
    if ($Process.StartTime.ToUniversalTime().Ticks -ne $ExpectedStartTicks) {
        throw "Captured process PID $ExpectedProcessId no longer has its recorded start time."
    }
    Stop-Process -InputObject $Process -ErrorAction Stop
    if (-not $Process.WaitForExit(10000)) {
        throw "Captured server PID $ExpectedProcessId did not exit within 10 seconds."
    }
}

function Restore-EvidencePairTransaction {
    param([Parameter(Mandatory)]$Transaction)
    foreach ($file in @($Transaction.Screenshot, $Transaction.Ledger)) {
        if (Test-Path -LiteralPath $file.StagingPath) {
            & $Transaction.RemoveFile $file.StagingPath
        }
        if ($file.Promoted) {
            if (Test-Path -LiteralPath $file.FinalPath) {
                & $Transaction.RemoveFile $file.FinalPath
            }
            $file.Promoted = $false
        }
        if ($file.BackedUp) {
            if (-not (Test-Path -LiteralPath $file.BackupPath -PathType Leaf)) {
                throw "Recorded evidence backup is missing: $($file.BackupPath)"
            }
            & $Transaction.MoveFile $file.BackupPath $file.FinalPath
            $file.BackedUp = $false
        }
    }
    $Transaction.FormalCommitted = $false
    $Transaction.CleanupComplete = $true
}

function Reconcile-EvidencePairResidue {
    param(
        [Parameter(Mandatory)][string]$ScreenshotPath,
        [Parameter(Mandatory)][string]$LedgerPath,
        [scriptblock]$RemoveFile = {
            param($Path)
            Remove-Item -LiteralPath $Path -Force
        }
    )
    $screenshotParent = [System.IO.Path]::GetFullPath((Split-Path -Parent $ScreenshotPath))
    $ledgerParent = [System.IO.Path]::GetFullPath((Split-Path -Parent $LedgerPath))
    if ($screenshotParent -ne $ledgerParent) { throw 'Evidence pair must share one directory and volume.' }
    [System.IO.Directory]::CreateDirectory($screenshotParent) | Out-Null
    $residue = @(
        Get-ChildItem -LiteralPath $screenshotParent -File -Force |
            Where-Object {
                $_.Name -match '^\.(VQ-01-live-local|local-live-vq01)\.(staging|backup)\.'
            }
    )
    if ($residue.Count -eq 0) { return }
    if (-not (Test-Path -LiteralPath $ScreenshotPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $LedgerPath -PathType Leaf)) {
        throw 'Unresolved evidence transaction residue requires manual recovery.'
    }
    $formalPair = [pscustomobject]@{
        StagingScreenshot = [System.IO.Path]::GetFullPath($ScreenshotPath)
        StagingLedger = [System.IO.Path]::GetFullPath($LedgerPath)
    }
    Assert-StagedEvidencePair -Transaction $formalPair
    $errors = [System.Collections.Generic.List[string]]::new()
    foreach ($item in $residue) {
        try { & $RemoveFile $item.FullName }
        catch { [void]$errors.Add("$($item.Name): $($_.Exception.Message)") }
    }
    if ($errors.Count -gt 0) {
        throw "Evidence transaction residue cleanup incomplete: $($errors -join '; ')"
    }
}

function New-EvidencePairTransaction {
    param(
        [Parameter(Mandatory)][string]$ScreenshotPath,
        [Parameter(Mandatory)][string]$LedgerPath,
        [scriptblock]$MoveFile = {
            param($Source, $Destination)
            Move-Item -LiteralPath $Source -Destination $Destination
        },
        [scriptblock]$RemoveFile = {
            param($Path)
            Remove-Item -LiteralPath $Path -Force
        }
    )
    $screenshotParent = [System.IO.Path]::GetFullPath((Split-Path -Parent $ScreenshotPath))
    $ledgerParent = [System.IO.Path]::GetFullPath((Split-Path -Parent $LedgerPath))
    if ($screenshotParent -ne $ledgerParent) { throw 'Evidence pair must share one directory and volume.' }
    [System.IO.Directory]::CreateDirectory($screenshotParent) | Out-Null
    Reconcile-EvidencePairResidue `
        -ScreenshotPath $ScreenshotPath `
        -LedgerPath $LedgerPath `
        -RemoveFile $RemoveFile
    $token = [Guid]::NewGuid().ToString('N')
    $screenshotState = [pscustomobject]@{
        FinalPath = [System.IO.Path]::GetFullPath($ScreenshotPath)
        StagingPath = Join-Path $screenshotParent ".VQ-01-live-local.staging.$token.png"
        BackupPath = Join-Path $screenshotParent ".VQ-01-live-local.backup.$token.png"
        HadOriginal = Test-Path -LiteralPath $ScreenshotPath -PathType Leaf
        BackedUp = $false
        Promoted = $false
        BackupCleaned = $false
    }
    $ledgerState = [pscustomobject]@{
        FinalPath = [System.IO.Path]::GetFullPath($LedgerPath)
        StagingPath = Join-Path $ledgerParent ".local-live-vq01.staging.$token.json"
        BackupPath = Join-Path $ledgerParent ".local-live-vq01.backup.$token.json"
        HadOriginal = Test-Path -LiteralPath $LedgerPath -PathType Leaf
        BackedUp = $false
        Promoted = $false
        BackupCleaned = $false
    }
    $transaction = [pscustomobject]@{
        Screenshot = $screenshotState
        Ledger = $ledgerState
        ScreenshotPath = $screenshotState.FinalPath
        LedgerPath = $ledgerState.FinalPath
        StagingScreenshot = $screenshotState.StagingPath
        StagingLedger = $ledgerState.StagingPath
        BackupScreenshot = $screenshotState.BackupPath
        BackupLedger = $ledgerState.BackupPath
        MoveFile = $MoveFile
        RemoveFile = $RemoveFile
        FormalCommitted = $false
        CleanupComplete = $false
    }
    try {
        if ($screenshotState.HadOriginal) {
            & $MoveFile $screenshotState.FinalPath $screenshotState.BackupPath
            $screenshotState.BackedUp = $true
        }
        if ($ledgerState.HadOriginal) {
            & $MoveFile $ledgerState.FinalPath $ledgerState.BackupPath
            $ledgerState.BackedUp = $true
        }
        return $transaction
    }
    catch {
        Restore-EvidencePairTransaction -Transaction $transaction
        throw
    }
}

function Assert-StagedEvidencePair {
    param([Parameter(Mandatory)]$Transaction)
    if (-not (Test-Path -LiteralPath $Transaction.StagingScreenshot -PathType Leaf)) {
        throw 'Staged screenshot is missing.'
    }
    if (-not (Test-Path -LiteralPath $Transaction.StagingLedger -PathType Leaf)) {
        throw 'Staged ledger is missing.'
    }
    $pngBytes = [System.IO.File]::ReadAllBytes($Transaction.StagingScreenshot)
    $pngSignature = [byte[]](137, 80, 78, 71, 13, 10, 26, 10)
    if ($pngBytes.Length -le $pngSignature.Length) { throw 'Staged screenshot is not a PNG.' }
    for ($index = 0; $index -lt $pngSignature.Length; $index++) {
        if ($pngBytes[$index] -ne $pngSignature[$index]) { throw 'Staged screenshot is not a PNG.' }
    }
    $ledger = Get-Content -Raw -LiteralPath $Transaction.StagingLedger | ConvertFrom-Json
    $expectedKeys = @(
        'evidence_version', 'viewport', 'status', 'mode', 'fixture_id', 'fixture_name',
        'backend', 'case_id_sha256', 'source_run_id_sha256', 'result_id_sha256',
        'screenshot_sha256', 'body_horizontal_overflow', 'server_owner', 'verified_at_utc'
    )
    $actualKeys = @($ledger.PSObject.Properties.Name)
    if (@(Compare-Object -ReferenceObject $expectedKeys -DifferenceObject $actualKeys).Count -ne 0) {
        throw 'Staged ledger fields do not match the exact allowlist.'
    }
    if ($ledger.evidence_version -ne 1 -or $ledger.status -ne 'completed' -or $ledger.mode -ne 'live' -or
        $null -ne $ledger.fixture_id -or $null -ne $ledger.fixture_name -or
        $ledger.backend -cne 'local-rule-v1' -or $ledger.body_horizontal_overflow -ne $false -or
        $ledger.server_owner -cne 'run-phase4-local-live-qa.ps1') {
        throw 'Staged ledger semantic contract failed.'
    }
    foreach ($key in @('case_id_sha256', 'source_run_id_sha256', 'result_id_sha256', 'screenshot_sha256')) {
        if ([string]$ledger.$key -cnotmatch '^[0-9a-f]{64}$') { throw "Staged ledger $key is invalid." }
    }
    $actualHash = (Get-FileHash -LiteralPath $Transaction.StagingScreenshot -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ledger.screenshot_sha256 -cne $actualHash) { throw 'Staged ledger screenshot hash mismatch.' }
    if ([string]$ledger.verified_at_utc -cnotmatch '^\d{4}-\d{2}-\d{2}T.*Z$') {
        throw 'Staged ledger verified_at_utc must use UTC Z.'
    }
    $parsedUtc = [DateTimeOffset]::MinValue
    $utcFormats = [string[]]@(
        "yyyy-MM-dd'T'HH:mm:ss'Z'",
        "yyyy-MM-dd'T'HH:mm:ss.FFFFFFF'Z'"
    )
    $utcStyles = [Globalization.DateTimeStyles]::AssumeUniversal -bor `
        [Globalization.DateTimeStyles]::AdjustToUniversal
    if (-not [DateTimeOffset]::TryParseExact(
            [string]$ledger.verified_at_utc,
            $utcFormats,
            [Globalization.CultureInfo]::InvariantCulture,
            $utcStyles,
            [ref]$parsedUtc
        )) {
        throw 'Staged ledger verified_at_utc is not strictly parseable UTC Z.'
    }
    if ($parsedUtc.Offset -ne [TimeSpan]::Zero) { throw 'Staged ledger verified_at_utc is not UTC.' }
}

function Complete-EvidencePairTransaction {
    param([Parameter(Mandatory)]$Transaction)
    Assert-StagedEvidencePair -Transaction $Transaction
    try {
        & $Transaction.MoveFile $Transaction.Screenshot.StagingPath $Transaction.Screenshot.FinalPath
        $Transaction.Screenshot.Promoted = $true
        & $Transaction.MoveFile $Transaction.Ledger.StagingPath $Transaction.Ledger.FinalPath
        $Transaction.Ledger.Promoted = $true
    }
    catch {
        Restore-EvidencePairTransaction -Transaction $Transaction
        throw
    }
}

function Commit-EvidencePairTransaction {
    param([Parameter(Mandatory)]$Transaction)
    if (-not $Transaction.Screenshot.Promoted -or -not $Transaction.Ledger.Promoted) {
        throw 'Evidence pair was not fully promoted.'
    }
    $Transaction.FormalCommitted = $true
    $errors = [System.Collections.Generic.List[string]]::new()
    foreach ($file in @($Transaction.Screenshot, $Transaction.Ledger)) {
        if ($file.BackedUp) {
            try {
                & $Transaction.RemoveFile $file.BackupPath
                $file.BackedUp = $false
                $file.BackupCleaned = $true
            }
            catch { [void]$errors.Add("$($file.BackupPath): $($_.Exception.Message)") }
        }
        else { $file.BackupCleaned = $true }
    }
    $Transaction.CleanupComplete = $errors.Count -eq 0
    if ($errors.Count -gt 0) {
        throw "Evidence backup cleanup incomplete; formal pair remains committed: $($errors -join '; ')"
    }
}

if ($MyInvocation.InvocationName -eq '.') { return }

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$screenshot = Join-Path $projectRoot 'evidence\ui\phase4\VQ-01-live-local.png'
$ledger = Join-Path $projectRoot 'evidence\ui\phase4\local-live-vq01.json'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Python environment not found at $python." }

$listener = $null
$serverProcess = $null
$serverProcessId = $null
$serverProcessStartTicks = $null
$port = $null
$locationPushed = $false
$evidenceTransaction = $null
$runSucceeded = $false
$hadBaseUrl = Test-Path -LiteralPath Env:DEBUGMATE_UI_BASE_URL
$priorBaseUrl = $env:DEBUGMATE_UI_BASE_URL
$hadScreenshotPath = Test-Path -LiteralPath Env:DEBUGMATE_UI_SCREENSHOT_PATH
$priorScreenshotPath = $env:DEBUGMATE_UI_SCREENSHOT_PATH
$hadLedgerPath = Test-Path -LiteralPath Env:DEBUGMATE_UI_LEDGER_PATH
$priorLedgerPath = $env:DEBUGMATE_UI_LEDGER_PATH

try {
    Push-Location -LiteralPath $projectRoot
    $locationPushed = $true
    $evidenceTransaction = New-EvidencePairTransaction -ScreenshotPath $screenshot -LedgerPath $ledger
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
    $serverProcessStartTicks = $serverProcess.StartTime.ToUniversalTime().Ticks
    Assert-CapturedServerOwnership -Process $serverProcess -Python $python -Port $port

    $baseUrl = "http://127.0.0.1:$port"
    $readyTimer = [System.Diagnostics.Stopwatch]::StartNew()
    $ready = $false
    while ($readyTimer.Elapsed.TotalSeconds -lt 30) {
        $serverProcess.Refresh()
        if ($serverProcess.HasExited) { throw 'Captured server exited before /config became ready.' }
        if (Test-ConfigReady -BaseUrl $baseUrl) { $ready = $true; break }
        Start-Sleep -Milliseconds 250
    }
    if (-not $ready) { throw 'Captured loopback Gradio /config did not become ready in 30 seconds.' }

    $env:DEBUGMATE_UI_BASE_URL = $baseUrl
    $env:DEBUGMATE_UI_SCREENSHOT_PATH = $evidenceTransaction.StagingScreenshot
    $env:DEBUGMATE_UI_LEDGER_PATH = $evidenceTransaction.StagingLedger
    & $python -m pytest -q -m browser `
        tests/ui/test_browser.py::test_vq_01_real_loopback_local_approval_produces_completed_live_result
    if ($LASTEXITCODE -ne 0) { throw "VQ-01 local-live browser test failed with exit code $LASTEXITCODE." }
    Complete-EvidencePairTransaction -Transaction $evidenceTransaction
    $runSucceeded = $true
}
finally {
    $cleanupErrors = [System.Collections.Generic.List[string]]::new()
    try {
        if ($null -ne $listener) {
            try { $listener.Stop() } catch { [void]$cleanupErrors.Add("TcpListener stop: $($_.Exception.Message)") }
        }
        if ($null -ne $serverProcess) {
            try {
                Stop-CapturedServer -Process $serverProcess -ExpectedProcessId $serverProcessId `
                    -ExpectedStartTicks $serverProcessStartTicks
            }
            catch { [void]$cleanupErrors.Add("Captured server stop: $($_.Exception.Message)") }
        }
        if ($null -ne $port) {
            try {
                Wait-ForLoopbackPortClosed -Port $port
                Write-Host "Captured loopback server stopped; port $port is closed."
            }
            catch { [void]$cleanupErrors.Add("Loopback port close check: $($_.Exception.Message)") }
        }
    }
    finally {
        try {
            if ($hadBaseUrl) { $env:DEBUGMATE_UI_BASE_URL = $priorBaseUrl }
            else { Remove-Item -LiteralPath Env:DEBUGMATE_UI_BASE_URL -ErrorAction SilentlyContinue }
            if ($hadScreenshotPath) { $env:DEBUGMATE_UI_SCREENSHOT_PATH = $priorScreenshotPath }
            else { Remove-Item -LiteralPath Env:DEBUGMATE_UI_SCREENSHOT_PATH -ErrorAction SilentlyContinue }
            if ($hadLedgerPath) { $env:DEBUGMATE_UI_LEDGER_PATH = $priorLedgerPath }
            else { Remove-Item -LiteralPath Env:DEBUGMATE_UI_LEDGER_PATH -ErrorAction SilentlyContinue }
        }
        catch { [void]$cleanupErrors.Add("Environment restore: $($_.Exception.Message)") }
        finally {
            if ($locationPushed) {
                try { Pop-Location } catch { [void]$cleanupErrors.Add("Location restore: $($_.Exception.Message)") }
            }
        }
    }
    if ($null -ne $evidenceTransaction) {
        if ($runSucceeded -and $cleanupErrors.Count -eq 0) {
            try { Commit-EvidencePairTransaction -Transaction $evidenceTransaction }
            catch { [void]$cleanupErrors.Add("Evidence commit: $($_.Exception.Message)") }
        }
        elseif (-not $runSucceeded -or $cleanupErrors.Count -gt 0) {
            try { Restore-EvidencePairTransaction -Transaction $evidenceTransaction }
            catch { [void]$cleanupErrors.Add("Evidence restore: $($_.Exception.Message)") }
        }
    }
    if ($cleanupErrors.Count -gt 0) { throw "Runner cleanup errors: $($cleanupErrors -join '; ')" }
}
