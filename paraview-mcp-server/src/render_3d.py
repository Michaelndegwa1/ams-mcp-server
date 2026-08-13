"""
render_3d.py
Interactive 3D piston views with stress and displacement on the meshed surface.
"""
from __future__ import annotations

import logging
from pathlib import Path

import h5py
import numpy as np

logger = logging.getLogger("render_3d")

_E = 71700.0  # MPa — 2618-T61, for equivalent strain display (vm/E)


def _collect_paths(f: h5py.File) -> list[str]:
    paths: list[str] = []
    f.visititems(lambda name, obj: paths.append(name) if isinstance(obj, h5py.Dataset) else None)
    return paths


def _find_path(paths: list[str], *keys: str) -> str | None:
    for p in paths:
        if all(k in p for k in keys):
            return p
    return None


def _von_mises(stress6: np.ndarray) -> np.ndarray:
    sxx, syy, szz = stress6[:, 0], stress6[:, 1], stress6[:, 2]
    sxy, syz, sxz = stress6[:, 3], stress6[:, 4], stress6[:, 5]
    return np.sqrt(
        0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2 + 6 * (sxy**2 + syz**2 + sxz**2))
    )


def _tet_faces(n: np.ndarray) -> list[tuple[int, int, int]]:
    a, b, c, d = int(n[0]), int(n[1]), int(n[2]), int(n[3])
    return [(a, b, c), (a, b, d), (a, c, d), (b, c, d)]


def load_volume_mesh(mesh_path: str) -> dict:
    """Load solid mesh geometry from a Gmsh or result .med file (no stress required)."""
    path = Path(mesh_path)
    with h5py.File(path, "r") as f:
        paths = _collect_paths(f)
        mesh_name = list(f["ENS_MAA"].keys())[0]
        step = list(f[f"ENS_MAA/{mesh_name}"].keys())[0]
        base = f"ENS_MAA/{mesh_name}/{step}"
        coords = f[f"{base}/NOE/COO"][:].reshape(-1, 3).astype(float)
        nod_path = _find_path(paths, "MAI", "TE4", "NOD") or _find_path(paths, "MAI", "TET4", "NOD")
        if not nod_path:
            te4 = f"{base}/MAI/TE4/NOD"
            if te4 in f:
                nod_path = te4
        if not nod_path:
            raise ValueError("No TE4/TET4 volume mesh in MED file")
        conn = f[nod_path][:].reshape(-1, 4).astype(int) - 1

    return {
        "path": str(path.resolve()),
        "coordinates": coords,
        "connectivity": conn,
    }


def render_design_3d(
    mesh_path: str | None,
    output_html: str,
    title: str = "Piston design — 3D",
    subtitle: str | None = None,
    profile_rz: list[list[float]] | None = None,
) -> dict:
    """Rotatable 3D CAD view of the piston (clean revolved solid, not FEA mesh)."""
    import plotly.graph_objects as go

    from src.revolve_mesh import build_revolved_solid_mesh

    if profile_rz is None:
        raise ValueError("profile_rz required for design view")

    coords, tris = build_revolved_solid_mesh(profile_rz, n_theta=120)
    x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]
    i, j, k = tris[:, 0], tris[:, 1], tris[:, 2]

    fig = go.Figure(
        data=[
            go.Mesh3d(
                x=x,
                y=y,
                z=z,
                i=i,
                j=j,
                k=k,
                color="#8a9ba8",
                flatshading=False,
                lighting=dict(ambient=0.55, diffuse=0.85, specular=0.55, roughness=0.25),
                lightposition=dict(x=100, y=150, z=200),
                hovertemplate="X: %{x:.1f}<br>Y: %{y:.1f}<br>Z: %{z:.1f} mm<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title=dict(text=f"{title}<br><sup>{subtitle or ''}</sup>", x=0.5),
        scene=dict(
            xaxis_title="X (mm)",
            yaxis_title="Y (mm)",
            zaxis_title="Z (mm)",
            aspectmode="data",
            bgcolor="#eef2f6",
            camera=dict(eye=dict(x=1.6, y=1.6, z=0.9)),
        ),
        margin=dict(l=0, r=0, t=70, b=0),
        paper_bgcolor="#ffffff",
        height=720,
        width=960,
    )

    out = Path(output_html)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out), include_plotlyjs="cdn", full_html=True)
    logger.info("Wrote design 3D %s", out)

    return {
        "status": "success",
        "output_html": str(out.resolve()),
        "node_count": len(coords),
        "triangle_count": len(tris),
        "source": "revolved_profile",
    }


