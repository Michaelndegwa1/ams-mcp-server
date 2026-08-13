param(
    [switch]$Production,
    [switch]$SkipEnvCheck
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Get-DotEnvValue {
    param([string]$Key, [string]$Default)
    $envFile = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path $envFile)) { return $Default }
    foreach ($line in Get-Content $envFile) {
        if ($line -match "^\s*$Key\s*=\s*(.+)\s*$") {
            return $Matches[1].Trim()
        }
    }
    return $Default
}

$port = if ($env:MCP_PORT) { [int]$env:MCP_PORT } else { [int](Get-DotEnvValue "MCP_PORT" "8769") }

Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
    $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
    if ($p -and $p.ProcessName -eq "python") { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
}

if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    Copy-Item (Join-Path $ProjectRoot ".env.example") (Join-Path $ProjectRoot ".env")
}

$env:MCP_PORT = "$port"
Write-Host "=== CalculiX MCP port $port ===" -ForegroundColor Cyan

python -m src.check_environment
if (-not $SkipEnvCheck -and $LASTEXITCODE -ne 0) { exit 1 }

if ($Production) { python -m src.server } else { python dev_server.py }
