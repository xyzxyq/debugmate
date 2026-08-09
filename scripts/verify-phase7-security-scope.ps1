[CmdletBinding()]
param(
    [string]$BaselinePath,
    [string]$RepositoryRoot
)

$ErrorActionPreference = 'Stop'

function Invoke-GitChecked {
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string[]]$Arguments)
    $output = @(& git -C $Root -c core.quotepath=false -c core.safecrlf=false @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) { throw "git $($Arguments -join ' ') failed: $($output -join '; ')" }
    return @($output | ForEach-Object { [string]$_ })
}

function Get-Phase7ChangedFiles {
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string]$BaselineCommit)
    $paths = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($line in Invoke-GitChecked -Root $Root -Arguments @('diff', '--name-only', "$BaselineCommit..HEAD", '--')) {
        if ($line) { [void]$paths.Add($line.Replace('\', '/')) }
    }
    foreach ($line in Invoke-GitChecked -Root $Root -Arguments @('status', '--porcelain=v1', '--untracked-files=all')) {
        if ($line.Length -lt 4) { continue }
        $path = $line.Substring(3).Trim('"')
        if ($path -like '* -> *') { $path = ($path -split ' -> ')[-1].Trim('"') }
        if ($path) { [void]$paths.Add($path.Replace('\', '/')) }
    }
    return @($paths | Sort-Object)
}

function Test-Phase7ReviewableTextPath {
    param([Parameter(Mandatory)][string]$RelativePath)
    $normalized = $RelativePath.Replace('\', '/')
    # Workflow metadata is separately frozen by assert-phase7-frozen-scope.ps1;
    # binary/media deliverables are intentionally outside a line-oriented scan.
    if ($normalized -like '.planning/*' -or $normalized -like 'deliverables/*' -or
        $normalized -like 'output/*') { return $false }
    $binaryExtensions = @(
        '.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.pdf', '.docx', '.pptx',
        '.mp3', '.wav', '.mp4', '.srt', '.zip', '.onnx', '.sqlite', '.db', '.pyc'
    )
    $extension = [IO.Path]::GetExtension($normalized).ToLowerInvariant()
    if ($binaryExtensions -contains $extension) { return $false }
    $textExtensions = @(
        '.py', '.pyi', '.ps1', '.psm1', '.psd1', '.js', '.jsx', '.ts', '.tsx',
        '.json', '.jsonl', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.conf', '.env',
        '.md', '.txt', '.rst', '.css', '.scss', '.html', '.xml', '.sql', '.sh',
        '.bash', '.bat', '.cmd', '.properties', '.example'
    )
    $leaf = [IO.Path]::GetFileName($normalized)
    return $textExtensions -contains $extension -or $leaf -in @(
        '.gitignore', '.gitattributes', 'Dockerfile', 'Makefile', 'Procfile'
    )
}

function Assert-Phase7ValueSafeFiles {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][AllowEmptyCollection()][string[]]$RelativePaths
    )
    $patterns = @(
        '-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        '(?i)(?:token|password|secret|signature|approval[_-]?token)\s*[:=]\s*["''](?!\[?REDACTED|null|none|empty|token\b|password\b|secret\b|signature\b)[^"'']{8,}',
        '(?i)gh[pousr]_[A-Za-z0-9]{12,}',
        '(?i)[A-Za-z]:[\\/]{1,2}Users[\\/]{1,2}', # PHASE7_SCAN_PATTERN
        '/Users/', # PHASE7_SCAN_PATTERN
        '/home/', # PHASE7_SCAN_PATTERN
        '(?i)(?:gradio|rapidocr).{0,24}(?:temp|cache|models?)[\\/]',
        '云端运行成功|Dify\s*(?:运行|调用|诊断)成功'
    )
    $findings = [Collections.Generic.List[string]]::new()
    foreach ($relative in $RelativePaths) {
        $candidate = Join-Path $Root ($relative.Replace('/', [IO.Path]::DirectorySeparatorChar))
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        $isEvidence = $relative -like 'evidence/ui/phase7/*'
        $lineNumber = 0
        foreach ($line in Get-Content -LiteralPath $candidate -Encoding utf8 -ErrorAction Stop) {
            $lineNumber++
            foreach ($pattern in $patterns) {
                if ($line -match $pattern) {
                    if (-not $isEvidence -and $relative -like 'tests/*' -and
                        $line -match '#\s*PHASE7_SYNTHETIC_SECRET\s*$') { continue }
                    if ($relative -in @(
                            'scripts/run-phase7-real-input-qa.ps1',
                            'scripts/verify-phase7-security-scope.ps1',
                            'tests/ui/test_browser.py'
                        ) -and $line -match '(?:#|;)\s*PHASE7_SCAN_PATTERN\s*$') { continue }
                    [void]$findings.Add("$relative`:$lineNumber")
                    break
                }
            }
        }
    }
    if ($findings.Count -gt 0) { throw "Phase 07 secret/path scan found $($findings.Count) match(es): $($findings -join ', ')" }
    Write-Host "Phase 07 secret/path scan completed with 0 findings across $($RelativePaths.Count) file(s)."
}

try {
    $rootValue = if ($RepositoryRoot) { $RepositoryRoot } else { Split-Path -Parent $PSScriptRoot }
    $root = (Resolve-Path -LiteralPath $rootValue -ErrorAction Stop).Path
    $baselineValue = if ($BaselinePath) {
        $BaselinePath
    }
    else {
        Join-Path $root '.planning\phases\07-real-input-privacy-ui\07-EXECUTION-BASELINE.json'
    }
    $baseline = (Resolve-Path -LiteralPath $baselineValue -ErrorAction Stop).Path
    $frozenGate = Join-Path $PSScriptRoot 'assert-phase7-frozen-scope.ps1'
    if (-not (Test-Path -LiteralPath $frozenGate -PathType Leaf)) { throw 'Frozen-scope validator is missing.' }
    & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $frozenGate `
        -BaselinePath $baseline -RepositoryRoot $root
    if ($LASTEXITCODE -ne 0) { throw 'Frozen-scope hash gate failed.' }

    $document = Get-Content -Raw -LiteralPath $baseline -Encoding utf8 | ConvertFrom-Json
    $baselineCommit = [string]$document.baseline_commit
    & git -C $root merge-base --is-ancestor $baselineCommit HEAD
    if ($LASTEXITCODE -ne 0) { throw 'baseline_commit is not an ancestor of current HEAD.' }

    $changed = @(Get-Phase7ChangedFiles -Root $root -BaselineCommit $baselineCommit)
    $scan = @($changed | Where-Object { Test-Phase7ReviewableTextPath -RelativePath $_ })
    $trackedEvidence = @(Invoke-GitChecked -Root $root -Arguments @('ls-files', 'evidence/ui/phase7'))
    foreach ($path in $trackedEvidence) { if ($scan -notcontains $path) { $scan += $path } }
    $scan = @($scan | Sort-Object -Unique)
    Assert-Phase7ValueSafeFiles -Root $root -RelativePaths $scan
    Write-Host "Phase 07 security/scope gate passed for baseline $baselineCommit."
    exit 0
}
catch {
    [Console]::Error.WriteLine([string]$_.Exception.Message)
    exit 1
}
