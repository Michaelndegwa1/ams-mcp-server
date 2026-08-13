"""FastMCP server — headless FreeCAD parametric CAD."""
from __future__ import annotations

import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from src import config
from src.build_info import code_fingerprint
from src import freecad_tools
from src.runner import uses_docker
from src import config as cfg

config.validate_config()
logger = logging.getLogger("server")
mcp = FastMCP("freecad-cad", host=config.MCP_HOST, port=config.MCP_PORT)


@mcp.tool()
def build_cylinder(
    radius: float,
    height: float,
    output_step: str | None = None,
    output_stl: str | None = None,
) -> str:
    """Create a cylinder and export STEP (+ STL). Dimensions in mm."""
    return json.dumps(freecad_tools.build_cylinder(radius, height, output_step, output_stl))


@mcp.tool()
def build_box(
    length: float,
    width: float,
    height: float,
    output_step: str | None = None,
) -> str:
    """Create a box and export STEP. Dimensions in mm."""
    return json.dumps(freecad_tools.build_box(length, width, height, output_step))


@mcp.tool()
def build_revolved_solid(
    profile_points: list,
    output_step: str | None = None,
    angle_degrees: float = 360.0,
) -> str:
    """Revolve XZ profile [[radius, z], ...] around Z — pistons, shafts, nozzles."""
    return json.dumps(freecad_tools.build_revolved_solid(profile_points, output_step, angle_degrees))


@mcp.tool()
def add_ring_groove(
    base_step_path: str,
    groove_radius: float,
    groove_depth: float,
    groove_z: float,
    output_step: str | None = None,
) -> str:
    """Cut a ring groove into an existing STEP body."""
    return json.dumps(
        freecad_tools.add_ring_groove(base_step_path, groove_radius, groove_depth, groove_z, output_step)
    )


@mcp.tool()
def pipeline_status() -> str:
    """Health check and paths."""
    return json.dumps({
        "status": "ok",
        "code_fingerprint": code_fingerprint(),
        "mcp_port": config.MCP_PORT,
        "freecad_cmd": cfg.resolve_freecad_cmd(),
        "docker_execution": uses_docker(),
        "docker_container": config.DOCKER_CONTAINER_NAME,
        "cad_dir": str(config.CAD_DIR.resolve()),
        "tools": ["build_cylinder", "build_box", "build_revolved_solid", "add_ring_groove", "pipeline_status"],
    })


if __name__ == "__main__":
    if config.MCP_TRANSPORT == "stdio":
        mcp.run()
    else:
        mcp.run(transport="streamable-http")
