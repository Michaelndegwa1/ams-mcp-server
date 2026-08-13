"""Salome MCP configuration."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SALOME_CMD = os.environ.get("SALOME_CMD", "salome")
DOCKER_CONTAINER_NAME = os.environ.get("DOCKER_CONTAINER_NAME", "").strip() or None
DOCKER_WORKSPACE = os.environ.get("DOCKER_WORKSPACE", "").strip() or None
DOCKER_WORKSPACE_HOST = os.environ.get("DOCKER_WORKSPACE_HOST", "").strip() or None

OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "./outputs"))
MESH_DIR = Path(os.environ.get("MESH_DIR", "./meshes"))
LOG_LEVEL = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8771"))
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "streamable-http").strip().lower()


def salome_in_docker() -> bool:
    if not DOCKER_CONTAINER_NAME:
        return False
    try:
        r = subprocess.run(
            ["docker", "exec", DOCKER_CONTAINER_NAME, "sh", "-lc", "command -v salome || test -x /opt/salome/salome"],
            capture_output=True, text=True, timeout=30,
        )
        return r.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def validate_config() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MESH_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logging.getLogger("config").info(
        "Salome MCP | docker=%s port=%s",
        DOCKER_CONTAINER_NAME or "(none — set container or local SALOME install)",
        MCP_PORT,
    )
