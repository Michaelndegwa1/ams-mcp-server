param([switch]$Production)
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
python -m src.check_environment
if ($LASTEXITCODE -ne 0) { exit 1 }
if ($Production) { python -m src.server } else { python dev_server.py }
