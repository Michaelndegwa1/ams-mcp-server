"""Environment check."""
from __future__ import annotations

import platform
import shutil
import subprocess
import sys

from src import config


def print_environment_report() -> int:
    print("=== CalculiX MCP environment check ===\n")
    print(f"  Python   : {sys.executable} ({platform.python_version()})")
    print(f"  MCP port : {config.MCP_PORT}")
    print(f"  CCX_PATH : {config.CCX_PATH}")

    local = shutil.which(config.CCX_PATH)
    in_docker = False
    if config.DOCKER_CONTAINER_NAME:
        try:
            r = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", config.DOCKER_CONTAINER_NAME],
                capture_output=True,
                text=True,
                timeout=15,
            )
            running = (r.stdout or "").strip().lower() == "true"
            print(f"  Docker   : {config.DOCKER_CONTAINER_NAME} ({'running' if running else 'not running'})")
            if running:
                r2 = subprocess.run(
                    ["docker", "exec", config.DOCKER_CONTAINER_NAME, "sh", "-lc", f"command -v {config.CCX_PATH}"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                in_docker = r2.returncode == 0
                print(f"  ccx in container : {in_docker}")
        except Exception as exc:
            print(f"  Docker   : error ({exc})")
    else:
        print("  Docker   : (not configured)")

    print(f"  ccx local: {local or 'not found'}")

    if local or in_docker:
        print("\nVERDICT: READY")
        print("\nNext step: python scripts/generate_example_mesh.py && python run_local_test.py")
        return 0

    print("\nVERDICT: BLOCKED — start calculix-container (see README)")
    return 1


if __name__ == "__main__":
    raise SystemExit(print_environment_report())
