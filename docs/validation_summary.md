# Validation Summary

This summary was refreshed from files already present on disk. No CFD solver, mesh generation, mesh checking, or case setup modification was performed.

Analyzed case directories:

- `cases/subsonic`
- `cases/choked`
- `cases/internal_shock`

## Current On-Disk Results

| Case | Latest time | Field availability | Max Courant | Mesh quality | p min/max [Pa] | T min/max [K] | rho min/max [kg/m3] | Ma min/max [-] | mdot in [kg/s] | mdot out [kg/s] | Mass error | Throat Mach | Max Mach | Verdict |
| --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `cases/subsonic` | 0.0025 | `p`, `T`, `rho`, `U`, `Ma` present | 0.545193 | pass; max non-orthogonality 18.0758 deg; max skewness 0.19051; negative volumes 0 | 260001 / 307225 | 287.802 / 302.027 | 3.14717 / 3.54363 | 0.0946621 / 0.343661 | -6.263109e-03 | 6.000709e-03 | 4.1896% | 0.343661 | 0.343661 | `QUESTIONABLE` |
| `cases/choked` | 0 | missing `rho`; only initial fields available | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | `NOT AVAILABLE / NEEDS RUN` |
| `cases/internal_shock` | 0 | missing `rho`; only initial fields available | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | `NOT AVAILABLE / NEEDS RUN` |

## Method

- Latest time was selected as the numerically largest existing time directory in each case.
- Mass flow used the direct patch integral `mdot = integral(rho * U dot n dA)` over the `inlet` and `outlet` boundary faces, using owner-cell `rho` and `U` values and mesh face area vectors.
- `phi`, `rhoPhi`, and `rho*phi` were not used.
- Mach number was read from `Ma` where present. For the current subsonic latest time, the stored `Ma` field is present.
- Throat Mach is the maximum Mach number in cells with `|x - 0.05 m| <= 0.003 m`.
- Maximum Mach is the maximum over all cells.
- Courant values were parsed only from existing `log.rhoCentralFoam`.
- Mesh quality was parsed only from existing `log.checkMesh`.

## Notes

The current `cases/subsonic` result has positive pressure, temperature, and density and remains subsonic. Its mass conservation error is `4.1896%`, which is marginal by the project criterion (`<1%` excellent, `<3%` acceptable, `3-5%` marginal, `>5%` problematic), so the verdict is `QUESTIONABLE`.

The current `cases/choked` and `cases/internal_shock` directories do not contain completed non-initial result directories with all required fields. They are therefore marked `NOT AVAILABLE / NEEDS RUN`; no previously documented choked or shock results are claimed from the current disk state.