def render_design_3d_legacy_med(
    mesh_path: str,
    output_html: str,
    title: str = "Piston design — 3D",
    subtitle: str | None = None,
) -> dict:
    """Legacy: mesh from MED (can look noisy). Prefer render_design_3d with profile."""
    import plotly.graph_objects as go

    data = load_volume_mesh(mesh_path)
    coords = data["coordinates"]
    conn = data["connectivity"]
    tris, _ = _boundary_triangles(conn)

    x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]
    i, j, k = tris[:, 0], tris[:, 1], tris[:, 2]
    z_color = coords[:, 2]

    fig = go.Figure(
        data=[
            go.Mesh3d(
                x=x, y=y, z=z, i=i, j=j, k=k,
                intensity=z_color, intensitymode="vertex",
                colorscale=[[0, "#2c5282"], [0.5, "#4299e1"], [1, "#bee3f8"]],
                colorbar=dict(title="Z (mm)", len=0.7),
            )
        ]
    )
    fig.update_layout(title=title, scene=dict(aspectmode="data"))
    out = Path(output_html)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out), include_plotlyjs="cdn")
    return {"status": "success", "output_html": str(out.resolve())}


def render_design_3d_from_profile(
    profile_rz: list[list[float]],
    output_html: str,
    title: str = "Piston design — 3D",
    subtitle: str | None = None,
) -> dict:
    return render_design_3d(None, output_html, title=title, subtitle=subtitle, profile_rz=profile_rz)


def load_volume_result(result_path: str) -> dict:
    path = Path(result_path)
    with h5py.File(path, "r") as f:
        paths = _collect_paths(f)
        mesh_name = list(f["ENS_MAA"].keys())[0]
        step = list(f[f"ENS_MAA/{mesh_name}"].keys())[0]
        base = f"ENS_MAA/{mesh_name}/{step}"
        coords = f[f"{base}/NOE/COO"][:].reshape(-1, 3).astype(float)
        nod_path = _find_path(paths, "MAI", "TE4", "NOD") or _find_path(paths, "MAI", "TET4", "NOD")
        if not nod_path:
            raise ValueError("No TE4/TET4 connectivity in result MED")
        conn = f[nod_path][:].reshape(-1, 4).astype(int) - 1

        depl = None
        depl_path = _find_path(paths, "DEPL", "NOE") or _find_path(paths, "DEPL")
        if depl_path:
            depl = f[depl_path][:].reshape(-1, 3).astype(float)

        stress_path = _find_path(paths, "SIEF", "CO") or _find_path(paths, "SIEF")
        if not stress_path:
            raise ValueError("No SIEF stress field in result MED")
        stress6 = f[stress_path][:].reshape(-1, 6).astype(float)
        elem_vm = _von_mises(stress6)

    return {
        "path": str(path.resolve()),
        "coordinates": coords,
        "connectivity": conn,
        "displacement": depl,
        "element_von_mises_mpa": elem_vm,
    }


