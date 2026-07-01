# start_tunnel.ps1 — Cloudflare tunnel to local MCP server
#
# Quick mode (URL changes every restart — demos only):
#   .\scripts\start_tunnel.ps1
#
# Stable mode (fixed hostname — requires one-time Cloudflare setup):
#   Copy cloudflared\config.example.yml -> cloudflared\config.yml, edit it,
#   then:  .\scripts\start_tunnel.ps1 -Named

param(
    [switch]$Named
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Port = if ($env:MCP_PORT) { $env:MCP_PORT } else { "8765" }

$Cloudflared = $env:CLOUDFLARED_PATH
if (-not $Cloudflared) {
    if (Test-Path "$ProjectRoot\cloudflared.exe") {
        $Cloudflared = "$ProjectRoot\cloudflared.exe"
    } elseif (Test-Path "$env:USERPROFILE\cloudflared.exe") {
        $Cloudflared = "$env:USERPROFILE\cloudflared.exe"
    } else {
        $Cloudflared = "cloudflared"
    }
}

if ($Named) {
    $Config = "$ProjectRoot\cloudflared\config.yml"
    if (-not (Test-Path $Config)) {
        Write-Host "Missing $Config" -ForegroundColor Red
        Write-Host "Copy cloudflared\config.example.yml -> cloudflared\config.yml and follow README."
        exit 1
    }
    Write-Host "Starting named tunnel from $Config" -ForegroundColor Cyan
    & $Cloudflared tunnel --config $Config run
} else {
    Write-Host "Starting quick tunnel -> http://localhost:$Port" -ForegroundColor Yellow
    Write-Host "WARNING: trycloudflare.com URL changes every restart. Update Claude connector each time."
    Write-Host "For a permanent URL, use: .\scripts\start_tunnel.ps1 -Named`n"
    & $Cloudflared tunnel --url "http://localhost:$Port"
}
