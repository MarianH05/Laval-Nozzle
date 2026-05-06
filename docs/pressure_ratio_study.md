# Pressure-Ratio Study

Updated from existing completed OpenFOAM outputs only. Mass flow uses `integral(rho * U dot n dA)`; `phi` and `rho*phi` are not used.

| case_name | p0_Pa | T0_K | pb_Pa | pb_over_p0 | expected_regime | observed_regime | latest_time | completion_status | observed_max_Mach | observed_throat_Mach | mdot_in_kg_s | mdot_out_kg_s | mass_error_percent | max_Courant | final_Courant | mesh_cells | validation_verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| subsonic | 3.000000e+05 | 300 | 2.900000e+05 | 0.966667 | fully subsonic flow through the nozzle | fully subsonic | 0.006 | complete: latest time reaches endTime and final solver log contains End | 0.480536 | 0.480536 | -0.0103835 | 0.0104557 | 0.690756 | 0.612799 | 0.449957 | 70000 | valid |
| choked | 3.000000e+05 | 300 | 1.585000e+05 | 0.528333 | choked flow with supersonic acceleration in the divergent section for the current back pressure | choked with internal shock | 0.002 | complete: latest time reaches endTime and final solver log contains End | 2.30388 | 1.03652 | -0.0139777 | 0.0139388 | 0.277965 | 0.355479 | 0.349096 | 70000 | valid |
| internal_shock | 3.000000e+05 | 300 | 1.400000e+05 | 0.466667 | choked flow with an internal normal shock in the divergent section | choked with internal shock | 0.002 | complete: latest time reaches endTime and final solver log contains End | 2.36018 | 1.03577 | -0.0139718 | 0.0139359 | 0.256732 | 0.201246 | 0.199918 | 70000 | valid |

## Interpretation

The subsonic case remains below Mach 1. The choked pressure ratio produces sonic throat conditions and downstream supersonic acceleration. The internal-shock case reaches supersonic flow downstream of the throat and then returns to subsonic flow, consistent with an internal shock.
