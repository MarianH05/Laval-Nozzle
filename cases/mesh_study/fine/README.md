# Fine Mesh Study Case

Fine-resolution choked Laval nozzle case for the mesh-independence study.

Only `system/blockMeshDict` resolution differs from `cases/choked`; geometry, physics, boundary conditions, solver, and runtime controls are kept the same. The fine mesh is limited to keep the case reasonable for a laptop-scale portfolio workflow.

- Target cell count: `140000-200000`
- Expected generated cells: `150000`

Run from the repository root:

```bash
./Allrun cases/mesh_study/fine
python3 scripts/mesh_independence.py
```
