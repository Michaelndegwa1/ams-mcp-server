# CalculiX MCP Server

Second FEA solver MCP — same tool API as Code_Aster for cross-checking results.

```text
Gmsh (8767)      →  mesh.inp
CalculiX (8769)  →  ccx job → .frd
ParaView (8768)  →  PNG (optional; FRD also supported)
```

## One-time: CalculiX Docker container

```powershell
docker pull ale10tech/calculix-core:ccx2.23-ubuntu24.04

docker run -d --name calculix-container `
  -v C:\Users\ADMIN\Downloads\ams-mcp-server:/data `
  ale10tech/calculix-core:ccx2.23-ubuntu24.04 sleep infinity
```

`.env` defaults match this mount (`/data`).

## Quick start

```powershell
cd calculix-mcp-server
pip install -r requirements.txt
copy .env.example .env

python scripts/generate_example_mesh.py   # needs gmsh — exports examples/test_beam.inp
python -m src.check_environment
python run_local_test.py
```

## Run MCP

```powershell
.\scripts\start_mcp.ps1
.\scripts\start_tunnel.ps1
```

Connector URL: `https://YOUR-TUNNEL/mcp` — port **8769**

## Mesh workflow with Gmsh MCP

Export `.inp` from Gmsh (not `.med`):

> Build cylinder r=5, h=100, mesh 3mm, export to `calculix-mcp-server/examples/piston.inp`

Then in CalculiX connector:

> Run structural_analysis on `/data/calculix-mcp-server/examples/piston.inp` — steel, fix FACE_INF, 500N on FACE_SUP.

## Tools

| Tool | Purpose |
|---|---|
| `structural_analysis` | Linear static solve via ccx |
| `pipeline_status` | Health + example paths |

## Ports

| Server | Port |
|---|---|
| Code_Aster | 8766 |
| Gmsh | 8767 |
| ParaView | 8768 |
| CalculiX | 8769 |
