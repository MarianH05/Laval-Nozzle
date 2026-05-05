# Mesh Independence Study

All variants use the choked Laval nozzle physics, geometry, solver, and runtime controls. Only `system/blockMeshDict` resolution changes.

| mesh | case_dir | target_cells | total_cell_count | max_non_orthogonality | max_skewness | mdot_in | mdot_out | mass_error_percent | mass_assessment | throat_Mach | max_Mach | runtime_s | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| coarse | cases/mesh_study/coarse | 20000 | 20000 |  |  |  |  |  |  |  |  |  | not run |
| medium | cases/mesh_study/medium | 70000 | 70000 |  |  |  |  |  |  |  |  |  | not run |
| fine | cases/mesh_study/fine | 150000 | 150000 |  |  |  |  |  |  |  |  |  | not run |

## Commands

- `coarse`: `./Allrun cases/mesh_study/coarse`
- `medium`: `./Allrun cases/mesh_study/medium`
- `fine`: `./Allrun cases/mesh_study/fine`
- After one or more cases finish: `python3 scripts/mesh_independence.py`

## Interpretation

The cases have not all been solved yet, so sufficiency cannot be concluded from computed results. The medium mesh is the intended portfolio default because it matches the existing 70000-cell baseline; confirm it by running at least the medium and fine cases and checking that throat Mach and mass flow change only slightly.
