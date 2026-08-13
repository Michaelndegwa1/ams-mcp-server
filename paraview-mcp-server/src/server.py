"""FastMCP server for headless FEA result visualization."""
from __future__ import annotations

import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from src import config
from src.build_info import code_fingerprint
from src import render_tools
from src.med_reader import inspect_result_file as inspect_med_file

config.validate_config()
logger = logging.getLogger("server")

logger.info(
    "ParaView MCP starting | transport=%s | fingerprint=%s | port=%s",
    config.MCP_TRANSPORT,
    code_fingerprint(),
    config.MCP_PORT,
)

mcp = FastMCP("paraview-visualization", host=config.MCP_HOST, port=config.MCP_PORT)


@mcp.tool()
def render_stress_contour(
    result_path: str,
    output_path: str | None = None,
    backend: str | None = None,
    title: str | None = None,
) -> str:
    """Render a Von Mises stress contour PNG from a Code_Aster .rmed file.

    Args:
        result_path: Path to .rmed result (host or container path under /data/...).
        output_path: Optional PNG output path (default: renders/stress_<id>.png).
        backend: auto | paraview | matplotlib (default from .env).
        title: Optional plot title.

    Returns:
        JSON with status, output_path, backend_used, max/min stress values.
    """
    result = render_tools.render_stress_contour(
        result_path=result_path,
        output_path=output_path,
        backend=backend,
        title=title,
    )
    return json.dumps(result)


@mcp.tool()
def render_displacement_contour(
    result_path: str,
    output_path: str | None = None,
    backend: str | None = None,
    title: str | None = None,
) -> str:
    """Render a displacement magnitude contour PNG from a Code_Aster .rmed file."""
    result = render_tools.render_displacement_contour(
        result_path=result_path,
        output_path=output_path,
        backend=backend,
        title=title,
    )
    return json.dumps(result)


@mcp.tool()
def inspect_result_file(result_path: str) -> str:
    """List MED dataset paths and whether stress/displacement/coords were found."""
    try:
        payload = inspect_med_file(result_path)
        payload["status"] = "ok"
    except Exception as exc:
        payload = {"status": "error", "message": str(exc)}
    payload["code_fingerprint"] = code_fingerprint()
    return json.dumps(payload)


@mcp.tool()
def pipeline_status() -> str:
    """Return MCP health, render backend, and ParaView availability."""
    payload = {
        "status": "ok",
        "code_fingerprint": code_fingerprint(),
        "transport": config.MCP_TRANSPORT,
        "mcp_port": config.MCP_PORT,
        "render_backend_config": config.RENDER_BACKEND,
        "render_backend_active": render_tools._choose_backend(),
        "pvpython_path": config.resolve_pvpython(),
        "pvpython_available": config.pvpython_available(),
        "render_dir": str(config.RENDER_DIR.resolve()),
        "tools": [
            "render_stress_contour",
            "render_displacement_contour",
            "inspect_result_file",
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
