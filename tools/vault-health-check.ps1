$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Required = @(
    "CODEX.md",
    "README.md",
    "wiki/index.md",
    "wiki/log.md",
    "wiki/hot.md",
    "wiki/Project Overview.md",
    "wiki/meta/Roadmap.md"
)

$Failures = New-Object System.Collections.Generic.List[string]

foreach ($rel in $Required) {
    $path = Join-Path $Root $rel
    if (-not (Test-Path -LiteralPath $path)) {
        $Failures.Add("Missing required file: $rel")
    }
}

$IgnoredMarkdownDirs = @(
    "\\.git\\",
    "\\.local\\",
    "\\batches\\",
    "\\reports\\",
    "\\downloads\\",
    "\\dist\\",
    "\\cache\\",
    "\\secrets\\",
    "\\cookies\\"
)

$MarkdownFiles = Get-ChildItem -Path $Root -Recurse -Filter *.md -File |
    Where-Object {
        $fullName = $_.FullName
        -not ($IgnoredMarkdownDirs | Where-Object { $fullName -match $_ })
    }

$NameMap = @{}
foreach ($file in $MarkdownFiles) {
    $name = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
    if (-not $NameMap.ContainsKey($name)) {
        $NameMap[$name] = New-Object System.Collections.Generic.List[string]
    }
    $NameMap[$name].Add($file.FullName)
}

$LinkPattern = [regex]"\[\[([^\]|#]+)"
$DeadLinks = New-Object System.Collections.Generic.List[string]

foreach ($file in $MarkdownFiles) {
    $text = Get-Content -LiteralPath $file.FullName -Raw
    foreach ($match in $LinkPattern.Matches($text)) {
        $target = $match.Groups[1].Value.Trim()
        if ([string]::IsNullOrWhiteSpace($target)) { continue }
        if ($target -match "^[a-zA-Z]+://") { continue }
        if (-not $NameMap.ContainsKey($target)) {
            $relFile = $file.FullName
            if ($relFile.StartsWith($Root)) {
                $relFile = $relFile.Substring($Root.Length).TrimStart("\", "/")
            }
            $DeadLinks.Add("$relFile -> [[$target]]")
        }
    }
}

if ($DeadLinks.Count -gt 0) {
    foreach ($link in $DeadLinks) {
        $Failures.Add("Dead wikilink: $link")
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $Root ".git"))) {
    $Failures.Add("Git is not initialized")
}

if ($Failures.Count -gt 0) {
    Write-Host "Vault health check failed:" -ForegroundColor Red
    foreach ($failure in $Failures) {
        Write-Host " - $failure"
    }
    exit 1
}

Write-Host "Vault health check passed." -ForegroundColor Green
Write-Host "Markdown files scanned: $($MarkdownFiles.Count)"
$AllMarkdownText = ($MarkdownFiles | ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw }) -join "`n"
Write-Host "Wikilinks checked: $($LinkPattern.Matches($AllMarkdownText).Count)"
