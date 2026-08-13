"""
salome_tools.py
Headless Salome GEOM + SMESH scripts for MCP tools.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from src import config
from src.build_info import code_fingerprint
from src.runner import run_script

logger = logging.getLogger("salome_tools")

_SALOME_INIT = """
import salome
salome.salome_init_without_session()
from salome.geom import geomBuilder
from salome.smesh import smeshBuilder
import SMESH
geompy = geomBuilder.New()
smesh = smeshBuilder.New()
"""


def _out(path: str | None, name: str, suffix: str) -> Path:
    p = Path(path) if path else config.MESH_DIR / f"{name}_{uuid.uuid4().hex[:8]}{suffix}"
    if not p.is_absolute():
        p = config.MESH_DIR / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p.resolve()


def _run(body: str, outputs: dict[str, Path]) -> dict:
    run_id = uuid.uuid4().hex[:8]
    script = config.OUTPUT_DIR / f"salome_{run_id}.py"
    script.write_text(_SALOME_INIT + body, encoding="utf-8")
    result = run_script(script)
    if not result["success"]:
        return {"status": "error", "message": "Salome script failed", "log": result.get("log"), "run_id": run_id}
    missing = [k for k, p in outputs.items() if not p.exists()]
    if missing:
        return {"status": "error", "message": f"Missing outputs: {missing}", "log": result.get("log"), "run_id": run_id}
    return {
        "status": "success",
        "run_id": run_id,
        "code_fingerprint": code_fingerprint(),
        "outputs": {k: str(v) for k, v in outputs.items()},
    }


def build_box(dx: float, dy: float, dz: float, output_step: str | None = None) -> dict:
    step = _out(output_step, "box", ".step")
    body = f"""
box = geompy.MakeBoxDXDYDZ({float(dx)}, {float(dy)}, {float(dz)})
geompy.addToStudy(box, "Box")
if not geompy.ExportSTEP(box, {str(step)!r}, GEOM.LU_METER):
    raise RuntimeError("ExportSTEP failed")
"""
    return _run(body, {"step": step})


def build_cylinder(radius: float, height: float, output_step: str | None = None) -> dict:
    step = _out(output_step, "cylinder", ".step")
    body = f"""
cyl = geompy.MakeCylinderRH({float(radius)}, {float(height)})
geompy.addToStudy(cyl, "Cylinder")
import GEOM
if not geompy.ExportSTEP(cyl, {str(step)!r}, GEOM.LU_METER):
    raise RuntimeError("ExportSTEP failed")
"""
    return _run(body, {"step": step})


def mesh_box_tetra(
    dx: float,
    dy: float,
    dz: float,
    mesh_size: float,
    output_med: str | None = None,
    group_name: str = "SOLID",
) -> dict:
    med = _out(output_med, "mesh", ".med")
    body = f"""
box = geompy.MakeBoxDXDYDZ({float(dx)}, {float(dy)}, {float(dz)})
mesh_obj = smesh.Mesh(box, "BoxMesh")
algo = mesh_obj.Tetrahedron(smeshBuilder.NETGEN)
hyp = algo.MaxElementVolume({float(mesh_size) ** 3})
if not mesh_obj.Compute():
    raise RuntimeError("Mesh computation failed")
grp = mesh_obj.CreateGroup(grpType=SMESH.VOLUME, name={group_name!r})
grp.Add(mesh_obj.GetElementsByType(SMESH.VOLUME))
if not mesh_obj.ExportMED({str(med)!r}, auto_groups=0, version=40, overwrite=True):
    raise RuntimeError("ExportMED failed")
"""
    return _run(body, {"med": med})


def mesh_cylinder_tetra(
    radius: float,
    height: float,
    mesh_size: float,
    output_med: str | None = None,
) -> dict:
    med = _out(output_med, "cyl_mesh", ".med")
    body = f"""
cyl = geompy.MakeCylinderRH({float(radius)}, {float(height)})
mesh_obj = smesh.Mesh(cyl, "CylMesh")
algo = mesh_obj.Tetrahedron(smeshBuilder.NETGEN)
hyp = algo.MaxElementVolume({float(mesh_size) ** 3})
if not mesh_obj.Compute():
    raise RuntimeError("Mesh computation failed")
if not mesh_obj.ExportMED({str(med)!r}, auto_groups=0, version=40, overwrite=True):
    raise RuntimeError("ExportMED failed")
"""
    return _run(body, {"med": med})


def mesh_step_file(
    step_path: str,
    mesh_size: float,
    output_med: str | None = None,
) -> dict:
    step = Path(step_path)
    if not step.exists():
        return {"status": "error", "message": f"STEP not found: {step_path}"}
    med = _out(output_med, "step_mesh", ".med")
    body = f"""
import GEOM
shape = geompy.ImportSTEP({str(step.resolve())!r}, True, False)
mesh_obj = smesh.Mesh(shape, "ImportedMesh")
algo = mesh_obj.Tetrahedron(smeshBuilder.NETGEN)
algo.MaxElementVolume({float(mesh_size) ** 3})
if not mesh_obj.Compute():
    raise RuntimeError("Mesh computation failed")
if not mesh_obj.ExportMED({str(med)!r}, auto_groups=0, version=40, overwrite=True):
    raise RuntimeError("ExportMED failed")
"""
    return _run(body, {"med": med})
