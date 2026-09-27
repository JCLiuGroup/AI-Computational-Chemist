# Validating ML Potentials

> Load this when: deciding whether a non-DeePMD MLP is fit for its declared use. For
> DeePMD metrics, committee policy, and model-deviation thresholds, use
> `tools/deepmd/references/validation.md`.

## Evidence gates

1. **Held-out error:** report energy, force, and stress metrics relevant to the target
   use, plus parity/residual plots separated by system or composition. Thresholds are
   project- and chemistry-dependent; do not promote generic example values into a
   universal production bar.
2. **Physics checks:** compare relevant equation-of-state, structural, defect,
   adsorption, barrier, vibrational, or other observables against the labeling method.
3. **Dynamics checks:** test stability, conservation, and target state points using
   `tools/lammps/references/validation.md` or the deployment engine's validator.
4. **Distribution coverage:** demonstrate coverage of the intended compositions,
   temperatures, pressures, phases, defects, and reaction environments. Use a
   committee or architecture-specific uncertainty method when warranted.

Frames outside the demonstrated trust region are candidates for labeling, not
production evidence.

## Reporting

Record dataset size and coverage, split protocol, labeling fingerprint, model/checkpoint
identity, all validation metrics, physics tests, and the exact claimed domain. Never
quote training-set error as model quality or extrapolate a validation claim beyond the
tested domain.
