"""
models.py
Pydantic models for every input the MCP tool accepts.
Validation lives here, separate from tool logic, so both stay readable.
"""
from pathlib import Path
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class MaterialProperties(BaseModel):
    E: float = Field(gt=0, description="Young's modulus in MPa. Steel ~210000, Aluminium ~70000.")
    NU: float = Field(gt=0, lt=0.5, description="Poisson's ratio. Steel ~0.3, Aluminium ~0.33.")
    yield_strength_mpa: Optional[float] = Field(
        default=None, gt=0, description="Yield strength in MPa, used for factor-of-safety. Defaults to 235 (S235 steel) if omitted."
    )


class BoundaryCondition(BaseModel):
    group_name: str = Field(description="Name of the mesh surface/node group to constrain (must exist in the mesh file).")
    fixed_dofs: List[Literal["DX", "DY", "DZ", "DRX", "DRY", "DRZ"]] = Field(
        description="Degrees of freedom to fix at this group."
    )


class Load(BaseModel):
    group_name: str = Field(description="Name of the mesh surface/node group the load is applied to.")
    direction: Literal["FX", "FY", "FZ"] = Field(description="Force direction.")
    magnitude: float = Field(description="Force in Newtons. Positive or negative.")


class StructuralAnalysisInput(BaseModel):
    mesh_path: str = Field(description="Path to the .med mesh file.")
    model_type: Literal["3D", "C_PLAN", "D_PLAN"] = "3D"
    material: MaterialProperties
    boundary_conditions: List[BoundaryCondition] = Field(min_length=1)
    loads: List[Load] = Field(min_length=1)

    def validate_mesh_exists(self) -> None:
        if not Path(self.mesh_path).exists():
            raise ValueError(f"Mesh file not found: {self.mesh_path}")
