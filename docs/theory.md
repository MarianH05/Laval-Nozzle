# Compressible Laval Nozzle Theory

This project uses ideal-gas air with `gamma = 1.4` and `R = 287 J/(kg K)`. The numerical cases are quasi-2D OpenFOAM cases with `empty` front/back patches and slip walls. The slip-wall choice is intentional for inviscid and isentropic validation comparisons; it does not model viscous wall losses or boundary-layer development.

## Isentropic Relations

For isentropic compressible flow:

```text
T/T0 = 1 / (1 + (gamma - 1)/2 * M^2)
p/p0 = (T/T0)^(gamma/(gamma - 1))
rho/rho0 = (T/T0)^(1/(gamma - 1))
```

The quasi-1D area-Mach relation is:

```text
A/A* = (1/M) * [(2/(gamma + 1)) * (1 + (gamma - 1)/2 * M^2)]^((gamma + 1)/(2*(gamma - 1)))
```

For `A/A* > 1`, the relation has subsonic and supersonic branches.

## Regimes

- `subsonic`: fully subsonic flow is expected throughout the nozzle.
- `choked`: sonic throat conditions are expected; the existing computed case also shows internal-shock-like downstream behavior and is documented that way.
- `internal_shock`: sonic throat conditions, supersonic divergent-section flow, and shock behavior are expected.

Area-Mach theory is not valid through shocks because entropy is produced and the downstream effective `A*` changes. Shock-containing cases must therefore be interpreted with masking or separate downstream fitting, not as single-branch isentropic solutions.
