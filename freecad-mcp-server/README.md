# FreeCAD MCP Server

Headless parametric CAD via `FreeCADCmd` — pistons, grooves, STEP export for the mesh/solve pipeline.

## Install FreeCAD (pick one)

**Option A — Docker (recommended)**

```powershell
docker pull ale10tech/freecad:ubuntu24.04
docker run -d --name freecad-container `
  -v C:\Users\ADMIN\Downloads\ams-mcp-server:/data `
  ale10tech/freecad:ubuntu24.04 sleep infinity
```

**Option B — Native Windows**

Install from [freecad.org](https://www.freecad.org/downloads.php), then set in `.env`:

```env
FREECAD_CMD=C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe
DOCKER_CONTAINER_NAME=
```

## Quick start

```powershell
cd freecad-mcp-server
pip install -r requirements.txt
copy .env.example .env
python -m src.check_environment
.\scripts\start_mcp.ps1
```

Port **8770**

## Tools

| Tool | Purpose |
|---|---|
| `build_cylinder` | Cylinder → STEP + STL |
| `build_box` | Box → STEP |
| `build_revolved_solid` | Revolve XZ profile (piston body) |
| `add_ring_groove` | Boolean cut groove into STEP |
| `pipeline_status` | Health check |

## Pipeline

```text
FreeCAD (8770) → STEP
Gmsh (8767)    → mesh .inp from STEP
CalculiX/Code_Aster → solve
ParaView (8768) → PNG
```

## Claude example

> Use FreeCAD to build a revolved piston profile [[25,0],[25,40],[20,45],[20,60],[25,60],[25,80],[15,80],[15,0]] and export STEP to models/piston.step
