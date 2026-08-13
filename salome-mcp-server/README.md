# Salome MCP Server

Headless **GEOM + SMESH** via `salome -t` — alternative to Gmsh for CAD import and tetrahedral MED export.

## Docker setup (required for most users)

Salome is large (~8–12 GB). Use official or community images:

```powershell
# Example — adjust tag to available image on your registry
docker pull salomeplatform/salome:9.12.0

docker run -d --name salome-container `
  -v C:\Users\ADMIN\Downloads\ams-mcp-server:/data `
  salomeplatform/salome:9.12.0 sleep infinity
```

If the image uses a different entrypoint, set `SALOME_CMD` in `.env`.

## Quick start

```powershell
cd salome-mcp-server
pip install -r requirements.txt
copy .env.example .env
python -m src.check_environment
.\scripts\start_mcp.ps1
```

Port **8771**

## Tools

| Tool | Purpose |
|---|---|
| `build_box` | GEOM box → STEP |
| `build_cylinder` | GEOM cylinder → STEP |
| `mesh_box_tetra` | Box + tet mesh → MED |
| `mesh_cylinder_tetra` | Cylinder + tet mesh → MED |
| `mesh_step_file` | Import FreeCAD STEP → MED |
| `pipeline_status` | Health check |

## Full pipeline

```text
FreeCAD (8770)  → STEP
Salome (8771)   → MED     ← alternative to Gmsh (8767)
Code_Aster (8766) / CalculiX (8769)
ParaView (8768)
```

## Claude example

> Import `/data/freecad-mcp-server/models/piston.step` in Salome, mesh with size 3mm, export MED to meshes/piston.med

## Note

Salome `-t` batch mode can leave orphan processes on Linux; in Docker one container per pipeline session is recommended.
