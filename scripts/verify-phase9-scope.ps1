[CmdletBinding()]
param(
    [string]$RepositoryRoot,
    [string]$InvocationText = '',
    [string]$BaselineCommit = 'c8c5d82b8cc5773b387de668ccc866faa8e9bebb'
)

$ErrorActionPreference = 'Stop'

function Invoke-GitChecked {
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string[]]$Arguments)
    $output = @(& git -C $Root -c core.quotepath=false -c core.safecrlf=false @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) { throw 'phase9_git_failed' }
    return @($output | ForEach-Object { [string]$_ })
}

function Test-FrozenTarget {
    param([Parameter(Mandatory)][string]$RelativePath)
    $path = $RelativePath.Replace('\', '/')
    if ($path -eq 'deliverables/asset-manifest.json' -or
        $path -eq 'deliverables/video-manifest.json' -or
        $path -eq 'evidence/course-v0.1/manifest.json') { return $true }
    if ($path -like 'evidence/course-v0.1/screenshots/*') { return $true }
    if ($path -like 'deliverables/*' -and $path -match '(?i)\.(pptx|mp4|srt)$') { return $true }
    return $false
}

function Get-StatusPath {
    param([Parameter(Mandatory)][string]$Line)
    if ($Line.Length -lt 4) { return '' }
    $path = $Line.Substring(3).Trim('"')
    if ($path -like '* -> *') { $path = ($path -split ' -> ')[-1].Trim('"') }
    return $path.Replace('\', '/')
}

function Assert-FrozenTargets {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$Baseline
    )
    if ($Baseline -cnotmatch '^[0-9a-f]{40}$') { throw 'frozen_baseline_invalid' }
    [void](Invoke-GitChecked -Root $Root -Arguments @('cat-file', '-e', "$Baseline`^{commit}"))
    [void](Invoke-GitChecked -Root $Root -Arguments @('merge-base', '--is-ancestor', $Baseline, 'HEAD'))
    foreach ($relative in Invoke-GitChecked -Root $Root -Arguments @(
        'diff', '--name-only', "$Baseline..HEAD", '--',
        'deliverables', 'evidence/course-v0.1'
    )) {
        $normalized = $relative.Replace('\', '/')
        if (Test-FrozenTarget -RelativePath $normalized) {
            throw "frozen_target_committed_drift:$normalized"
        }
    }
    foreach ($line in Invoke-GitChecked -Root $Root -Arguments @('status', '--porcelain=v1', '--untracked-files=all')) {
        $relative = Get-StatusPath -Line $line
        if (-not $relative -or -not (Test-FrozenTarget -RelativePath $relative)) { continue }
        if ($line.StartsWith('??')) { throw "frozen_target_new:$relative" }
        throw "frozen_target_changed:$relative"
    }
}

function Assert-Phase9ProjectionSafety {
    param([Parameter(Mandatory)][string]$Root)
    $relativePaths = [Collections.Generic.List[string]]::new()
    $evaluation = Join-Path $Root 'evidence\evaluation\phase9'
    if (Test-Path -LiteralPath $evaluation -PathType Container) {
        foreach ($item in Get-ChildItem -LiteralPath $evaluation -Recurse -File -Force) {
            $relativePaths.Add($item.FullName.Substring($Root.Length).TrimStart('\').Replace('\', '/'))
        }
    }
    foreach ($name in @('current-evaluation.md', 'current-prompt-comparison.md')) {
        $candidate = Join-Path $Root (Join-Path 'docs\course' $name)
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $relativePaths.Add($candidate.Substring($Root.Length).TrimStart('\').Replace('\', '/'))
        }
    }
    foreach ($relative in $relativePaths | Sort-Object -Unique) {
        if ($relative -match '(?i)\.(png|mp3|mp4|pptx|srt)$') {
            throw "phase9_projection_media_forbidden:$relative"
        }
        $candidate = Join-Path $Root ($relative.Replace('/', [IO.Path]::DirectorySeparatorChar))
        $text = Get-Content -LiteralPath $candidate -Raw -Encoding utf8
        if ($text -match '(?i)(?:authorization\s*[:=]|bearer\s+[a-z0-9._-]{8,}|api[_-]?key\s*[:=]|approval[_-]?(?:token|signature)|provider[_-]?(?:body|response)|[a-z]:[\\/]+users[\\/]|/users/|/home/)') {
            throw "privacy_scan_failed:$relative"
        }
    }
}

try {
    $rootValue = if ($RepositoryRoot) { $RepositoryRoot } else { Split-Path -Parent $PSScriptRoot }
    $root = (Resolve-Path -LiteralPath $rootValue -ErrorAction Stop).Path
    if ($InvocationText -match '(?i)(?:build-course-ppt|build-course-video)\.py') {
        throw 'course_builder_forbidden'
    }
    Assert-FrozenTargets -Root $root -Baseline $BaselineCommit
    Assert-Phase9ProjectionSafety -Root $root
    Write-Host 'phase9_scope_gate_passed'
    exit 0
}
catch {
    [Console]::Error.WriteLine([string]$_.Exception.Message)
    exit 1
}
