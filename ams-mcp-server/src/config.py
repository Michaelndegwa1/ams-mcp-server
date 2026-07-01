"""
config.py
Single source of truth for environment configuration.
No other module should call os.environ directly.
"""
import os
import logging
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Core paths ---------------------------------------------------------
# CODE_ASTER_PATH must point to the as_run (or run_aster) executable
# INSIDE your Docker container. Confirm the exact path with:
#   docker exec -it <container_name> which as_run
# or
#   docker exec -it <container_name> which run_aster
CODE_ASTER_PATH = os.environ.get("CODE_ASTER_PATH", "/opt/aster/bin/as_run")

# Optional: when Python runs on the host but Code_Aster is in Docker, set the
# container name so `python -m src.check_environment` can probe the split setup.
DOCKER_CONTAINER_NAME = os.environ.get("DOCKER_CONTAINER_NAME", "").strip() or None
# Optional: path inside the container that maps to this project root (for a future
# docker exec wrapper in runner.py). Example: /data/ams-mcp-server
DOCKER_WORKSPACE = os.environ.get("DOCKER_WORKSPACE", "").strip() or None
# Optional: host path that corresponds to DOCKER_WORKSPACE. If unset, auto-detected
# from the Docker bind mount that contains this project.
DOCKER_WORKSPACE_HOST = os.environ.get("DOCKER_WORKSPACE_HOST", "").strip() or None

OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "./outputs"))
LOG_LEVEL_NAME = os.environ.get("LOG_LEVEL", "INFO")
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME.upper(), logging.INFO)

# Default yield strength used for factor-of-safety calc if material
# doesn't specify one. Structural steel (S235) ~ 235 MPa.
DEFAULT_YIELD_STRENGTH_MPA = float(os.environ.get("DEFAULT_YIELD_STRENGTH_MPA", "235.0"))

# MCP server transport (Claude connector)
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8765"))
# "streamable-http" for Cloudflare HTTPS connector; "stdio" for local Claude spawn
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "streamable-http").strip().lower()


def _solver_exists_here() -> bool:
    if CODE_ASTER_PATH.startswith("/"):
        return os.path.isfile(CODE_ASTER_PATH)
    return Path(CODE_ASTER_PATH).exists()


def _solver_exists_in_container() -> bool:
    if not DOCKER_CONTAINER_NAME:
        return False
    try:
        result = subprocess.run(
            ["docker", "exec", DOCKER_CONTAINER_NAME, "test", "-x", CODE_ASTER_PATH],
            capture_output=True,
            timeout=20,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def validate_config() -> None:
    """Run once at server startup. Fails loudly and early rather than
    letting a bad path surface mid-demo as a confusing subprocess error."""
    issues = []

    solver_here = _solver_exists_here()
    solver_in_docker = _solver_exists_in_container()

    if not solver_here and not solver_in_docker:
        issues.append(
            f"CODE_ASTER_PATH does not exist on this machine: {CODE_ASTER_PATH}\n"
            f"  -> If Code_Aster runs inside Docker, set DOCKER_CONTAINER_NAME in .env "
            f"and ensure the container is running with run_aster at CODE_ASTER_PATH."
        )
    elif not solver_here and solver_in_docker:
        logging.getLogger("config").info(
            "Split setup: Code_Aster will run via docker exec in container '%s'",
            DOCKER_CONTAINER_NAME,
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if issues:
        for issue in issues:
            logging.getLogger("config").error(issue)
        raise RuntimeError(
            "Configuration validation failed. Fix CODE_ASTER_PATH in .env before continuing."
        )

    logging.getLogger("config").info("Config validated. CODE_ASTER_PATH=%s OUTPUT_DIR=%s", CODE_ASTER_PATH, OUTPUT_DIR)
