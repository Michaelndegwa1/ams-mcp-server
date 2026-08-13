"""Salome MCP FastMCP server — GEOM + SMESH."""
from __future__ import annotations

import json
import sys
from mcp.server.fastmcp import FastMCP
from src import config
from src.build_info import code_fingerprint
from src import salome_tools
from src.runner import uses_docker

config.validate_config()
mcp = FastMCP("salome-mesh", host=config.MCP_HOST, port=config.MCP_PORT)


@mcp.tool()
def build_box(dx: float, dy: float, dz: float, output_step: str | None = None) -> str:
    """Create a box in Salome GEOM and export STEP (mm)."""
    return json.dumps(salome_tools.build_box(dx, dy, dz, output_step))


@mcp.tool()
def build_cylinder(radius: float, height: float, output_step: str | None = None) -> str:
    """Create a cylinder in Salome GEOM and export STEP."""
    return json.dumps(salome_tools.build_cylinder(radius, height, output_step))


@mcp.tool()
def mesh_box_tetra(
    dx: float, dy: float, dz: float, mesh_size: float, output_med: str | None = None
) -> str:
    """Build box geometry and tetrahedral mesh, export MED for Code_Aster."""
    return json.dumps(salome_tools.mesh_box_tetra(dx, dy, dz, mesh_size, output_med))


@mcp.tool()
def mesh_cylinder_tetra(
    radius: float, height: float, mesh_size: float, output_med: str | None = None
) -> str:
    """Cylinder + tet mesh → MED."""
    return json.dumps(salome_tools.mesh_cylinder_tetra(radius, height, mesh_size, output_med))


@mcp.tool()
def mesh_step_file(step_path: str, mesh_size: float, output_med: str | None = None) -> str:
    """Import STEP (e.g. from FreeCAD MCP) and export tetrahedral MED mesh."""
    return json.dumps(salome_tools.mesh_step_file(step_path, mesh_size, output_med))


@mcp.tool()
def pipeline_status() -> str:
    """Health check."""
    return json.dumps({
        "status": "ok",
        "code_fingerprint": code_fingerprint(),
        "mcp_port": config.MCP_PORT,
        "docker_execution": uses_docker(),
        "docker_container": config.DOCKER_CONTAINER_NAME,
        "mesh_dir": str(config.MESH_DIR.resolve()),
        "tools": [
            "build_box", "build_cylinder", "mesh_box_tetra",
            "mesh_cylinder_tetra", "mesh_step_file", "pipeline_status",
        ],
    })


if __name__ == "__main__":
    mcp.run(transport="streamable-http" if config.MCP_TRANSPORT != "stdio" else None) or mcp.run()
