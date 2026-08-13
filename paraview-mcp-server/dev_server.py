"""Dev MCP server with auto-reload."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from watchfiles import run_process

PROJECT_ROOT = Path(__file__).resolve().parent
WATCH_PATHS = [PROJECT_ROOT / "src"]
if (PROJECT_ROOT / ".env").exists():
    WATCH_PATHS.append(PROJECT_ROOT / ".env")


def _run_server() -> None:
    subprocess.run([sys.executable, "-m", "src.server"], cwd=PROJECT_ROOT, check=False)


def main() -> None:
    print("ParaView MCP dev server — auto-reload enabled")
    print("Press Ctrl+C to stop.\n")
    run_process(*WATCH_PATHS, target=_run_server)


if __name__ == "__main__":
    main()
