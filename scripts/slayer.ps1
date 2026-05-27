$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $Root "src"
python -m slayer_cli @args
exit $LASTEXITCODE
