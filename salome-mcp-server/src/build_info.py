import hashlib
from pathlib import Path
_FILES = ("salome_tools.py", "runner.py", "server.py")
def code_fingerprint() -> str:
    d = hashlib.sha256()
    src = Path(__file__).resolve().parent
    for n in _FILES:
        d.update(n.encode())
        p = src / n
        if p.exists(): d.update(p.read_bytes())
    return d.hexdigest()[:12]
