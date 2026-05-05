# Validation Summary

Case directory: `cases/internal_shock`

Latest time analyzed: `0.002`

## Mass Flow Check

- method: direct patch integral `mdot = integral(rho * U dot n dA)`
- field source: OpenFOAM ASCII `rho` and `U` at the analyzed time; no `phi` or `rho*phi` required
- inlet patch: `inlet`
- outlet patch: `outlet`
- `mdot_in`: -1.39718001e-02 kg/s
- `mdot_out`: 1.39359301e-02 kg/s
- mass conservation error: 0.2567%
- assessment: excellent

Criteria: `<1%` excellent, `<3%` acceptable, `3-5%` marginal, `>5%` problematic.

## Courant Number Summary

- entries parsed: 104026
- maximum mean Co: 0.0448416
- maximum max Co: 0.201246
- final mean/max Co: 0.0349514 / 0.199918
- stability note: prefer `maxCo < 0.5`; warn if `maxCo > 1.0`

## Mesh Quality Summary

- maximum non-orthogonality: 18.0758
- maximum skewness: 0.19051
- negative volume cells: 0
- mesh passed: True

## Physical Sanity Checks

- `p` min/max: 19704.1 / 288233
- `T` min/max: 137.74 / 296.557
- `rho` min/max: 0.498352 / 3.38591
- `Ma` min/max: 0.255844 / 2.42717
- assessment: pass

## Choking Check

- throat-region max Mach: 1.03564
- global max Mach: 2.35988
- status: pass
- note: throat Mach is approximately sonic

## Comparison With Isentropic Theory

- reference uses isentropic air relations with `gamma = 1.4` evaluated from CFD centerline Mach number
- RMS error in `p/p0`: 0.0798456
- RMS error in `T/T0`: 0.00343901
- RMS error in `rho/rho0`: 0.0842885
- plots written to `docs/images/internal_shock`
- centerline CSV written to `cases/internal_shock/postProcessing/centerline/centerline_latest.csv`

## Area-Mach Relation Validation

- reference solves the quasi-1D isentropic area-Mach relation from `system/blockMeshDict`
- throat x-location: 0.05 m
- throat area proxy: 0.02 m2 per unit depth
- A/A* range: 1.00017 to 2.49464
- RMS error in Mach over valid isentropic points: 0.0944668
- pre-shock isentropic RMS error in Mach: 0.062915
- post-shock isentropic RMS error in Mach: 0.0227071
- post-shock comparison points: 18
- valid comparison points: 336 / 399
- detected shock location: x = 0.0677379 m
- branch/masking note: subsonic branch before the throat and supersonic branch after the throat; the detected shock and downstream post-shock region are masked because the geometric-throat isentropic area-Mach relation is not applicable across entropy production
- Mach comparison plot: `docs/images/internal_shock_mach_area_relation.png`
- area-ratio plot: `docs/images/internal_shock_area_ratio.png`

## Time-History Steadiness Check

- final max Courant: 0.199918
- final mass conservation error from histories: 0.256732%
- last-10% relative variation: 220.497% using `mass conservation error`
- steadiness classification: still transient
- criterion: `<1%` quasi-steady, `1-5%` nearly steady, `>5%` still transient
- Courant plot: `docs/images/internal_shock_courant_history.png`
- timestep plot: `docs/images/internal_shock_timestep_history.png`
- mass-flow plot: `docs/images/internal_shock_mass_flow_history.png`
- throat-Mach plot: `docs/images/internal_shock_throat_mach_history.png`

## Final Verdict

**VALID**
