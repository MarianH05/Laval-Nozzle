# Time-History Assessment

Generated from existing solver logs and written time folders only. Log histories provide `time`, `deltaT`, Courant number, and execution time. Mass-flow and throat-Mach histories are recomputed from written time directories using existing `rho`, `U`, and `T` fields.

| case | log_samples | field_time_samples | throat_mach_samples | final_log_time | final_deltaT | max_Courant | final_max_Courant | execution_time_s | final_mass_error_percent | final_throat_mach | steady_signal | steady_variation_percent | steady_verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| subsonic | 106396 | 11 | 11 | 0.00599995 | 5.192950e-08 | 0.612799 | 0.449957 | 6622.1 | 0.690756 | 0.480624 | outlet mass flow from written fields | 4.04627 | nearly steady |
| choked | 58939 | 3 | 3 | 0.00199997 | 3.289320e-08 | 0.355479 | 0.349096 | 3608.93 | 0.277965 | 1.04479 | outlet mass flow from written fields | 0.402783 | quasi-steady |
| internal_shock | 104026 | 5 | 5 | 0.00199998 | 1.882590e-08 | 0.201246 | 0.199918 | 6289.63 | 0.256732 | 1.04399 | outlet mass flow from written fields | 0.76632 | quasi-steady |

## Limitations

- Field-based mass-flow and throat-Mach histories have only as many samples as saved time directories, not every solver step.
- Restarted or alternate solver logs are merged by time where possible; execution time is reported from parsed logs and can include restart segments when present.
- No convergence claim is made from unsaved intermediate fields.
