"""
validation_engine.py
Concept 03 layer: turns raw structural results into a client-facing
plain-language verdict. Built on top of Concept 01's pipeline - this
module does not touch Code_Aster directly, it only interprets results
that have already been parsed.
"""


def build_verdict(max_displacement_mm: float, max_stress_mpa: float,
                   factor_of_safety: float, material_name: str = "structural steel") -> dict:
    """
    Returns a structured verdict dict, including a plain-language summary
    suitable for a non-expert client to read directly.
    """
    if factor_of_safety is None:
        status = "unknown"
        verdict_text = (
            "The analysis completed, but stress data needed to compute a "
            "safety margin was not available. Manual engineering review recommended."
        )
    elif factor_of_safety >= 2.0:
        status = "safe"
        verdict_text = (
            f"This design is SAFE under the applied load. "
            f"Factor of safety is {factor_of_safety}, meaning the {material_name} component "
            f"can withstand roughly {factor_of_safety}x the applied load before yielding."
        )
    elif factor_of_safety >= 1.0:
        status = "marginal"
        verdict_text = (
            f"This design PASSES but with a narrow margin. "
            f"Factor of safety is {factor_of_safety}. Standard engineering practice "
            f"typically targets 2.0 or higher for structural components - consider "
            f"reinforcing or reducing load."
        )
    else:
        status = "unsafe"
        verdict_text = (
            f"This design FAILS under the applied load. "
            f"Factor of safety is {factor_of_safety}, meaning the {material_name} component "
            f"is expected to yield before reaching the applied load. Redesign required."
        )

    return {
        "status": status,
        "verdict": verdict_text,
        "max_displacement_mm": round(max_displacement_mm, 4) if max_displacement_mm is not None else None,
        "max_stress_mpa": round(max_stress_mpa, 2) if max_stress_mpa is not None else None,
        "factor_of_safety": factor_of_safety,
    }
