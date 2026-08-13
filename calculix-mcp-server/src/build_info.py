"""Pipeline fingerprint."""
from __future__ import annotations

import hashlib
from pathlib import Path

_FILES = ("calculix_tool.py", "inp_generator.py", "runner.py", "frd_parser.py", "inp_mesh_utils.py")


def code_fingerprint() -> str:
    digest = hashlib.sha256()
    src = Path(__file__).resolve().parent
    for name in _FILES:
        path = src / name
        digest.update(name.encode())
        if path.exists():
            digest.update(path.read_bytes())
    return digest.hexdigest()[:12]
