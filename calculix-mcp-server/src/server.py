"""CalculiX MCP FastMCP server."""
from __future__ import annotations

import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from src import config
from src.build_info import code_fingerprint
from src.calculix_tool import run_structural_analysis
from src.runner import project_root, resolve_host_mesh_path, uses_docker_execution, host_to_container_path

config.validate_config()
logger = logging.getLogger("server")

mcp = FastMCP("calculix-fem", host=config.MCP_HOST, port=config.MCP_PORT)


@mcp.tool()
def structural_analysis(
    mesh_path: str,
    material: dict,
    boundary_conditions: list,
    loads: list,
    solid_elset: str = "SOLID",
) -> str:
    """Run linear static FEA with CalculiX (ccx) on a Gmsh-exported .inp mesh.

    Same parameter shape as the Code_Aster MCP tool for cross-checking solvers.

    Args:
        mesh_path: Path to .inp mesh with NSET/ELSET groups (export from Gmsh MCP).
        material: {E, NU, yield_strength_mpa?} — E in MPa, mesh in mm.
        boundary_conditions: [{group_name, fixed_dofs: [DX,DY,DZ]}] — NSET or face ELSET.
        loads: [{group_name, direction: FX|FY|FZ, magnitude: Newtons}] — ELSET face load.
        solid_elset: Volume ELSET name (default SOLID).

    Returns:
        JSON with max_displacement_mm, max_stress_mpa, factor_of_safety, frd_path.
    """
    result = run_structural_analysis(
        mesh_path=mesh_path,
        material=material,
        boundary_conditions=boundary_conditions,
        loads=loads,
        solid_elset=solid_elset,
    )
    return json.dumps(result)


@mcp.tool()
def pipeline_status() -> str:
    """Health check, docker/ccx config, code fingerprint."""
    root = project_root()
    example = root / "examples" / "test_beam.inp"
    payload = {
        "status": "ok",
        "code_fingerprint": code_fingerprint(),
        "solver": "calculix",
        "mcp_port": config.MCP_PORT,
        "ccx_path": config.CCX_PATH,
        "docker_execution": uses_docker_execution(),
        "docker_container": config.DOCKER_CONTAINER_NAME,
        "example_mesh_host": str(example) if example.exists() else None,
    }
    if uses_docker_execution() and example.exists():
        try:
            payload["example_mesh_container"] = host_to_container_path(example)
        except ValueError:
            payload["example_mesh_container"] = None
    return json.dumps(payload)


if __name__ == "__main__":
    logger.info(
        "CalculiX MCP | transport=%s | fingerprint=%s",
        config.MCP_TRANSPORT,
        code_fingerprint(),
    )
    if config.MCP_TRANSPORT == "stdio":
        mcp.run()
    elif config.MCP_TRANSPORT == "streamable-http":
        mcp.run(transport="streamable-http")
    else:
        sys.exit(1)
