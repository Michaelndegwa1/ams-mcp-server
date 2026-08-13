"""
matplotlib_renderer.py
Headless stress/displacement PNG renders from MED fields (no ParaView required).
"""
from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.med_reader import load_med_fields

logger = logging.getLogger("matplotlib_renderer")


def _pick_view_coords(coords: np.ndarray) -> tuple[np.ndarray, np.ndarray, str]:
    """Choose the two axes with largest spatial extent for a 2D projection."""
    spans = coords.max(axis=0) - coords.min(axis=0)
    order = np.argsort(spans)[::-1]
    i, j = int(order[0]), int(order[1])
    labels = ["X", "Y", "Z"]
    title = f"{labels[i]} vs {labels[j]} (mm)"
    return coords[:, i], coords[:, j], title


def render_field_scatter(
    result_path: str,
    output_path: str,
    field: str = "von_mises",
    title: str | None = None,
    colormap: str = "turbo",
) -> dict:
    data = load_med_fields(result_path)
    coords = data.get("coordinates")

    if field in ("von_mises", "stress", "von_mises_mpa"):
        values = data.get("von_mises_mpa")
        default_title = "Von Mises stress (MPa)"
        cbar_label = "MPa"
    elif field in ("displacement", "displacement_mm", "depl"):
        values = data.get("displacement_mm")
        default_title = "Displacement magnitude (mm)"
        cbar_label = "mm"
    else:
        return {"status": "error", "message": f"Unknown field: {field}"}

    if values is None:
        return {"status": "error", "message": f"Field '{field}' not found in {data['path']}"}

    values = np.asarray(values, dtype=float).reshape(-1)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 7), dpi=120)

    if coords is not None and len(coords) == len(values):
        x, y, axis_title = _pick_view_coords(np.asarray(coords))
        sc = ax.scatter(x, y, c=values, cmap=colormap, s=18, linewidths=0, alpha=0.9)
        ax.set_xlabel(f"{axis_title.split()[0]} (mm)")
        ax.set_ylabel(f"{axis_title.split()[2]} (mm)")
        ax.set_aspect("equal", adjustable="box")
    else:
        sc = ax.scatter(np.arange(len(values)), values, c=values, cmap=colormap, s=12)
        ax.set_xlabel("Sample index")
        ax.set_ylabel(cbar_label)
        axis_title = "Index plot (Gauss-point stress or missing coordinates)"

    ax.set_title(title or default_title)
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label(cbar_label)
    fig.text(
        0.01,
        0.01,
        f"max={values.max():.4g}  min={values.min():.4g}  nodes={len(values)}",
        fontsize=9,
        ha="left",
    )
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)

    logger.info("Wrote render %s", out)
    return {
        "status": "success",
        "backend": "matplotlib",
        "output_path": str(out.resolve()),
        "field": field,
        "max_value": float(values.max()),
        "min_value": float(values.min()),
        "node_count": len(values),
        "projection": axis_title,
    }
