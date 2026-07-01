# Getting a Test Mesh Tonight

You need a `.med` mesh file with **named groups** for the fixed end and the
loaded point/face — `comm_generator.py` references group names directly
(`GROUP_MA='Encastre'`, etc.), it doesn't know geometry.

## Fastest path: use one of Code_Aster's own test cases

Code_Aster ships with an `astest/` directory containing hundreds of official
test cases, each with a working mesh + known correct answer. This is exactly
what your Prototyping Plan's "validation benchmark" calls for.

Inside your Docker container:

```bash
docker exec -it <container_name> bash
find / -iname "*.mmed" -path "*astest*" 2>/dev/null | grep -i -E "sslv|forma" | head -20
```

Look for something starting `sslv` (Static Structural Linear Validation) or
`forma` (formation/training cases) — these are simple, well-documented
linear elastic cases (bars, beams, plates) with known analytical answers.
A good first target: **`sslv01a`** or **`sslv112`** — both are simple beam
or bar tension cases.

Once you find one:

```bash
docker cp <container_name>:/path/to/sslv01a.mmed ./examples/test_beam.med
```

Then **open the matching `.comm` file for that same test case** (same
directory, `.comm` extension) in a text editor — it will tell you the exact
`GROUP_MA` names used for boundary conditions and loads in that mesh. Use
those exact names in `run_local_test.py` instead of the placeholder
`"Encastre"` / `"Load_Point"`.

## If you can't find a matching .comm file

Run this inside the container to dump the mesh's group names directly:

```python
import h5py
with h5py.File("test_beam.med", "r") as f:
    f.visititems(lambda name, obj: print(name))
```

Group names will appear somewhere under a path containing `FAS` or
`GROUPE`. Whatever you see there is what goes into `group_name` in your
boundary conditions and loads.

## If nothing is found at all

Tell me and I'll generate a `.comm` macro that builds a simple 3D beam mesh
analytically inside Code_Aster itself (no external mesh file needed) — slower
to set up but guarantees you have *something* working mesh-wise before the
pitch.
