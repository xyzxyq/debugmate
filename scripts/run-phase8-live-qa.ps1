[CmdletBinding()]
param(
    [ValidateSet('dify', 'local_fallback')]
    [string]$BrowserBackend = 'dify',
    [switch]$UseVerifiedCloudEvidence
)

$ErrorActionPreference = 'Stop'
Import-Module Microsoft.PowerShell.Utility -ErrorAction Stop

function Assert-JUnitZeroIssues {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "phase8_junit_missing:$Path" }
    [xml]$doc = Get-Content -LiteralPath $Path -Raw -Encoding utf8
    $suites = @($doc.SelectNodes('//testsuite'))
    if ($suites.Count -eq 0) { throw 'phase8_junit_empty' }
    $counts = [ordered]@{ tests = 0; failures = 0; errors = 0; skipped = 0 }
    foreach ($suite in $suites) {
        foreach ($name in @($counts.Keys)) {
            $value = [string]$suite.GetAttribute($name)
            if ($value -notmatch '^\d+$') { throw "phase8_junit_invalid:$name" }
            $counts[$name] += [int]$value
        }
    }
    if ($counts.tests -le 0 -or $counts.failures -gt 0 -or $counts.errors -gt 0 -or $counts.skipped -gt 0) {
        throw "phase8_junit_gate_failed:tests=$($counts.tests),failures=$($counts.failures),errors=$($counts.errors),skipped=$($counts.skipped)"
    }
}

function New-Phase8EvidenceTransaction {
    param([Parameter(Mandatory)][string]$FinalDirectory, [Parameter(Mandatory)][string]$QaRunId)
    $final = [IO.Path]::GetFullPath($FinalDirectory)
    $parent = Split-Path -Parent $final
    [IO.Directory]::CreateDirectory($parent) | Out-Null
    $staging = Join-Path $parent "phase8.$QaRunId.staging"
    $backup = Join-Path $parent "phase8.$QaRunId.backup"
    if ((Test-Path -LiteralPath $staging) -or (Test-Path -LiteralPath $backup)) { throw 'phase8_transaction_residue' }
    [IO.Directory]::CreateDirectory($staging) | Out-Null
    return [pscustomobject]@{ Final = $final; Staging = $staging; Backup = $backup; HadOriginal = Test-Path -LiteralPath $final -PathType Container; BackedUp = $false; Promoted = $false }
}

function Restore-Phase8EvidenceTransaction {
    param([Parameter(Mandatory)]$Transaction)
    if (Test-Path -LiteralPath $Transaction.Staging) { Remove-Item -LiteralPath $Transaction.Staging -Recurse -Force }
    if ($Transaction.Promoted -and (Test-Path -LiteralPath $Transaction.Final)) { Remove-Item -LiteralPath $Transaction.Final -Recurse -Force; $Transaction.Promoted = $false }
    if ($Transaction.BackedUp) { Move-Item -LiteralPath $Transaction.Backup -Destination $Transaction.Final; $Transaction.BackedUp = $false }
}

function Complete-Phase8EvidenceTransaction {
    param([Parameter(Mandatory)]$Transaction)
    try {
        if ($Transaction.HadOriginal) { Move-Item -LiteralPath $Transaction.Final -Destination $Transaction.Backup; $Transaction.BackedUp = $true }
        Move-Item -LiteralPath $Transaction.Staging -Destination $Transaction.Final
        $Transaction.Promoted = $true
        if ($Transaction.BackedUp) { Remove-Item -LiteralPath $Transaction.Backup -Recurse -Force; $Transaction.BackedUp = $false }
    } catch { Restore-Phase8EvidenceTransaction $Transaction; throw }
}

function Wait-ForLoopbackPortClosed {
    param([Parameter(Mandatory)][int]$Port)
    $watch = [Diagnostics.Stopwatch]::StartNew()
    while ($watch.Elapsed.TotalSeconds -lt 10) {
        if (@(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue).Count -eq 0) { return }
        Start-Sleep -Milliseconds 100
    }
    throw "phase8_loopback_port_open:$Port"
}

