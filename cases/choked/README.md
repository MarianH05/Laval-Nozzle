# Choked Case

OpenFOAM case for the nominal choked Laval nozzle operating condition.

This case uses the same geometry and solver setup as the baseline, with outlet static pressure set to `158500 Pa`, giving `pb/p0 = 0.528`. This is near the ideal critical pressure ratio for air, so the throat is expected to reach approximately Mach 1.

Run from the repository root:

```bash
./Allrun cases/choked
./Allvalidate cases/choked
```

See `case_info.md` for the pressure-ratio rationale and expected Mach behavior.
