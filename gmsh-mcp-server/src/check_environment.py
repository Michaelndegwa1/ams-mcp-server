"""
check_environment.py
Verify Gmsh and MCP configuration before starting the server or a demo.
"""
from __future__ import annotations

import platform
import sys
from pathlib import Path

from src import config


def gather_environment_report() -> dict:
    mesh_dir = config.MESH_DIR.resolve()
    output_dir = config.OUTPUT_DIR.resolve()

    report = {
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform_system": platform.system(),
        "cwd": str(Path.cwd().resolve()),
        "mesh_dir": str(mesh_dir),
        "output_dir": str(output_dir),
        "mcp_port": config.MCP_PORT,
        "gmsh_available": False,
        "gmsh_version": None,
        "verdict": "",
        "recommendation": "",
    }

    try:
        from src.gmsh_tools import _import_gmsh

        gmsh = _import_gmsh()
        gmsh.initialize()
        try:
            report["gmsh_version"] = gmsh.__version__
        except AttributeError:
            report["gmsh_version"] = "installed"
        gmsh.finalize()
        report["gmsh_available"] = True
        report["verdict"] = "READY"
        report["recommendation"] = (
            "Run python run_local_test.py to generate a sample cylinder mesh, "
            "then start the MCP server with .\\scripts\\start_mcp.ps1"
        )
    except Exception as exc:
        report["gmsh_error"] = str(exc)
        report["verdict"] = "BLOCKED - gmsh not available"
        report["recommendation"] = "pip install gmsh  (or pip install -r requirements.txt)"

    return report


def print_environment_report() -> int:
    report = gather_environment_report()
    print("=== Gmsh MCP environment check ===\n")
    print(f"  Python     : {report['python_executable']} ({report['python_version']})")
    print(f"  Platform   : {report['platform_system']}")
    print(f"  MCP port   : {report['mcp_port']}")
    print(f"  mesh_dir   : {report['mesh_dir']}")
    print(f"  output_dir : {report['output_dir']}")
    print(f"  gmsh       : {report.get('gmsh_version') or report.get('gmsh_error', 'missing')}")
    print(f"\nVERDICT: {report['verdict']}")
    print(f"\nNext step: {report['recommendation']}\n")
    return 0 if report["verdict"].startswith("READY") else 1


if __name__ == "__main__":
    raise SystemExit(print_environment_report())
