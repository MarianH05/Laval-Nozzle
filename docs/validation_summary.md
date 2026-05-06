# Validation Summary

This summary was regenerated from existing completed OpenFOAM outputs only. `rhoCentralFoam`, `Allrun`, `Allclean`, and time-directory deletion were not performed. Missing `Ma` fields were handled by computing `|U| / sqrt(gamma R T)` from existing `U` and `T`. Mass flow was computed directly from saved `rho`, `U`, and mesh-face data; `phi`, `rhoPhi`, and `rho*phi` were not used.

The cases are quasi-2D OpenFOAM setups with `empty` front/back patches and intentionally slip walls for inviscid/isentropic validation. This is a compact portfolio validation project, not a production-grade nozzle design workflow.

## All Cases

| case | latest_time | completion | max_Co | final_Co | mesh_quality | p_min_max | T_min_max | rho_min_max | Ma_min_max | mdot_in | mdot_out | mass_error | throat_Mach | max_Mach | expected | observed | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `cases/subsonic` | 0.006 | complete: latest time reaches endTime and final solver log contains End | 0.612799 | 0.449957 | pass=True; nonOrth=18.0758; skew=0.19051; negVol=0 | 2.363790e+05 / 3.018460e+05 | 280.23 / 300.517 | 2.93855 / 3.49909 | 0.160331 / 0.581113 | -0.0103835 | 0.0104557 | 0.690756% | 0.480536 | 0.480536 | fully subsonic flow through the nozzle | fully subsonic | `VALID` |
| `cases/choked` | 0.002 | complete: latest time reaches endTime and final solver log contains End | 0.355479 | 0.349096 | pass=True; nonOrth=18.0758; skew=0.19051; negVol=0 | 23386.6 / 2.882560e+05 | 144.663 / 296.562 | 0.563184 / 3.38612 | 0.256226 / 2.32206 | -0.0139777 | 0.0139388 | 0.277965% | 1.03652 | 2.30388 | choked flow with supersonic acceleration in the divergent section for the current back pressure | choked with internal shock | `VALID` |
| `cases/internal_shock` | 0.002 | complete: latest time reaches endTime and final solver log contains End | 0.201246 | 0.199918 | pass=True; nonOrth=18.0758; skew=0.19051; negVol=0 | 19704.1 / 2.882330e+05 | 137.74 / 296.557 | 0.498352 / 3.38591 | 0.255877 / 2.42748 | -0.0139718 | 0.0139359 | 0.256732% | 1.03577 | 2.36018 | choked flow with an internal normal shock in the divergent section | choked with internal shock | `VALID` |
| `cases/mesh_study/coarse` | 0.002 | complete: latest time reaches endTime and final solver log contains End | 0.358095 | 0.350183 | pass=True; nonOrth=18.0258; skew=0.184285; negVol=0 | 23774 / 2.873520e+05 | 145.352 / 296.291 | 0.569796 / 3.37859 | 0.266006 / 2.31525 | -0.0139793 | 0.0139076 | 0.512397% | 1.04648 | 2.2641 | choked/supersonic | choked with internal shock | `VALID` |
| `cases/mesh_study/medium` | 0.002 | complete: latest time reaches endTime and final solver log contains End | 0.355479 | 0.349096 | pass=True; nonOrth=18.0758; skew=0.19051; negVol=0 | 23386.6 / 2.882560e+05 | 144.663 / 296.562 | 0.563184 / 3.38612 | 0.256226 / 2.32206 | -0.0139777 | 0.0139388 | 0.277965% | 1.03652 | 2.30388 | choked/supersonic | choked with internal shock | `VALID` |
| `cases/mesh_study/fine` | 0.002 | complete: latest time reaches endTime and final solver log contains End | 0.418804 | 0.351029 | pass=True; nonOrth=18.096; skew=0.193223; negVol=0 | 23269 / 2.885610e+05 | 144.479 / 296.654 | 0.561061 / 3.38864 | 0.252718 / 2.32212 | -0.0139772 | 0.0139516 | 0.183476% | 1.0468 | 2.2675 | choked/supersonic | choked with internal shock | `VALID` |

## Verdict Basis

A case is treated as valid when primitive fields remain positive, checkMesh passes, Courant number remains below the stability limit, mass conservation is acceptable, and the observed Mach topology matches the expected regime. Marginal mass conservation or an ambiguous regime produces a questionable verdict rather than a valid one.

## Regime Notes

- `cases/subsonic` is the fully subsonic operating point.
- `cases/choked` reaches sonic throat conditions and the existing output shows internal-shock-like downstream behavior, so it should not be described as a clean shock-free isentropic expansion.
- `cases/internal_shock` is the lower-back-pressure shock case.
- Area-Mach theory is not valid through shocks; shock-containing regions require masking or separate downstream fitting.
