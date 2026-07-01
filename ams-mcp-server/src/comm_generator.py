"""
comm_generator.py
Builds a valid Code_Aster .comm file (string) from a StructuralAnalysisInput.
Does not write to disk - the caller decides where the file goes.

CHANGE FROM ORIGINAL: FORCE_FACE in Code_Aster is a surface traction
(force PER UNIT AREA, i.e. N/mm^2 for a mesh in mm), not a total
resultant force. This module now expects `load_pressures` - the same
loads, but with `.magnitude` already converted from total Newtons to
N/mm^2 by dividing by the true mesh face area (done in
code_aster_tool.py via mesh_utils.compute_face_area, BEFORE this
function is called). This function itself is otherwise unchanged.
"""
from typing import List

from src.models import Load, StructuralAnalysisInput


def generate_comm(params: StructuralAnalysisInput, load_pressures: List[Load],
                   result_unit: int = 80, mesh_unit: int = 21) -> str:
    """
    Args:
        params: validated input (material, boundary_conditions, model_type, ...)
        load_pressures: loads with `.magnitude` already converted to a
            surface traction (N/mm^2), NOT the raw total-force values
            from params.loads. See code_aster_tool.py for the conversion.
    """
    yield_strength = params.material.yield_strength_mpa or 235.0

    lines = []
    lines.append("DEBUT(LANG='EN')")
    lines.append("")
    lines.append(f"mesh = LIRE_MAILLAGE(UNITE={mesh_unit}, FORMAT='MED')")
    lines.append("")
    lines.append(
        "model = AFFE_MODELE(MAILLAGE=mesh,\n"
        f"                     AFFE=_F(TOUT='OUI', PHENOMENE='MECANIQUE', MODELISATION='{params.model_type}'))"
    )
    lines.append("")
    lines.append(
        "steel = DEFI_MATERIAU(ELAS=_F(E={E}, NU={NU}))".format(
            E=params.material.E, NU=params.material.NU
        )
    )
    lines.append(
        "mat = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(TOUT='OUI', MATER=steel))"
    )
    lines.append("")

    bc_blocks = []
    for bc in params.boundary_conditions:
        dof_kwargs = ", ".join(f"{dof}=0.0" for dof in bc.fixed_dofs)
        bc_blocks.append(
            f"             _F(GROUP_MA='{bc.group_name}', {dof_kwargs})"
        )
    bc_block_str = ",\n".join(bc_blocks)
    lines.append(
        "bc = AFFE_CHAR_MECA(MODELE=model,\n"
        f"                    DDL_IMPO=(\n{bc_block_str}\n                    ))"
    )
    lines.append("")

    # NOTE: `ld.magnitude` here is a TRACTION (N/mm^2), already converted
    # from the user's intended total force. FORCE_FACE takes force-per-
    # unit-area, so this is the physically correct value to hand it.
    load_blocks = []
    for ld in load_pressures:
        load_blocks.append(
            f"               _F(GROUP_MA='{ld.group_name}', {ld.direction}={ld.magnitude})"
        )
    load_block_str = ",\n".join(load_blocks)
    lines.append(
        "load = AFFE_CHAR_MECA(MODELE=model,\n"
        f"                      FORCE_FACE=(\n{load_block_str}\n                      ))"
    )
    lines.append("")

    lines.append(
        "res = MECA_STATIQUE(MODELE=model,\n"
        "                     CHAM_MATER=mat,\n"
        "                     EXCIT=(_F(CHARGE=bc), _F(CHARGE=load)))"
    )
    lines.append("")
    lines.append(
        f"IMPR_RESU(FORMAT='MED', UNITE={result_unit},\n"
        "          RESU=_F(RESULTAT=res, NOM_CHAM=('DEPL', 'SIEF_ELGA')))"
    )
    lines.append("")
    lines.append("FIN()")

    return "\n".join(lines)
