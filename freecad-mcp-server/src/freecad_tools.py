"""
freecad_tools.py
Generate and run headless FreeCAD Python scripts (Part workbench).
"""
from __future__ import annotations

import logging
import textwrap
import uuid
from pathlib import Path

from src import config
from src.build_info import code_fingerprint
from src.runner import run_script

logger = logging.getLogger("freecad_tools")

_SCRIPT_HEADER = textwrap.dedent("""
    import FreeCAD as App
    import Part
    import Mesh
    doc = App.newDocument("mcp_job")
""")


def _resolve_out(path: str | None, default_name: str, suffix: str) -> Path:
    if path:
        p = Path(path)
        if not p.is_absolute():
            p = config.CAD_DIR / p
    else:
        p = config.CAD_DIR / f"{default_name}_{uuid.uuid4().hex[:8]}{suffix}"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p.resolve()


def _run_job(script_body: str, outputs: dict[str, Path]) -> dict:
    run_id = uuid.uuid4().hex[:8]
    script_path = config.OUTPUT_DIR / f"freecad_{run_id}.py"
    script_path.write_text(_SCRIPT_HEADER + script_body, encoding="utf-8")

    result = run_script(script_path)
    if not result["success"]:
        return {"status": "error", "message": "FreeCAD script failed", "log": result.get("log"), "run_id": run_id}

    missing = [k for k, p in outputs.items() if not p.exists()]
    if missing:
        return {
            "status": "error",
            "message": f"Expected output files missing: {missing}",
            "log": result.get("log"),
            "run_id": run_id,
        }

    payload = {
        "status": "success",
        "run_id": run_id,
        "code_fingerprint": code_fingerprint(),
        "outputs": {k: str(v) for k, v in outputs.items()},
    }
    return payload


def build_cylinder(
    radius: float,
    height: float,
    output_step: str | None = None,
    output_stl: str | None = None,
) -> dict:
    step = _resolve_out(output_step, "cylinder", ".step")
    stl = _resolve_out(output_stl, "cylinder", ".stl")
    fcstd = step.with_suffix(".FCStd")

    body = f"""
    cyl = doc.addObject("Part::Cylinder", "Cylinder")
    cyl.Radius = {float(radius)}
    cyl.Height = {float(height)}
    doc.recompute()
    Part.export([cyl], {step!r})
    Mesh.export([cyl], {stl!r})
    doc.saveAs({str(fcstd)!r})
    """
    return _run_job(body, {"step": step, "stl": stl, "fcstd": fcstd})


def build_box(
    length: float,
    width: float,
    height: float,
    output_step: str | None = None,
) -> dict:
    step = _resolve_out(output_step, "box", ".step")
    fcstd = step.with_suffix(".FCStd")
    body = f"""
    box = doc.addObject("Part::Box", "Box")
    box.Length = {float(length)}
    box.Width = {float(width)}
    box.Height = {float(height)}
    doc.recompute()
    Part.export([box], {step!r})
    doc.saveAs({str(fcstd)!r})
    """
    return _run_job(body, {"step": step, "fcstd": fcstd})


def build_revolved_solid(
    profile_points: list[list[float]],
    output_step: str | None = None,
    angle_degrees: float = 360.0,
) -> dict:
    """Revolve an XZ profile [radius, z] around the Z axis (piston / shaft geometry)."""
    if len(profile_points) < 3:
        return {"status": "error", "message": "profile_points needs at least 3 [radius, z] pairs"}

    step = _resolve_out(output_step, "revolved", ".step")
    fcstd = step.with_suffix(".FCStd")
    pts_repr = repr([(float(r), float(z)) for r, z in profile_points])

    body = f"""
    profile = {pts_repr}
    vectors = [App.Vector(r, 0, z) for r, z in profile]
    if vectors[0] != vectors[-1]:
        vectors.append(vectors[0])
    wire = Part.makePolygon(vectors)
    face = Part.Face(wire)
    solid = face.revolve(App.Vector(0, 0, 0), App.Vector(0, 0, 1), {float(angle_degrees)})
    obj = doc.addObject("Part::Feature", "RevolvedSolid")
    obj.Shape = solid
    doc.recompute()
    Part.export([obj], {step!r})
    doc.saveAs({str(fcstd)!r})
    """
    return _run_job(body, {"step": step, "fcstd": fcstd})


def add_ring_groove(
    base_step_path: str,
    groove_radius: float,
    groove_depth: float,
    groove_z: float,
    output_step: str | None = None,
) -> dict:
    """Cut a torus-based ring groove into an existing STEP body (simplified piston groove)."""
    base = Path(base_step_path)
    if not base.exists():
        return {"status": "error", "message": f"Base STEP not found: {base_step_path}"}

    step = _resolve_out(output_step, "grooved", ".step")
    fcstd = step.with_suffix(".FCStd")
    body = f"""
    import os
    shape = Part.read({str(base.resolve())!r})
    base_obj = doc.addObject("Part::Feature", "Base")
    base_obj.Shape = shape
    groove = doc.addObject("Part::Torus", "GrooveCutter")
    groove.Radius1 = {float(groove_radius)}
    groove.Radius2 = {float(groove_depth)}
    groove.Placement = App.Placement(App.Vector({float(groove_radius)}, 0, {float(groove_z)}), App.Rotation())
    doc.recompute()
    cut = doc.addObject("Part::Cut", "Cut")
    cut.Base = base_obj
    cut.Tool = groove
    doc.recompute()
    Part.export([cut], {step!r})
    doc.saveAs({str(fcstd)!r})
    """
    return _run_job(body, {"step": step, "fcstd": fcstd})
