"""
gmsh_tools.py
Headless Gmsh geometry + meshing for MCP tools.

Each public function initializes Gmsh, performs one operation, and finalizes.
Gmsh is not thread-safe; a module lock serializes concurrent tool calls.
"""
from __future__ import annotations

import logging
import math
import threading
import uuid
from pathlib import Path
from typing import Any

from src import config

logger = logging.getLogger("gmsh_tools")

_gmsh_lock = threading.Lock()


def _import_gmsh():
    try:
        import gmsh  # noqa: WPS433 — lazy import keeps check_environment usable without gmsh
    except ImportError as exc:
        raise RuntimeError(
            "gmsh Python package not installed. Run: pip install gmsh"
        ) from exc
    return gmsh


def _resolve_output_path(path: str, default_dir: Path | None = None) -> Path:
    raw = Path(path.strip())
    if raw.is_absolute():
        target = raw
    elif default_dir is not None:
        target = default_dir / raw
    else:
        target = config.MESH_DIR / raw
    target.parent.mkdir(parents=True, exist_ok=True)
    return target.resolve()


def _entity_summary() -> dict[str, Any]:
    gmsh = _import_gmsh()
    volumes = gmsh.model.getEntities(3)
    surfaces = gmsh.model.getEntities(2)
    curves = gmsh.model.getEntities(1)
    points = gmsh.model.getEntities(0)
    physical_groups: list[dict[str, Any]] = []
    for dim in (0, 1, 2, 3):
        for tag in gmsh.model.getPhysicalGroups(dim):
            name = gmsh.model.getPhysicalName(dim, tag[1]) or f"PG_{dim}_{tag[1]}"
            entities = gmsh.model.getEntitiesForPhysicalGroup(dim, tag[1])
            physical_groups.append(
                {"dimension": dim, "tag": tag[1], "name": name, "entities": list(entities)}
            )
    return {
        "volumes": [{"tag": tag} for _, tag in volumes],
        "surfaces": [{"tag": tag} for _, tag in surfaces],
        "curves": [{"tag": tag} for _, tag in curves],
        "points": [{"tag": tag} for _, tag in points],
        "physical_groups": physical_groups,
    }


def _surface_center_z(gmsh, surface_tag: int) -> float:
    xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.occ.getBoundingBox(2, surface_tag)
    return (zmin + zmax) / 2.0


def _auto_tag_cylinder_end_caps(gmsh, height: float, z_base: float = 0.0, tol: float | None = None) -> list[dict[str, Any]]:
    """Name bottom/top end caps FACE_INF / FACE_SUP by Z position."""
    if tol is None:
        tol = max(float(height) * 0.05, 1e-3)
    surfaces = [tag for dim, tag in gmsh.model.getEntities(2)]
    bottom = []
    top = []
    for tag in surfaces:
        zc = _surface_center_z(gmsh, tag)
        if abs(zc - z_base) <= tol:
            bottom.append(tag)
        elif abs(zc - (z_base + float(height))) <= tol:
            top.append(tag)
    applied = []
    if bottom:
        pg = gmsh.model.addPhysicalGroup(2, bottom)
        gmsh.model.setPhysicalName(2, pg, "FACE_INF")
        applied.append({"dimension": 2, "name": "FACE_INF", "entities": bottom, "tag": pg})
    if top:
        pg = gmsh.model.addPhysicalGroup(2, top)
        gmsh.model.setPhysicalName(2, pg, "FACE_SUP")
        applied.append({"dimension": 2, "name": "FACE_SUP", "entities": top, "tag": pg})
    volumes = [tag for dim, tag in gmsh.model.getEntities(3)]
    if volumes:
        pg = gmsh.model.addPhysicalGroup(3, volumes)
        gmsh.model.setPhysicalName(3, pg, "SOLID")
        applied.append({"dimension": 3, "name": "SOLID", "entities": volumes, "tag": pg})
    return applied


