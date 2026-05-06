# Validation Summary: Choked Case

Case directory: `cases/choked`

Latest time analyzed: `0.002`

This document summarizes existing OpenFOAM outputs only. No solver rerun, mesh regeneration, cleaning, or result deletion was performed. Mass flow is computed directly from saved `rho`, `U`, and mesh-face data; `phi`, `rhoPhi`, and `rho*phi` are not used.

## Key Metrics

| Metric | Value |
| --- | ---: |
| Max Courant number | 0.355479 |
| Final Courant number | 0.349096 |
| Pressure range [Pa] | 23386.6 / 288256 |
| Temperature range [K] | 144.663 / 296.562 |
| Density range [kg/m3] | 0.563184 / 3.38612 |
| Mach range | 0.256226 / 2.32206 |
| Throat Mach | 1.03652 |
| Max Mach | 2.30388 |
| Inlet mass flow [kg/s] | -0.0139777 |
| Outlet mass flow [kg/s] | 0.0139388 |
| Mass conservation error [%] | 0.277965 |

## Assessment

The choked case reaches approximately sonic conditions at the throat and accelerates supersonically downstream. The existing output also shows internal-shock-like downstream behavior, so this case should not be described as a clean shock-free isentropic expansion. The directory name is retained because it identifies the intended choked pressure-ratio case.

Primitive fields remain positive, the existing mesh quality summary passes, the Courant history remains bounded, and the final mass conservation error is below 1%.

## Area-Mach Interpretation

The area-Mach comparison uses the subsonic branch upstream of the throat and the supersonic branch downstream. Its relatively high RMS Mach error indicates that ideal isentropic theory is only a diagnostic reference for this case. Area-Mach theory is not valid through shock-containing regions.

## Artifacts

- Profile plots: `docs/images/choked/`
- Area-Mach plot: `docs/images/choked_area_mach_validation.png`
- Time-history plots: `docs/images/choked_courant_history.png`, `docs/images/choked_mass_flow_history.png`, `docs/images/choked_throat_mach_history.png`

## Final Verdict

`VALID`
