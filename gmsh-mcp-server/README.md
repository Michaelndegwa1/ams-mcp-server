# Gmsh MCP Server

Headless mesh generation for Claude — same pattern as `ams-mcp-server` for Code_Aster.

```text
Claude (connector URL)
    -> Cloudflare tunnel (HTTPS)
    -> python dev_server.py on :8767
    -> build_cylinder / build_revolved_solid / mesh_and_export
    -> .med file -> Code_Aster MCP structural_analysis
```

## Quick start

```powershell
cd gmsh-mcp-server
pip install -r requirements.txt
copy .env.example .env

python -m src.check_environment
python run_local_test.py
```

## Run MCP server

### Terminal 1 — MCP server

```powershell
.\scripts\start_mcp.ps1
```

### Terminal 2 — Cloudflare tunnel (for claude.ai)

```powershell
.\scripts\start_tunnel.ps1
```

Add connector URL: `https://YOUR-TUNNEL-HOST/mcp`

Default port **8767** (Code_Aster MCP uses 8766).

## Tools exposed to Claude

| Tool | Purpose |
|---|---|
| `build_cylinder` | Quick rod/beam/pin geometry + mesh |
| `build_extrusion` | Extrude a 2D profile along +Z |
| `build_revolved_solid` | Revolve XZ profile (pistons, nozzles) |
| `mesh_and_export` | Mesh an existing .geo/.step file |
| `pipeline_status` | Health check |

## End-to-end pipeline (two connectors in Claude)

1. **Gmsh connector** — build and mesh:
   > Create a cylinder r=5mm, h=100mm, mesh size 3mm, export to meshes/piston.med with physical groups FACE_INF and FACE_SUP on the end caps.

2. **Code_Aster connector** — solve:
   > Run structural_analysis on `/data/ams-mcp-server/../gmsh-mcp-server/meshes/piston.med` with steel, fix FACE_INF, 500N on FACE_SUP in FZ.

Adjust paths to match your Docker bind mount (`/data/...`).

## Physical groups

Code_Aster needs named surface groups for BCs and loads. Pass `physical_groups` when meshing:

```json
{
  "volumes": {"SOLID": [1]},
  "surfaces": {"FACE_INF": [1], "FACE_SUP": [2]}
}
```

Use the `entities` field in tool responses to discover Gmsh entity tags after building geometry.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `MCP_PORT` | 8767 | HTTP port |
| `MESH_DIR` | ./meshes | Default mesh output directory |
| `OUTPUT_DIR` | ./outputs | Scratch/output directory |
| `MCP_TRANSPORT` | streamable-http | Use `stdio` for local Claude spawn |

## Build order (full pipeline suite)

1. **gmsh-mcp-server** (this project) — meshing
2. **ams-mcp-server** — Code_Aster solver (done)
3. **paraview-mcp-server** (future) — stress contour PNGs
4. **calculix-mcp-server** (future) — alternate solver