function New-Phase8SafeProjection {
    param(
        [Parameter(Mandatory)][string]$Staging,
        [Parameter(Mandatory)][string]$QaRunId,
        [Parameter(Mandatory)][ValidateSet('dify', 'local_fallback')][string]$Backend
    )
    $zip = @(Get-ChildItem -LiteralPath $Staging -Filter '*.zip' -File -Force)
    if ($zip.Count -ne 1) { throw 'phase8_result_zip_count_invalid' }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $extract = Join-Path $Staging '.verified-bundle'
    if (Test-Path -LiteralPath $extract) { Remove-Item -LiteralPath $extract -Recurse -Force }
    [IO.Directory]::CreateDirectory($extract) | Out-Null
    $archive = [IO.Compression.ZipFile]::OpenRead($zip[0].FullName)
    try {
        $names = @($archive.Entries | ForEach-Object { $_.FullName } | Sort-Object)
        foreach ($required in @('diagnosis.json','report.md','card.png','recap.mp3','checksums.sha256','result-manifest.json')) {
            if ($names -notcontains $required) { throw "phase8_result_member_missing:$required" }
        }
        [IO.Compression.ZipFile]::ExtractToDirectory($zip[0].FullName, $extract)
    } finally { $archive.Dispose() }
    $ffprobe = Get-Command -Name 'ffprobe.exe' -ErrorAction Stop
    $probe = & $ffprobe.Source -v error -show_entries format=duration -of json (Join-Path $extract 'recap.mp3') 2>&1
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($probe -join ''))) { throw 'phase8_ffprobe_failed' }
    $zipHash = (Get-FileHash -LiteralPath $zip[0].FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $projection = [ordered]@{
        evidence_version = 1
        qa_run_id = $QaRunId
        backend = $Backend
        status = if ($Backend -eq 'dify') { 'accepted' } else { 'accepted_with_local_fallback' }
        usage = 'not_reported'
        result_zip_sha256 = $zipHash
        result_members = [ordered]@{}
    }
    if ($Backend -eq 'local_fallback') {
        $projection['fallback_reason'] = 'dify_external_node_unavailable'
    }
    foreach ($name in @('diagnosis.json','report.md','card.png','recap.mp3','checksums.sha256','result-manifest.json')) {
        $projection.result_members[$name] = (Get-FileHash -LiteralPath (Join-Path $extract $name) -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $projectionJson = $projection | ConvertTo-Json -Depth 5
    [IO.File]::WriteAllText((Join-Path $Staging 'live-run.json'), $projectionJson + "`n", [Text.UTF8Encoding]::new($false))
    $checksums = @($zip[0].Name, 'live-run.json') | ForEach-Object {
        $target = Join-Path $Staging $_
        "{0}  {1}" -f (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant(), $_
    }
    [IO.File]::WriteAllLines((Join-Path $Staging 'checksums.sha256'), $checksums, [Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $Staging 'manifest.json'), $projectionJson + "`n", [Text.UTF8Encoding]::new($false))
    Remove-Item -LiteralPath $extract -Recurse -Force
}

if ($MyInvocation.InvocationName -eq '.') { return }
$root = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot) -ErrorAction Stop).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'phase8_python_missing' }
$qaRunId = 'p8qa_' + [Guid]::NewGuid().ToString('N')
$runtime = Join-Path $root ('.debugmate-runtime\phase8-qa\' + $qaRunId)
$formal = Join-Path $root 'evidence\dify-live\phase8'
$transaction = New-Phase8EvidenceTransaction -FinalDirectory $formal -QaRunId $qaRunId
$server = $null
$port = $null
$prior = @{}
foreach ($name in @('DEBUGMATE_UI_BASE_URL','DEBUGMATE_PHASE8_QA_RUN_ID','DEBUGMATE_PHASE8_STAGING_DIR','DEBUGMATE_PHASE8_EXPECTED_BACKEND','DEBUGMATE_DIFY_DIAGNOSIS_APP_CONFIGURED')) {
    $prior[$name] = [pscustomobject]@{ Exists = Test-Path -LiteralPath "Env:$name"; Value = [Environment]::GetEnvironmentVariable($name) }
}
try {
    Push-Location -LiteralPath $root
    [IO.Directory]::CreateDirectory($runtime) | Out-Null
    $cloudJunit = Join-Path $runtime 'cloud-junit.xml'
    $browserJunit = Join-Path $runtime 'browser-junit.xml'
    $cloudSmoke = Join-Path $root '.debugmate-runtime\phase8-cloud-smoke\live-smoke.json'
    $cloudEnvelope = Join-Path $root '.debugmate-runtime\phase8-cloud-smoke\run-envelope.json'
    if ($UseVerifiedCloudEvidence) {
        if (-not (Test-Path -LiteralPath $cloudSmoke -PathType Leaf) -or -not (Test-Path -LiteralPath $cloudEnvelope -PathType Leaf)) {
            throw 'phase8_verified_cloud_evidence_missing'
        }
        $validation = & $python (Join-Path $root 'scripts\verify-phase8-cloud-cache.py')
        if ($LASTEXITCODE -ne 0 -or ($validation -join '').Trim() -ne 'verified_cloud_cache') { throw 'phase8_verified_cloud_evidence_invalid' }
        Write-Host 'phase8_cloud_using_verified_evidence_cache'
        $cacheRecord = [ordered]@{ evidence_version = 1; backend = 'dify'; status = 'live_attempt_failed_verified_success_retained'; failure_code = 'workflow_envelope_or_ambiguous_timeout'; source = 'versioned_or_user_supplied_strict_envelope'; }
        [IO.File]::WriteAllText((Join-Path $transaction.Staging 'cloud-live-status.json'), (($cacheRecord | ConvertTo-Json -Depth 5) + "`n"), [Text.UTF8Encoding]::new($false))
    } else {
        & $python -m pytest -q -m cloud tests/cloud/test_dify_live_cloud.py --junitxml $cloudJunit
        if ($LASTEXITCODE -ne 0) { throw "phase8_cloud_failed:$LASTEXITCODE" }
        Assert-JUnitZeroIssues $cloudJunit
    }
    foreach ($source in @($cloudSmoke, $cloudEnvelope)) {
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "phase8_cloud_evidence_missing:$source" }
        Copy-Item -LiteralPath $source -Destination $transaction.Staging -Force
    }
    $readback = Join-Path $root 'evidence\dify-live\phase8\knowledge-readback.json'
    if (-not (Test-Path -LiteralPath $readback -PathType Leaf)) { throw 'phase8_knowledge_readback_missing' }
    Copy-Item -LiteralPath $readback -Destination $transaction.Staging -Force
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
    $listener.Start(); $port = ([Net.IPEndPoint]$listener.LocalEndpoint).Port; $listener.Stop()
    $env:DEBUGMATE_DIFY_DIAGNOSIS_APP_CONFIGURED = if ($BrowserBackend -eq 'dify') { '1' } else { '0' }
    $server = Start-Process -FilePath $python -ArgumentList @('-m','debugmate.ui.serve','--host','127.0.0.1','--port',"$port") -WorkingDirectory $root -WindowStyle Hidden -PassThru
    $ready = [Diagnostics.Stopwatch]::StartNew()
    $baseUrl = "http://127.0.0.1:$port"
    while ($true) {
        try { $response = Invoke-WebRequest -Uri "$baseUrl/config" -TimeoutSec 2 -UseBasicParsing; if ($response.StatusCode -eq 200) { break } } catch { }
        $server.Refresh()
        if ($server.HasExited -or $ready.Elapsed.TotalSeconds -gt 60) { throw 'phase8_loopback_not_ready' }
        Start-Sleep -Milliseconds 250
    }
    $env:DEBUGMATE_UI_BASE_URL = $baseUrl
    $env:DEBUGMATE_PHASE8_QA_RUN_ID = $qaRunId
    $env:DEBUGMATE_PHASE8_STAGING_DIR = $transaction.Staging
    $env:DEBUGMATE_PHASE8_EXPECTED_BACKEND = $BrowserBackend
    $env:DEBUGMATE_DIFY_DIAGNOSIS_APP_CONFIGURED = if ($BrowserBackend -eq 'dify') { '1' } else { '0' }
    & $python -m pytest -q -m browser tests/ui/test_phase8_live_browser.py --junitxml $browserJunit
    if ($LASTEXITCODE -ne 0) { throw "phase8_browser_failed:$LASTEXITCODE" }
    Assert-JUnitZeroIssues $browserJunit
    New-Phase8SafeProjection -Staging $transaction.Staging -QaRunId $qaRunId -Backend $BrowserBackend
    & (Join-Path $root 'scripts\verify-phase8-security-scope.ps1') -RepositoryRoot $root -EvidenceRoot $transaction.Staging
    if ($LASTEXITCODE -ne 0) { throw 'phase8_security_failed' }
    if (@(Get-ChildItem -LiteralPath $transaction.Staging -File -Force).Count -lt 1) { throw 'phase8_evidence_empty' }
    Complete-Phase8EvidenceTransaction $transaction
    Write-Host "phase8_live_qa_passed:$qaRunId"
} catch {
    Restore-Phase8EvidenceTransaction $transaction
    throw
} finally {
    if ($null -ne $server) {
        $server.Refresh()
        if (-not $server.HasExited) { Stop-Process -InputObject $server -ErrorAction Stop; [void]$server.WaitForExit(10000) }
    }
    if ($null -ne $port) { Wait-ForLoopbackPortClosed $port }
    foreach ($name in $prior.Keys) {
        if ($prior[$name].Exists) { [Environment]::SetEnvironmentVariable($name, $prior[$name].Value) }
        else { Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue }
    }
    Pop-Location
}
