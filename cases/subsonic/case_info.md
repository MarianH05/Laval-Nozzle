# Subsonic Laval Nozzle Case

- Inlet total pressure, p0: 300000 Pa
- Inlet total temperature, T0: 300 K
- Outlet static pressure, pb: 290000 Pa
- Back-pressure ratio, pb/p0: 0.967
- Expected flow regime: fully subsonic flow through the nozzle.
- Expected Mach behavior: Mach number rises through the converging section, reaches a subsonic maximum at the throat, then falls again in the divergent section.

The outlet pressure was chosen above the ideal critical pressure ratio for air,
pb/p0 = (2/(gamma + 1))^(gamma/(gamma - 1)) = 0.528 for gamma = 1.4.
Keeping pb/p0 far above this value prevents choking and gives a robust
fully subsonic reference case. The back pressure was increased from the
earlier 0.900 ratio after the settled CFD solution approached choking.
