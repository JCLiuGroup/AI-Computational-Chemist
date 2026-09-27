# Response workflow (master state)

- **manuscript:** Enhanced thermal stability of Pt vs Au nanoparticle catalysts (FAKE fixture)
- **fingerprint:** `method-fingerprint.md`
- **objective:** answer R2.C1 — does Pt resist vacancy formation more than Au?

## Reusable assets

_(none reused here — both runs are cheap; in a real campaign shared slabs/gas refs would be listed here with the fingerprint they were built under)_

## R2.C1 — status: validated — outcome: addresses

| stage | status | evidence |
|---|---|---|
| pt-vacancy | validated | `scripts/vacancy.py`; N=108; E_perfect=−0.0135 eV; E_vac=1.0013 eV; **E_v=1.015 eV**; BFGS fmax<0.02 |
| au-vacancy | validated | `scripts/vacancy.py`; N=108; E_perfect=0.2815 eV; E_vac=1.0908 eV; **E_v=0.812 eV**; BFGS fmax<0.02 |

**Result:** E_v(Pt) = 1.015 eV, E_v(Au) = 0.812 eV, difference = 0.203 eV → **E_v(Pt) > E_v(Au)**.

**Validation:** both positive and ~1 eV (sane for EMT); Pt exceeds Au by ~0.2 eV.
Criterion met — result **supports** the claim (does not contradict). Trend agrees with
the experimental ordering (Pt ≈ 1.35 eV, Au ≈ 0.9 eV); absolute EMT values are toy-level,
used only for the ordering.

## Outcome

All approved comments validated; package drafted → `response-package.md`.
