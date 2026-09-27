---
name: phonopy
description: Finite-displacement phonon workflows with phonopy. Use for displacement generation, force collection from VASP or MLP backends, force constants, phonon band structure and DOS, thermal properties, and imaginary-mode diagnosis.
---

# Phonopy

Pipeline: tightly relaxed structure → displacements → one static force run each (identical settings) → FORCE_SETS → band/DOS/thermal analysis.

## Where to find what

| Situation | Go to |
|---|---|
| commands and settings for every pipeline step; per-displacement INCAR; BORN/NAC for polar materials | `references/running.md` |
| imaginary modes — noise or real instability? what convergence to report | `references/validation.md` |
| force-constant build fails, acoustic branches don't hit zero, spectrum looks wrong | `references/errors.md` |
| example contribution rules | `examples/README.md` |
| not covered locally (phonopy docs, examples, phono3py, seekpath) | `references/resources.md` |

## Hard guardrails

- The input structure must be relaxed to forces < 1 meV/Å — residual forces become phantom imaginary modes.
- All displacement runs use identical settings; the displacement→force-file mapping is provenance, never reordered by hand.
- Never hide imaginary modes to make thermal properties computable — they are undefined for an unstable spectrum.
- Supercell-size convergence is part of the result, not optional.
