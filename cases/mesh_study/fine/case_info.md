# Fine Mesh Choked Laval Nozzle Case

- Template: `cases/choked`
- Target cells: 140000-200000
- Expected generated cells: 150000
- Physics: same choked-case boundary conditions, solver, runtime controls, and geometry
- Purpose: finer reference without making the case excessively expensive

Run from the repository root with:

```sh
./Allrun cases/mesh_study/fine
python3 scripts/mesh_independence.py
```
