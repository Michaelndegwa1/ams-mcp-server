#!/usr/bin/env python3
"""Render piston CAD profile + 3D mesh preview as PNG."""
from __future__ import annotations

from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parent.parent
MED = REPO / "gmsh-mcp-server" / "meshes" / "piston_first_pass.med"
OUT = REPO / "paraview-mcp-server" / "renders" / "piston_design.png"

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
    profile = scaled_profile()

    with h5py.File(MED, "r") as f:
        mesh_name = list(f["ENS_MAA"].keys())[0]
        step_key = list(f[f"ENS_MAA/{mesh_name}"].keys())[0]
        grp = f[f"ENS_MAA/{mesh_name}/{step_key}"]
        coords = grp["NOE/COO"][:].reshape(-1, 3)
        tr3 = grp["MAI/TR3/NOD"][:].reshape(-1, 3).astype(int) - 1

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

    sample = np.linspace(0, len(tr3) - 1, min(800, len(tr3)), dtype=int)
    faces = [coords[tri] for tri in tr3[sample]]
    mesh_art = Poly3DCollection(faces, alpha=0.45, facecolor="#5b9bd5", edgecolor="#2e6da4", linewidths=0.05)
    ax2.add_collection3d(mesh_art)
    ax2.auto_scale_xyz(coords[:, 0], coords[:, 1], coords[:, 2])
    ax2.set_xlabel("X (mm)")
    ax2.set_ylabel("Y (mm)")
    ax2.set_zlabel("Z (mm)")
    ax2.set_title("3D meshed solid")
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


if __name__ == "__main__":
    main()
