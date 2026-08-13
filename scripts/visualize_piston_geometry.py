#!/usr/bin/env python3
"""Render piston CAD profile + 3D mesh preview as PNG."""
from __future__ import annotations

from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "paraview-mcp-server" / "renders" / "piston_design.png"
PARAVIEW_SRC = REPO / "paraview-mcp-server"

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
BORE_MM = 103.25
HEIGHT_MM = 165.2


def scaled_profile() -> np.ndarray:
    r_scale = (BORE_MM / 2.0) / 25.0
    z_scale = HEIGHT_MM / 80.0
    pts = [[r * r_scale, z * z_scale] for r, z in REFERENCE_PROFILE]
    pts.append(pts[0])
    return np.array(pts)


def main() -> None:
    sys.path.insert(0, str(PARAVIEW_SRC))
    from src.revolve_mesh import build_revolved_solid_mesh, scale_profile
    from src.render_3d import render_design_3d_from_profile

    profile = scaled_profile()

    fig = plt.figure(figsize=(14, 6), dpi=140)

    ax1 = fig.add_subplot(121)
    ax1.fill(profile[:, 0], profile[:, 1], alpha=0.35, color="#4a90d9")
    ax1.plot(profile[:, 0], profile[:, 1], color="#1a5490", lw=2)
    ax1.axvline(0, color="k", lw=0.5, alpha=0.3)
    ax1.set_xlabel("Radius (mm)")
    ax1.set_ylabel("Axial Z (mm)")
    ax1.set_title("Cross-section (half-profile, revolved 360°)")
    ax1.set_aspect("equal")
    ax1.grid(True, alpha=0.3)
    ax1.annotate("Crown", xy=(profile[5, 0], profile[5, 1]), xytext=(60, 150),
                 arrowprops=dict(arrowstyle="->", color="#333"), fontsize=9)
    ax1.annotate("Skirt", xy=(profile[7, 0], profile[7, 1] * 0.5), xytext=(8, 40),
                 arrowprops=dict(arrowstyle="->", color="#333"), fontsize=9)

    ax2 = fig.add_subplot(122, projection="3d")
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    prof = scale_profile(REFERENCE_PROFILE, BORE_MM, HEIGHT_MM)
    coords3d, tris3d = build_revolved_solid_mesh(prof, n_theta=72)
    polys = [coords3d[t] for t in tris3d]
    mesh_art = Poly3DCollection(polys, alpha=0.92, facecolor="#8a9ba8", edgecolor="none")
    ax2.add_collection3d(mesh_art)
    ax2.auto_scale_xyz(coords3d[:, 0], coords3d[:, 1], coords3d[:, 2])
    ax2.set_xlabel("X (mm)")
    ax2.set_ylabel("Y (mm)")
    ax2.set_zlabel("Z (mm)")
    ax2.set_title("3D solid (revolved profile)")
    ax2.view_init(elev=22, azim=-55)

    fig.suptitle(
        f'Piston design — {BORE_MM/25.4:.3f}" bore, {HEIGHT_MM:.0f} mm height (LS3-class V8)',
        fontsize=13,
    )
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {OUT}")

    # Interactive 3D design (rotate in browser)
    html_out = REPO / "paraview-mcp-server" / "renders" / "piston_design_3d.html"
    profile_rz = scale_profile(REFERENCE_PROFILE, BORE_MM, HEIGHT_MM)
    render_design_3d_from_profile(
        profile_rz,
        str(html_out),
        title="Piston design — 3D solid",
        subtitle=f'{BORE_MM / 25.4:.3f}" bore × {HEIGHT_MM:.0f} mm height (LS3-class V8)',
    )
    print(f"Wrote {html_out.resolve()}")
    print("Open the .html file in Chrome/Edge — drag to rotate, scroll to zoom.")


if __name__ == "__main__":
    main()
