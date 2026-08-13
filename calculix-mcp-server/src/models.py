"""Shared input models (same shape as Code_Aster MCP for cross-solver prompts)."""
from __future__ import annotations

from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class MaterialProperties(BaseModel):
    E: float = Field(gt=0, description="Young's modulus in MPa")
    NU: float = Field(gt=0, lt=0.5, description="Poisson's ratio")
    yield_strength_mpa: Optional[float] = Field(default=None, gt=0)


class BoundaryCondition(BaseModel):
    group_name: str = Field(description="NSET name in the CalculiX .inp mesh")
    fixed_dofs: List[Literal["DX", "DY", "DZ"]] = Field(description="Fixed translational DOFs")


class Load(BaseModel):
    group_name: str = Field(description="ELSET name for pressure load (face elements)")
    direction: Literal["FX", "FY", "FZ"] = Field(description="Used to pick pressure face normal check")
    magnitude: float = Field(description="Total force in Newtons (converted to pressure on the face)")


class StructuralAnalysisInput(BaseModel):
    mesh_path: str = Field(description="Path to CalculiX mesh .inp (from Gmsh export or native CCX mesh)")
    material: MaterialProperties
    boundary_conditions: List[BoundaryCondition] = Field(min_length=1)
    loads: List[Load] = Field(min_length=1)
    solid_elset: str = Field(default="SOLID", description="ELSET name for 3D solid elements")

    def validate_mesh_exists(self) -> None:
        if not Path(self.mesh_path).exists():
            raise ValueError(f"Mesh file not found: {self.mesh_path}")
