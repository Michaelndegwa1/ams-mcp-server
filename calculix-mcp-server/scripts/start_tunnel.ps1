$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Port = (Get-Content (Join-Path $ProjectRoot ".env") | Where-Object { $_ -match "^MCP_PORT=" }) -replace "MCP_PORT=", ""
if (-not $Port) { $Port = "8769" }
$cf = "$((Split-Path -Parent $ProjectRoot))\ams-mcp-server\cloudflared.exe"
& $cf tunnel --url "http://localhost:$Port"
