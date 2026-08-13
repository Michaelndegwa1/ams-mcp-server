"""
config.py
Single source of truth for environment configuration.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "./outputs"))
MESH_DIR = Path(os.environ.get("MESH_DIR", "./meshes"))
LOG_LEVEL_NAME = os.environ.get("LOG_LEVEL", "INFO")
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME.upper(), logging.INFO)

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8767"))
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "streamable-http").strip().lower()


def validate_config() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MESH_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("config").info(
        "Config validated. OUTPUT_DIR=%s MESH_DIR=%s MCP_PORT=%s",
        OUTPUT_DIR.resolve(),
        MESH_DIR.resolve(),
        MCP_PORT,
    )
