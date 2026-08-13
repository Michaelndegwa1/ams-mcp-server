import subprocess, sys
from src import config
from src.runner import uses_docker

def main() -> int:
    print("=== Salome MCP environment check ===\n")
    print(f"  MCP port : {config.MCP_PORT}")
    print(f"  SALOME   : {config.SALOME_CMD}")
    if config.DOCKER_CONTAINER_NAME:
        try:
            r = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", config.DOCKER_CONTAINER_NAME],
                capture_output=True, text=True, timeout=15,
            )
            print(f"  Docker   : {config.DOCKER_CONTAINER_NAME} running={((r.stdout or '').strip() == 'true')}")
        except Exception as exc:
            print(f"  Docker   : {exc}")
    if uses_docker() or config.salome_in_docker():
        print("\nVERDICT: READY (docker)")
        return 0
    print("\nVERDICT: BLOCKED — Salome requires Docker image (see README, ~8GB download)")
    return 1

if __name__ == "__main__":
    sys.exit(main())
