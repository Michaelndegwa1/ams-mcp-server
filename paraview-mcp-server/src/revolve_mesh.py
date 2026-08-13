"""
revolve_mesh.py
Clean CAD-style revolved solid mesh from an XZ profile (radius, z).
"""
from __future__ import annotations

import numpy as np


def scale_profile(
    profile: list[list[float]],
    bore_mm: float,
    height_mm: float,
    ref_max_radius: float = 25.0,
    ref_height: float = 80.0,
) -> list[list[float]]:
    rs = (bore_mm / 2.0) / ref_max_radius
    zs = height_mm / ref_height
    return [[r * rs, z * zs] for r, z in profile]


def build_revolved_solid_mesh(
    profile_rz: list[list[float]],
    n_theta: int = 96,
    cap_bottom: bool = True,
    cap_top: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Watertight surface by revolving an XZ profile (radius, z) about the Z axis.
    """
    prof = np.asarray(profile_rz, dtype=float)
    if len(prof) < 3:
        raise ValueError("profile needs at least 3 points")

    n_levels = len(prof)
    theta = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)

    verts: list[list[float]] = []
    ring_base: list[int] = []
    for r, z in prof:
        ring_base.append(len(verts))
        r = max(float(r), 0.0)
        for t in theta:
            verts.append([r * np.cos(t), r * np.sin(t), z])

    tris: list[list[int]] = []
    for i in range(n_levels - 1):
        a0, b0 = ring_base[i], ring_base[i + 1]
        for j in range(n_theta):
            jn = (j + 1) % n_theta
            a, b = a0 + j, a0 + jn
            c, d = b0 + j, b0 + jn
            tris.append([a, b, c])
            tris.append([b, d, c])

    def add_cap(z: float, r_inner: float, r_outer: float, flip: bool) -> None:
        if r_outer <= 1e-9:
            return
        axis = len(verts)
        verts.append([0.0, 0.0, z])
        inner_start = len(verts)
        for r in (max(r_inner, 0.0), r_outer):
            for t in theta:
                verts.append([r * np.cos(t), r * np.sin(t), z])
        inner_ring, outer_ring = inner_start, inner_start + n_theta
        for j in range(n_theta):
            jn = (j + 1) % n_theta
            if r_inner > 1e-6:
                o0, o1, o2 = [axis, inner_ring + j, inner_ring + jn]
                u0, u1, u2 = [inner_ring + j, outer_ring + j, outer_ring + jn]
                v0, v1, v2 = [inner_ring + j, outer_ring + jn, inner_ring + jn]
                if flip:
                    o0, o1, o2, u0, u1, u2, v0, v1, v2 = o2, o1, o0, u2, u1, u0, v2, v1, v0
                tris.extend([[o0, o1, o2], [u0, u1, u2], [v0, v1, v2]])
            else:
                t = [axis, outer_ring + j, outer_ring + jn]
                if flip:
                    t = t[::-1]
                tris.append(t)

    z_bot = float(prof[0, 1])
    z_top = float(prof[:, 1].max())
    r_bot_in = float(prof[prof[:, 1] == z_bot][:, 0].min())
    r_bot_out = float(prof[prof[:, 1] == z_bot][:, 0].max())
    r_top_in = float(prof[prof[:, 1] == z_top][:, 0].min())
    r_top_out = float(prof[prof[:, 1] == z_top][:, 0].max())

    if cap_bottom:
        add_cap(z_bot, r_bot_in, r_bot_out, flip=True)
    if cap_top:
        add_cap(z_top, r_top_in, r_top_out, flip=False)

    return np.array(verts, dtype=float), np.array(tris, dtype=int)
