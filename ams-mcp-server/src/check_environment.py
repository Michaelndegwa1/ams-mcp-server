"""
check_environment.py
One-shot diagnostic: are Python/MCP and Code_Aster in the same environment?

Run before a demo or after changing .env / Claude Desktop config:

    python -m src.check_environment
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from src import config


def _run(cmd: list[str], timeout: int = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _inside_docker() -> bool:
    if os.path.exists("/.dockerenv"):
        return True
    cgroup = Path("/proc/1/cgroup")
    if cgroup.exists():
        try:
            content = cgroup.read_text(encoding="utf-8", errors="ignore")
            return "docker" in content or "containerd" in content
        except OSError:
            pass
    return False


def _code_aster_exists_in_container(container: str, aster_path: str) -> tuple[bool, str]:
    if not _docker_available():
        return False, "docker CLI not found on PATH"

    try:
        result = _run(
            ["docker", "exec", container, "test", "-x", aster_path],
            timeout=20,
        )
        if result.returncode == 0:
            return True, f"executable found in container '{container}'"

        which = _run(
            ["docker", "exec", container, "sh", "-lc", "which run_aster as_run 2>/dev/null | head -1"],
            timeout=20,
        )
        hint = (which.stdout or which.stderr or "").strip()
        if hint:
            return False, f"not at {aster_path}; container has: {hint}"
        return False, f"not found at {aster_path} inside container '{container}'"
    except subprocess.TimeoutExpired:
        return False, f"timed out probing container '{container}'"
    except FileNotFoundError:
        return False, "docker CLI not found on PATH"
    except Exception as exc:
        return False, str(exc)


def _container_running(container: str) -> tuple[bool, str]:
    if not _docker_available():
        return False, "docker CLI not found on PATH"
    try:
        result = _run(["docker", "inspect", "-f", "{{.State.Running}}", container])
        if result.returncode != 0:
            msg = (result.stderr or result.stdout or "").strip()
            return False, msg or f"container '{container}' not found"
        running = (result.stdout or "").strip().lower() == "true"
        return running, "running" if running else "exists but not running"
    except Exception as exc:
        return False, str(exc)


def gather_environment_report() -> dict:
    # Keep Unix solver paths intact — Path("/opt/...") becomes "\opt\..." on Windows.
    aster_path_str = config.CODE_ASTER_PATH
    if aster_path_str.startswith("/"):
        aster_exists_here = os.path.isfile(aster_path_str)
    else:
        aster_exists_here = Path(aster_path_str).exists()
    container = config.DOCKER_CONTAINER_NAME
    mesh_probe = Path("examples/test_beam.med")

    report = {
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "cwd": str(Path.cwd().resolve()),
        "inside_docker": _inside_docker(),
        "code_aster_path": aster_path_str,
        "code_aster_exists_here": aster_exists_here,
        "output_dir": str(config.OUTPUT_DIR.resolve()),
        "output_dir_exists": config.OUTPUT_DIR.exists(),
        "docker_cli_available": _docker_available(),
        "docker_container_name": container,
        "docker_workspace": config.DOCKER_WORKSPACE,
        "test_mesh_path": str(mesh_probe.resolve()) if mesh_probe.exists() else None,
        "verdict": "",
        "recommendation": "",
    }

    if aster_exists_here:
        report["verdict"] = "READY - same environment"
        report["recommendation"] = (
            "CODE_ASTER_PATH exists where this Python process runs. "
            "run_local_test.py and the MCP server can call Code_Aster directly."
        )
        return report

    if container:
        running, run_detail = _container_running(container)
        report["docker_container_running"] = running
        report["docker_container_status"] = run_detail

        if running:
            in_container, detail = _code_aster_exists_in_container(container, aster_path_str)
            report["code_aster_exists_in_container"] = in_container
            report["code_aster_container_detail"] = detail

            if in_container:
                from src.runner import uses_docker_execution

                if uses_docker_execution():
                    report["verdict"] = "READY - split setup (docker exec bridge)"
                    report["recommendation"] = (
                        f"Code_Aster runs in container '{container}' via docker exec. "
                        "run_local_test.py and the MCP server can run from Windows."
                    )
                else:
                    report["verdict"] = "SPLIT - host Python, Code_Aster in Docker"
                    report["recommendation"] = (
                        f"Code_Aster is in container '{container}' but this Python is on "
                        f"{platform.system()}. Set DOCKER_CONTAINER_NAME in .env so "
                        "runner.py can bridge via docker exec."
                    )
            else:
                report["verdict"] = "MISCONFIGURED - container reachable, solver path wrong"
                report["recommendation"] = (
                    f"Container '{container}' is running but {aster_path_str} was not found. "
                    "Run: docker exec <container> which run_aster"
                )
        else:
            report["code_aster_exists_in_container"] = False
            report["verdict"] = "BLOCKED - Docker container not running"
            report["recommendation"] = (
                f"Start container '{container}' ({run_detail}), then re-run this check."
            )
    else:
        report["verdict"] = "BLOCKED - Code_Aster not on host, no container configured"
        report["recommendation"] = (
            "Either run this project inside the Code_Aster Docker image, or set "
            "DOCKER_CONTAINER_NAME in .env and use a docker exec wrapper in runner.py."
        )

    return report


def print_environment_report() -> int:
    report = gather_environment_report()

    print("=== AMS MCP environment check ===\n")

    print("Python")
    print(f"  executable : {report['python_executable']}")
    print(f"  version    : {report['python_version']}")
    print(f"  cwd        : {report['cwd']}")
    print(f"  platform   : {report['platform_system']} {report['platform_release']}")
    print(f"  in docker  : {report['inside_docker']}")

    print("\nCode_Aster")
    print(f"  CODE_ASTER_PATH : {report['code_aster_path']}")
    print(f"  exists here     : {report['code_aster_exists_here']}")

    print("\nPaths")
    print(f"  OUTPUT_DIR      : {report['output_dir']} (exists: {report['output_dir_exists']})")
    print(f"  test_beam.med   : {report['test_mesh_path'] or 'not found at examples/test_beam.med'}")

    print("\nDocker")
    print(f"  CLI available        : {report['docker_cli_available']}")
    print(f"  DOCKER_CONTAINER_NAME: {report['docker_container_name'] or '(not set)'}")
    if report.get("docker_workspace"):
        print(f"  DOCKER_WORKSPACE     : {report['docker_workspace']}")
    if "docker_container_running" in report:
        print(f"  container status     : {report.get('docker_container_status')}")
    if "code_aster_exists_in_container" in report:
        print(f"  solver in container  : {report['code_aster_exists_in_container']}")
        if report.get("code_aster_container_detail"):
            print(f"  detail               : {report['code_aster_container_detail']}")

    print(f"\nVERDICT: {report['verdict']}")
    print(f"\nNext step: {report['recommendation']}\n")

    if report["verdict"].startswith("READY"):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(print_environment_report())
