# Validation Summary

Case directory: `cases/subsonic`

Latest time analyzed: `0.004`

## Mass Flow Check

- method: direct patch integral `mdot = integral(rho * U dot n dA)`
- field source: OpenFOAM ASCII `rho` and `U` at the analyzed time; no `phi` or `rho*phi` required
- inlet patch: `inlet`
- outlet patch: `outlet`
- `mdot_in`: -8.41622209e-03 kg/s
- `mdot_out`: 8.41952137e-03 kg/s
- mass conservation error: 0.0392%
- assessment: excellent

Criteria: `<1%` excellent, `<3%` acceptable, `3-5%` marginal, `>5%` problematic.

## Courant Number Summary

- entries parsed: 61121
- maximum mean Co: 0.101724
- maximum max Co: 0.545193
- final mean/max Co: 0.0913851 / 0.502251
- stability note: prefer `maxCo < 0.5`; warn if `maxCo > 1.0`

## Mesh Quality Summary

- maximum non-orthogonality: 18.0758
- maximum skewness: 0.19051
- negative volume cells: 0
- mesh passed: True

## Physical Sanity Checks

- `p` min/max: 248111 / 305779
- `T` min/max: 284.027 / 301.626
- `rho` min/max: 3.04317 / 3.53165
- `Ma` min/max: 0.127996 / 0.431461
- assessment: pass

## Choking Check

- throat-region max Mach: 0.352685
- global max Mach: 0.356308
- status: pass
- note: subsonic case: Mach should remain below 1

## Comparison With Isentropic Theory

- reference uses isentropic air relations with `gamma = 1.4` evaluated from CFD centerline Mach number
- RMS error in `p/p0`: 0.0161714
- RMS error in `T/T0`: 0.00468849
- RMS error in `rho/rho0`: 0.0118969
- plots written to `docs/images/subsonic`
- centerline CSV written to `cases/subsonic/postProcessing/centerline/centerline_latest.csv`

## Area-Mach Relation Validation

- reference solves the quasi-1D isentropic area-Mach relation from `system/blockMeshDict`
- throat x-location: 0.05 m
- throat area proxy: 0.02 m2 per unit depth
- A/A* range: 1.00017 to 2.49464
- RMS error in Mach over valid isentropic points: 0.259729
- valid comparison points: 399 / 399
- branch/masking note: subsonic branch used over the full nozzle
- Mach comparison plot: `docs/images/subsonic_mach_area_relation.png`
- area-ratio plot: `docs/images/subsonic_area_ratio.png`

## Time-History Steadiness Check

- final max Courant: 0.502251
- final mass conservation error from histories: 0.0392015%
- last-10% relative variation: 250.152% using `mass conservation error`
- steadiness classification: still transient
- criterion: `<1%` quasi-steady, `1-5%` nearly steady, `>5%` still transient
- Courant plot: `docs/images/subsonic_courant_history.png`
- timestep plot: `docs/images/subsonic_timestep_history.png`
- mass-flow plot: `docs/images/subsonic_mass_flow_history.png`
- throat-Mach plot: `docs/images/subsonic_throat_mach_history.png`

## Final Verdict

**VALID**
