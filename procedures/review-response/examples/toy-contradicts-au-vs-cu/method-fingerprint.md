# Method fingerprint

- **origin:** designed — experimental manuscript, nothing to extract (mode B)
- **reproduction_mode:** exploration
- **note:** toy ASE-EMT fixture (same rationale as the sibling example). In a real
  response this would hold the field-convention DFT settings.

## Settings (the binding contract — all calcs use these comparable knobs)

- **code:** ASE EMT (effective-medium theory, built-in)
- **method:** EMT total energies; positions relaxed at fixed cell
- **model:** fcc bulk, 3×3×3 conventional supercell (108 atoms)
- **defect:** single monovacancy (remove one atom)
- **relaxation:** BFGS, fmax = 0.02 eV/Å, fixed cell
- **reference state:** per-atom energy of the perfect supercell

## Experiment–model correspondence

- the claim concerns bulk point-defect energetics → a bulk monovacancy is the minimal decisive model
- Au and Cu compared at identical settings, so the **difference** is the result

## Limitations (stated in any response text)

- EMT is a qualitative toy potential; absolute values are not quantitative. The result
  is used only for the **ordering** E_v(Au) vs E_v(Cu), which is what the claim needs.
- no temperature, no surface / nanoparticle-size effects (bulk model)
- here the ordering happens to also match the experimental vacancy-energy ordering
  (Cu ≈ 1.28 eV > Au ≈ 0.9 eV), so the contradiction below is robust, not a toy artifact.
