"""
server.py
FastMCP server for Claude connectors.

HTTP mode (default) — use with Cloudflare tunnel:
  python dev_server.py          # auto-reload on code changes (recommended)
  python -m src.server          # single process, manual restart

Claude connector URL:
  https://YOUR-TUNNEL-HOST/mcp

stdio mode — Claude spawns a fresh process per session (no tunnel):
  set MCP_TRANSPORT=stdio
  python -m src.server
"""
import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from src import config
from src.build_info import code_fingerprint
from src.code_aster_tool import run_structural_analysis

config.validate_config()
logger = logging.getLogger("server")

logger.info(
    "AMS MCP starting | transport=%s | fingerprint=%s | docker=%s",
    config.MCP_TRANSPORT,
    code_fingerprint(),
    config.DOCKER_CONTAINER_NAME or "(local)",
)

mcp = FastMCP("ams-code-aster", host=config.MCP_HOST, port=config.MCP_PORT)


@mcp.tool()
def structural_analysis(
    mesh_path: str,
    material: dict,
    boundary_conditions: list,
    loads: list,
    model_type: str = "3D",
) -> str:
    """Runs a linear static structural analysis using Code_Aster.

    Use this when an engineer needs to know maximum displacement, maximum
    Von Mises stress, or factor of safety for a structural component under
    mechanical load (e.g. a beam, plate, or bracket).

    Args:
        mesh_path: Path to the .med mesh file. Accepts a host path (Windows or
            Linux) or, in Docker split setups, the container path (e.g.
            /data/ams-mcp-server/examples/test_beam.med). Call pipeline_status
            for example paths on this server.
        material: dict with keys E (Young's modulus, MPa), NU (Poisson's ratio),
                  and optionally yield_strength_mpa.
        boundary_conditions: list of dicts, each with group_name (str) and
                  fixed_dofs (list of "DX"/"DY"/"DZ"/"DRX"/"DRY"/"DRZ").
        loads: list of dicts, each with group_name (str), direction
                  ("FX"/"FY"/"FZ"), and magnitude (float, Newtons total force).
        model_type: "3D", "C_PLAN", or "D_PLAN". Defaults to "3D".

    Returns:
        JSON string with status, max_displacement_mm, max_stress_mpa,
        factor_of_safety, safety_status, engineering_verdict, and
        code_fingerprint proving which pipeline version ran.
    """
    logger.info(
        "structural_analysis | mesh=%s | fingerprint=%s",
        mesh_path,
        code_fingerprint(),
    )
    result = run_structural_analysis(
        mesh_path=mesh_path,
        model_type=model_type,
        material=material,
        boundary_conditions=boundary_conditions,
        loads=loads,
    )
    result["code_fingerprint"] = code_fingerprint()
    logger.info("structural_analysis result status=%s", result.get("status"))
    return json.dumps(result)


@mcp.tool()
def pipeline_status() -> str:
    """Return MCP server health, config, and code fingerprint.

    Call this to verify Claude is hitting the latest server code after a deploy
    or dev_server.py auto-reload.
    """
    from src.runner import uses_docker_execution, host_to_container_path, project_root

    root = project_root()
    example_host = root / "examples" / "test_beam.med"
    payload = {
        "status": "ok",
        "code_fingerprint": code_fingerprint(),
        "transport": config.MCP_TRANSPORT,
        "mcp_port": config.MCP_PORT,
        "docker_execution": uses_docker_execution(),
        "docker_container": config.DOCKER_CONTAINER_NAME,
        "code_aster_path": config.CODE_ASTER_PATH,
        "project_root": str(root),
        "example_mesh_host": str(example_host) if example_host.exists() else None,
    }
    if uses_docker_execution() and example_host.exists():
        try:
            payload["example_mesh_container"] = host_to_container_path(example_host)
        except ValueError:
            payload["example_mesh_container"] = None
    else:
        payload["example_mesh_container"] = None

    return json.dumps(payload)


if __name__ == "__main__":
    if config.MCP_TRANSPORT == "stdio":
        mcp.run()
    elif config.MCP_TRANSPORT == "streamable-http":
        mcp.run(transport="streamable-http")
    else:
        print(f"Unknown MCP_TRANSPORT: {config.MCP_TRANSPORT}", file=sys.stderr)
        sys.exit(1)
