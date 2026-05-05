# Medium Mesh Study Case

Medium-resolution choked Laval nozzle case for the mesh-independence study.

Only `system/blockMeshDict` resolution differs from the other mesh-study cases; geometry, physics, boundary conditions, solver, and runtime controls are kept the same. This mesh matches the current baseline resolution.

- Target cell count: approximately `70000`
- Expected generated cells: `70000`

Run from the repository root:

```bash
./Allrun cases/mesh_study/medium
python3 scripts/mesh_independence.py
```