def _boundary_triangles(conn: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (ntri, 3) node indices and per-triangle element id for outer surface."""
    face_map: dict[tuple[int, int, int], list[int]] = {}
    for ei, nodes in enumerate(conn):
        for tri in _tet_faces(nodes):
            key = tuple(sorted(tri))
            face_map.setdefault(key, []).append(ei)

    tris: list[tuple[int, int, int]] = []
    elem_ids: list[int] = []
    for key, eids in face_map.items():
        if len(eids) == 1:
            tris.append(key)  # sorted — reorder for consistent winding later
            elem_ids.append(eids[0])

    if not tris:
        raise ValueError("Could not extract boundary surface")

    tri_arr = np.array(tris, dtype=int)
    # Restore winding from first owning element for consistent normals
    fixed = []
    for i, (key, eid) in enumerate(zip(tris, elem_ids)):
        for cand in _tet_faces(conn[eid]):
            if tuple(sorted(cand)) == key:
                fixed.append(cand)
                break
    return np.array(fixed, dtype=int), np.array(elem_ids, dtype=int)


def _nodal_from_elements(conn: np.ndarray, elem_values: np.ndarray, n_nodes: int) -> np.ndarray:
    acc = np.zeros(n_nodes, dtype=float)
    cnt = np.zeros(n_nodes, dtype=float)
    for ei, nodes in enumerate(conn):
        for nid in nodes:
            acc[nid] += elem_values[ei]
            cnt[nid] += 1.0
    return acc / np.maximum(cnt, 1.0)


def render_interactive_3d(
    result_path: str,
    output_html: str,
    title: str = "Piston — 3D stress & displacement",
    deform_scale: float = 5.0,
) -> dict:
    """Write rotatable Plotly HTML with stress and displacement views."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    data = load_volume_result(result_path)
    coords = data["coordinates"]
    conn = data["connectivity"]
    elem_vm = data["element_von_mises_mpa"]
    depl = data["displacement"]
    n_nodes = len(coords)

    tris, tri_elem = _boundary_triangles(conn)
    tri_stress = elem_vm[tri_elem]
    node_stress = _nodal_from_elements(conn, elem_vm, n_nodes)
    node_disp = np.linalg.norm(depl, axis=1) if depl is not None else np.zeros(n_nodes)
    node_strain_pct = (node_stress / _E) * 100.0  # equivalent strain %

    if depl is not None and deform_scale:
        display_coords = coords + depl * float(deform_scale)
    else:
        display_coords = coords

    x, y, z = display_coords[:, 0], display_coords[:, 1], display_coords[:, 2]
    i, j, k = tris[:, 0], tris[:, 1], tris[:, 2]

    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "scene"}, {"type": "scene"}]],
        subplot_titles=("Von Mises stress (MPa)", "Displacement (mm)"),
        horizontal_spacing=0.02,
    )

    fig.add_trace(
        go.Mesh3d(
            x=x, y=y, z=z, i=i, j=j, k=k,
            intensity=node_stress,
            intensitymode="vertex",
            colorscale="Turbo",
            colorbar=dict(title="MPa", x=0.45, len=0.75),
            lighting=dict(ambient=0.45, diffuse=0.85, specular=0.35, roughness=0.5),
            lightposition=dict(x=100, y=200, z=300),
            name="Stress",
            hovertemplate="σ_vm: %{intensity:.2f} MPa<br>X: %{x:.1f}<br>Y: %{y:.1f}<br>Z: %{z:.1f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Mesh3d(
            x=x, y=y, z=z, i=i, j=j, k=k,
            intensity=node_disp,
            intensitymode="vertex",
            colorscale="Viridis",
            colorbar=dict(title="mm", x=1.02, len=0.75),
            lighting=dict(ambient=0.45, diffuse=0.85, specular=0.35, roughness=0.5),
            name="Displacement",
            hovertemplate="|u|: %{intensity:.4f} mm<br>ε≈ %{customdata:.4f}%<extra></extra>",
            customdata=node_strain_pct,
        ),
        row=1,
        col=2,
    )

    scene_kw = dict(
        xaxis_title="X (mm)",
        yaxis_title="Y (mm)",
        zaxis_title="Z (mm)",
        aspectmode="data",
    )
    fig.update_layout(
        title=dict(text=title, x=0.5),
        scene=scene_kw,
        scene2=scene_kw,
        margin=dict(l=0, r=0, t=60, b=0),
        paper_bgcolor="#fafafa",
        height=620,
        width=1200,
    )
    if deform_scale and depl is not None:
        fig.add_annotation(
            text=f"Display shape: +{deform_scale}× exaggerated displacement",
            xref="paper", yref="paper", x=0.5, y=-0.02, showarrow=False, font=dict(size=11),
        )

    out = Path(output_html)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out), include_plotlyjs="cdn", full_html=True)
    logger.info("Wrote interactive 3D %s", out)

    return {
        "status": "success",
        "output_html": str(out.resolve()),
        "max_stress_mpa": float(elem_vm.max()),
        "max_displacement_mm": float(node_disp.max()),
        "max_equivalent_strain_pct": float(node_strain_pct.max()),
        "triangle_count": len(tris),
        "deform_scale": deform_scale,
    }


def render_multiview_png(
    result_path: str,
    output_png: str,
    title: str = "Piston — 3D Von Mises stress",
    deform_scale: float = 5.0,
) -> dict:
    """Static PNG with four camera angles (matplotlib)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    data = load_volume_result(result_path)
    coords = data["coordinates"]
    conn = data["connectivity"]
    elem_vm = data["element_von_mises_mpa"]
    depl = data["displacement"]

    tris, tri_elem = _boundary_triangles(conn)
    tri_vm = elem_vm[tri_elem]
    if depl is not None and deform_scale:
        coords = coords + depl * float(deform_scale)

    vmin, vmax = float(elem_vm.min()), float(elem_vm.max())
    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    cmap = plt.colormaps["turbo"]

    fig = plt.figure(figsize=(12, 10), dpi=130)
    views = [(25, -60), (25, 30), (5, 0), (90, 0)]
    titles = ["Isometric", "Side", "Front", "Top"]

    for idx, (elev, azim) in enumerate(views):
        ax = fig.add_subplot(2, 2, idx + 1, projection="3d")
        polys = [coords[tri] for tri in tris]
        colors = cmap(norm(tri_vm))
        coll = Poly3DCollection(polys, facecolors=colors, edgecolor="none", alpha=0.95)
        ax.add_collection3d(coll)
        ax.auto_scale_xyz(coords[:, 0], coords[:, 1], coords[:, 2])
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(titles[idx], fontsize=10)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")

    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=fig.axes, shrink=0.55, pad=0.02, label="Von Mises (MPa)")
    fig.suptitle(title, fontsize=13)
    if deform_scale and depl is not None:
        fig.text(0.5, 0.02, f"Displacement exaggerated {deform_scale}× for visibility", ha="center", fontsize=9)
    fig.tight_layout(rect=[0, 0.03, 0.92, 0.95])

    out = Path(output_png)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)

    return {
        "status": "success",
        "output_png": str(out.resolve()),
        "max_stress_mpa": float(vmax),
    }
