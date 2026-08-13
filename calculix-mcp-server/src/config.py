"""Configuration for CalculiX MCP server."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CCX_PATH = os.environ.get("CCX_PATH", "ccx")
DOCKER_CONTAINER_NAME = os.environ.get("DOCKER_CONTAINER_NAME", "").strip() or None
DOCKER_WORKSPACE = os.environ.get("DOCKER_WORKSPACE", "").strip() or None
DOCKER_WORKSPACE_HOST = os.environ.get("DOCKER_WORKSPACE_HOST", "").strip() or None

OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "./outputs"))
LOG_LEVEL_NAME = os.environ.get("LOG_LEVEL", "INFO")
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME.upper(), logging.INFO)
DEFAULT_YIELD_STRENGTH_MPA = float(os.environ.get("DEFAULT_YIELD_STRENGTH_MPA", "235.0"))

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8769"))
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "streamable-http").strip().lower()


def _ccx_exists_in_container() -> bool:
    if not DOCKER_CONTAINER_NAME:
        return False
    try:
        result = subprocess.run(
            ["docker", "exec", DOCKER_CONTAINER_NAME, "sh", "-lc", f"command -v {CCX_PATH}"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return result.returncode == 0 and bool((result.stdout or "").strip())
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def validate_config() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    import shutil

    local = shutil.which(CCX_PATH)
    in_docker = _ccx_exists_in_container()
    if not local and not in_docker:
        logging.getLogger("config").warning(
            "CalculiX not found locally or in container '%s'. "
            "MCP starts; structural_analysis fails until ccx is available.",
            DOCKER_CONTAINER_NAME or "(unset)",
        )
    elif in_docker and not local:
        logging.getLogger("config").info(
            "Split setup: CalculiX via docker exec in '%s'", DOCKER_CONTAINER_NAME
        )

    logging.getLogger("config").info(
        "Config validated. CCX_PATH=%s OUTPUT_DIR=%s", CCX_PATH, OUTPUT_DIR.resolve()
    )
