"""Environment check."""
import subprocess
import sys
from src import config
from src.runner import uses_docker


def main() -> int:
    print("=== FreeCAD MCP environment check ===\n")
    print(f"  MCP port : {config.MCP_PORT}")
    print(f"  FREECAD  : {config.resolve_freecad_cmd() or '(not on PATH)'}")
    if config.DOCKER_CONTAINER_NAME:
        try:
            r = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", config.DOCKER_CONTAINER_NAME],
                capture_output=True, text=True, timeout=15,
            )
            print(f"  Docker   : {config.DOCKER_CONTAINER_NAME} running={((r.stdout or '').strip() == 'true')}")
        except Exception as exc:
            print(f"  Docker   : error {exc}")
    if config.resolve_freecad_cmd() or uses_docker():
        print("\nVERDICT: READY")
        return 0
    print("\nVERDICT: BLOCKED — install FreeCAD or start freecad-container (see README)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
