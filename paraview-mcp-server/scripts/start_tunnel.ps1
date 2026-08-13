param([switch]$Named)
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

$Port = if ($env:MCP_PORT) { $env:MCP_PORT } else { Get-DotEnvValue "MCP_PORT" "8768" }
$parent = Split-Path -Parent $ProjectRoot
$Cloudflared = if (Test-Path "$parent\ams-mcp-server\cloudflared.exe") {
    "$parent\ams-mcp-server\cloudflared.exe"
} else { "cloudflared" }

Write-Host "Tunnel -> http://localhost:$Port" -ForegroundColor Yellow
& $Cloudflared tunnel --url "http://localhost:$Port"
