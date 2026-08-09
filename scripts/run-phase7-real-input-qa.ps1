[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

function Get-Phase7ExpectedInventory {
    return @(
        [pscustomobject]@{ Scenario = 'P7-VQ-01'; Width = 1366; Height = 768 },
        [pscustomobject]@{ Scenario = 'P7-VQ-02'; Width = 1366; Height = 768 },
        [pscustomobject]@{ Scenario = 'P7-VQ-03'; Width = 1366; Height = 768 },
        [pscustomobject]@{ Scenario = 'P7-VQ-04'; Width = 1366; Height = 768 },
        [pscustomobject]@{ Scenario = 'P7-VQ-07'; Width = 1366; Height = 768 },
        [pscustomobject]@{ Scenario = 'P7-VQ-08-1024'; Width = 1024; Height = 768 },
        [pscustomobject]@{ Scenario = 'P7-VQ-08-768'; Width = 768; Height = 1024 },
        [pscustomobject]@{ Scenario = 'P7-VQ-10'; Width = 1366; Height = 768 },
        [pscustomobject]@{ Scenario = 'P7-VQ-11'; Width = 1366; Height = 768 }
    )
}

function Assert-JUnitZeroIssues {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "JUnit result missing: $Path" }
    [xml]$document = Get-Content -Raw -LiteralPath $Path -Encoding utf8
    $suites = @($document.SelectNodes('//testsuite'))
    if ($suites.Count -eq 0) { throw "JUnit result has no testsuite: $Path" }
    $counts = [ordered]@{ tests = 0; failures = 0; errors = 0; skipped = 0 }
    foreach ($suite in $suites) {
        foreach ($name in @('tests', 'failures', 'errors', 'skipped')) {
            $value = [string]$suite.GetAttribute($name)
            if ($value -notmatch '^\d+$') { throw "JUnit $name count is invalid: $Path" }
            $counts[$name] += [int]$value
        }
    }
    if ($counts.tests -le 0 -or $counts.failures -gt 0 -or $counts.errors -gt 0 -or
        $counts.skipped -gt 0) {
        throw "JUnit gate failed: tests=$($counts.tests) failures=$($counts.failures) errors=$($counts.errors) skipped=$($counts.skipped)."
    }
    return [pscustomobject]$counts
}

