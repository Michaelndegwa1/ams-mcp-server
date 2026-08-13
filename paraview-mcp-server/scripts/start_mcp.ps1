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

$port = if ($env:MCP_PORT) { [int]$env:MCP_PORT } else { [int](Get-DotEnvValue "MCP_PORT" "8768") }

function Stop-PythonOnPort {
    param([int]$Port)
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        $proc = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -eq "python") {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "=== ParaView MCP ===" -ForegroundColor Cyan
Write-Host "Port: $port`n"
Stop-PythonOnPort -Port $port
Start-Sleep -Milliseconds 400
$env:MCP_PORT = "$port"

if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    Copy-Item (Join-Path $ProjectRoot ".env.example") (Join-Path $ProjectRoot ".env")
}

python -m src.check_environment
if (-not $SkipEnvCheck -and $LASTEXITCODE -ne 0) { exit 1 }

if ($Production) { python -m src.server } else { python dev_server.py }
