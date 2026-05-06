# Mesh Independence Study

All mesh-study cases were analyzed from existing completed outputs only. Runtime is parsed from available solver log segments; no solver was rerun.

| mesh | cell_count | runtime_s | throat_Mach | delta_throat_Mach_from_previous | max_Mach | mass_error_percent | delta_mass_error_from_previous_pctpt | mdot_in_kg_s | mdot_out_kg_s | max_Courant | final_Courant | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| coarse | 20000 | 463.85 | 1.04648 |  | 2.2641 | 0.512397 |  | -0.0139793 | 0.0139076 | 0.358095 | 0.350183 | valid |
| medium | 70000 | 3500.52 | 1.03652 | -0.00995227 | 2.30388 | 0.277965 | -0.234432 | -0.0139777 | 0.0139388 | 0.355479 | 0.349096 | valid |
| fine | 150000 | 12863.8 | 1.0468 | 0.0102739 | 2.2675 | 0.183476 | -0.0944886 | -0.0139772 | 0.0139516 | 0.418804 | 0.351029 | valid |

## Medium-Mesh Sufficiency

The medium-to-fine throat Mach change is `0.0102739` (`0.9815%` relative to fine) and the mass-error change is `0.0944886` percentage points. The medium mesh is sufficient for regime classification and validation-level conclusions, because the sonic throat, supersonic divergent flow, and mass conservation are unchanged within about 1% relative throat Mach.

For strict quantitative reporting with an absolute throat-Mach tolerance of `0.01`, use the fine mesh or report the medium result with this residual discretization difference.

Generated plots:

- `docs/images/mesh_independence_throat_mach.png`
- `docs/images/mesh_independence_mass_error.png`
- `docs/images/mesh_independence_max_mach.png`
