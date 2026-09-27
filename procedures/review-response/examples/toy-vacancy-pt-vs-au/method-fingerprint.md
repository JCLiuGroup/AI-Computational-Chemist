# Method fingerprint

- **origin:** designed — experimental manuscript, nothing to extract (mode B)
- **reproduction_mode:** exploration
- **note:** integration-test fixture. The method is a **toy** (ASE-EMT) chosen so the
  whole pipeline runs anywhere in seconds with no DFT engine or cluster. In a real
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
- Pt and Au compared at identical settings, so the **difference** is the result

## Limitations (stated in the response text)

- EMT is a qualitative toy potential; absolute values are not quantitative. The result
  is used only for the **ordering** E_v(Pt) vs E_v(Au), which is what the claim needs.
- no temperature, no surface / nanoparticle-size effects (bulk model)
