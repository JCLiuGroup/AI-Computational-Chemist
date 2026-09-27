# Response workflow (master state)

- **manuscript:** Noble-metal advantage: superior sinter-resistance of Au vs Cu (FAKE fixture)
- **fingerprint:** `method-fingerprint.md`
- **objective:** answer R1.C1 — does Au resist vacancy formation more than Cu?

## Reusable assets

_(none reused here — both runs are cheap; in a real campaign shared slabs/gas refs would be listed here with the fingerprint they were built under)_

## R1.C1 — status: validated — outcome: **contradicts**

| stage | status | evidence |
|---|---|---|
| au-vacancy | validated | `scripts/vacancy.py`; N=108; E_perfect=0.2815 eV; E_vac=1.0908 eV; **E_v=0.812 eV**; BFGS fmax<0.02 |
| cu-vacancy | validated | `scripts/vacancy.py`; N=108; E_perfect=−0.6136 eV; E_vac=0.6357 eV; **E_v=1.244 eV**; BFGS fmax<0.02 |

**Result:** E_v(Au) = 0.812 eV, E_v(Cu) = 1.244 eV, difference = −0.432 eV → **E_v(Au) < E_v(Cu)**.

**Validation:** both positive and ~1 eV (sane for EMT); the calculation is technically
sound (converged, relaxed, comparable settings). The science, however, runs **opposite**
to the manuscript's central claim: the Au monovacancy is *cheaper* to form than the Cu
one, so Au does **not** resist vacancy formation more than Cu — it resists it *less*. The
EMT ordering also agrees with the experimental vacancy-energy ordering (Cu > Au), so this
is a robust contradiction, not a toy-potential artifact.

## Outcome — HALT (integrity branch)

Phase 4 returned **`contradicts`** for the only compute-new comment. Per the
review-response contract, the workflow **stops here and surfaces to the authors before any
response text is drafted**. No `response-package.md` is produced. The contradicting result,
its evidence, and the options are written to `escalation.md` for the authors' decision.
Drafting resumes only after the authors decide how to proceed (revise the claim, extend the
calculations, or re-examine the setup).
