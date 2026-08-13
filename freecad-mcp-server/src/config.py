"""FreeCAD MCP configuration."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

FREECAD_CMD = os.environ.get("FREECAD_CMD", "FreeCADCmd")
DOCKER_CONTAINER_NAME = os.environ.get("DOCKER_CONTAINER_NAME", "").strip() or None
DOCKER_WORKSPACE = os.environ.get("DOCKER_WORKSPACE", "").strip() or None
DOCKER_WORKSPACE_HOST = os.environ.get("DOCKER_WORKSPACE_HOST", "").strip() or None

OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "./outputs"))
CAD_DIR = Path(os.environ.get("CAD_DIR", "./models"))
LOG_LEVEL = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8770"))
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "streamable-http").strip().lower()


def resolve_freecad_cmd() -> str | None:
    if Path(FREECAD_CMD).is_file():
        return FREECAD_CMD
    import shutil
    return shutil.which(FREECAD_CMD)


def freecad_in_docker() -> bool:
    if not DOCKER_CONTAINER_NAME:
        return False
    try:
        r = subprocess.run(
            ["docker", "exec", DOCKER_CONTAINER_NAME, "sh", "-lc", "command -v freecadcmd || command -v FreeCADCmd"],
            capture_output=True, text=True, timeout=20,
        )
        return r.returncode == 0 and bool(r.stdout.strip())
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def validate_config() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CAD_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    cmd = resolve_freecad_cmd()
    logging.getLogger("config").info(
        "FreeCAD MCP | cmd=%s docker=%s port=%s",
        cmd or "(docker only)" if freecad_in_docker() else cmd or "NOT FOUND",
        DOCKER_CONTAINER_NAME or "(none)",
        MCP_PORT,
    )
