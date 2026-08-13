"""Export example cylinder mesh to CalculiX .inp via Gmsh (3D solids + face NSETs)."""
from __future__ import annotations

import sys
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
OUT = EXAMPLES / "test_beam.inp"


def _fmt_coord(value: float) -> str:
    if abs(value) < 1e-12:
        return "0.0"
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0.0"


def _nodes_for_physical(name: str) -> list[int]:
    import gmsh

    for dim, tag in gmsh.model.getPhysicalGroups():
        if gmsh.model.getPhysicalName(dim, tag) != name:
            continue
        node_ids: set[int] = set()
        for ent in gmsh.model.getEntitiesForPhysicalGroup(dim, tag):
            node_tags, _, _ = gmsh.model.mesh.getNodes(dim, ent)
            node_ids.update(int(t) for t in node_tags)
        return sorted(node_ids)
    return []


def _format_set(name: str, kind: str, ids: list[int]) -> list[str]:
    lines = [f"*{kind}, {kind}={name}"]
    chunk: list[str] = []
    for nid in ids:
        chunk.append(str(nid))
        if len(chunk) == 16:
            lines.append(", ".join(chunk))
            chunk = []
    if chunk:
        lines.append(", ".join(chunk))
    return lines


def _write_calculix_3d(path: Path) -> None:
    import gmsh

    lines: list[str] = ["*NODE"]
    node_tags, coord, _ = gmsh.model.mesh.getNodes()
    for i, tag in enumerate(node_tags):
        x, y, z = coord[3 * i : 3 * i + 3]
        lines.append(f"{int(tag)}, {_fmt_coord(x)}, {_fmt_coord(y)}, {_fmt_coord(z)}")

    lines.append("*ELEMENT, type=C3D4, ELSET=SOLID")
    types, tags, node_tags_flat = gmsh.model.mesh.getElements(3)
    if types:
        npe = gmsh.model.mesh.getElementProperties(types[0])[3]
        offset = 0
        for eid, _ in zip(tags[0], range(len(tags[0]))):
            conn = node_tags_flat[0][offset : offset + npe]
            offset += npe
            lines.append(f"{int(eid)}, {', '.join(str(int(n)) for n in conn)}")

    solid_ids = [int(e) for e in tags[0]] if types else []
    lines.extend(_format_set("SOLID", "ELSET", solid_ids))

    for face in ("FACE_INF", "FACE_SUP"):
        nodes = _nodes_for_physical(face)
        if nodes:
            lines.extend(_format_set(face, "NSET", nodes))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        gmsh.model.occ.addCylinder(0, 0, 0, 0, 0, 100, 5)
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
        _write_calculix_3d(OUT)
        print(f"Wrote {OUT}")
    finally:
        gmsh.finalize()


if __name__ == "__main__":
    main()
