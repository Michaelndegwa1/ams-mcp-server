"""
render_tools.py
Orchestrator: pick render backend and produce PNG images from .rmed results.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from src import config
from src.build_info import code_fingerprint
from src import matplotlib_renderer
from src import paraview_runner
from src.med_reader import inspect_result_file

logger = logging.getLogger("render_tools")

_STRESS_FIELDS = ("von_mises", "stress", "von_mises_mpa")
_DISPL_FIELDS = ("displacement", "displacement_mm", "depl")


def _choose_backend(requested: str | None = None) -> str:
    backend = (requested or config.RENDER_BACKEND or "auto").lower()
    if backend == "auto":
        return "paraview" if config.pvpython_available() else "matplotlib"
    return backend


def _default_output(name: str) -> Path:
    run_id = str(uuid.uuid4())[:8]
    return config.RENDER_DIR / f"{name}_{run_id}.png"


def render_stress_contour(
    result_path: str,
    output_path: str | None = None,
    backend: str | None = None,
    title: str | None = None,
) -> dict:
    out = Path(output_path) if output_path else _default_output("stress")
    chosen = _choose_backend(backend)

    if chosen == "paraview":
        result = paraview_runner.render_with_paraview(
            result_path=result_path,
            output_path=str(out),
            field_name="von Mises Stress",
        )
        if result.get("status") == "success":
            result["code_fingerprint"] = code_fingerprint()
            return result
        logger.warning("ParaView render failed, falling back to matplotlib: %s", result.get("message"))
        chosen = "matplotlib"

    result = matplotlib_renderer.render_field_scatter(
        result_path=result_path,
        output_path=str(out),
        field="von_mises",
        title=title,
    )
    result["code_fingerprint"] = code_fingerprint()
    result["backend_requested"] = backend or config.RENDER_BACKEND
    result["backend_used"] = chosen
    return result


def render_displacement_contour(
    result_path: str,
    output_path: str | None = None,
    backend: str | None = None,
    title: str | None = None,
) -> dict:
    out = Path(output_path) if output_path else _default_output("displacement")
    chosen = _choose_backend(backend)

    if chosen == "paraview":
        result = paraview_runner.render_with_paraview(
            result_path=result_path,
            output_path=str(out),
            field_name="Displacement",
        )
        if result.get("status") == "success":
            result["code_fingerprint"] = code_fingerprint()
            return result
        logger.warning("ParaView render failed, falling back to matplotlib: %s", result.get("message"))
        chosen = "matplotlib"

    result = matplotlib_renderer.render_field_scatter(
        result_path=result_path,
        output_path=str(out),
        field="displacement",
        title=title,
    )
    result["code_fingerprint"] = code_fingerprint()
    result["backend_requested"] = backend or config.RENDER_BACKEND
    result["backend_used"] = chosen
    return result
