# Pressure-Ratio Study

This study was updated from existing completed OpenFOAM outputs only. The cases use the same quasi-2D Laval nozzle geometry, `rhoCentralFoam`, ideal-gas air, slip walls, and `empty` front/back patches. Mass flow is computed directly as `integral(rho * U dot n dA)` from saved `rho`, `U`, and mesh-face data; `phi`, `rhoPhi`, and `rho*phi` are not used for mass-flow validation.

| Case | `p0` [Pa] | `T0` [K] | `pb` [Pa] | `pb/p0` | Expected regime | Observed regime | Latest time | Max Mach | Throat Mach | Mass error [%] | Max Co | Verdict |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `subsonic` | 300000 | 300 | 290000 | 0.966667 | fully subsonic flow through the nozzle | fully subsonic | 0.006 | 0.480536 | 0.480536 | 0.690756 | 0.612799 | valid |
| `choked` | 300000 | 300 | 158500 | 0.528333 | choked flow with supersonic acceleration for the current back pressure | choked with internal-shock-like behavior | 0.002 | 2.30388 | 1.03652 | 0.277965 | 0.355479 | valid |
| `internal_shock` | 300000 | 300 | 140000 | 0.466667 | choked flow with an internal normal shock in the divergent section | choked with internal shock | 0.002 | 2.36018 | 1.03577 | 0.256732 | 0.201246 | valid |

## Interpretation

The `subsonic` case remains below Mach 1 and is treated as the fully subsonic operating point. The `choked` case reaches approximately sonic conditions at the throat; the existing solution also shows internal-shock-like behavior downstream, so it should not be described as a clean shock-free isentropic expansion. The `internal_shock` case reaches sonic throat conditions, accelerates supersonically in the divergent section, and shows shock behavior consistent with its lower back pressure.

The directory names are retained because they describe the intended pressure-ratio sequence. The documentation reports the observed behavior explicitly where it differs from an idealized label.
