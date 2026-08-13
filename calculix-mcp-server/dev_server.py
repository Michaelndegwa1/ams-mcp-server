"""Dev server with auto-reload."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from watchfiles import run_process

PROJECT_ROOT = Path(__file__).resolve().parent


def _run_server() -> None:
    subprocess.run([sys.executable, "-m", "src.server"], cwd=PROJECT_ROOT, check=False)


def main() -> None:
    paths = [PROJECT_ROOT / "src"]
    env = PROJECT_ROOT / ".env"
    if env.exists():
        paths.append(env)
    run_process(*paths, target=_run_server)


if __name__ == "__main__":
    main()
