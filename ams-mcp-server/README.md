# AMS Code_Aster MCP Server

Natural-language structural analysis via Claude, backed by Code_Aster.

## Architecture

```text
Claude (connector URL)
    -> Cloudflare tunnel (HTTPS, stable hostname recommended)
    -> python dev_server.py (auto-reload) on :8765
    -> structural_analysis tool
    -> docker exec -> code-aster-container -> run_aster
```

## Quick start

```powershell
cd ams-mcp-server
pip install -r requirements.txt
copy .env.example .env
# Edit .env: CODE_ASTER_PATH, DOCKER_CONTAINER_NAME

python -m src.check_environment
python run_local_test.py examples\test_beam.med
```

## Long-running MCP + Cloudflare (recommended)

### Terminal 1 — MCP server with auto-reload

```powershell
.\scripts\start_mcp.ps1
```

Saves to `src/` or `.env` automatically restart the server. Claude always gets fresh code.

### Terminal 2 — Cloudflare tunnel

**Demo (URL changes every restart):**

```powershell
.\scripts\start_tunnel.ps1
```

Copy the `https://....trycloudflare.com` URL.

**Production (stable URL — do this once):**

1. `cloudflared tunnel login`
2. `cloudflared tunnel create ams-mcp`
3. `cloudflared tunnel route dns ams-mcp mcp.yourdomain.com`
4. Copy `cloudflared/config.example.yml` → `cloudflared/config.yml` and fill in tunnel ID
5. `.\scripts\start_tunnel.ps1 -Named`

### Claude connector

Add connector URL:

```text
https://YOUR-TUNNEL-HOST/mcp
```

### Verify you are on latest code

Ask Claude to call `pipeline_status` or check any analysis result for `code_fingerprint`.
After you save a file, the fingerprint changes when auto-reload runs.

Also check `.comm` files: 500 N should show `FZ=114.36...`, not `FZ=500.0`.

## Docker requirements

- Container `code-aster-container` (or set `DOCKER_CONTAINER_NAME` in `.env`)
- Project mounted at `/data/ams-mcp-server` inside container
- Code_Aster image: `simvia/code_aster:stable`

## Environment variables

| Variable | Purpose |
|---|---|
| `CODE_ASTER_PATH` | Path to `run_aster` inside container |
| `DOCKER_CONTAINER_NAME` | Docker container for split setup |
| `MCP_PORT` | HTTP port (default 8765) |
| `MCP_TRANSPORT` | `streamable-http` or `stdio` |

## Tools exposed to Claude

- `structural_analysis` — full FEA pipeline
- `pipeline_status` — health check + code fingerprint
