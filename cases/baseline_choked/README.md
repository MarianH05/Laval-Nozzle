# Baseline Choked Case

This directory contains the validated baseline OpenFOAM case moved from the repository root.

Physics and solver settings were preserved during the repository reorganization.

Known validation results:

```text
mass conservation error: 0.4482%
maximum Courant number: 0.353893
throat-region Mach number: 1.03557
verdict: VALID
```

Run from the repository root:

```bash
./Allrun cases/baseline_choked
./Allvalidate cases/baseline_choked
```
