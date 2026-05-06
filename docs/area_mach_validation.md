# Area-Mach Validation

This validation is generated from existing latest-time fields only. Centerline data are extracted from OpenFOAM ASCII fields, `A(x)/A*` is reconstructed from `system/blockMeshDict`, and the subsonic and supersonic branches of the quasi-1D isentropic area-Mach relation are solved numerically.

The geometry is quasi-2D, so the area is an area proxy per unit depth reconstructed from nozzle height. Area-Mach theory is inviscid and isentropic; it is not valid through shocks or across entropy-producing regions.

| Case | Latest time | CFD throat Mach | CFD max Mach | RMS Mach error | Pre-shock RMS | Post-shock RMS | Valid points | Masked points | Shock `x` [m] | Plot |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `subsonic` | 0.006 | 0.480624 | 0.480624 | 0.197192 |  |  | 459 | 0 |  | `docs/images/subsonic_area_mach_validation.png` |
| `choked` | 0.002 | 1.04479 | 2.26366 | 0.569107 |  |  | 459 | 0 |  | `docs/images/choked_area_mach_validation.png` |
| `internal_shock` | 0.002 | 1.04399 | 2.37448 | 0.0757175 | 0.0146076 | 0.0286899 | 370 | 89 | 0.0561075 | `docs/images/internal_shock_area_mach_validation.png` |

## Interpretation

- The `subsonic` case is compared against the subsonic branch over the full nozzle.
- The `choked` case uses the subsonic branch upstream of the throat and the supersonic branch downstream, but the high RMS error indicates that the computed field is not a clean shock-free isentropic expansion over the whole divergent section.
- The `internal_shock` case masks the detected shock region. Post-shock comparison, where reported, uses a fitted downstream subsonic branch because entropy has changed across the shock.
