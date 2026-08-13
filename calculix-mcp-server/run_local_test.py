"""Local CalculiX pipeline test."""
from __future__ import annotations

import json
import sys

from src import config
from src.calculix_tool import run_structural_analysis


def main() -> None:
    config.validate_config()
    mesh = sys.argv[1] if len(sys.argv) > 1 else "examples/test_beam.inp"

    result = run_structural_analysis(
        mesh_path=mesh,
        material={"E": 210000.0, "NU": 0.3, "yield_strength_mpa": 235.0},
        boundary_conditions=[{"group_name": "FACE_INF", "fixed_dofs": ["DX", "DY", "DZ"]}],
        loads=[{"group_name": "FACE_SUP", "direction": "FZ", "magnitude": 500.0}],
        solid_elset="SOLID",
    )
    print(json.dumps(result, indent=2))
    if result.get("status") != "success":
        sys.exit(1)
    print(f"\nSUCCESS — {result.get('engineering_verdict')}")


if __name__ == "__main__":
    main()
