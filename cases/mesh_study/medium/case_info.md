# Medium Mesh Choked Laval Nozzle Case

- Template: `cases/choked`
- Target cells: approximately 70000
- Expected generated cells: 70000
- Physics: same choked-case boundary conditions, solver, runtime controls, and geometry
- Purpose: baseline portfolio mesh for the choked nozzle case

Run from the repository root with:

```sh
./Allrun cases/mesh_study/medium
python3 scripts/mesh_independence.py
```
