# Subsonic Case

OpenFOAM case for the fully subsonic Laval nozzle operating condition.

This case uses the baseline geometry, ideal-gas air model, `rhoCentralFoam`, and `blockMesh` mesh topology. The outlet static pressure is set to `290000 Pa`, giving `pb/p0 = 0.967`, which is well above the ideal critical pressure ratio for air and keeps the validated solution subsonic throughout the nozzle.

Run from the repository root:

```bash
./Allrun cases/subsonic
./Allvalidate cases/subsonic
```

See `case_info.md` for the pressure-ratio rationale and expected Mach behavior.
