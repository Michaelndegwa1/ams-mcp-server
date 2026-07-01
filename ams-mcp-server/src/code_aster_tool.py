"""
code_aster_tool.py
Orchestrator: wires comm_generator, runner, results_parser, and
validation_engine into one function the MCP server calls.

CHANGE FROM ORIGINAL: Code_Aster's FORCE_FACE keyword expects a surface
traction (N/mm^2), not a total resultant force in Newtons. Previously,
the raw `magnitude` field (documented and intended as "Force in
Newtons") was passed straight through to FORCE_FACE, which silently
applied `magnitude` N/mm^2 to every point of the loaded face - i.e. the
ACTUAL applied force was `magnitude * face_area`, not `magnitude`.

Fix: for every load, compute the true area of its target face group
directly from the mesh (mesh_utils.compute_face_area, which integrates
over the real - possibly curved/quadratic - element geometry via Gauss
quadrature), then convert:

    pressure (N/mm^2) = intended_total_force (N) / face_area (mm^2)

before handing anything to generate_comm. This makes `magnitude` behave
as documented (a total force in Newtons) for ANY mesh, not just one
with a precomputed/hardcoded area.
"""
import uuid
import logging
from pathlib import Path

from pydantic import ValidationError

from src import config
from src import mesh_utils
from src.models import StructuralAnalysisInput, Load
from src.comm_generator import generate_comm
from src.runner import generate_export, run_code_aster, resolve_host_mesh_path
from src.results_parser import parse_results
from src.build_info import code_fingerprint
from src.validation_engine import build_verdict

logger = logging.getLogger("code_aster_tool")


def _convert_loads_to_pressures(params: StructuralAnalysisInput) -> tuple[list[Load], dict[str, float]]:
    """Returns Load objects with `.magnitude` as surface traction (N/mm^2),
    plus a cache of mesh-derived face areas (mm^2) per group name."""
    converted: list[Load] = []
    area_cache: dict[str, float] = {}
    for ld in params.loads:
        if ld.group_name not in area_cache:
            area = mesh_utils.compute_face_area(params.mesh_path, ld.group_name)
            if area <= 0:
                raise ValueError(
                    f"Computed non-positive area ({area}) for group '{ld.group_name}' "
                    f"in mesh {params.mesh_path} - refusing to divide by it."
                )
            area_cache[ld.group_name] = area
            logger.info(
                "Group '%s': computed area = %.6f mm^2 (intended force %.3f N -> traction %.6f N/mm^2)",
                ld.group_name,
                area,
                ld.magnitude,
                ld.magnitude / area,
            )
        area = area_cache[ld.group_name]
        pressure_value = ld.magnitude / area
        converted.append(
            Load(group_name=ld.group_name, direction=ld.direction, magnitude=pressure_value)
        )
    return converted, area_cache


def run_structural_analysis(mesh_path: str, model_type: str, material: dict,
                             boundary_conditions: list, loads: list) -> dict:
    """
    Full pipeline: validate -> compute face areas -> convert force to
    pressure -> generate .comm -> generate .export -> run Code_Aster ->
    parse results -> build verdict.

    Returns a dict. Always has a "status" key: "success" or "error".
    """
    # --- 1. Validate inputs ---
    try:
        host_mesh = resolve_host_mesh_path(mesh_path)
        params = StructuralAnalysisInput(
            mesh_path=str(host_mesh),
            model_type=model_type,
            material=material,
            boundary_conditions=boundary_conditions,
            loads=loads,
        )
        params.validate_mesh_exists()
    except (ValidationError, ValueError) as e:
        return {"status": "error", "message": f"Invalid input: {e}"}

    # --- 2. Convert total-force loads (N) into surface tractions (N/mm^2) ---
    try:
        load_pressures, area_cache = _convert_loads_to_pressures(params)
    except ValueError as e:
        return {"status": "error", "message": f"Failed computing face area for load: {e}"}

    # --- 3. Unique file paths for this run ---
    run_id = str(uuid.uuid4())[:8]
    comm_path = config.OUTPUT_DIR / f"run_{run_id}.comm"
    export_path = config.OUTPUT_DIR / f"run_{run_id}.export"
    result_path = config.OUTPUT_DIR / f"run_{run_id}.rmed"

    # --- 4. Generate .comm and .export ---
    try:
        comm_content = generate_comm(params, load_pressures, mesh_unit=21)
        comm_path.write_text(comm_content)

        export_content = generate_export(comm_path, Path(params.mesh_path), result_path, mesh_unit=21)
        export_path.write_text(export_content)
    except Exception as e:
        return {"status": "error", "message": f"Failed generating input files: {e}"}

    # --- 5. Run Code_Aster ---
    run_result = run_code_aster(export_path)
    if not run_result["success"]:
        return {
            "status": "error",
            "message": "Code_Aster execution failed",
            "log": run_result["log"],
            "run_id": run_id,
        }

    # --- 6. Parse results ---
    yield_strength = params.material.yield_strength_mpa or config.DEFAULT_YIELD_STRENGTH_MPA
    try:
        parsed = parse_results(result_path, yield_strength_mpa=yield_strength)
    except Exception as e:
        return {"status": "error", "message": f"Failed parsing results: {e}", "run_id": run_id}

    if parsed["max_displacement_mm"] is None and parsed["max_stress_mpa"] is None:
        return {
            "status": "error",
            "message": "Code_Aster ran successfully but no displacement or stress data could be extracted. "
                       "Run inspect_structure() against the .rmed file to locate the correct field paths.",
            "run_id": run_id,
        }

    # --- 7. Build verdict (Concept 03 layer) ---
    verdict = build_verdict(
        max_displacement_mm=parsed["max_displacement_mm"],
        max_stress_mpa=parsed["max_stress_mpa"],
        factor_of_safety=parsed["factor_of_safety"],
    )

    return {
        "status": "success",
        "run_id": run_id,
        "code_fingerprint": code_fingerprint(),
        "max_displacement_mm": verdict["max_displacement_mm"],
        "max_stress_mpa": verdict["max_stress_mpa"],
        "factor_of_safety": verdict["factor_of_safety"],
        "node_count": parsed["node_count"],
        "safety_status": verdict["status"],
        "engineering_verdict": verdict["verdict"],
        "applied_face_areas_mm2": {
            group: round(area, 4) for group, area in area_cache.items()
        },
    }
