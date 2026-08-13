"""
med_reader.py
Extract mesh coordinates and result fields from Code_Aster .rmed (HDF5/MED) files.
"""
from __future__ import annotations

import logging
from pathlib import Path

import h5py
import numpy as np

logger = logging.getLogger("med_reader")


def _collect_dataset_paths(f: h5py.File) -> list[str]:
    paths: list[str] = []
    f.visititems(lambda name, obj: paths.append(name) if isinstance(obj, h5py.Dataset) else None)
    return paths


def _find_path(paths: list[str], *keywords: str) -> str | None:
    for path in paths:
        if all(kw in path for kw in keywords):
            return path
    return None


def _find_path_any(paths: list[str], keyword_groups: list[tuple[str, ...]]) -> str | None:
    for group in keyword_groups:
        found = _find_path(paths, *group)
        if found:
            return found
    return None


def resolve_result_path(path: str) -> Path:
    raw = Path(path.strip())
    if raw.exists():
        return raw.resolve()

    search_roots = [
        Path.cwd(),
        Path(__file__).resolve().parent.parent,
        Path(__file__).resolve().parent.parent.parent / "ams-mcp-server" / "outputs",
    ]
    rel = path.lstrip("/\\")
    for root in search_roots:
        candidate = root / rel
        if candidate.exists():
            return candidate.resolve()
        candidate = root / Path(rel).name
        if candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(f"Result file not found: {path}")


def inspect_result_file(result_path: str) -> dict:
    path = resolve_result_path(result_path)
    with h5py.File(path, "r") as f:
        datasets = _collect_dataset_paths(f)
    return {
        "path": str(path),
        "dataset_count": len(datasets),
        "datasets_sample": datasets[:40],
        "has_depl": any("DEPL" in p for p in datasets),
        "has_stress": any(k in p for p in datasets for k in ("SIEQ", "SIEF", "VMIS", "STRESS")),
        "has_coords": any("COO" in p and "NOE" in p for p in datasets),
    }


def load_med_fields(result_path: str) -> dict:
    """Load coordinates, displacement magnitude, and von Mises stress if present."""
    path = resolve_result_path(result_path)
    out: dict = {"path": str(path), "node_count": None}

    with h5py.File(path, "r") as f:
        paths = _collect_dataset_paths(f)

        coor_path = _find_path_any(paths, [("NOE", "COO"), ("COOR",)])
        depl_path = _find_path_any(paths, [("DEPL", "NOE"), ("DEPL",)])
        stress_path = _find_path_any(
            paths,
            [
                ("SIEF", "CO"),
                ("SIEQ", "NOEU"),
                ("SIEQ", "NOE"),
                ("VMIS",),
            ],
        )

        if depl_path:
            depl = np.asarray(f[depl_path][()], dtype=float).reshape(-1, 3)
            mag = np.linalg.norm(depl[:, :3], axis=1)
            out["displacement_mm"] = mag
            out["depl_path"] = depl_path

        if coor_path:
            coords = np.asarray(f[coor_path][()], dtype=float).reshape(-1, 3)
            out["coordinates"] = coords
            out["coords_path"] = coor_path
            out["node_count"] = len(coords)

        if stress_path:
            stress = np.asarray(f[stress_path][()], dtype=float)
            if stress.ndim == 1:
                if stress.size % 6 == 0:
                    stress = stress.reshape(-1, 6)
                else:
                    stress = stress.reshape(-1, 1)
            if stress.shape[-1] >= 6:
                sxx, syy, szz, sxy, syz, sxz = stress[..., 0], stress[..., 1], stress[..., 2], stress[..., 3], stress[..., 4], stress[..., 5]
                vm = np.sqrt(
                    0.5
                    * (
                        (sxx - syy) ** 2
                        + (syy - szz) ** 2
                        + (szz - sxx) ** 2
                        + 6 * (sxy**2 + syz**2 + sxz**2)
                    )
                )
            else:
                vm = stress.reshape(-1)
            out["von_mises_mpa"] = vm.reshape(-1)
            out["stress_path"] = stress_path
            out["stress_location"] = "gauss" if "MAI" in stress_path or "ELGA" in stress_path else "node"

        if out.get("displacement_mm") is not None and out.get("node_count") is None:
            out["node_count"] = len(out["displacement_mm"])
        if out.get("von_mises_mpa") is not None and out["node_count"] is None:
            out["node_count"] = len(out["von_mises_mpa"])

    if out.get("coordinates") is None and out.get("von_mises_mpa") is None and out.get("displacement_mm") is None:
        raise ValueError(
            "Could not extract plottable fields from MED file. "
            "Run inspect_result_file to see available dataset paths."
        )

    return out
