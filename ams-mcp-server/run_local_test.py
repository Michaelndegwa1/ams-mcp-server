"""
run_local_test.py
Run this FIRST, tonight, before touching the MCP server or Claude Desktop.

It calls run_structural_analysis() directly - no MCP, no Claude - so if
something breaks you know immediately whether the problem is in
Code_Aster/Docker/your mesh, or in the MCP layer on top of it.

Usage:
    python run_local_test.py /path/to/your/mesh.med
"""
import sys
import json
import time
import logging

from src import config
from src.code_aster_tool import run_structural_analysis

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_local_test.py /path/to/mesh.med")
        print("\nNo mesh path given - if you don't have one yet, see examples/README_GET_TEST_MESH.md")
        sys.exit(1)

    mesh_path = sys.argv[1]

    config.validate_config()

    # Demo case: steel cantilever beam, fixed at one end, point load at the other.
    # Adjust group_name values to match the actual group names in YOUR mesh file -
    # these are placeholders ("Encastre" / "Load_Point") and WILL need to match
    # whatever your mesh's named groups actually are.
    params = dict(
        mesh_path=mesh_path,
        model_type="3D",
        material={
            "E": 210000.0,        # steel, MPa
            "NU": 0.3,
            "yield_strength_mpa": 235.0,
        },
        boundary_conditions=[
            {"group_name": "FACE_INF", "fixed_dofs": ["DX", "DY", "DZ"]}
        ],
        loads=[
            {"group_name": "FACE_SUP", "direction": "FZ", "magnitude": 500.0}
        ],
    )

    print("\n--- Running structural analysis ---")
    print(json.dumps(params, indent=2))

    start = time.time()
    result = run_structural_analysis(**params)
    elapsed = time.time() - start

    print(f"\n--- Result (took {elapsed:.1f}s) ---")
    print(json.dumps(result, indent=2))

    if result["status"] == "success":
        print(f"\nSUCCESS in {elapsed:.1f}s")
        print(f"  {result['engineering_verdict']}")
    else:
        print(f"\nFAILED: {result.get('message')}")
        if "log" in result:
            print(f"\n--- Code_Aster log tail ---\n{result['log']}")


if __name__ == "__main__":
    main()
