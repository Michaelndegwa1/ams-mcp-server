"""
calculix_tool.py
Full CalculiX static analysis pipeline for MCP.
"""
from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from pydantic import ValidationError

from src import config
from src.build_info import code_fingerprint
from src.inp_generator import generate_inp
from src.inp_mesh_utils import compute_elset_area
from src.models import Load, StructuralAnalysisInput
from src.runner import resolve_host_mesh_path, run_calculix, uses_docker_execution, host_to_container_path
from src.frd_parser import parse_frd
from src.validation_engine import build_verdict

logger = logging.getLogger("calculix_tool")


def _convert_loads(params: StructuralAnalysisInput) -> tuple[list[Load], dict[str, float]]:
    converted: list[Load] = []
    areas: dict[str, float] = {}
    mesh = Path(params.mesh_path)
    for ld in params.loads:
        if ld.group_name not in areas:
            areas[ld.group_name] = compute_elset_area(mesh, ld.group_name)
        pressure = ld.magnitude / areas[ld.group_name]
        converted.append(Load(group_name=ld.group_name, direction=ld.direction, magnitude=pressure))
        logger.info(
            "Load '%s': %.3f N over %.4f mm^2 -> P=%.6f N/mm^2",
            ld.group_name,
            ld.magnitude,
            areas[ld.group_name],
            pressure,
        )
    return converted, areas


def run_structural_analysis(
    mesh_path: str,
    material: dict,
    boundary_conditions: list,
    loads: list,
    solid_elset: str = "SOLID",
) -> dict:
    try:
        host_mesh = resolve_host_mesh_path(mesh_path)
        params = StructuralAnalysisInput(
            mesh_path=str(host_mesh),
            material=material,
            boundary_conditions=boundary_conditions,
            loads=loads,
            solid_elset=solid_elset,
        )
        params.validate_mesh_exists()
    except (ValidationError, ValueError) as exc:
        return {"status": "error", "message": f"Invalid input: {exc}"}

    try:
        load_pressures, area_cache = _convert_loads(params)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    run_id = str(uuid.uuid4())[:8]
    work_dir = config.OUTPUT_DIR.resolve()
    mesh_copy = work_dir / f"run_{run_id}_mesh.inp"
    job_base = work_dir / f"run_{run_id}"
    job_inp = Path(f"{job_base}.inp")

    try:
        shutil.copy2(host_mesh, mesh_copy)
        if uses_docker_execution():
            include_ref = host_to_container_path(mesh_copy)
        else:
            include_ref = mesh_copy.name

        deck = generate_inp(params, load_pressures, mesh_include_path=include_ref, job_name=job_base.name)
        job_inp.write_text(deck, encoding="utf-8")
    except Exception as exc:
        return {"status": "error", "message": f"Failed generating .inp: {exc}"}

    run_result = run_calculix(job_base)
    if not run_result["success"]:
        return {
            "status": "error",
            "message": "CalculiX execution failed",
            "log": run_result.get("log"),
            "run_id": run_id,
        }

    frd_path = Path(run_result["frd_path"])
    yield_strength = params.material.yield_strength_mpa or config.DEFAULT_YIELD_STRENGTH_MPA
    try:
        parsed = parse_frd(frd_path, yield_strength_mpa=yield_strength)
    except Exception as exc:
        return {"status": "error", "message": f"Failed parsing FRD: {exc}", "run_id": run_id}

    verdict = build_verdict(
        parsed["max_displacement_mm"],
        parsed["max_stress_mpa"],
        parsed["factor_of_safety"],
    )

    return {
        "status": "success",
        "solver": "calculix",
        "run_id": run_id,
        "code_fingerprint": code_fingerprint(),
        "frd_path": str(frd_path),
        "max_displacement_mm": verdict["max_displacement_mm"],
        "max_stress_mpa": verdict["max_stress_mpa"],
        "factor_of_safety": verdict["factor_of_safety"],
        "safety_status": verdict["status"],
        "engineering_verdict": verdict["verdict"],
        "applied_face_areas_mm2": {k: round(v, 4) for k, v in area_cache.items()},
    }
