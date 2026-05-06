# Validation Summary: Internal-Shock Case

Case directory: `cases/internal_shock`

Latest time analyzed: `0.002`

This document summarizes existing OpenFOAM outputs only. No solver rerun, mesh regeneration, cleaning, or result deletion was performed. Mass flow is computed directly from saved `rho`, `U`, and mesh-face data; `phi`, `rhoPhi`, and `rho*phi` are not used.

## Key Metrics

| Metric | Value |
| --- | ---: |
| Max Courant number | 0.201246 |
| Final Courant number | 0.199918 |
| Pressure range [Pa] | 19704.1 / 288233 |
| Temperature range [K] | 137.74 / 296.557 |
| Density range [kg/m3] | 0.498352 / 3.38591 |
| Mach range | 0.255877 / 2.42748 |
| Throat Mach | 1.03577 |
| Max Mach | 2.36018 |
| Inlet mass flow [kg/s] | -0.0139718 |
| Outlet mass flow [kg/s] | 0.0139359 |
| Mass conservation error [%] | 0.256732 |

## Assessment

The internal-shock case reaches approximately sonic conditions at the throat, accelerates supersonically in the divergent section, and shows shock behavior consistent with the lower imposed back pressure. Primitive fields remain positive, the existing mesh quality summary passes, the Courant history remains bounded, and the final mass conservation error is below 1%.

## Area-Mach Interpretation

The detected shock region is masked for the area-Mach comparison because geometric-throat isentropic theory is not valid through entropy-producing shocks. Where a post-shock comparison is reported, it uses a fitted downstream subsonic branch rather than the original upstream `A*`.

## Artifacts

- Profile plots: `docs/images/internal_shock/`
- Area-Mach plot: `docs/images/internal_shock_area_mach_validation.png`
- Time-history plots: `docs/images/internal_shock_courant_history.png`, `docs/images/internal_shock_mass_flow_history.png`, `docs/images/internal_shock_throat_mach_history.png`

## Final Verdict

`VALID`
