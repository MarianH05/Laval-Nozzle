# Choked Laval Nozzle Case

- Inlet total pressure, p0: 300000 Pa
- Inlet total temperature, T0: 300 K
- Outlet static pressure, pb: 158500 Pa
- Back-pressure ratio, pb/p0: 0.528
- Expected flow regime: choked flow with supersonic acceleration in the divergent section for the current back pressure.
- Expected Mach behavior: Mach number increases to approximately 1 at the throat and accelerates above Mach 1 downstream. The regenerated CFD result shows a strong downstream adjustment, so this case should be interpreted as a choked/supersonic operating point rather than a purely incipient choking limit.

The outlet pressure was chosen from the ideal critical pressure ratio for air,
pb/p0 = (2/(gamma + 1))^(gamma/(gamma - 1)) = 0.528 for gamma = 1.4.
This is the nominal pressure ratio where a one-dimensional converging throat
reaches Mach 1. In a converging-diverging nozzle with finite exit area, this
back pressure can still drive supersonic acceleration downstream of the throat.
