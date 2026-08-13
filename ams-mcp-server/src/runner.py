"""
runner.py
Handles all interaction with the Code_Aster executable via subprocess.
Knows nothing about MCP - it just runs Code_Aster and reports what happened.

When Python runs on the host and Code_Aster lives in Docker (split setup),
this module translates host paths to container paths and invokes run_aster via
`docker exec`, with the working directory set to the mounted outputs folder.
"""
import json
import logging
import os
import shlex
import shutil
import subprocess
from pathlib import Path, PurePosixPath

from src import config

logger = logging.getLogger("runner")


def _docker_bin() -> str:
    return shutil.which("docker") or "docker"


def uses_docker_execution() -> bool:
    """True when the solver is reached through docker exec, not a local binary."""
    if config.DOCKER_CONTAINER_NAME:
        if config.CODE_ASTER_PATH.startswith("/"):
            if os.path.isfile(config.CODE_ASTER_PATH):
                return False
        elif Path(config.CODE_ASTER_PATH).exists():
            return False
        return True
    return False


def _docker_mounts() -> list[dict]:
    if not config.DOCKER_CONTAINER_NAME:
        return []
    try:
        result = subprocess.run(
            [_docker_bin(), "inspect", config.DOCKER_CONTAINER_NAME, "--format", "{{json .Mounts}}"],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        return json.loads(result.stdout or "[]")
    except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
        logger.warning("Could not read Docker mounts: %s", exc)
        return []


def _normalize_host_path(path: Path) -> Path:
    return Path(os.path.normcase(path.resolve()))


def project_root() -> Path:
    """ams-mcp-server package root (parent of src/)."""
    return Path(__file__).resolve().parent.parent


def container_to_host_path(container_path: str) -> Path:
    """Map a container file path to the corresponding host path via bind mounts."""
    container = PurePosixPath(container_path)

    if config.DOCKER_WORKSPACE and config.DOCKER_WORKSPACE_HOST:
        workspace_container = PurePosixPath(config.DOCKER_WORKSPACE.rstrip("/"))
        workspace_host = Path(config.DOCKER_WORKSPACE_HOST)
        try:
            rel = container.relative_to(workspace_container)
        except ValueError as exc:
            raise ValueError(
                f"Path {container_path} is not under configured container workspace "
                f"{config.DOCKER_WORKSPACE}"
            ) from exc
        return _normalize_host_path(workspace_host / Path(rel.as_posix()))

    for mount in _docker_mounts():
        if mount.get("Type") != "bind":
            continue
        source = mount.get("Source")
        destination = mount.get("Destination")
        if not source or not destination:
            continue
        dest = PurePosixPath(destination.rstrip("/"))
        try:
            rel = container.relative_to(dest)
        except ValueError:
            continue
        return _normalize_host_path(Path(source) / Path(rel.as_posix()))

    raise ValueError(
        f"No Docker bind mount contains container path {container_path}. "
        f"Set DOCKER_WORKSPACE=/data/ams-mcp-server in .env or ensure the project "
        f"is bind-mounted into '{config.DOCKER_CONTAINER_NAME}'."
    )


def resolve_host_mesh_path(mesh_path: str) -> Path:
    """
    Resolve a mesh path that may be host (Windows/Linux) or container (POSIX).

    Claude often passes container paths like /data/ams-mcp-server/examples/test_beam.med
    while mesh I/O runs on the Windows host. This function normalizes to a host path.
    """
    raw = mesh_path.strip()
    if not raw:
        raise ValueError("mesh_path is empty")

    direct = Path(raw)
    if direct.exists():
        return _normalize_host_path(direct)

    if raw.startswith("/") and uses_docker_execution():
        try:
            host = container_to_host_path(raw)
            if host.exists():
                logger.info("Resolved container mesh path %s -> %s", raw, host)
                return host
        except ValueError as exc:
            logger.debug("container_to_host_path failed for %s: %s", raw, exc)

    search_roots = [Path.cwd(), project_root()]
    rel = raw.lstrip("/")
    for root in search_roots:
        candidate = root / rel
        if candidate.exists():
            logger.info("Resolved mesh path %s -> %s", raw, candidate)
            return _normalize_host_path(candidate)

    basename = PurePosixPath(raw).name
    if basename and basename != raw:
        for root in search_roots:
            candidate = root / "examples" / basename
            if candidate.exists():
                logger.info("Resolved mesh path %s -> %s", raw, candidate)
                return _normalize_host_path(candidate)

    hint = (
        f"Mesh file not found: {mesh_path}. "
        f"Use a host path such as {project_root() / 'examples' / 'test_beam.med'}"
    )
    if uses_docker_execution():
        try:
            example_container = host_to_container_path(project_root() / "examples" / "test_beam.med")
            hint += f", or the container path {example_container}"
        except ValueError:
            hint += ", or a container path under your Docker bind mount (e.g. /data/ams-mcp-server/examples/test_beam.med)"
    raise ValueError(hint)


def host_to_container_path(host_path: Path) -> str:
    """
    Map a host file path to the corresponding path inside the container,
    using the bind mount that contains it. Raises ValueError if no mount matches.
    """
    host_path = _normalize_host_path(host_path)

    if config.DOCKER_WORKSPACE and config.DOCKER_WORKSPACE_HOST:
        workspace_host = _normalize_host_path(Path(config.DOCKER_WORKSPACE_HOST))
        workspace_container = PurePosixPath(config.DOCKER_WORKSPACE.rstrip("/"))
        try:
            rel = host_path.relative_to(workspace_host)
        except ValueError as exc:
            raise ValueError(
                f"Path {host_path} is not under configured host workspace {workspace_host}"
            ) from exc
        return str(workspace_container / PurePosixPath(rel.as_posix()))

    for mount in _docker_mounts():
        if mount.get("Type") != "bind":
            continue
        source = mount.get("Source")
        destination = mount.get("Destination")
        if not source or not destination:
            continue
        mount_host = _normalize_host_path(Path(source))
        try:
            rel = host_path.relative_to(mount_host)
        except ValueError:
            continue
        container_path = PurePosixPath(destination.rstrip("/")) / PurePosixPath(rel.as_posix())
        return str(container_path)

    raise ValueError(
        f"No Docker bind mount contains host path {host_path}. "
        f"Ensure the project is mounted into container '{config.DOCKER_CONTAINER_NAME}' "
        f"or set DOCKER_WORKSPACE in .env."
    )


def generate_export(comm_path: Path, mesh_path: Path, result_path: Path,
                     mesh_unit: int = 21, result_unit: int = 80,
                     time_limit: int = 300, memory_limit: int = 512) -> str:
    """
    Builds the .export file content, matching the format this Code_Aster
    version's run_aster expects: F <type> <path> <D/R> <unit>

    comm and rmed are referenced by basename; run_aster is started with cwd
    set to the outputs directory. mmed uses an absolute path (container path
    when executing via docker exec).
    """
    if uses_docker_execution():
        mesh_ref = host_to_container_path(Path(mesh_path))
    else:
        mesh_ref = str(Path(mesh_path).resolve())

    lines = [
        f"P time_limit {time_limit}",
        f"P memory_limit {memory_limit}",
        "P ncpus 1",
        "P mpi_nbcpu 1",
        "P mpi_nbnoeud 1",
        f"F comm {comm_path.name} D 1",
        f"F mmed {mesh_ref} D {mesh_unit}",
        f"F rmed {result_path.name} R {result_unit}",
    ]
    return "\n".join(lines)


def _docker_run_shell(container_export_file: str) -> str:
    """Shell snippet that activates the Spack view env, then runs run_aster.

    The image's profile.sh prepends a bare Python missing mpi4py/numpy; we
    override PATH and LD_LIBRARY_PATH to use the full Spack view afterwards.
    """
    aster = shlex.quote(config.CODE_ASTER_PATH)
    export_file = shlex.quote(container_export_file)
    return (
        f"ROOT=$(dirname $(dirname $(readlink -f {aster}))) && "
        f"VIEW=$(dirname $(dirname {aster})) && "
        f"export RUNASTER_ROOT=$ROOT && "
        f"source $ROOT/share/aster/profile.sh && "
        f"export PATH=$VIEW/bin:$PATH && "
        f"export LD_LIBRARY_PATH=$VIEW/lib:$VIEW/lib64:$LD_LIBRARY_PATH && "
        f"exec {aster} {export_file}"
    )


def _build_run_command(export_path: Path) -> tuple[list[str], str | None]:
    export_path = export_path.resolve()
    export_dir = export_path.parent

    if uses_docker_execution():
        container_export_dir = host_to_container_path(export_dir)
        container_export_file = f"{container_export_dir}/{export_path.name}"
        cmd = [
            _docker_bin(), "exec",
            "-w", container_export_dir,
            config.DOCKER_CONTAINER_NAME,
            "bash", "-lc",
            _docker_run_shell(container_export_file),
        ]
        return cmd, container_export_dir

    return [config.CODE_ASTER_PATH, str(export_path)], None


def run_code_aster(export_path: Path, timeout: int = 300) -> dict:
    """
    Executes Code_Aster via subprocess using the .export file.
    Returns {"success": bool, "log": str}.
    """
    cmd, container_cwd = _build_run_command(export_path)
    logger.info("Running: %s", cmd[0:5] if uses_docker_execution() else " ".join(cmd))
    if uses_docker_execution():
        logger.info("Container: %s  cwd: %s", config.DOCKER_CONTAINER_NAME, container_cwd)
        logger.debug("Docker shell: %s", cmd[-1])
    elif container_cwd:
        logger.info("Container working directory: %s", container_cwd)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        msg = f"Code_Aster timed out after {timeout} seconds"
        logger.error(msg)
        return {"success": False, "log": msg}
    except FileNotFoundError:
        if uses_docker_execution():
            msg = (
                f"Could not run docker exec for container '{config.DOCKER_CONTAINER_NAME}'. "
                f"Is Docker running and is the container name correct in .env?"
            )
        else:
            msg = (
                f"Could not find executable at {config.CODE_ASTER_PATH}. "
                f"Check CODE_ASTER_PATH in .env."
            )
        logger.error(msg)
        return {"success": False, "log": msg}

    full_log = (result.stdout or "") + "\n" + (result.stderr or "")
    logger.info("Code_Aster exit code: %s", result.returncode)

    if result.returncode != 0 or "<F>" in full_log or "_ABNORMAL_ABORT" in full_log:
        return {"success": False, "log": full_log[-4000:]}

    return {"success": True, "log": full_log[-500:]}
