"""
server.py
FastMCP server exposing headless Gmsh geometry and meshing tools.

HTTP mode (default) — use with Cloudflare tunnel:
  python dev_server.py
  python -m src.server

Claude connector URL:
  https://YOUR-TUNNEL-HOST/mcp
"""
from __future__ import annotations

import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from src import config
from src.build_info import code_fingerprint
from src import gmsh_tools

config.validate_config()
logger = logging.getLogger("server")

logger.info(
    "Gmsh MCP starting | transport=%s | fingerprint=%s | port=%s",
    config.MCP_TRANSPORT,
    code_fingerprint(),
    config.MCP_PORT,
)

mcp = FastMCP("gmsh-meshing", host=config.MCP_HOST, port=config.MCP_PORT)


@mcp.tool()
def build_extrusion(
    profile_points: list,
    height: float,
    mesh_size: float | None = None,
    physical_groups: dict | None = None,
    output_path: str | None = None,
) -> str:
    """Extrude a closed 2D profile (XY plane) along +Z and optionally mesh/export.

    Args:
        profile_points: Closed polygon as [[x, y], ...] in mm.
        height: Extrusion distance along +Z (mm).
        mesh_size: If set, generates a 3D mesh with this characteristic length (mm).
        physical_groups: Optional dict with keys volumes/surfaces/curves/points mapping
            names to entity tag lists, e.g. {"surfaces": {"FACE_INF": [1], "FACE_SUP": [2]}}.
        output_path: Export path (.med or .msh) when mesh_size is set.

    Returns:
        JSON with volume_tags, entity summary, mesh stats, and output_path.
    """
    result = gmsh_tools.build_extrusion(
        profile_points=profile_points,
        height=height,
        mesh_size=mesh_size,
        physical_groups=physical_groups,
        output_path=output_path,
    )
    return json.dumps(result)


@mcp.tool()
def build_revolved_solid(
    profile_points: list,
    axis_point: list,
    axis_direction: list,
    angle_degrees: float = 360.0,
    mesh_size: float | None = None,
    physical_groups: dict | None = None,
    output_path: str | None = None,
) -> str:
    """Revolve a 2D profile in the XZ plane (radius, z) around an axis.

    Use for axisymmetric solids: pistons, rods, nozzles. Profile points are
    [radius, z] pairs; default axis is Z through the origin.

    Args:
        profile_points: [[radius, z], ...] closed profile in mm.
        axis_point: [x, y, z] point on the revolution axis.
        axis_direction: [dx, dy, dz] axis direction vector.
        angle_degrees: Revolution angle (default 360 for full solid).
        mesh_size: Characteristic mesh size (mm); if set, meshes and can export.
        physical_groups: Named physical groups for volumes/surfaces (for Code_Aster BCs).
        output_path: Export .med/.msh when meshing.

    Returns:
        JSON with volume_tags, entities, mesh stats, output_path.
    """
    result = gmsh_tools.build_revolved_solid(
        profile_points=profile_points,
        axis_point=axis_point,
        axis_direction=axis_direction,
        angle_degrees=angle_degrees,
        mesh_size=mesh_size,
        physical_groups=physical_groups,
        output_path=output_path,
    )
    return json.dumps(result)


@mcp.tool()
def build_cylinder(
    radius: float,
    height: float,
    center: list | None = None,
    mesh_size: float | None = None,
    physical_groups: dict | None = None,
    output_path: str | None = None,
) -> str:
    """Create a cylinder aligned with +Z — quick start for beams, rods, pins.

    Args:
        radius: Cylinder radius (mm).
        height: Cylinder height along +Z (mm).
        center: Optional [x, y, z] base center (default origin).
        mesh_size: Characteristic mesh size (mm).
        physical_groups: Named groups for solver boundary conditions.
        output_path: Export path when meshing.

    Returns:
        JSON with volume_tag, mesh stats, and output_path.
    """
    result = gmsh_tools.build_cylinder(
        radius=radius,
        height=height,
        center=center,
        mesh_size=mesh_size,
        physical_groups=physical_groups,
        output_path=output_path,
    )
    return json.dumps(result)


@mcp.tool()
def mesh_and_export(
    input_path: str,
    output_path: str,
    mesh_size: float = 2.0,
    physical_groups: dict | None = None,
    format: str = "med",
) -> str:
    """Load existing geometry (.geo, .brep, .step), mesh, and export.

    Args:
        input_path: Path to geometry file.
        output_path: Destination .med or .msh path.
        mesh_size: Characteristic element size (mm).
        physical_groups: Optional named physical groups before export.
        format: Export format hint (default med for Code_Aster).

    Returns:
        JSON with node/element counts and output_path.
    """
    result = gmsh_tools.mesh_and_export(
        input_path=input_path,
        output_path=output_path,
        mesh_size=mesh_size,
        physical_groups=physical_groups,
        format=format,
    )
    return json.dumps(result)


@mcp.tool()
def pipeline_status() -> str:
    """Return MCP server health, paths, and code fingerprint."""
    gmsh_ok = False
    gmsh_version = None
    gmsh_error = None
    try:
        gmsh = gmsh_tools._import_gmsh()
        gmsh.initialize()
        gmsh_version = gmsh.option.getString("General.Version") if hasattr(gmsh.option, "getString") else "unknown"
        gmsh.finalize()
        gmsh_ok = True
    except Exception as exc:
        gmsh_error = str(exc)

    payload = {
        "status": "ok" if gmsh_ok else "degraded",
        "code_fingerprint": code_fingerprint(),
        "transport": config.MCP_TRANSPORT,
        "mcp_port": config.MCP_PORT,
        "mesh_dir": str(config.MESH_DIR.resolve()),
        "output_dir": str(config.OUTPUT_DIR.resolve()),
        "gmsh_available": gmsh_ok,
        "gmsh_version": gmsh_version,
        "gmsh_error": gmsh_error,
        "tools": [
            "build_extrusion",
            "build_revolved_solid",
            "build_cylinder",
            "mesh_and_export",
            "pipeline_status",
        ],
    }
    return json.dumps(payload)


if __name__ == "__main__":
    if config.MCP_TRANSPORT == "stdio":
        mcp.run()
    elif config.MCP_TRANSPORT == "streamable-http":
        mcp.run(transport="streamable-http")
    else:
        print(f"Unknown MCP_TRANSPORT: {config.MCP_TRANSPORT}", file=sys.stderr)
        sys.exit(1)
