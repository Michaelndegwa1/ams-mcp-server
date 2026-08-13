"""Run Salome TUI scripts via salome -t."""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path, PurePosixPath

from src import config

logger = logging.getLogger("runner")


def uses_docker() -> bool:
    return bool(config.DOCKER_CONTAINER_NAME)


def _mounts() -> list[dict]:
    if not config.DOCKER_CONTAINER_NAME:
        return []
    try:
        r = subprocess.run(
            ["docker", "inspect", config.DOCKER_CONTAINER_NAME, "--format", "{{json .Mounts}}"],
            capture_output=True, text=True, timeout=20, check=True,
        )
        return json.loads(r.stdout or "[]")
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return []


def host_to_container(path: Path) -> str:
    path = path.resolve()
    if config.DOCKER_WORKSPACE and config.DOCKER_WORKSPACE_HOST:
        host = Path(config.DOCKER_WORKSPACE_HOST).resolve()
        rel = path.relative_to(host)
        return str(PurePosixPath(config.DOCKER_WORKSPACE.rstrip("/")) / PurePosixPath(rel.as_posix()))
    for m in _mounts():
        if m.get("Type") != "bind":
            continue
        src, dst = m.get("Source"), m.get("Destination")
        if not src or not dst:
            continue
        try:
            rel = path.relative_to(Path(src).resolve())
            return str(PurePosixPath(dst.rstrip("/")) / PurePosixPath(rel.as_posix()))
        except ValueError:
            continue
    raise ValueError(f"No docker mount for {path}")


def run_script(script_path: Path, timeout: int = 600) -> dict:
    script_path = script_path.resolve()

    if uses_docker():
        cscript = host_to_container(script_path)
        cdir = str(PurePosixPath(cscript).parent)
        cmd = [
            "docker", "exec", "-w", cdir, config.DOCKER_CONTAINER_NAME,
            "sh", "-lc",
            f"salome -t {PurePosixPath(cscript).name} 2>/dev/null || /opt/salome/salome -t {PurePosixPath(cscript).name}",
        ]
    else:
        cmd = [config.SALOME_CMD, "-t", str(script_path)]

    logger.info("Running Salome script: %s", script_path.name)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"success": False, "log": "Salome timed out"}
    except FileNotFoundError:
        return {"success": False, "log": f"Salome not found: {config.SALOME_CMD}. Use Docker (see README)."}

    log = (r.stdout or "") + "\n" + (r.stderr or "")
    return {"success": r.returncode == 0, "log": log[-4000:], "exit_code": r.returncode}
