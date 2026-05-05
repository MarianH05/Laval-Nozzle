# Pressure-Ratio Study

This table reflects only the files currently present in `cases/subsonic`, `cases/choked`, and `cases/internal_shock`. No solver, mesher, or checker was rerun for this update.

| case_name | case_dir | latest_time | status | p0_Pa | T0_K | pb_Pa | pb_over_p0 | expected_regime | max_Courant | mesh_max_non_orthogonality | mesh_max_skewness | mesh_negative_volume_cells | mesh_passed | p_min_Pa | p_max_Pa | T_min_K | T_max_K | rho_min_kg_m3 | rho_max_kg_m3 | Ma_min | Ma_max | mdot_in_kg_s | mdot_out_kg_s | mass_error_percent | throat_Mach | validation_verdict | notes |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| subsonic | `cases/subsonic` | 0.0025 | computed | 3.000000e+05 | 300 | 2.900000e+05 | 0.966667 | fully subsonic flow through the nozzle | 0.545193 | 18.0758 | 0.19051 | 0 | true | 260001 | 307225 | 287.802 | 302.027 | 3.14717 | 3.54363 | 0.0946621 | 0.343661 | -6.263109e-03 | 6.000709e-03 | 4.18962 | 0.343661 | questionable | Latest fields present; stored `Ma` used; mass conservation is marginal. |
| choked | `cases/choked` | 0 | `NOT AVAILABLE / NEEDS RUN` | 3.000000e+05 | 300 | 1.585000e+05 | 0.528333 | choked flow with supersonic acceleration in the divergent section for the current back pressure | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | `NOT AVAILABLE / NEEDS RUN` | Latest numeric time is initial time `0` and required field `rho` is missing. |
| internal_shock | `cases/internal_shock` | 0 | `NOT AVAILABLE / NEEDS RUN` | 3.000000e+05 | 300 | 1.400000e+05 | 0.466667 | choked flow with an internal normal shock in the divergent section | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | `NOT AVAILABLE / NEEDS RUN` | Latest numeric time is initial time `0` and required field `rho` is missing. |

## Interpretation

The prescribed reservoir state is fixed at `p0 = 300000 Pa` and `T0 = 300 K` while back pressure is varied. A high `pb/p0` is expected to remain fully subsonic; pressure ratios near the ideal critical value for air (`pb/p0 ~= 0.528`) should choke at the throat; lower back pressures can produce supersonic flow and, for suitable back pressure, an internal normal shock.

Only the current `subsonic` case has a usable latest result directory with `p`, `T`, `rho`, and `U`. Its field values remain physically positive and subsonic, but the direct inlet/outlet mass-flow mismatch is `4.18962%`, so the validation verdict is `questionable`.

The current `choked` and `internal_shock` directories do not contain completed non-initial result directories with all required fields. They remain study definitions in the present checkout and are not treated as completed CFD results.
