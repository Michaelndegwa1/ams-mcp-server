"""
run_local_test.py
Render a stress PNG from a Code_Aster .rmed file.

Usage:
    python run_local_test.py path/to/run_xxx.rmed
    python run_local_test.py --generate   # runs Code_Aster beam test first
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src import config
from src import render_tools


def _generate_rmed() -> Path:
    ams_root = Path(__file__).resolve().parent.parent / "ams-mcp-server"
    mesh = ams_root / "examples" / "test_beam.med"
    if not mesh.exists():
        raise FileNotFoundError(f"Missing beam mesh: {mesh}")

    print("Running Code_Aster local test to produce .rmed ...")
    subprocess.run(
        [sys.executable, "run_local_test.py", str(mesh)],
        cwd=ams_root,
        check=True,
    )

    rmed_files = sorted(
        (ams_root / "outputs").glob("run_*.rmed"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not rmed_files:
        raise FileNotFoundError("Code_Aster ran but no .rmed was produced in ams-mcp-server/outputs")
    return rmed_files[0]


def main() -> None:
    config.validate_config()

    if len(sys.argv) >= 2 and sys.argv[1] == "--generate":
        rmed = _generate_rmed()
    elif len(sys.argv) >= 2:
        rmed = Path(sys.argv[1])
    else:
        print(__doc__)
        print("\nTip: python run_local_test.py --generate")
        sys.exit(1)

    result = render_tools.render_stress_contour(
        result_path=str(rmed),
        output_path=str(config.RENDER_DIR / "test_stress.png"),
    )
    print(json.dumps(result, indent=2))
    if result.get("status") != "success":
        sys.exit(1)
    print(f"\nSUCCESS — PNG at {result['output_path']}")


if __name__ == "__main__":
    main()
