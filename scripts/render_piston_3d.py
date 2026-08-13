#!/usr/bin/env python3
"""Generate 3D stress/displacement views of piston FEA results."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "paraview-mcp-server"))

from src.render_3d import render_interactive_3d, render_multiview_png


def main() -> int:
    parser = argparse.ArgumentParser(description="3D piston stress/displacement visualization")
    parser.add_argument(
        "rmed",
        nargs="?",
        default=str(REPO / "ams-mcp-server" / "outputs" / "run_83f90cca.rmed"),
        help="Path to Code_Aster .rmed result",
    )
    parser.add_argument("--deform-scale", type=float, default=8.0, help="Displacement exaggeration")
    args = parser.parse_args()

    render_dir = REPO / "paraview-mcp-server" / "renders"
    html_out = render_dir / "piston_3d_stress.html"
    png_out = render_dir / "piston_3d_stress.png"

    html_result = render_interactive_3d(
        args.rmed,
        str(html_out),
        title="Piston V8 — 3D Von Mises stress & displacement",
        deform_scale=args.deform_scale,
    )
    png_result = render_multiview_png(
        args.rmed,
        str(png_out),
        title="Piston V8 — Von Mises stress (4 views)",
        deform_scale=args.deform_scale,
    )

    print(json.dumps({"html": html_result, "png": png_result}, indent=2))
    print(f"\nINTERACTIVE (rotate/zoom): {html_out}")
    print(f"STATIC PNG:               {png_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
