"""
run_local_test.py
Generate a sample cylinder mesh without MCP — verifies Gmsh pipeline end-to-end.

Usage:
    python run_local_test.py
    python run_local_test.py meshes/my_beam.med
"""
from __future__ import annotations

import json
import sys

from src import config
from src import gmsh_tools


def main() -> None:
    config.validate_config()
    output = sys.argv[1] if len(sys.argv) > 1 else "meshes/test_cylinder.med"

    # Simple steel-beam-like cylinder: r=5 mm, h=100 mm
    result = gmsh_tools.build_cylinder(
        radius=5.0,
        height=100.0,
        mesh_size=3.0,
        physical_groups={
            "volumes": {"SOLID": [1]},
            "surfaces": {"FACE_INF": [1], "FACE_SUP": [2]},
        },
        output_path=output,
    )

    print(json.dumps(result, indent=2))
    if result.get("status") == "success":
        print(f"\nSUCCESS — mesh written to {result.get('output_path')}")
        print("Feed this path to the Code_Aster structural_analysis tool.")
    else:
        print(f"\nFAILED: {result.get('message')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
