# Coarse Mesh Choked Laval Nozzle Case

- Template: `cases/choked`
- Target cells: approximately 20000
- Expected generated cells: 20000
- Physics: same choked-case boundary conditions, solver, runtime controls, and geometry
- Purpose: low-cost mesh-independence reference

Run from the repository root with:

```sh
./Allrun cases/mesh_study/coarse
python3 scripts/mesh_independence.py
```
