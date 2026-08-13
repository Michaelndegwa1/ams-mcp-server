# start_tunnel.ps1 — Cloudflare tunnel to local Gmsh MCP server
param(
    [switch]$Named
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

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

$Port = if ($env:MCP_PORT) { $env:MCP_PORT } else { Get-DotEnvValue "MCP_PORT" "8767" }

$Cloudflared = $env:CLOUDFLARED_PATH
if (-not $Cloudflared) {
    $parent = Split-Path -Parent $ProjectRoot
    if (Test-Path "$parent\ams-mcp-server\cloudflared.exe") {
        $Cloudflared = "$parent\ams-mcp-server\cloudflared.exe"
    } elseif (Test-Path "$ProjectRoot\cloudflared.exe") {
        $Cloudflared = "$ProjectRoot\cloudflared.exe"
    } else {
        $Cloudflared = "cloudflared"
    }
}

Write-Host "Starting quick tunnel -> http://localhost:$Port" -ForegroundColor Yellow
Write-Host "Claude connector URL: https://YOUR-URL.trycloudflare.com/mcp`n"
& $Cloudflared tunnel --url "http://localhost:$Port"
