"""
paraview_runner.py
Invoke ParaView headlessly via pvpython to render MED result contours.
"""
from __future__ import annotations

import logging
import subprocess
import textwrap
import uuid
from pathlib import Path

from src import config
from src.med_reader import resolve_result_path

logger = logging.getLogger("paraview_runner")

_PV_SCRIPT = textwrap.dedent(
    """
    import sys
    from paraview.simple import *

    input_path, output_path, field_name = sys.argv[1], sys.argv[2], sys.argv[3]

    paraview.simple._DisableFirstRenderCameraReset()
    reader = OpenDataFile(input_path)
    if reader is None:
        raise RuntimeError(f"ParaView could not open {{input_path}}")

    UpdatePipeline()
    display = Show(reader)
    ColorBy(display, ("POINTS", field_name))
    display.RescaleTransferFunctionToDataRange(True)
    Render()
    SaveScreenshot(output_path, ImageResolution=[1600, 1200])
    """
).strip()


def render_with_paraview(
    result_path: str,
    output_path: str,
    field_name: str = "von Mises Stress",
) -> dict:
    pvpython = config.resolve_pvpython()
    if not pvpython:
        return {"status": "error", "message": "pvpython not found. Set PVPYTHON_PATH in .env"}

    src = resolve_result_path(result_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    run_id = str(uuid.uuid4())[:8]
    script_path = config.OUTPUT_DIR / f"pv_render_{run_id}.py"
    script_path.write_text(_PV_SCRIPT, encoding="utf-8")

    cmd = [pvpython, str(script_path), str(src), str(out.resolve()), field_name]
    logger.info("Running ParaView render: %s", cmd)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "ParaView render timed out after 180s"}
    except FileNotFoundError:
        return {"status": "error", "message": f"Could not execute {pvpython}"}

    if result.returncode != 0 or not out.exists():
        log = (result.stdout or "") + "\n" + (result.stderr or "")
        return {
            "status": "error",
            "message": "ParaView render failed",
            "log": log[-3000:],
        }

    return {
        "status": "success",
        "backend": "paraview",
        "output_path": str(out.resolve()),
        "field": field_name,
    }
