"""Configuration for ParaView MCP server."""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "./outputs"))
RENDER_DIR = Path(os.environ.get("RENDER_DIR", "./renders"))
LOG_LEVEL_NAME = os.environ.get("LOG_LEVEL", "INFO")
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME.upper(), logging.INFO)

PVPYTHON_PATH = os.environ.get("PVPYTHON_PATH", "").strip() or None
RENDER_BACKEND = os.environ.get("RENDER_BACKEND", "auto").strip().lower()

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8768"))
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "streamable-http").strip().lower()


def pvpython_available() -> bool:
    if PVPYTHON_PATH:
        return Path(PVPYTHON_PATH).is_file()
    return shutil.which("pvpython") is not None


def resolve_pvpython() -> str | None:
    if PVPYTHON_PATH and Path(PVPYTHON_PATH).is_file():
        return PVPYTHON_PATH
    found = shutil.which("pvpython")
    return found


def validate_config() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    backend = RENDER_BACKEND
    if backend == "auto":
        backend = "paraview" if pvpython_available() else "matplotlib"
    logging.getLogger("config").info(
        "Config validated. RENDER_DIR=%s backend=%s pvpython=%s",
        RENDER_DIR.resolve(),
        backend,
        resolve_pvpython() or "(not found — using matplotlib fallback)",
    )
