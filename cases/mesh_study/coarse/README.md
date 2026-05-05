# Coarse Mesh Study Case

Coarse-resolution choked Laval nozzle case for the mesh-independence study.

Only `system/blockMeshDict` resolution differs from `cases/choked`; geometry, physics, boundary conditions, solver, and runtime controls are kept the same.

- Target cell count: approximately `20000`
- Expected generated cells: `20000`

Run from the repository root:

```bash
./Allrun cases/mesh_study/coarse
python3 scripts/mesh_independence.py
```
