"""Execute FreeCADCmd scripts locally or via docker exec."""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path, PurePosixPath

from src import config

logger = logging.getLogger("runner")


def uses_docker() -> bool:
    if not config.DOCKER_CONTAINER_NAME:
        return False
    if config.resolve_freecad_cmd():
        return False
    return config.freecad_in_docker()


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


def run_script(script_path: Path, timeout: int = 180) -> dict:
    script_path = script_path.resolve()
    if uses_docker():
        container_script = host_to_container(script_path)
        container_dir = str(PurePosixPath(container_script).parent)
        cmd = [
            "docker", "exec", "-w", container_dir, config.DOCKER_CONTAINER_NAME,
            "sh", "-lc", f"freecadcmd {PurePosixPath(container_script).name} 2>/dev/null || FreeCADCmd {PurePosixPath(container_script).name}",
        ]
    else:
        fc = config.resolve_freecad_cmd()
        if not fc:
            return {"success": False, "log": "FreeCADCmd not found. Set FREECAD_CMD or DOCKER_CONTAINER_NAME."}
        cmd = [fc, str(script_path)]

    logger.info("Running FreeCAD script: %s", script_path.name)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"success": False, "log": "FreeCAD timed out"}
    except FileNotFoundError as exc:
        return {"success": False, "log": str(exc)}

    log = (r.stdout or "") + "\n" + (r.stderr or "")
    return {"success": r.returncode == 0, "log": log[-3000:], "exit_code": r.returncode}
