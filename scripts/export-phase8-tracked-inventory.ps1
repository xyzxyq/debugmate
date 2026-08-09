param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryRoot,
    [Parameter(Mandatory = $true)]
    [string[]]$CandidatePath,
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $RepositoryRoot -ErrorAction Stop).Path
$output = [System.IO.Path]::GetFullPath($OutputPath)
$entries = [System.Collections.Generic.List[object]]::new()
$seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)

foreach ($candidateValue in $CandidatePath) {
    $candidate = (Resolve-Path -LiteralPath $candidateValue -ErrorAction Stop).Path
    $item = Get-Item -LiteralPath $candidate -Force -ErrorAction Stop
    if ($item.PSIsContainer) {
        throw "Candidate paths must be regular files"
    }
    if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw "Candidate paths must not be links or reparse points"
    }
    $relative = [System.IO.Path]::GetRelativePath($root, $candidate).Replace('\', '/')
    if ($relative -eq '..' -or $relative.StartsWith('../', [System.StringComparison]::Ordinal)) {
        throw "Candidate paths must remain below RepositoryRoot"
    }
    if (-not $seen.Add($relative)) {
        throw "Duplicate candidate path: $relative"
    }

    # Native QA boundary: git ls-files and git check-ignore never run in product Python.
    & git -C $root ls-files --error-unmatch -- $relative *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Candidate path is not Git tracked: $relative"
    }
    & git -C $root check-ignore --quiet -- $relative
    if ($LASTEXITCODE -eq 0) {
        throw "Candidate path is ignored: $relative"
    }
    if ($LASTEXITCODE -ne 1) {
        throw "Unable to verify ignore state: $relative"
    }

    $entries.Add([ordered]@{
        'path' = $relative
        'sha256' = (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash.ToLowerInvariant()
    })
}

$sorted = @($entries | Sort-Object -Property @{ Expression = { $_.path }; Ascending = $true })
$json = ConvertTo-Json -InputObject $sorted -Depth 3
$parent = Split-Path -Parent $output
if ($parent) {
    [System.IO.Directory]::CreateDirectory($parent) | Out-Null
}
[System.IO.File]::WriteAllText($output, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
