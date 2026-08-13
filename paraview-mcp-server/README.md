# ParaView MCP Server

Headless FEA visualization for Claude — closes the "no pictures" gap after Code_Aster solves.

```text
Code_Aster MCP  ->  .rmed
ParaView MCP    ->  stress/displacement PNG
```

Works **without ParaView installed** via matplotlib fallback. Set `PVPYTHON_PATH` for full ParaView renders.

## Quick start

```powershell
cd paraview-mcp-server
pip install -r requirements.txt
copy .env.example .env

python -m src.check_environment
python run_local_test.py --generate    # runs Code_Aster, then renders PNG
```

## Run MCP (port 8768)

```powershell
.\scripts\start_mcp.ps1
.\scripts\start_tunnel.ps1             # second terminal for claude.ai
```

Connector URL: `https://YOUR-TUNNEL-HOST/mcp`

## Tools

| Tool | Purpose |
|---|---|
| `render_stress_contour` | Von Mises stress PNG from `.rmed` |
| `render_displacement_contour` | Displacement magnitude PNG |
| `inspect_result_file` | Probe MED dataset paths |
| `pipeline_status` | Health + backend info |

## Full pipeline in Claude (3 connectors)

1. **Gmsh** (8767) — build mesh
2. **Code_Aster** (8766) — solve → `.rmed`
3. **ParaView** (8768) — render PNG

Example:

> Render a stress contour from `/data/ams-mcp-server/outputs/run_xxx.rmed` and tell me the max stress.

## ParaView install (optional, better renders)

1. Install [ParaView](https://www.paraview.org/download/)
2. Set in `.env`:
   ```env
   PVPYTHON_PATH=C:\Program Files\ParaView 5.12.0\bin\pvpython.exe
   RENDER_BACKEND=paraview
   ```

## Ports

| Server | Port |
|---|---|
| Code_Aster | 8766 |
| Gmsh | 8767 |
| ParaView | 8768 |
