# start_mcp.ps1 — start MCP server with auto-reload (recommended for development)
# Usage:  .\scripts\start_mcp.ps1
#         .\scripts\start_mcp.ps1 -Production   # no auto-reload, single process

param(
    [switch]$Production
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$port = if ($env:MCP_PORT) { [int]$env:MCP_PORT } else { 8765 }

function Stop-PortListener {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        $procId = $conn.OwningProcess
        if ($procId -and $procId -ne 0) {
            Write-Host "Stopping process $procId listening on port $Port..."
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "=== AMS Code_Aster MCP ===" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"
Write-Host "Port:    $Port"
Write-Host ""

Stop-PortListener -Port $port
Start-Sleep -Milliseconds 500

python -m src.check_environment
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nEnvironment check failed. Fix .env / Docker before starting." -ForegroundColor Red
    exit 1
}

if ($Production) {
    Write-Host "`nStarting production server (no auto-reload)..." -ForegroundColor Yellow
    python -m src.server
} else {
    Write-Host "`nStarting dev server (auto-reload on src/ and .env changes)..." -ForegroundColor Green
    python dev_server.py
}
