[CmdletBinding()]
param(
    [string]$RepositoryRoot = ".",
    [string]$EvidenceRoot = "evidence\dify-live\phase8",
    [string]$BaselineCommit = ""
)

$ErrorActionPreference = 'Stop'
Import-Module Microsoft.PowerShell.Utility -ErrorAction Stop

function Invoke-GitLines {
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string[]]$Arguments)
    $lines = @(& git -C $Root -c core.quotepath=false -c core.safecrlf=false @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) { throw 'phase8_git_failed' }
    return @($lines | ForEach-Object { [string]$_ })
}

function Test-FrozenTargets {
    param([Parameter(Mandatory)][string]$RelativePath)
    $path = $RelativePath.Replace('\', '/')
    return $path -eq 'deliverables/asset-manifest.json' -or
        $path -eq 'deliverables/video-manifest.json' -or
        $path -eq 'evidence/course-v0.1/manifest.json' -or
        $path -like 'evidence/course-v0.1/screenshots/*' -or
        ($path -like 'deliverables/*' -and $path -match '(?i)\.(pptx|mp4|srt)$')
}

function Get-StatusPath {
    param([Parameter(Mandatory)][string]$Line)
    if ($Line.Length -lt 4) { return '' }
    $path = $Line.Substring(3).Trim('"')
    if ($path -like '* -> *') { $path = ($path -split ' -> ')[-1].Trim('"') }
    return $path.Replace('\', '/')
}

function Get-GitFileSha256 {
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string]$Commit, [Parameter(Mandatory)][string]$RelativePath)
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = 'git.exe'
    $startInfo.Arguments = "-C `"$Root`" show `"$Commit`:$RelativePath`""
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    [void]$process.Start()
    $memory = [IO.MemoryStream]::new()
    $process.StandardOutput.BaseStream.CopyTo($memory)
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw "phase8_frozen_blob_missing:$RelativePath" }
    $memory.Position = 0
    try { return (Get-FileHash -InputStream $memory -Algorithm SHA256).Hash.ToLowerInvariant() }
    finally { $memory.Dispose(); $process.Dispose() }
}

function Assert-FrozenTargets {
    param([Parameter(Mandatory)][string]$Root, [string]$Baseline)
    $commit = if ($Baseline) { $Baseline } else { (Invoke-GitLines $Root @('rev-parse', 'HEAD') | Select-Object -First 1) }
    if ($commit -notmatch '^[0-9a-f]{40}$') { throw 'phase8_frozen_baseline_invalid' }
    [void](Invoke-GitLines $Root @('cat-file', '-e', "$commit`^{commit}"))
    foreach ($relative in Invoke-GitLines $Root @('diff', '--name-only', "$commit..HEAD", '--', 'deliverables', 'evidence/course-v0.1')) {
        if (Test-FrozenTargets $relative) { throw "phase8_frozen_target_committed_drift:$relative" }
    }
    foreach ($line in Invoke-GitLines $Root @('status', '--porcelain=v1', '--untracked-files=all')) {
        $relative = Get-StatusPath $line
        if ($relative -and (Test-FrozenTargets $relative)) { throw "phase8_frozen_target_dirty:$relative" }
    }
    foreach ($relative in (Invoke-GitLines $Root @('ls-files', '--', 'deliverables', 'evidence/course-v0.1'))) {
        if (-not (Test-FrozenTargets $relative)) { continue }
        $candidate = Join-Path $Root $relative
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { throw "phase8_frozen_file_missing:$relative" }
        if ($relative -match '(?i)\.(png|pptx|mp4)$') {
            $baselineHash = Get-GitFileSha256 -Root $Root -Commit $commit -RelativePath $relative
            $actualHash = (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($actualHash -cne $baselineHash) { throw "phase8_frozen_hash_mismatch:$relative" }
        }
    }
}

function Get-Phase8EvidenceFiles {
    param([Parameter(Mandatory)][string]$Root)
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { return @() }
    return @(Get-ChildItem -LiteralPath $Root -Recurse -File -Force)
}

function Assert-Phase8ProjectionSafety {
    param([Parameter(Mandatory)][string]$Root)
    # The projection must not contain Authorization, raw_remote IDs/bodies,
    # provider bodies, approval material, keys, or personal paths. The formal
    # checksums.sha256 file is treated as text and is scanned as well.
    $forbidden = '(?i)(authorization\s*[:=]|bearer\s+[a-z0-9._-]{8,}|api[_-]?key\s*[:=]|approval[_-]?(token|signature)|provider[_-]?(body|response)|[a-z]:[\\/]+users[\\/]|/users/|/home/|raw[_-]?remote|remote[_-]?(id|body)|dataset[_-]?id\s*[:=]|document[_-]?id\s*[:=])'
    foreach ($file in Get-Phase8EvidenceFiles $Root) {
        if ($file.Extension -match '(?i)\.(png|mp3)$') { continue }
        if ($file.Extension -ieq '.zip') {
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            $archive = [IO.Compression.ZipFile]::OpenRead($file.FullName)
            try {
                foreach ($entry in $archive.Entries) {
                    if ($entry.FullName -match '(?i)\.(png|mp3)$') { continue }
                    if ($entry.Length -gt 4MB) { throw "phase8_zip_member_too_large:$($entry.FullName)" }
                    $reader = [IO.StreamReader]::new($entry.Open(), [Text.Encoding]::UTF8, $true)
                    try { $content = $reader.ReadToEnd() } finally { $reader.Dispose() }
                    if ($content -match $forbidden) { throw "phase8_zip_projection_safety_failed:$($entry.FullName)" }
                }
            } finally { $archive.Dispose() }
            continue
        }
        $content = [IO.File]::ReadAllText($file.FullName, [Text.Encoding]::UTF8)
        if ($content -match $forbidden) { throw "phase8_projection_safety_failed:$($file.Name)" }
    }
}

try {
    $root = (Resolve-Path -LiteralPath $RepositoryRoot -ErrorAction Stop).Path
    $evidence = [IO.Path]::GetFullPath((Join-Path $root $EvidenceRoot))
    Assert-FrozenTargets -Root $root -Baseline $BaselineCommit
    Assert-Phase8ProjectionSafety -Root $evidence
    Write-Host 'phase8_security_scope_passed'
    exit 0
} catch {
    [Console]::Error.WriteLine([string]$_.Exception.Message)
    exit 1
}
