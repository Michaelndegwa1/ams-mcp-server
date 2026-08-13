"""
inp_mesh_utils.py
Parse CalculiX .inp meshes and compute face-set areas for load conversion.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import numpy as np

logger = logging.getLogger("inp_mesh_utils")

_DOF_MAP = {"DX": 1, "DY": 2, "DZ": 3}


def parse_inp_mesh(inp_path: Path) -> dict:
    text = inp_path.read_text(encoding="utf-8", errors="replace")
    nodes: dict[int, np.ndarray] = {}
    elements: dict[int, list[int]] = {}
    nsets: dict[str, set[int]] = {}
    elsets: dict[str, list[int]] = {}

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        upper = line.upper()
        if upper.startswith("*NODE"):
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("*"):
                parts = [p.strip() for p in lines[i].split(",") if p.strip()]
                if len(parts) >= 4:
                    nid = int(parts[0])
                    nodes[nid] = np.array([float(parts[1]), float(parts[2]), float(parts[3])])
                i += 1
            continue
        if upper.startswith("*ELEMENT"):
            etype_match = re.search(r"TYPE=([A-Z0-9]+)", upper)
            elset_match = re.search(r"ELSET=([A-Za-z0-9_\-]+)", line, re.I)
            elset = elset_match.group(1) if elset_match else "DEFAULT"
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("*"):
                parts = [p.strip() for p in lines[i].split(",") if p.strip()]
                if len(parts) >= 2:
                    eid = int(parts[0])
                    conn = [int(p) for p in parts[1:]]
                    elements[eid] = conn
                    elsets.setdefault(elset, []).append(eid)
                i += 1
            continue
        if upper.startswith("*NSET"):
            nset_match = re.search(r"NSET=([A-Za-z0-9_\-]+)", line, re.I)
            nset = nset_match.group(1) if nset_match else "DEFAULT"
            generate = "GENERATE" in upper
            i += 1
            ids: set[int] = set()
            while i < len(lines) and not lines[i].strip().startswith("*"):
                parts = [p.strip() for p in lines[i].split(",") if p.strip()]
                if generate and len(parts) >= 3:
                    start, stop, step = int(parts[0]), int(parts[1]), int(parts[2])
                    ids.update(range(start, stop + 1, step))
                elif parts:
                    ids.add(int(parts[0]))
                i += 1
            nsets[nset] = ids
            continue
        i += 1

    return {"nodes": nodes, "elements": elements, "nsets": nsets, "elsets": elsets}


def _tri_area(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    return 0.5 * float(np.linalg.norm(np.cross(b - a, c - a)))


def compute_elset_area(inp_path: Path, elset_name: str) -> float:
    mesh = parse_inp_mesh(inp_path)
    nodes = mesh["nodes"]
    elset = mesh["elsets"].get(elset_name)
    if not elset:
        raise ValueError(f"ELSET '{elset_name}' not found in {inp_path}")

    total = 0.0
    for eid in elset:
        conn = mesh["elements"].get(eid, [])
        if len(conn) == 3:
            total += _tri_area(nodes[conn[0]], nodes[conn[1]], nodes[conn[2]])
        elif len(conn) == 4:
            p = [nodes[n] for n in conn]
            total += _tri_area(p[0], p[1], p[2]) + _tri_area(p[0], p[2], p[3])
        elif len(conn) >= 3:
            p0 = nodes[conn[0]]
            for k in range(1, len(conn) - 1):
                total += _tri_area(p0, nodes[conn[k]], nodes[conn[k + 1]])

    if total <= 0:
        raise ValueError(f"Non-positive area for ELSET '{elset_name}'")
    logger.info("ELSET '%s' area = %.6f mm^2", elset_name, total)
    return total
