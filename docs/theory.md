# Compressible Laval Nozzle Theory

This project uses ideal-gas air with `gamma = 1.4` and `R = 287 J/(kg K)`.

For isentropic compressible flow:

```text
T/T0 = 1 / (1 + (gamma - 1)/2 * M^2)
p/p0 = (T/T0)^(gamma/(gamma - 1))
rho/rho0 = (T/T0)^(1/(gamma - 1))
```

The area-Mach relation is:

```text
A/A* = (1/M) * [(2/(gamma + 1)) * (1 + (gamma - 1)/2 * M^2)]^((gamma + 1)/(2*(gamma - 1)))
```

For a converging-diverging nozzle:

- subsonic flow accelerates in the converging section
- choking occurs when Mach number reaches 1 at the throat
- supersonic flow accelerates in the diverging section
- a sufficiently high back pressure can force an internal normal shock

The current validated baseline is a choked/supersonic case.
