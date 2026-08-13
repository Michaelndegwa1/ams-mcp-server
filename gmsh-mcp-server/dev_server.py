"""
dev_server.py
Development MCP server with auto-reload on src/ and .env changes.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from watchfiles import run_process

PROJECT_ROOT = Path(__file__).resolve().parent


def _run_server() -> None:
    subprocess.run(
        [sys.executable, "-m", "src.server"],
        cwd=PROJECT_ROOT,
        check=False,
    )


def main() -> None:
    print("Gmsh MCP dev server — auto-reload enabled (watching src/ and .env)")
    print("Press Ctrl+C to stop.\n")
    run_process(
        PROJECT_ROOT / "src",
        PROJECT_ROOT / ".env",
        target=_run_server,
    )


if __name__ == "__main__":
    main()
