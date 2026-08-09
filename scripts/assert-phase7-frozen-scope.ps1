[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$BaselinePath,
    [string]$RepositoryRoot = "."
)

$ErrorActionPreference = "Stop"

function Test-FrozenPath {
    param([Parameter(Mandatory)][string]$Path)
    $normalized = $Path.Replace("\", "/")
    return $normalized -match "^(deliverables/|evidence/ui/phase4/|evidence/course-v0\.1/)" -or
        $normalized -match "\.(pptx|mp4|srt)$" -or
        $normalized -match "^\.planning/phases/(08|09|10)(?:-|/)"
}

function Invoke-GitLines {
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string[]]$Arguments
    )
    $output = @(& git -C $Root -c core.quotepath=false -c core.safecrlf=false @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed: $($output -join [Environment]::NewLine)"
    }
    return @($output | ForEach-Object { [string]$_ })
}

function Get-TrackedFrozenFiles {
    param([Parameter(Mandatory)][string]$Root)
    $tracked = Invoke-GitLines -Root $Root -Arguments @("ls-files")
    return @(
        $tracked |
            ForEach-Object { $_.Replace("\", "/") } |
            Where-Object { Test-FrozenPath -Path $_ } |
            Sort-Object -Unique
    )
}

try {
    $root = (Resolve-Path -LiteralPath $RepositoryRoot -ErrorAction Stop).Path
    $baselineFile = (Resolve-Path -LiteralPath $BaselinePath -ErrorAction Stop).Path
    $gitRoot = (Invoke-GitLines -Root $root -Arguments @("rev-parse", "--show-toplevel") | Select-Object -First 1)
    $gitRoot = (Resolve-Path -LiteralPath $gitRoot -ErrorAction Stop).Path
    if ($gitRoot -cne $root) { throw "RepositoryRoot must be the Git repository root." }

    $baseline = Get-Content -LiteralPath $baselineFile -Raw -Encoding utf8 | ConvertFrom-Json
    if ($null -eq $baseline -or $baseline -is [System.Array]) { throw "Baseline JSON must be one object." }

    $expectedTopKeys = @("schema_version", "baseline_commit", "captured_at_utc", "frozen_files")
    $actualTopKeys = @($baseline.PSObject.Properties.Name)
    if (@(Compare-Object -ReferenceObject $expectedTopKeys -DifferenceObject $actualTopKeys).Count -ne 0) {
        throw "Baseline JSON must contain exactly: $($expectedTopKeys -join ', ')."
    }
    if ($baseline.schema_version -isnot [int] -or $baseline.schema_version -ne 1) {
        throw "schema_version must be integer 1."
    }
    if ([string]$baseline.baseline_commit -cnotmatch "^[0-9a-f]{40}$") {
        throw "baseline_commit must be 40 lowercase hexadecimal characters."
    }
    if ([string]$baseline.captured_at_utc -cnotmatch "^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$") {
        throw "captured_at_utc must be an ISO-8601 UTC-Z timestamp."
    }
    $parsedUtc = [DateTimeOffset]::MinValue
    if (-not [DateTimeOffset]::TryParse(
            [string]$baseline.captured_at_utc,
            [Globalization.CultureInfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::AssumeUniversal -bor [Globalization.DateTimeStyles]::AdjustToUniversal,
            [ref]$parsedUtc
        ) -or $parsedUtc.Offset -ne [TimeSpan]::Zero) {
        throw "captured_at_utc is not a valid UTC timestamp."
    }
    if ($null -eq $baseline.frozen_files -or $baseline.frozen_files -is [System.Array]) {
        throw "frozen_files must be an object."
    }

    [void](Invoke-GitLines -Root $root -Arguments @("cat-file", "-e", "$($baseline.baseline_commit)^{commit}"))
    $trackedFrozen = @(Get-TrackedFrozenFiles -Root $root)
    $storedPaths = @($baseline.frozen_files.PSObject.Properties.Name | Sort-Object -Unique)
    if (@(Compare-Object -ReferenceObject $trackedFrozen -DifferenceObject $storedPaths -CaseSensitive).Count -ne 0) {
        throw "frozen_files keys do not exactly match the complete tracked frozen target set."
    }

    foreach ($relativePath in $trackedFrozen) {
        $storedHash = [string]$baseline.frozen_files.PSObject.Properties[$relativePath].Value
        if ($storedHash -cnotmatch "^[0-9a-f]{64}$") {
            throw "Stored SHA-256 is invalid for $relativePath."
        }
        $candidate = Join-Path $root ($relativePath.Replace("/", [IO.Path]::DirectorySeparatorChar))
        $resolved = (Resolve-Path -LiteralPath $candidate -ErrorAction Stop).Path
        $relativeNative = $relativePath.Replace("/", [IO.Path]::DirectorySeparatorChar)
        $expectedAbsolute = [IO.Path]::GetFullPath((Join-Path $root $relativeNative))
        if ($resolved -cne $expectedAbsolute) { throw "Frozen target resolves outside its lexical path: $relativePath." }
        $currentHash = (Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($currentHash -cnotmatch "^[0-9a-f]{64}$") { throw "Current SHA-256 is invalid for $relativePath." }
        if ($currentHash -cne $storedHash) { throw "Frozen target hash mismatch: $relativePath." }
    }

    $relativeToBaseline = Invoke-GitLines -Root $root -Arguments @(
        "diff", "--name-only", [string]$baseline.baseline_commit, "--"
    )
    $dirtyTracked = @($relativeToBaseline | Where-Object { Test-FrozenPath -Path $_ })
    if ($dirtyTracked.Count -gt 0) {
        throw "Frozen targets differ from baseline_commit: $($dirtyTracked -join ', ')."
    }

    $porcelain = Invoke-GitLines -Root $root -Arguments @("status", "--porcelain=v1", "--untracked-files=all")
    $dirtyWorking = [System.Collections.Generic.List[string]]::new()
    foreach ($line in $porcelain) {
        if ($line.Length -lt 4) { continue }
        $path = $line.Substring(3).Trim('"')
        if ($path -like "* -> *") { $path = ($path -split " -> ")[-1].Trim('"') }
        if (Test-FrozenPath -Path $path) { [void]$dirtyWorking.Add($path) }
    }
    if ($dirtyWorking.Count -gt 0) {
        throw "Frozen targets are dirty in the working tree: $($dirtyWorking -join ', ')."
    }

    Write-Host "Phase 07 frozen scope verified: $($trackedFrozen.Count) tracked targets match the captured baseline."
    exit 0
}
catch {
    [Console]::Error.WriteLine([string]$_.Exception.Message)
    exit 1
}
