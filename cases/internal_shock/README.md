# Internal-Shock Case

OpenFOAM case for a choked Laval nozzle flow with an expected normal shock inside the divergent section.

This case uses the baseline geometry, ideal-gas air model, `rhoCentralFoam`, and `blockMesh` mesh topology. The outlet static pressure is set to `140000 Pa`, giving `pb/p0 = 0.467`, which is below the choking threshold but above the ideal shock-free supersonic exit pressure ratio for this area ratio. This pressure ratio was selected to retain an internal-shock solution while avoiding the nonphysical startup transient seen with a lower back pressure.

Run from the repository root:

```bash
./Allrun cases/internal_shock
./Allvalidate cases/internal_shock
```

See `case_info.md` for the pressure-ratio rationale and expected Mach behavior.
