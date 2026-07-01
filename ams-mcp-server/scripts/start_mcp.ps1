# start_mcp.ps1 — start MCP server with auto-reload (recommended for development)
# Usage:  .\scripts\start_mcp.ps1
#         .\scripts\start_mcp.ps1 -Production   # no auto-reload, single process

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

$port = if ($env:MCP_PORT) { [int]$env:MCP_PORT } else { [int](Get-DotEnvValue "MCP_PORT" "8766") }

function Stop-PythonOnPort {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        $procId = $conn.OwningProcess
        if (-not $procId -or $procId -eq 0) { continue }
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -eq "python") {
            Write-Host "Stopping python (PID $procId) on port $Port..."
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        } elseif ($proc) {
            Write-Host "Port $Port in use by $($proc.ProcessName) (PID $procId) - leaving it alone." -ForegroundColor Yellow
        }
    }
}

Write-Host "=== AMS Code_Aster MCP ===" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"
Write-Host "Port:    $port"
if ($port -eq 8765) {
    Write-Host "NOTE: Docker code-aster-container often maps 8765. Set MCP_PORT=8766 in .env if bind fails." -ForegroundColor Yellow
}
Write-Host ""

Stop-PythonOnPort -Port $port
Start-Sleep -Milliseconds 500

$env:MCP_PORT = "$port"

python -m src.check_environment
if (-not $SkipEnvCheck -and $LASTEXITCODE -ne 0) {
    Write-Host "`nEnvironment check failed. Fix .env / Docker, or use -SkipEnvCheck to start MCP anyway." -ForegroundColor Red
    exit 1
}

if ($Production) {
    Write-Host "`nStarting production server (no auto-reload)..." -ForegroundColor Yellow
    python -m src.server
} else {
    Write-Host "`nStarting dev server (auto-reload on src/ and .env changes)..." -ForegroundColor Green
    python dev_server.py
}
