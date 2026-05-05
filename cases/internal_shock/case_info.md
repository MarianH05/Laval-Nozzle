# Internal-Shock Laval Nozzle Case

- Inlet total pressure, p0: 300000 Pa
- Inlet total temperature, T0: 300 K
- Outlet static pressure, pb: 140000 Pa
- Back-pressure ratio, pb/p0: 0.467
- Expected flow regime: choked flow with an internal normal shock in the divergent section.
- Expected Mach behavior: Mach number reaches 1 at the throat, accelerates to supersonic values downstream of the throat, drops abruptly across a normal shock, then continues subsonically to the outlet.

The throat-to-exit area ratio of the template geometry is about 0.4, giving
A_exit/A_throat about 2.5. For gamma = 1.4, the ideal shock-free supersonic
exit pressure ratio for this area ratio is about 0.064, while the critical
choking ratio is 0.528. Choosing pb/p0 = 0.467 places the case between those
limits, where a converging-diverging nozzle is expected to choke and contain a
normal shock in the divergent section. The back pressure is kept lower than the
critical choking ratio but higher than the earlier 0.350 setting to reduce the
strength of the startup transient and avoid nonphysical temperature excursions.
