# Validation Summary

Case directory: `cases/choked`

Latest time analyzed: `0.002`

## Mass Flow Check

- method: direct patch integral `mdot = integral(rho * U dot n dA)`
- field source: OpenFOAM ASCII `rho` and `U` at the analyzed time; no `phi` or `rho*phi` required
- inlet patch: `inlet`
- outlet patch: `outlet`
- `mdot_in`: -1.39776858e-02 kg/s
- `mdot_out`: 1.39388328e-02 kg/s
- mass conservation error: 0.2780%
- assessment: excellent

Criteria: `<1%` excellent, `<3%` acceptable, `3-5%` marginal, `>5%` problematic.

## Courant Number Summary

- entries parsed: 58939
- maximum mean Co: 0.0773551
- maximum max Co: 0.355479
- final mean/max Co: 0.0594591 / 0.349096
- stability note: prefer `maxCo < 0.5`; warn if `maxCo > 1.0`

## Mesh Quality Summary

- maximum non-orthogonality: 18.0758
- maximum skewness: 0.19051
- negative volume cells: 0
- mesh passed: True

## Physical Sanity Checks

- `p` min/max: 23386.6 / 288256
- `T` min/max: 144.663 / 296.562
- `rho` min/max: 0.563184 / 3.38612
- `Ma` min/max: 0.256193 / 2.32177
- assessment: pass

## Choking Check

- throat-region max Mach: 1.03639
- global max Mach: 2.30358
- status: pass
- note: throat Mach is approximately sonic

## Comparison With Isentropic Theory

- reference uses isentropic air relations with `gamma = 1.4` evaluated from CFD centerline Mach number
- RMS error in `p/p0`: 0.106815
- RMS error in `T/T0`: 0.00294581
- RMS error in `rho/rho0`: 0.111694
- plots written to `docs/images/choked`
- centerline CSV written to `cases/choked/postProcessing/centerline/centerline_latest.csv`

## Area-Mach Relation Validation

- reference solves the quasi-1D isentropic area-Mach relation from `system/blockMeshDict`
- throat x-location: 0.05 m
- throat area proxy: 0.02 m2 per unit depth
- A/A* range: 1.00017 to 2.49464
- RMS error in Mach over valid isentropic points: 0.587603
- valid comparison points: 399 / 399
- branch/masking note: subsonic branch before the throat and supersonic branch after the throat
- Mach comparison plot: `docs/images/choked_mach_area_relation.png`
- area-ratio plot: `docs/images/choked_area_ratio.png`

## Time-History Steadiness Check

- final max Courant: 0.349096
- final mass conservation error from histories: 0.277965%
- last-10% relative variation: 95.3662% using `mass conservation error`
- steadiness classification: still transient
- criterion: `<1%` quasi-steady, `1-5%` nearly steady, `>5%` still transient
- Courant plot: `docs/images/choked_courant_history.png`
- timestep plot: `docs/images/choked_timestep_history.png`
- mass-flow plot: `docs/images/choked_mass_flow_history.png`
- throat-Mach plot: `docs/images/choked_throat_mach_history.png`

## Final Verdict

**VALID**
