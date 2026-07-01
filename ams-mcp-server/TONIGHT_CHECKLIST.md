# Tonight's Checklist — Get to a Working Demo

Work in this exact order. Don't skip ahead — each step isolates a different
failure point, so if something breaks you'll know exactly where.

## 1. Confirm Code_Aster runs at all (5 min)
```bash
docker exec -it <container_name> as_run --help
```
If this fails, fix it before touching any Python. Nothing downstream works
without this.

## 2. Get a real test mesh with known group names (15 min)
Follow `examples/README_GET_TEST_MESH.md`. Do NOT invent group names —
use the exact ones from a real `.mmed`/`.comm` pair from Code_Aster's
own test library.

## 3. Set up the project (5 min)
```bash
cd ams-mcp-server
python -m venv env
source env/bin/activate          # or env\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set CODE_ASTER_PATH to match `which as_run` INSIDE the container
```

**Important:** if Code_Aster only exists inside Docker and this Python
project runs on your host machine, `subprocess.run([CODE_ASTER_PATH, ...])`
will fail — there's no `as_run` on the host. Two options:
- Run this whole project *inside* the container (simplest for tonight), or
- Change the `cmd` list in `runner.py`'s `run_code_aster()` to:
  `["docker", "exec", "<container_name>", "as_run", str(export_path)]`
  (and make sure paths inside the container match)

## 4. Run the standalone test script (this is the real test)
```bash
python run_local_test.py examples/test_beam.med
```
Edit the `group_name` values inside `run_local_test.py` first to match your
mesh (step 2). Watch the output:
- `✓ SUCCESS` → pipeline works end to end. Move to step 5.
- `✗ FAILED` with a Code_Aster log → read the log, usually a group name
  mismatch or .comm syntax issue.
- Result returned but `max_displacement_mm` / `max_stress_mpa` are `null` →
  the field-path guessing in `results_parser.py` didn't match your MED
  version. Run `inspect_structure()` from that file against your actual
  `.rmed` output and update the keyword search in `parse_results()`.

## 5. Only once step 4 shows ✓ SUCCESS: wire up MCP
```bash
python -m src.server
```
Should start and hang silently (waiting on stdin) — that's correct, it
means it's alive. Ctrl+C to stop.

Register it in Claude Desktop's config and restart Claude Desktop, then
try a prompt like:

> "Run a static structural analysis on the beam mesh at
> examples/test_beam.med — steel, fixed at the Encastre group, 500N
> downward force at the Load_Point group."

## 6. Backup plan if live demo is risky
Run step 4 successfully once, screenshot the terminal output (prompt,
JSON result, verdict text). If the live MCP call misbehaves tomorrow during
the 10 minutes, fall back to: "let me show you the validated run from last
night" + screenshot, then walk through the architecture diagram instead.
A working pipeline you can *describe* beats a live call that hangs in front
of the room.

## Priority if you run out of time tonight
1. Step 4 (`run_local_test.py` showing ✓ SUCCESS) is the non-negotiable
   minimum. This alone proves Objective 1 (Technical Feasibility) from
   your Prototyping Plan.
2. Step 5 (MCP + Claude Desktop) proves Objective 2 (FEM-Agent Integration)
   but is secondary — you can talk through the architecture diagram if it's
   not fully wired by morning.
