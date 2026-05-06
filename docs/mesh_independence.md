# Mesh Independence Study

All mesh-study cases were analyzed from existing completed outputs only. The study uses the choked operating point and varies the `blockMeshDict` resolution; physical setup values are otherwise unchanged. Runtime is parsed from available solver logs, and no solver rerun is implied by this document.

| Mesh | Cells | Runtime [s] | Throat Mach | Delta throat Mach | Max Mach | Mass error [%] | Delta mass error [pct pt] | `mdot_in` [kg/s] | `mdot_out` [kg/s] | Max Co | Final Co | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `coarse` | 20000 | 463.85 | 1.04648 |  | 2.2641 | 0.512397 |  | -0.0139793 | 0.0139076 | 0.358095 | 0.350183 | valid |
| `medium` | 70000 | 3500.52 | 1.03652 | -0.00995227 | 2.30388 | 0.277965 | -0.234432 | -0.0139777 | 0.0139388 | 0.355479 | 0.349096 | valid |
| `fine` | 150000 | 12863.8 | 1.0468 | 0.0102739 | 2.2675 | 0.183476 | -0.0944886 | -0.0139772 | 0.0139516 | 0.418804 | 0.351029 | valid |

## Assessment

The medium-to-fine throat Mach change is `0.0102739`, or `0.9815%` relative to the fine result. The mass-conservation error decreases monotonically with refinement. The medium mesh is sufficient for pressure-ratio regime classification and validation-level conclusions, while the fine mesh is preferable for stricter quantitative throat-Mach reporting.

The mesh study should not be read as a production-grade grid-convergence study. It is a compact portfolio-level assessment of sensitivity for this quasi-2D, slip-wall, inviscid-style validation setup.

Generated plots:

- `docs/images/mesh_independence_throat_mach.png`
- `docs/images/mesh_independence_mass_error.png`
- `docs/images/mesh_independence_max_mach.png`
