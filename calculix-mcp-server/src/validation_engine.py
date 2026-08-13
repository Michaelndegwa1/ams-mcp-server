"""Engineering verdict from parsed results."""
from __future__ import annotations


def build_verdict(
    max_displacement_mm: float | None,
    max_stress_mpa: float | None,
    factor_of_safety: float | None,
) -> dict:
    if max_stress_mpa is None and max_displacement_mm is None:
        return {
            "status": "unknown",
            "verdict": "No displacement or stress data extracted from FRD file.",
            "max_displacement_mm": max_displacement_mm,
            "max_stress_mpa": max_stress_mpa,
            "factor_of_safety": factor_of_safety,
        }

    fos = factor_of_safety or 0.0
    if fos >= 1.5:
        status = "safe"
        verdict = (
            f"This design is SAFE under the applied load. Factor of safety is {fos:.2f}."
        )
    elif fos >= 1.0:
        status = "marginal"
        verdict = f"Marginal design — factor of safety {fos:.2f} is below typical target 1.5."
    else:
        status = "unsafe"
        verdict = f"UNSAFE — factor of safety {fos:.2f} is below 1.0 (yield likely)."

    return {
        "status": status,
        "verdict": verdict,
        "max_displacement_mm": max_displacement_mm,
        "max_stress_mpa": max_stress_mpa,
        "factor_of_safety": factor_of_safety,
    }
