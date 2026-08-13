$root = Split-Path -Parent $PSScriptRoot
$port = (Get-Content "$root\.env" | Where-Object { $_ -match '^MCP_PORT=' }) -replace 'MCP_PORT=',''
if (-not $port) { $port = '8770' }
& "$((Split-Path -Parent $root))\ams-mcp-server\cloudflared.exe" tunnel --url "http://localhost:$port"
