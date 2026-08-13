# FEA Pipeline — MCP Server Suite

Natural-language structural analysis: one MCP server per tool, Claude orchestrates across connectors.

## Servers & ports

| Server | Port | Role |
|---|---|---|
| `ams-mcp-server` (Code_Aster) | 8766 | Primary solver |
| `gmsh-mcp-server` | 8767 | Mesh (.med / .inp) |
| `paraview-mcp-server` | 8768 | Result PNG |
| `calculix-mcp-server` | 8769 | Cross-check solver |
| `freecad-mcp-server` | 8770 | Parametric CAD → STEP |
| `salome-mcp-server` | 8771 | GEOM/SMESH → MED |

## Typical workflow

```text
FreeCAD → STEP → Salome or Gmsh → mesh → Code_Aster/CalculiX → ParaView PNG
```

## Start all (6 terminals)

```powershell
# Each project folder:
.\scripts\start_mcp.ps1
# Plus one tunnel per connector you expose to Claude
.\scripts\start_tunnel.ps1
```

## Docker containers

| Container | Image |
|---|---|
| code-aster-container | simvia/code_aster:stable |
| calculix-container | ale10tech/calculix-core:ccx2.23-ubuntu24.04 |
| freecad-container | ale10tech/freecad:ubuntu24.04 |
| salome-container | salomeplatform/salome:9.12.0 |

Mount: `-v C:\Users\ADMIN\Downloads\ams-mcp-server:/data`
