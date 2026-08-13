import subprocess, sys
from pathlib import Path
from watchfiles import run_process
ROOT = Path(__file__).resolve().parent
def _run():
    subprocess.run([sys.executable, "-m", "src.server"], cwd=ROOT, check=False)
def main():
    paths = [ROOT / "src"]
    if (ROOT / ".env").exists(): paths.append(ROOT / ".env")
    run_process(*paths, target=_run)
if __name__ == "__main__": main()
