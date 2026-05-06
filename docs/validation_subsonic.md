# Validation Summary: Subsonic Case

Case directory: `cases/subsonic`

Latest time analyzed: `0.006`

This document summarizes existing OpenFOAM outputs only. No solver rerun, mesh regeneration, cleaning, or result deletion was performed. Mass flow is computed directly from saved `rho`, `U`, and mesh-face data; `phi`, `rhoPhi`, and `rho*phi` are not used.

## Key Metrics

| Metric | Value |
| --- | ---: |
| Max Courant number | 0.612799 |
| Final Courant number | 0.449957 |
| Pressure range [Pa] | 236379 / 301846 |
| Temperature range [K] | 280.23 / 300.517 |
| Density range [kg/m3] | 2.93855 / 3.49909 |
| Mach range | 0.160331 / 0.581113 |
| Throat Mach | 0.480536 |
| Max Mach | 0.480536 |
| Inlet mass flow [kg/s] | -0.0103835 |
| Outlet mass flow [kg/s] | 0.0104557 |
| Mass conservation error [%] | 0.690756 |

## Assessment

The subsonic case remains below Mach 1 throughout the nozzle and matches the expected fully subsonic regime. Primitive fields remain positive, the existing mesh quality summary passes, the Courant history remains bounded, and the final mass conservation error is below 1%.

The quasi-1D area-Mach comparison uses the subsonic branch over the full nozzle. This is a validation diagnostic for the quasi-2D slip-wall setup, not a production nozzle-design certification.

## Artifacts

- Profile plots: `docs/images/subsonic/`
- Area-Mach plot: `docs/images/subsonic_area_mach_validation.png`
- Time-history plots: `docs/images/subsonic_courant_history.png`, `docs/images/subsonic_mass_flow_history.png`, `docs/images/subsonic_throat_mach_history.png`

## Final Verdict

`VALID`