function Assert-Phase7EvidenceSet {
    param(
        [Parameter(Mandatory)][string]$Directory,
        [Parameter(Mandatory)][string]$QaRunId,
        [Parameter(Mandatory)][DateTimeOffset]$RunStartedAtUtc,
        [Parameter(Mandatory)][DateTimeOffset]$RunFinishedAtUtc
    )
    if ($QaRunId -cnotmatch '^p7qa_[0-9a-f]{32}$') { throw 'qa_run_id is invalid.' }
    if ($RunStartedAtUtc.Offset -ne [TimeSpan]::Zero -or $RunFinishedAtUtc.Offset -ne [TimeSpan]::Zero -or
        $RunFinishedAtUtc -lt $RunStartedAtUtc) { throw 'Runner UTC interval is invalid.' }
    $resolved = (Resolve-Path -LiteralPath $Directory -ErrorAction Stop).Path
    $items = @(Get-ChildItem -LiteralPath $resolved -Force)
    if (@($items | Where-Object { $_.PSIsContainer }).Count -gt 0) { throw 'Evidence staging contains a directory.' }
    if (@($items | Where-Object { $_.Name -match '\.(?:staging|backup)(?:\.|$)' }).Count -gt 0) {
        throw 'Evidence staging contains transaction residue.'
    }
    $expected = @(Get-Phase7ExpectedInventory)
    $expectedNames = @($expected | ForEach-Object { "$($_.Scenario).json"; "$($_.Scenario).png" } | Sort-Object)
    $actualNames = @($items.Name | Sort-Object)
    if (@(Compare-Object -ReferenceObject $expectedNames -DifferenceObject $actualNames -CaseSensitive).Count -ne 0) {
        throw 'Evidence files do not match the exact nine ledger/PNG inventory.'
    }
    $allowedKeys = @(
        'evidence_version', 'qa_run_id', 'scenario_id', 'viewport', 'privacy_state',
        'result_status', 'mode', 'ocr_backend', 'ocr_status', 'case_id_sha256',
        'source_run_id_sha256', 'result_id_sha256', 'screenshot_sha256',
        'body_horizontal_overflow', 'verified_at_utc'
    )
    foreach ($entry in $expected) {
        $ledgerPath = Join-Path $resolved "$($entry.Scenario).json"
        $pngPath = Join-Path $resolved "$($entry.Scenario).png"
        $ledger = Get-Content -Raw -LiteralPath $ledgerPath -Encoding utf8 | ConvertFrom-Json
        $actualKeys = @($ledger.PSObject.Properties.Name)
        if (@(Compare-Object -ReferenceObject $allowedKeys -DifferenceObject $actualKeys -CaseSensitive).Count -ne 0) {
            throw "Ledger allowlist mismatch: $($entry.Scenario)"
        }
        if ($ledger.evidence_version -ne 1 -or $ledger.qa_run_id -cne $QaRunId -or
            $ledger.scenario_id -cne $entry.Scenario -or $ledger.viewport.width -ne $entry.Width -or
            $ledger.viewport.height -ne $entry.Height -or $ledger.body_horizontal_overflow -ne $false) {
            throw "Ledger identity/viewport contract failed: $($entry.Scenario)"
        }
        foreach ($hashName in @('case_id_sha256', 'source_run_id_sha256', 'result_id_sha256', 'screenshot_sha256')) {
            if ([string]$ledger.$hashName -cnotmatch '^[0-9a-f]{64}$') {
                throw "Ledger hash invalid: $($entry.Scenario)/$hashName"
            }
        }
        $bytes = [IO.File]::ReadAllBytes($pngPath)
        if ($bytes.Length -le 8 -or [Convert]::ToHexString($bytes[0..7]) -cne '89504E470D0A1A0A') {
            throw "Evidence PNG invalid: $($entry.Scenario)"
        }
        $actualHash = (Get-FileHash -LiteralPath $pngPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($ledger.screenshot_sha256 -cne $actualHash) { throw "Screenshot hash mismatch: $($entry.Scenario)" }
        $verified = [DateTimeOffset]::MinValue
        if (-not [DateTimeOffset]::TryParseExact(
                [string]$ledger.verified_at_utc,
                [string[]]@("yyyy-MM-dd'T'HH:mm:ss'Z'", "yyyy-MM-dd'T'HH:mm:ss.FFFFFFF'Z'"),
                [Globalization.CultureInfo]::InvariantCulture,
                [Globalization.DateTimeStyles]::AssumeUniversal -bor [Globalization.DateTimeStyles]::AdjustToUniversal,
                [ref]$verified
            ) -or $verified.Offset -ne [TimeSpan]::Zero -or $verified -lt $RunStartedAtUtc -or
            $verified -gt $RunFinishedAtUtc) {
            throw "Ledger timestamp is outside the current runner interval: $($entry.Scenario)"
        }
        $serialized = Get-Content -Raw -LiteralPath $ledgerPath -Encoding utf8
        if ($serialized -match '(?i)(?:BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|[A-Za-z]:\\Users\\|/Users/|/home/|gh[pousr]_[A-Za-z0-9]+|(?:token|password|secret|signature)\s*[:=]\s*(?!null|redacted)["'']?[A-Za-z0-9])') {
            throw "Ledger contains a secret or local path: $($entry.Scenario)"
        }
    }
}

function New-Phase7EvidenceTransaction {
    param(
        [Parameter(Mandatory)][string]$FinalDirectory,
        [Parameter(Mandatory)][string]$QaRunId,
        [scriptblock]$MoveDirectory = { param($Source, $Destination) Move-Item -LiteralPath $Source -Destination $Destination },
        [scriptblock]$RemoveDirectory = { param($Path) Remove-Item -LiteralPath $Path -Recurse -Force }
    )
    $final = [IO.Path]::GetFullPath($FinalDirectory)
    $parent = Split-Path -Parent $final
    [IO.Directory]::CreateDirectory($parent) | Out-Null
    $residue = @(Get-ChildItem -LiteralPath $parent -Force | Where-Object {
            $_.Name -match '^phase7\..+\.(staging|backup)$'
        })
    if ($residue.Count -gt 0) { throw 'Pre-existing Phase 07 evidence transaction residue detected.' }
    $staging = Join-Path $parent "phase7.$QaRunId.staging"
    $backup = Join-Path $parent "phase7.$QaRunId.backup"
    if ((Test-Path -LiteralPath $staging) -or (Test-Path -LiteralPath $backup)) {
        throw 'Fresh Phase 07 transaction target already exists.'
    }
    [IO.Directory]::CreateDirectory($staging) | Out-Null
    return [pscustomobject]@{
        Final = $final; Staging = $staging; Backup = $backup
        HadOriginal = Test-Path -LiteralPath $final -PathType Container
        BackedUp = $false; Promoted = $false
        MoveDirectory = $MoveDirectory; RemoveDirectory = $RemoveDirectory
    }
}

function Restore-Phase7EvidenceTransaction {
    param([Parameter(Mandatory)]$Transaction)
    if (Test-Path -LiteralPath $Transaction.Staging) { & $Transaction.RemoveDirectory $Transaction.Staging }
    if ($Transaction.Promoted -and (Test-Path -LiteralPath $Transaction.Final)) {
        & $Transaction.RemoveDirectory $Transaction.Final
        $Transaction.Promoted = $false
    }
    if ($Transaction.BackedUp) {
        if (-not (Test-Path -LiteralPath $Transaction.Backup -PathType Container)) { throw 'Evidence backup is missing.' }
        & $Transaction.MoveDirectory $Transaction.Backup $Transaction.Final
        $Transaction.BackedUp = $false
    }
}

function Complete-Phase7EvidenceTransaction {
    param([Parameter(Mandatory)]$Transaction)
    try {
        if ($Transaction.HadOriginal) {
            & $Transaction.MoveDirectory $Transaction.Final $Transaction.Backup
            $Transaction.BackedUp = $true
        }
        & $Transaction.MoveDirectory $Transaction.Staging $Transaction.Final
        $Transaction.Promoted = $true
        if ($Transaction.BackedUp) {
            & $Transaction.RemoveDirectory $Transaction.Backup
            $Transaction.BackedUp = $false
        }
    }
    catch {
        Restore-Phase7EvidenceTransaction -Transaction $Transaction
        throw
    }
}

function Test-ConfigReady {
    param([Parameter(Mandatory)][string]$BaseUrl)
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/config" -TimeoutSec 1 -UseBasicParsing
        if ($response.StatusCode -ne 200) { return $false }
        $config = $response.Content | ConvertFrom-Json
        return $null -ne $config -and $config.PSObject.Properties.Name -contains 'components' -and
            $config.components -is [System.Array]
    }
    catch { return $false }
}

