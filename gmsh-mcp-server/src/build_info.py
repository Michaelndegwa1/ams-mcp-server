"""
build_info.py
Fingerprint of the pipeline source so every run proves which code executed.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

_PIPELINE_FILES = (
    "gmsh_tools.py",
    "server.py",
)


def code_fingerprint() -> str:
    digest = hashlib.sha256()
    src = Path(__file__).resolve().parent
    for name in _PIPELINE_FILES:
        path = src / name
        digest.update(name.encode())
        if path.exists():
            digest.update(path.read_bytes())
    return digest.hexdigest()[:12]
