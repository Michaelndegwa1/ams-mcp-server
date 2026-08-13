"""Pipeline fingerprint."""
from __future__ import annotations

import hashlib
from pathlib import Path

_FILES = ("freecad_tools.py", "runner.py", "server.py")


def code_fingerprint() -> str:
    d = hashlib.sha256()
    src = Path(__file__).resolve().parent
    for name in _FILES:
        d.update(name.encode())
        p = src / name
        if p.exists():
            d.update(p.read_bytes())
    return d.hexdigest()[:12]
