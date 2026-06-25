param(
    [string]$Version = "0.2.1-alpha",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
if (-not $OutputDir) {
    $OutputDir = Join-Path $Root "dist"
}

$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
$PackageName = "legends-yt-dlp-slayer-$Version"
$ZipPath = Join-Path $OutputDir "$PackageName.zip"
$HashPath = "$ZipPath.sha256"
$StageRoot = Join-Path ([System.IO.Path]::GetTempPath()) "$PackageName-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
$Stage = Join-Path $StageRoot $PackageName
$PackageExcludes = @(
    ".env",
    ".local/*",
    "assets/banner-concepts/*",
    "batches/*",
    "dist/*",
    "downloads/*",
    "reports/*",
    "rights-evidence/*",
    "work/*",
    "*.cookie",
    "*.cookies",
    "*.mp4",
    "*.mov",
    "*.mkv",
    "*.webm",
    "*.mp3",
    "*.wav"
)

function Assert-InsidePath {
    param(
        [string]$Path,
        [string]$Parent
    )
    $ResolvedPath = [System.IO.Path]::GetFullPath($Path)
    $ResolvedParent = [System.IO.Path]::GetFullPath($Parent)
    if (-not $ResolvedPath.StartsWith($ResolvedParent, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing path outside expected parent: $ResolvedPath"
    }
}

function Test-PackageExcluded {
    param([string]$Path)
    $Normalized = $Path -replace "\\", "/"
    foreach ($Pattern in $PackageExcludes) {
        if ($Normalized -like $Pattern) {
            return $true
        }
    }
    return $false
}

try {
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    New-Item -ItemType Directory -Force -Path $Stage | Out-Null

    Push-Location $Root
    try {
        $Files = git ls-files --cached
        if (-not $Files) {
            throw "No packageable files found"
        }

        foreach ($File in $Files) {
            if (Test-PackageExcluded -Path $File) {
                continue
            }
            $Source = Join-Path $Root $File
            if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
                continue
            }
            $Target = Join-Path $Stage $File
            $TargetDir = Split-Path -Parent $Target
            New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
            Copy-Item -LiteralPath $Source -Destination $Target -Force
        }

        $Commit = git rev-parse --short HEAD
        $Manifest = @(
            "Package: $PackageName",
            "Version: $Version",
            "Commit: $Commit",
            "Created: $(Get-Date -Format o)",
            "",
            "This alpha package contains tracked source, docs, scripts, tests, skill files, and legal/community files.",
            "It intentionally excludes untracked local experiments, local secrets, .local binaries, batches, reports, downloads, caches, cookies, and git metadata.",
            "",
            "Install check:",
            "powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp install",
            "powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --production"
        )
        Set-Content -LiteralPath (Join-Path $Stage "PACKAGE-MANIFEST.txt") -Value $Manifest -Encoding UTF8

        if (Test-Path -LiteralPath $ZipPath) {
            Remove-Item -LiteralPath $ZipPath -Force
        }
        if (Test-Path -LiteralPath $HashPath) {
            Remove-Item -LiteralPath $HashPath -Force
        }

        Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $ZipPath -CompressionLevel Optimal
        $Hash = Get-FileHash -Algorithm SHA256 -LiteralPath $ZipPath
        Set-Content -LiteralPath $HashPath -Value "$($Hash.Hash.ToLower())  $(Split-Path -Leaf $ZipPath)" -Encoding ASCII

        Write-Output "Package: $ZipPath"
        Write-Output "SHA256: $HashPath"
    }
    finally {
        Pop-Location
    }
}
finally {
    if (Test-Path -LiteralPath $StageRoot) {
        Assert-InsidePath -Path $StageRoot -Parent ([System.IO.Path]::GetTempPath())
        Remove-Item -LiteralPath $StageRoot -Recurse -Force
    }
}
