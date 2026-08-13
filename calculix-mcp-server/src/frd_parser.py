"""
frd_parser.py
Extract max displacement and Von Mises stress from CalculiX .frd output.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import numpy as np

logger = logging.getLogger("frd_parser")


def parse_frd(frd_path: Path, yield_strength_mpa: float = 235.0) -> dict:
    text = frd_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    disp_mags: list[float] = []
    vm_stress: list[float] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line == "-4  DISP":
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("-3"):
                parts = lines[i].split()
                if len(parts) >= 5 and parts[0].isdigit():
                    try:
                        ux, uy, uz = float(parts[2]), float(parts[3]), float(parts[4])
                        disp_mags.append(float(np.sqrt(ux * ux + uy * uy + uz * uz)))
                    except ValueError:
                        pass
                i += 1
            continue
        if line == "-4  STRESS" or line == "-4  TOSTR":
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("-3"):
                parts = lines[i].split()
                if len(parts) >= 7 and parts[0].isdigit():
                    try:
                        sxx, syy, szz = float(parts[2]), float(parts[3]), float(parts[4])
                        sxy, syz, sxz = float(parts[5]), float(parts[6]), float(parts[7]) if len(parts) > 7 else 0.0
                        if len(parts) == 7:
                            sxz = 0.0
                        vm = np.sqrt(
                            0.5
                            * (
                                (sxx - syy) ** 2
                                + (syy - szz) ** 2
                                + (szz - sxx) ** 2
                                + 6 * (sxy**2 + syz**2 + sxz**2)
                            )
                        )
                        vm_stress.append(float(vm))
                    except (ValueError, IndexError):
                        pass
                i += 1
            continue
        i += 1

    if not disp_mags and not vm_stress:
        nums = re.findall(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", text)
        logger.warning("Fallback FRD parse — limited extraction")

    out = {
        "max_displacement_mm": max(disp_mags) if disp_mags else None,
        "max_stress_mpa": max(vm_stress) if vm_stress else None,
        "node_count": len(disp_mags) if disp_mags else None,
        "factor_of_safety": None,
    }
    if out["max_stress_mpa"]:
        out["factor_of_safety"] = round(yield_strength_mpa / out["max_stress_mpa"], 2)
    return out