function Assert-CapturedServerOwnership {
    param(
        [Parameter(Mandatory)][System.Diagnostics.Process]$Process,
        [Parameter(Mandatory)][string]$Python,
        [Parameter(Mandatory)][int]$Port
    )
    $info = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $($Process.Id)"
    if ($null -eq $info) { throw 'Captured server process is missing.' }
    $command = [string]$info.CommandLine
    foreach ($part in @([regex]::Escape($Python), 'debugmate\.ui\.serve', '--host', '127\.0\.0\.1', '--port', "(?<!\d)$Port(?!\d)")) {
        if ($command -notmatch $part) { throw 'Captured server ownership check failed.' }
    }
}

function Stop-CapturedServer {
    param(
        [Parameter(Mandatory)][System.Diagnostics.Process]$Process,
        [Parameter(Mandatory)][int]$ExpectedProcessId,
        [Parameter(Mandatory)][Int64]$ExpectedStartTicks
    )
    $Process.Refresh()
    if ($Process.Id -ne $ExpectedProcessId -or $Process.StartTime.ToUniversalTime().Ticks -ne $ExpectedStartTicks) {
        throw 'Captured server identity changed.'
    }
    if (-not $Process.HasExited) {
        Stop-Process -InputObject $Process -ErrorAction Stop
        if (-not $Process.WaitForExit(10000)) { throw 'Captured server did not stop.' }
    }
}

function Wait-ForLoopbackPortClosed {
    param([Parameter(Mandatory)][int]$Port)
    $timer = [Diagnostics.Stopwatch]::StartNew()
    while ($timer.Elapsed.TotalSeconds -lt 5) {
        if (@(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue).Count -eq 0) { return }
        Start-Sleep -Milliseconds 100
    }
    throw "Captured loopback port $Port remained open."
}

if ($MyInvocation.InvocationName -eq '.') { return }

$projectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$formalEvidence = Join-Path $projectRoot 'evidence\ui\phase7'
$runtimeRoot = Join-Path $projectRoot '.debugmate-runtime\phase7-qa'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Python environment missing: $python" }
$qaRunId = 'p7qa_' + [Guid]::NewGuid().ToString('N')
$runStartedAtUtc = [DateTimeOffset]::UtcNow
$transaction = $null
$server = $null
$port = $null
$locationPushed = $false
$priorEnvironment = @{}
foreach ($name in @('DEBUGMATE_UI_BASE_URL', 'DEBUGMATE_PHASE7_QA_RUN_ID', 'DEBUGMATE_PHASE7_STAGING_DIR')) {
    $priorEnvironment[$name] = [pscustomobject]@{
        Exists = Test-Path -LiteralPath "Env:$name"; Value = [Environment]::GetEnvironmentVariable($name)
    }
}
try {
    Push-Location -LiteralPath $projectRoot
    $locationPushed = $true
    $transaction = New-Phase7EvidenceTransaction -FinalDirectory $formalEvidence -QaRunId $qaRunId
    $qaRuntime = Join-Path $runtimeRoot $qaRunId
    [IO.Directory]::CreateDirectory($qaRuntime) | Out-Null
    $ocrJunit = Join-Path $qaRuntime 'ocr-junit.xml'
    $browserJunit = Join-Path $qaRuntime 'browser-junit.xml'

    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
    $listener.Start(); $port = ([Net.IPEndPoint]$listener.LocalEndpoint).Port; $listener.Stop()
    $server = Start-Process -FilePath $python -ArgumentList @(
        '-m', 'debugmate.ui.serve', '--host', '127.0.0.1', '--port', "$port"
    ) -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
    $serverId = $server.Id
    $serverTicks = $server.StartTime.ToUniversalTime().Ticks
    Assert-CapturedServerOwnership -Process $server -Python $python -Port $port
    $baseUrl = "http://127.0.0.1:$port"
    $readyTimer = [Diagnostics.Stopwatch]::StartNew()
    while (-not (Test-ConfigReady -BaseUrl $baseUrl)) {
        $server.Refresh()
        if ($server.HasExited -or $readyTimer.Elapsed.TotalSeconds -ge 30) { throw 'Owned Gradio /config did not become ready.' }
        Start-Sleep -Milliseconds 250
    }
    $env:DEBUGMATE_UI_BASE_URL = $baseUrl
    $env:DEBUGMATE_PHASE7_QA_RUN_ID = $qaRunId
    $env:DEBUGMATE_PHASE7_STAGING_DIR = $transaction.Staging

    & $python -m pytest -q -m ocr tests/privacy/test_rapidocr_smoke.py --junitxml $ocrJunit
    if ($LASTEXITCODE -ne 0) { throw "Production RapidOCR smoke failed: $LASTEXITCODE" }
    Assert-JUnitZeroIssues -Path $ocrJunit | Out-Null
    & $python -m pytest -q -m browser tests/ui/test_browser.py -k 'phase7 or p7_' --junitxml $browserJunit
    if ($LASTEXITCODE -ne 0) { throw "Phase 07 Microsoft Edge suite failed: $LASTEXITCODE" }
    Assert-JUnitZeroIssues -Path $browserJunit | Out-Null
    $runFinishedAtUtc = [DateTimeOffset]::UtcNow
    Assert-Phase7EvidenceSet -Directory $transaction.Staging -QaRunId $qaRunId `
        -RunStartedAtUtc $runStartedAtUtc -RunFinishedAtUtc $runFinishedAtUtc
    Complete-Phase7EvidenceTransaction -Transaction $transaction
    Write-Host "Phase 07 QA passed: qa_run_id=$qaRunId, 9 ledger/PNG pairs promoted."
}
catch {
    if ($null -ne $transaction) { Restore-Phase7EvidenceTransaction -Transaction $transaction }
    throw
}
finally {
    $cleanupErrors = [Collections.Generic.List[string]]::new()
    if ($null -ne $server) {
        try { Stop-CapturedServer -Process $server -ExpectedProcessId $serverId -ExpectedStartTicks $serverTicks }
        catch { [void]$cleanupErrors.Add($_.Exception.Message) }
    }
    if ($null -ne $port) {
        try { Wait-ForLoopbackPortClosed -Port $port }
        catch { [void]$cleanupErrors.Add($_.Exception.Message) }
    }
    foreach ($name in $priorEnvironment.Keys) {
        try {
            if ($priorEnvironment[$name].Exists) { [Environment]::SetEnvironmentVariable($name, $priorEnvironment[$name].Value) }
            else { Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue }
        }
        catch { [void]$cleanupErrors.Add("environment $name restore failed") }
    }
    if ($locationPushed) { Pop-Location }
    if ($cleanupErrors.Count -gt 0) { throw "Runner cleanup failed: $($cleanupErrors -join '; ')" }
}
