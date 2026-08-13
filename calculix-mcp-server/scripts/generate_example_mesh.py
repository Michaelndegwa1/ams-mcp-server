"""Export example cylinder mesh to CalculiX .inp via Gmsh."""
from __future__ import annotations

import sys
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
OUT = EXAMPLES / "test_beam.inp"


def main() -> None:
    try:
        import gmsh
    except ImportError:
        print("Install gmsh: pip install gmsh  (or run from gmsh-mcp-server venv)")
        sys.exit(1)

    EXAMPLES.mkdir(parents=True, exist_ok=True)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("beam")
        cyl = gmsh.model.occ.addCylinder(0, 0, 0, 0, 0, 100, 5)
        gmsh.model.occ.synchronize()

        surfaces = [tag for dim, tag in gmsh.model.getEntities(2)]
        bottom, top = [], []
        for tag in surfaces:
            xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.occ.getBoundingBox(2, tag)
            zc = (zmin + zmax) / 2
            if abs(zc) < 0.01:
                bottom.append(tag)
            elif abs(zc - 100) < 0.01:
                top.append(tag)

        if bottom:
            pg = gmsh.model.addPhysicalGroup(2, bottom)
            gmsh.model.setPhysicalName(2, pg, "FACE_INF")
        if top:
            pg = gmsh.model.addPhysicalGroup(2, top)
            gmsh.model.setPhysicalName(2, pg, "FACE_SUP")
        vols = [tag for dim, tag in gmsh.model.getEntities(3)]
        if vols:
            pg = gmsh.model.addPhysicalGroup(3, vols)
            gmsh.model.setPhysicalName(3, pg, "SOLID")

        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 3.0)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(OUT))
        print(f"Wrote {OUT}")
    finally:
        gmsh.finalize()


if __name__ == "__main__":
    main()
