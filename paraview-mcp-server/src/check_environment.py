"""Environment check for ParaView MCP server."""
from __future__ import annotations

import platform
import sys
from pathlib import Path

from src import config


def print_environment_report() -> int:
    print("=== ParaView MCP environment check ===\n")
    print(f"  Python     : {sys.executable} ({platform.python_version()})")
    print(f"  MCP port   : {config.MCP_PORT}")
    print(f"  render_dir : {config.RENDER_DIR.resolve()}")
    print(f"  backend    : {config.RENDER_BACKEND}")
    pv = config.resolve_pvpython()
    print(f"  pvpython   : {pv or '(not found — matplotlib fallback will be used)'}")
    try:
        import h5py  # noqa: F401
        import matplotlib  # noqa: F401

        print("  h5py/mpl   : ok")
        verdict = "READY"
        note = (
            "Run python run_local_test.py <path-to.rmed> after a Code_Aster solve, "
            "then .\\scripts\\start_mcp.ps1"
        )
    except ImportError as exc:
        verdict = "BLOCKED"
        note = f"pip install -r requirements.txt ({exc})"

    print(f"\nVERDICT: {verdict}")
    print(f"\nNext step: {note}\n")
    return 0 if verdict == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(print_environment_report())