def _apply_physical_groups(groups: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not groups:
        return []
    gmsh = _import_gmsh()
    applied: list[dict[str, Any]] = []

    for dim_key, dim in (("volumes", 3), ("surfaces", 2), ("curves", 1), ("points", 0)):
        named = groups.get(dim_key) or {}
        for name, entity_tags in named.items():
            if not entity_tags:
                continue
            pg_tag = gmsh.model.addPhysicalGroup(dim, [int(t) for t in entity_tags])
            gmsh.model.setPhysicalName(dim, pg_tag, str(name))
            applied.append({"dimension": dim, "name": name, "entities": entity_tags, "tag": pg_tag})
    return applied


def _mesh_stats() -> dict[str, int | None]:
    gmsh = _import_gmsh()
    node_tags, _, _ = gmsh.model.mesh.getNodes()
    elem_types, elem_tags, _ = gmsh.model.mesh.getElements()
    element_count = sum(len(tags) for tags in elem_tags)
    return {
        "node_count": len(node_tags),
        "element_count": int(element_count),
        "element_types": [int(t) for t in elem_types],
    }


def _run_gmsh(model_name: str, build_fn) -> dict[str, Any]:
    with _gmsh_lock:
        gmsh = _import_gmsh()
        gmsh.initialize()
        try:
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.model.add(model_name)
            result = build_fn(gmsh)
            gmsh.model.occ.synchronize()
            result["entities"] = _entity_summary()
            return result
        finally:
            gmsh.finalize()


def build_extrusion(
    profile_points: list[list[float]],
    height: float,
    mesh_size: float | None = None,
    physical_groups: dict[str, Any] | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Extrude a closed 2D profile (XY plane, z=0) along +Z.

    profile_points: [[x, y], ...] closed polygon (first point need not repeat last).
    """
    if len(profile_points) < 3:
        return {"status": "error", "message": "profile_points needs at least 3 [x, y] pairs"}
    if height <= 0:
        return {"status": "error", "message": "height must be positive"}

    run_id = str(uuid.uuid4())[:8]

    def build(gmsh):
        pts = []
        for x, y in profile_points:
            pts.append(gmsh.model.occ.addPoint(float(x), float(y), 0))
        lines = [
            gmsh.model.occ.addLine(pts[i], pts[(i + 1) % len(pts)])
            for i in range(len(pts))
        ]
        loop = gmsh.model.occ.addCurveLoop(lines)
        surface = gmsh.model.occ.addPlaneSurface([loop])
        extruded = gmsh.model.occ.extrude([(2, surface)], 0, 0, float(height))
        volume_tags = [tag for dim, tag in extruded if dim == 3]

        if mesh_size is not None:
            gmsh.option.setNumber("Mesh.CharacteristicLengthMax", float(mesh_size))
            gmsh.option.setNumber("Mesh.CharacteristicLengthMin", float(mesh_size) * 0.5)

        applied_groups = _apply_physical_groups(physical_groups)

        export_path = None
        mesh_info = None
        if mesh_size is not None:
            gmsh.model.occ.synchronize()
            gmsh.model.mesh.generate(3)
            mesh_info = _mesh_stats()
            if output_path:
                export_path = _resolve_output_path(output_path)
                gmsh.write(str(export_path))

        return {
            "status": "success",
            "run_id": run_id,
            "operation": "build_extrusion",
            "volume_tags": volume_tags,
            "height": float(height),
            "physical_groups_applied": applied_groups,
            "mesh": mesh_info,
            "output_path": str(export_path) if export_path else None,
        }

    try:
        payload = _run_gmsh(f"extrusion_{run_id}", build)
        payload["code_fingerprint"] = __import__("src.build_info", fromlist=["code_fingerprint"]).code_fingerprint()
        return payload
    except Exception as exc:
        logger.exception("build_extrusion failed")
        return {"status": "error", "message": str(exc), "run_id": run_id}


def build_revolved_solid(
    profile_points: list[list[float]],
    axis_point: list[float],
    axis_direction: list[float],
    angle_degrees: float = 360.0,
    mesh_size: float | None = None,
    physical_groups: dict[str, Any] | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Revolve a 2D profile in the XZ plane (x=radius, y=0, z=axial) around an axis.

    Typical piston/cylinder use: profile in XZ, revolve about the Z axis.
    """
    if len(profile_points) < 3:
        return {"status": "error", "message": "profile_points needs at least 3 [radius, z] pairs"}
    if len(axis_point) != 3 or len(axis_direction) != 3:
        return {"status": "error", "message": "axis_point and axis_direction must be length-3 vectors"}

    angle_rad = math.radians(float(angle_degrees))
    if angle_rad <= 0:
        return {"status": "error", "message": "angle_degrees must be positive"}

    run_id = str(uuid.uuid4())[:8]
    ax, ay, az = (float(v) for v in axis_point)
    dx, dy, dz = (float(v) for v in axis_direction)

    def build(gmsh):
        pts = []
        for radius, z in profile_points:
            pts.append(gmsh.model.occ.addPoint(float(radius), 0.0, float(z)))
        lines = [
            gmsh.model.occ.addLine(pts[i], pts[(i + 1) % len(pts)])
            for i in range(len(pts))
        ]
        loop = gmsh.model.occ.addCurveLoop(lines)
        surface = gmsh.model.occ.addPlaneSurface([loop])
        revolved = gmsh.model.occ.revolve([(2, surface)], ax, ay, az, dx, dy, dz, angle_rad)
        volume_tags = [tag for dim, tag in revolved if dim == 3]

        if mesh_size is not None:
            gmsh.option.setNumber("Mesh.CharacteristicLengthMax", float(mesh_size))
            gmsh.option.setNumber("Mesh.CharacteristicLengthMin", float(mesh_size) * 0.5)

        applied_groups = _apply_physical_groups(physical_groups)

        export_path = None
        mesh_info = None
        if mesh_size is not None:
            gmsh.model.occ.synchronize()
            gmsh.model.mesh.generate(3)
            mesh_info = _mesh_stats()
            if output_path:
                export_path = _resolve_output_path(output_path)
                gmsh.write(str(export_path))

        return {
            "status": "success",
            "run_id": run_id,
            "operation": "build_revolved_solid",
            "volume_tags": volume_tags,
            "angle_degrees": float(angle_degrees),
            "physical_groups_applied": applied_groups,
            "mesh": mesh_info,
            "output_path": str(export_path) if export_path else None,
        }

    try:
        payload = _run_gmsh(f"revolve_{run_id}", build)
        payload["code_fingerprint"] = __import__("src.build_info", fromlist=["code_fingerprint"]).code_fingerprint()
        return payload
    except Exception as exc:
        logger.exception("build_revolved_solid failed")
        return {"status": "error", "message": str(exc), "run_id": run_id}


def build_cylinder(
    radius: float,
    height: float,
    center: list[float] | None = None,
    mesh_size: float | None = None,
    physical_groups: dict[str, Any] | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Create a simple cylinder aligned with +Z (convenience for beams/rods/pistons)."""
    if radius <= 0 or height <= 0:
        return {"status": "error", "message": "radius and height must be positive"}

    cx, cy, cz = center if center else [0.0, 0.0, 0.0]
    if len([cx, cy, cz]) != 3:
        return {"status": "error", "message": "center must be [x, y, z]"}

    run_id = str(uuid.uuid4())[:8]

    def build(gmsh):
        cyl = gmsh.model.occ.addCylinder(
            float(cx), float(cy), float(cz),
            0.0, 0.0, float(height),
            float(radius),
        )
        if mesh_size is not None:
            gmsh.option.setNumber("Mesh.CharacteristicLengthMax", float(mesh_size))
            gmsh.option.setNumber("Mesh.CharacteristicLengthMin", float(mesh_size) * 0.5)

        if physical_groups:
            applied_groups = _apply_physical_groups(physical_groups)
        else:
            gmsh.model.occ.synchronize()
            applied_groups = _auto_tag_cylinder_end_caps(gmsh, height=float(height), z_base=float(cz))

        export_path = None
        mesh_info = None
        if mesh_size is not None:
            gmsh.model.occ.synchronize()
            gmsh.model.mesh.generate(3)
            mesh_info = _mesh_stats()
            if output_path:
                export_path = _resolve_output_path(output_path)
                gmsh.write(str(export_path))

        return {
            "status": "success",
            "run_id": run_id,
            "operation": "build_cylinder",
            "volume_tag": cyl,
            "radius": float(radius),
            "height": float(height),
            "center": [float(cx), float(cy), float(cz)],
            "physical_groups_applied": applied_groups,
            "mesh": mesh_info,
            "output_path": str(export_path) if export_path else None,
        }

    try:
        payload = _run_gmsh(f"cylinder_{run_id}", build)
        payload["code_fingerprint"] = __import__("src.build_info", fromlist=["code_fingerprint"]).code_fingerprint()
        return payload
    except Exception as exc:
        logger.exception("build_cylinder failed")
        return {"status": "error", "message": str(exc), "run_id": run_id}


def mesh_and_export(
    input_path: str,
    output_path: str,
    mesh_size: float = 2.0,
    physical_groups: dict[str, Any] | None = None,
    format: str = "med",
) -> dict[str, Any]:
    """
    Load an existing .geo/.brep/.step file, mesh it, and export.

    For workflows where geometry was built in a prior step and saved to disk.
    """
    src = Path(input_path.strip())
    if not src.is_absolute():
        for root in (Path.cwd(), config.MESH_DIR, config.OUTPUT_DIR):
            candidate = root / src
            if candidate.exists():
                src = candidate.resolve()
                break
    if not src.exists():
        return {"status": "error", "message": f"Input file not found: {input_path}"}

    export_path = _resolve_output_path(output_path)
    if format == "med" and export_path.suffix.lower() not in {".med", ".msh"}:
        export_path = export_path.with_suffix(".med")

    run_id = str(uuid.uuid4())[:8]

    def build(gmsh):
        gmsh.open(str(src))
        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", float(mesh_size))
        gmsh.option.setNumber("Mesh.CharacteristicLengthMin", float(mesh_size) * 0.5)
        _apply_physical_groups(physical_groups)
        gmsh.model.occ.synchronize()
        gmsh.model.mesh.generate(3)
        gmsh.write(str(export_path))
        return {
            "status": "success",
            "run_id": run_id,
            "operation": "mesh_and_export",
            "input_path": str(src),
            "output_path": str(export_path),
            "mesh": _mesh_stats(),
        }

    try:
        payload = _run_gmsh(f"mesh_{run_id}", build)
        payload["code_fingerprint"] = __import__("src.build_info", fromlist=["code_fingerprint"]).code_fingerprint()
        return payload
    except Exception as exc:
        logger.exception("mesh_and_export failed")
        return {"status": "error", "message": str(exc), "run_id": run_id}
