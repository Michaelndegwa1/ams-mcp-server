"""
results_parser.py
Reads the .rmed (HDF5/MED) results file Code_Aster produces and extracts
the numbers an engineer cares about: max displacement, max Von Mises stress.

NOTE ON MED STRUCTURE: exact internal paths can shift slightly between
Code_Aster versions. The `inspect_structure()` function is provided so you
can run it once against YOUR container's output and confirm/adjust the
field path constants below before the demo.
"""
import hashlib
import logging
from datetime import datetime, timezone

import h5py
import numpy as np
from pathlib import Path

logger = logging.getLogger("results_parser")


def inspect_structure(result_path: Path) -> list:
    """Run this once manually against a real .rmed file to see where
    DEPL (displacement) and SIEF (stress) fields actually live in YOUR
    Code_Aster version's output. Returns a list of all dataset paths."""
    paths = []
    with h5py.File(result_path, "r") as f:
        f.visititems(lambda name, obj: paths.append(name))
    return paths


def _find_path_containing(all_paths: list, *keywords: str) -> str | None:
    for p in all_paths:
        if all(kw in p for kw in keywords):
            return p
    return None


def parse_results(result_path: Path, yield_strength_mpa: float = 235.0) -> dict:
    """
    Returns:
        {
          "max_displacement_mm": float | None,
          "max_stress_mpa": float | None,
          "node_count": int | None,
          "factor_of_safety": float | None,
        }
    Missing fields return None rather than raising - some analysis
    configurations produce different output structures and the parser
    must not crash the whole pipeline on an unexpected layout.
    """
    out = {
        "max_displacement_mm": None,
        "max_stress_mpa": None,
        "node_count": None,
        "factor_of_safety": None,
    }

    result_path = Path(result_path)
    file_bytes = result_path.read_bytes()
    file_hash = hashlib.sha256(file_bytes).hexdigest()[:16]
    logger.info(
        "Opening result file: %s (mtime=%s, sha256=%s, size=%d bytes)",
        result_path.resolve(),
        datetime.fromtimestamp(result_path.stat().st_mtime, tz=timezone.utc).isoformat(),
        file_hash,
        len(file_bytes),
    )

    with h5py.File(result_path, "r") as f:
        all_paths = []
        f.visititems(lambda name, obj: all_paths.append(name) if isinstance(obj, h5py.Dataset) else None)

        # --- Displacement field ---
        try:
            depl_path = _find_path_containing(all_paths, "DEPL")
            if depl_path is None:
                logger.warning("No dataset path containing 'DEPL' found. Run inspect_structure() to locate it.")
            else:
                displacements = f[depl_path][()]
                # displacements expected as (n_nodes, n_dofs) - DX,DY,DZ at minimum
                arr = np.asarray(displacements)
                if arr.ndim == 1:
                    # sometimes stored flat; reshape assuming 3 components
                    arr = arr.reshape(-1, 3)
                magnitudes = np.linalg.norm(arr[:, :3], axis=1)
                out["max_displacement_mm"] = float(np.max(magnitudes))
                out["node_count"] = int(arr.shape[0])
        except (KeyError, ValueError) as e:
            logger.warning("Could not extract displacement field: %s", e)

        # --- Stress field (Von Mises from SIEF_ELGA components) ---
        try:
            sief_path = _find_path_containing(all_paths, "SIEF")
            if sief_path is None:
                logger.warning("No dataset path containing 'SIEF' found. Run inspect_structure() to locate it.")
            else:
                sief = np.asarray(f[sief_path][()])
                # Expect columns ordered SIXX, SIYY, SIZZ, SIXY, SIYZ, SIXZ (Code_Aster convention)
                if sief.shape[-1] >= 6:
                    s11, s22, s33 = sief[..., 0], sief[..., 1], sief[..., 2]
                    s12, s23, s13 = sief[..., 3], sief[..., 4], sief[..., 5]
                    vm = np.sqrt(
                        0.5 * ((s11 - s22) ** 2 + (s22 - s33) ** 2 + (s33 - s11) ** 2
                               + 6 * (s12 ** 2 + s23 ** 2 + s13 ** 2))
                    )
                    out["max_stress_mpa"] = float(np.max(vm))
        except (KeyError, ValueError) as e:
            logger.warning("Could not extract stress field: %s", e)

    if out["max_stress_mpa"]:
        out["factor_of_safety"] = round(yield_strength_mpa / out["max_stress_mpa"], 2)

    return out
