"""
runner.py
Execute CalculiX ccx via subprocess or docker exec.
"""
from __future__ import annotations

import json
import logging
import os
import shlex
import subprocess
import uuid
from pathlib import Path, PurePosixPath

from src import config

logger = logging.getLogger("runner")


def uses_docker_execution() -> bool:
    if config.DOCKER_CONTAINER_NAME:
        if Path(config.CCX_PATH).exists() if not config.CCX_PATH.startswith("/") else os.path.isfile(config.CCX_PATH):
            return False
        return True
    return False


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _docker_mounts() -> list[dict]:
    if not config.DOCKER_CONTAINER_NAME:
        return []
    try:
        result = subprocess.run(
            ["docker", "inspect", config.DOCKER_CONTAINER_NAME, "--format", "{{json .Mounts}}"],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        return json.loads(result.stdout or "[]")
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return []


def host_to_container_path(host_path: Path) -> str:
    host_path = Path(host_path).resolve()
    if config.DOCKER_WORKSPACE and config.DOCKER_WORKSPACE_HOST:
        ws_host = Path(config.DOCKER_WORKSPACE_HOST).resolve()
        ws_container = PurePosixPath(config.DOCKER_WORKSPACE.rstrip("/"))
        rel = host_path.relative_to(ws_host)
        return str(ws_container / PurePosixPath(rel.as_posix()))

    for mount in _docker_mounts():
        if mount.get("Type") != "bind":
            continue
        source = mount.get("Source")
        destination = mount.get("Destination")
        if not source or not destination:
            continue
        try:
            rel = host_path.relative_to(Path(source).resolve())
        except ValueError:
            continue
        return str(PurePosixPath(destination.rstrip("/")) / PurePosixPath(rel.as_posix()))

    raise ValueError(f"No Docker mount contains {host_path}")


def resolve_host_mesh_path(mesh_path: str) -> Path:
    raw = mesh_path.strip()
    direct = Path(raw)
    if direct.exists():
        return direct.resolve()

    if raw.startswith("/") and uses_docker_execution():
        for mount in _docker_mounts():
            dest = mount.get("Destination", "").rstrip("/")
            source = mount.get("Source")
            if source and dest and raw.startswith(dest + "/"):
                rel = raw[len(dest) + 1 :]
                candidate = Path(source) / rel
                if candidate.exists():
                    return candidate.resolve()

    for root in (Path.cwd(), project_root()):
        for candidate in (root / raw, root / "examples" / Path(raw).name):
            if candidate.exists():
                return candidate.resolve()

    raise ValueError(f"Mesh .inp not found: {mesh_path}")


def run_calculix(job_basename: Path, timeout: int = 300) -> dict:
    """Run ccx on job basename (no extension) in job_basename.parent directory."""
    work_dir = job_basename.parent.resolve()
    job_name = job_basename.name

    if uses_docker_execution():
        container_dir = host_to_container_path(work_dir)
        cmd = [
            "docker", "exec",
            "-w", container_dir,
            config.DOCKER_CONTAINER_NAME,
            config.CCX_PATH,
            job_name,
        ]
    else:
        cmd = [config.CCX_PATH, job_name]

    logger.info("Running CalculiX: %s (cwd=%s)", " ".join(cmd[:6]), work_dir)

    try:
        result = subprocess.run(
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"success": False, "log": f"CalculiX timed out after {timeout}s"}
    except FileNotFoundError:
        return {"success": False, "log": f"Could not run {config.CCX_PATH}. Is CalculiX installed?"}

    log = (result.stdout or "") + "\n" + (result.stderr or "")
    frd = work_dir / f"{job_name}.frd"
    if result.returncode != 0 or not frd.exists():
        return {"success": False, "log": log[-4000:]}
    return {"success": True, "log": log[-500:], "frd_path": str(frd)}
