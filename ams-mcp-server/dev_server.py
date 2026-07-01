"""
dev_server.py
Development MCP server with auto-reload.

Watches src/ and .env — when you save a file, the server restarts automatically
so Claude (via Cloudflare tunnel) always hits the latest code without manual
kill/restart cycles.

Usage:
    python dev_server.py
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
    print("AMS MCP dev server — auto-reload enabled (watching src/ and .env)")
    print("Press Ctrl+C to stop.\n")
    run_process(
        PROJECT_ROOT / "src",
        PROJECT_ROOT / ".env",
        target=_run_server,
    )


if __name__ == "__main__":
    main()
