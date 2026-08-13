#!/usr/bin/env python3
"""
Piston first-pass FEA (local, no Claude) — maps design steps 1-7 to Gmsh + Code_Aster + PNG.

Usage:
    python scripts/piston_first_pass_fea.py
    python scripts/piston_first_pass_fea.py --bore-mm 86 --stroke-mm 86 --redline-rpm 7200
    python scripts/piston_first_pass_fea.py --mesh-only
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _import_project_module(project: str, module: str):
    """Import a module from gmsh-mcp-server / ams-mcp-server without cross-project clashes."""
    import importlib
    from dotenv import load_dotenv

    root = REPO / project
    load_dotenv(root / ".env")
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    to_drop = [k for k in sys.modules if k == "src" or k.startswith("src.")]
    for k in to_drop:
        del sys.modules[k]
    return importlib.import_module(module)

# Reference revolved profile (mm): radius vs axial z — skirt + crown sketch from docs
REFERENCE_PROFILE = [
    [25, 0],
    [25, 40],
    [20, 45],
    [20, 60],
    [25, 60],
    [25, 80],
    [15, 80],
    [15, 0],
]
REF_MAX_RADIUS_MM = 25.0
REF_HEIGHT_MM = 80.0

# Forged 2618-T61 (step 4)
MATERIAL_2618 = {
    "E": 71700.0,
    "NU": 0.33,
    "yield_strength_mpa": 370.0,
}

INCH_MM = 25.4

# Default baseline: GM LS3–class NA V8 (common reference for bore/stroke/rod/mass)
#   4.065" bore × 3.622" stroke, 10.7:1, 6600 rpm, 6.098" rod, ~430 g piston+pin
V8_LS3_CLASS = {
    "bore_mm": 103.25,
    "stroke_mm": 92.0,
    "cr": 10.7,
    "redline_rpm": 6600.0,
    "rod_mm": 6.098 * INCH_MM,  # 154.9 mm
    "piston_mass_g": 430.0,
    "label": "LS3-class NA V8 (GM Gen IV, representative)",
}


def scale_profile(bore_mm: float, piston_height_mm: float) -> list[list[float]]:
    r_scale = (bore_mm / 2.0) / REF_MAX_RADIUS_MM
    z_scale = piston_height_mm / REF_HEIGHT_MM
    return [[r * r_scale, z * z_scale] for r, z in REFERENCE_PROFILE]


def step1_baseline(bore_mm: float, stroke_mm: float, cr: float, redline_rpm: float) -> dict:
    mean_piston_speed_m_s = (2.0 * (stroke_mm / 1000.0) * redline_rpm) / 60.0
    return {
        "bore_mm": bore_mm,
        "stroke_mm": stroke_mm,
        "compression_ratio": cr,
        "redline_rpm": redline_rpm,
        "mean_piston_speed_m_s": round(mean_piston_speed_m_s, 2),
        "durability_note": (
            "OK for NA street (<~22 m/s)"
            if mean_piston_speed_m_s <= 22
            else "High mean speed — verify material and skirt design"
        ),
    }


def step2_gas_load(bore_mm: float, peak_pressure_mpa: float) -> dict:
    crown_area_mm2 = math.pi * (bore_mm / 2.0) ** 2
    peak_force_n = peak_pressure_mpa * crown_area_mm2  # MPa * mm² = N
    return {
        "peak_cylinder_pressure_mpa": peak_pressure_mpa,
        "crown_area_mm2": round(crown_area_mm2, 2),
        "peak_gas_force_n": round(peak_force_n, 1),
    }


def step3_inertial_load(
    stroke_mm: float,
    redline_rpm: float,
    rod_mm: float,
    piston_mass_g: float,
) -> dict:
    omega = 2.0 * math.pi * redline_rpm / 60.0
    stroke_m = stroke_mm / 1000.0
    rod_m = rod_mm / 1000.0
    # Peak piston acceleration near TDC (approximate slider-crank)
    a_peak = omega**2 * (stroke_m / 2.0) * (1.0 + stroke_m / (2.0 * rod_m))
    mass_kg = piston_mass_g / 1000.0
    inertial_force_n = mass_kg * a_peak
    return {
        "rod_length_mm": rod_mm,
        "piston_mass_g": piston_mass_g,
        "peak_acceleration_m_s2": round(a_peak, 1),
        "peak_inertial_force_n": round(inertial_force_n, 1),
    }


def step5_geometry_hints(bore_mm: float) -> dict:
    crown_thickness_min = 0.12 * bore_mm
    crown_thickness_max = 0.18 * bore_mm
    return {
        "suggested_crown_thickness_mm": f"{crown_thickness_min:.1f}–{crown_thickness_max:.1f}",
        "piston_height_mm_default": round(REF_HEIGHT_MM * (bore_mm / (2 * REF_MAX_RADIUS_MM)), 1),
    }


def run_mesh(bore_mm: float, piston_height_mm: float, mesh_size: float, out_path: Path) -> dict:
    gmsh_tools = _import_project_module("gmsh-mcp-server", "src.gmsh_tools")

    profile = scale_profile(bore_mm, piston_height_mm)
    return gmsh_tools.build_revolved_solid(
        profile_points=profile,
        axis_point=[0, 0, 0],
        axis_direction=[0, 0, 1],
        mesh_size=mesh_size,
        output_path=str(out_path),
    )


def run_fea(mesh_path: Path, gas_force_n: float, use_inertial: bool, inertial_force_n: float) -> dict:
    aster_config = _import_project_module("ams-mcp-server", "src.config")
    code_aster_tool = _import_project_module("ams-mcp-server", "src.code_aster_tool")
    aster_config.validate_config()
    load_n = max(gas_force_n, inertial_force_n) if use_inertial else gas_force_n
    governing = "gas+inertial (max)" if use_inertial and inertial_force_n > gas_force_n else "gas pressure"
    if use_inertial and inertial_force_n > gas_force_n:
        governing = "inertial (max)"

    result = code_aster_tool.run_structural_analysis(
        mesh_path=str(Path(mesh_path).resolve()),
        model_type="3D",
        material=MATERIAL_2618,
        boundary_conditions=[{"group_name": "FACE_INF", "fixed_dofs": ["DX", "DY", "DZ"]}],
        loads=[{"group_name": "FACE_SUP", "direction": "FZ", "magnitude": load_n}],
    )
    result["governing_load_n"] = round(load_n, 1)
    result["governing_case"] = governing
    return result


def run_render(rmed_path: Path, png_path: Path) -> dict:
    _import_project_module("paraview-mcp-server", "src.config").validate_config()
    render_tools = _import_project_module("paraview-mcp-server", "src.render_tools")
    return render_tools.render_stress_contour(
        result_path=str(rmed_path),
        output_path=str(png_path),
        title="Piston first-pass — Von Mises stress",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Piston first-pass FEA (steps 1–7, local)")
    parser.add_argument(
        "--preset",
        choices=("v8",),
        default="v8",
        help="Engine preset (default: v8 = LS3-class NA V8)",
    )
    parser.add_argument("--bore-mm", type=float, default=V8_LS3_CLASS["bore_mm"], help="Cylinder bore (mm)")
    parser.add_argument("--stroke-mm", type=float, default=V8_LS3_CLASS["stroke_mm"], help="Stroke (mm)")
    parser.add_argument("--cr", type=float, default=V8_LS3_CLASS["cr"], help="Compression ratio")
    parser.add_argument("--redline-rpm", type=float, default=V8_LS3_CLASS["redline_rpm"], help="Redline RPM")
    parser.add_argument(
        "--peak-pressure-mpa",
        type=float,
        default=None,
        help="Peak cylinder pressure (MPa); default ~7.5 MPa for CR 11 NA",
    )
    parser.add_argument(
        "--rod-mm",
        type=float,
        default=V8_LS3_CLASS["rod_mm"],
        help="Rod center-to-center length (mm); default 6.098 in (LS3)",
    )
    parser.add_argument(
        "--piston-mass-g",
        type=float,
        default=V8_LS3_CLASS["piston_mass_g"],
        help="Piston + pin mass (g); default ~430 g forged V8",
    )
    parser.add_argument("--piston-height-mm", type=float, default=None, help="Axial piston height (mm)")
    parser.add_argument("--mesh-size", type=float, default=3.0, help="Gmsh characteristic length (mm)")
    parser.add_argument("--fos-target", type=float, default=2.0, help="Target factor of safety vs yield")
    parser.add_argument("--include-inertial", action="store_true", help="Use max(gas, inertial) for FEA load")
    parser.add_argument("--mesh-only", action="store_true", help="Stop after Gmsh mesh export")
    parser.add_argument("--skip-render", action="store_true", help="Skip ParaView PNG step")
    args = parser.parse_args()

    peak_mpa = args.peak_pressure_mpa if args.peak_pressure_mpa is not None else min(9.0, 5.0 + 0.25 * args.cr)

    print(f"\nPreset: {V8_LS3_CLASS['label']}")
    print(f"  {args.bore_mm/INCH_MM:.3f}\" bore × {args.stroke_mm/INCH_MM:.3f}\" stroke  |  "
          f"CR {args.cr}  |  {args.redline_rpm:.0f} rpm  |  rod {args.rod_mm/INCH_MM:.3f}\"  |  "
          f"{args.piston_mass_g:.0f} g piston+pin")

    baseline = step1_baseline(args.bore_mm, args.stroke_mm, args.cr, args.redline_rpm)
    gas = step2_gas_load(args.bore_mm, peak_mpa)
    inertial = step3_inertial_load(args.stroke_mm, args.redline_rpm, args.rod_mm, args.piston_mass_g)
    geom = step5_geometry_hints(args.bore_mm)
    piston_h = args.piston_height_mm or geom["piston_height_mm_default"]

    print("\n=== Step 1 — Engine baseline ===")
    print(json.dumps(baseline, indent=2))

    print("\n=== Step 2 — Peak gas load (FEA input) ===")
    print(json.dumps(gas, indent=2))

    print("\n=== Step 3 — Inertial load at redline ===")
    print(json.dumps(inertial, indent=2))
    if inertial["peak_inertial_force_n"] > gas["peak_gas_force_n"]:
        print("  >> Inertial exceeds gas — pin/skirt may govern; use --include-inertial for FEA")

    print("\n=== Step 4 — Material (2618-T61) ===")
    print(json.dumps(MATERIAL_2618, indent=2))

    print("\n=== Step 5 — Geometry hints ===")
    print(json.dumps({**geom, "piston_height_mm_used": piston_h}, indent=2))

    mesh_dir = REPO / "gmsh-mcp-server" / "meshes"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    mesh_path = mesh_dir / "piston_first_pass.med"

    print("\n=== Step 6 — Gmsh mesh ===")
    mesh_result = run_mesh(args.bore_mm, piston_h, args.mesh_size, mesh_path)
    print(json.dumps(mesh_result, indent=2, default=str))
    if mesh_result.get("status") != "success":
        return 1
    if args.mesh_only:
        print(f"\nMesh only — saved to {mesh_path}")
        return 0

    print("\n=== Step 7 — Code_Aster FEA ===")
    fea = run_fea(
        mesh_path,
        gas["peak_gas_force_n"],
        args.include_inertial,
        inertial["peak_inertial_force_n"],
    )
    print(json.dumps({k: fea[k] for k in fea if k != "log"}, indent=2))
    if fea.get("status") != "success":
        if fea.get("log"):
            print("\n--- log tail ---\n", fea["log"][-2000:])
        return 1

    fos = fea.get("factor_of_safety")
    yield_mpa = MATERIAL_2618["yield_strength_mpa"]
    print(f"\n--- Step 7 verdict ---")
    print(f"  Governing load : {fea.get('governing_case')} ({fea.get('governing_load_n')} N)")
    print(f"  Max stress     : {fea.get('max_stress_mpa')} MPa  (yield {yield_mpa} MPa)")
    print(f"  FoS            : {fos}  (target {args.fos_target}+)")
    print(f"  {fea.get('engineering_verdict')}")

    if not args.skip_render:
        rmed_candidates = list((REPO / "ams-mcp-server" / "outputs").glob(f"run_{fea.get('run_id')}*.rmed"))
        if not rmed_candidates:
            rmed_candidates = sorted(
                (REPO / "ams-mcp-server" / "outputs").glob("run_*.rmed"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        if rmed_candidates:
            render_dir = REPO / "paraview-mcp-server" / "renders"
            render_dir.mkdir(parents=True, exist_ok=True)
            png_path = render_dir / "piston_first_pass_stress.png"
            print("\n=== Step 7b — Stress PNG ===")
            png_result = run_render(rmed_candidates[0], png_path)
            print(json.dumps(png_result, indent=2))
            if png_result.get("status") == "success":
                print(f"\nFINAL PRODUCT: {png_path}")
        else:
            print("\n=== Step 7b — Stress PNG ===")
            print(f"No .rmed found for run_id {fea.get('run_id')} — render skipped.")

    print("\n=== Step 8 (later) ===")
    print("  Full CAD (FreeCAD), ring grooves, thermal coupling — not in this script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
