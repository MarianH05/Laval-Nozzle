# Area-Mach Validation

Generated from existing latest-time fields only. Centerline data are extracted from OpenFOAM ASCII fields; nozzle `A(x)/A*` is reconstructed from `system/blockMeshDict`; both subsonic and supersonic branches of the quasi-1D isentropic area-Mach relation are solved numerically.

| case | latest_time | cfd_throat_mach | cfd_max_mach | rms_error | pre_shock_rms_error | post_shock_rms_error | valid_points | masked_points | shock_x_m | plot |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| subsonic | 0.006 | 0.480624 | 0.480624 | 0.197192 |  |  | 459 | 0 |  | docs/images/subsonic_area_mach_validation.png |
| choked | 0.002 | 1.04479 | 2.26366 | 0.569107 |  |  | 459 | 0 |  | docs/images/choked_area_mach_validation.png |
| internal_shock | 0.002 | 1.04399 | 2.37448 | 0.0757175 | 0.0146076 | 0.0286899 | 370 | 89 | 0.0561075 | docs/images/internal_shock_area_mach_validation.png |

## Notes

- The subsonic case is compared against the subsonic branch over the full nozzle.
- The choked case uses the subsonic branch upstream of the throat and the supersonic branch downstream.
- The internal-shock case masks the detected shock region and does not apply geometric-throat isentropic theory through the shock. Post-shock comparison, where reported, uses a fitted downstream subsonic branch because entropy has changed across the shock.
- The geometry is quasi-2D, so the area is an area proxy per unit depth reconstructed from nozzle height.
