# Escalation to the authors — CONTRADICTING RESULT (Phase 4 halt)

> This file **replaces** `response-package.md` for this run. The Phase-4 validation of
> R1.C1 returned `contradicts`, so the workflow stopped before drafting any rebuttal text.
> This is the integrity-critical branch: the calculation undermines a manuscript claim,
> and that is surfaced plainly to the authors — never buried, softened, or spun into a
> response. Nothing is drafted, finalized, or sent. The authors decide what happens next.

## What the reviewer asked (R1.C1)

> "A straightforward first-principles estimate of the monovacancy formation energy in bulk
> Au versus Cu would either substantiate this central argument or expose it as a non
> sequitur." (p.3)

## What we computed

Monovacancy formation energy in fcc Au and fcc Cu at identical settings (108-atom
supercell, positions relaxed to |F| < 0.02 eV/Å), so the two values are directly
comparable:

| Metal | E_v (formation) | provenance |
|---|---|---|
| Au | **0.81 eV** | `scripts/vacancy.py`, 108-atom cell, E_vac=1.0908 eV |
| Cu | **1.24 eV** | `scripts/vacancy.py`, 108-atom cell, E_vac=0.6357 eV |

## The problem

The manuscript's central claim is:

> "Owing to its noble character, Au resists monovacancy formation more strongly than Cu …"

The calculation says the **opposite**: the Au monovacancy costs ~0.43 eV *less* to form
than the Cu one, so **Au resists vacancy formation less than Cu, not more**. The
experimental vacancy-energy ordering (Cu ≈ 1.28 eV > Au ≈ 0.9 eV) agrees, so the result is
robust rather than a toy-potential artifact. The underlying issue is conceptual — the
manuscript equates *chemical* nobility (filled-d inertness) with *thermodynamic* defect
resistance, and these do not track together. This is the same slip R1.C2 flags about the
word "noble."

## Options for the authors (no option chosen here)

1. **Revise the claim.** Drop the "Au resists vacancy formation more than Cu" argument; the
   vacancy energetics do not support it (and contradict it). Any stability difference must be
   attributed to something else (e.g. surface/diffusion kinetics, size, support).
2. **Re-examine the setup before concluding.** If the authors believe a more faithful model
   would reverse this, specify it (DFT at the field-standard fingerprint, surface vs bulk
   vacancies, finite-size cell, nanoparticle facets) and we re-run. The current result is
   technically sound at its level, so a reversal would need a stated physical reason.
3. **Reframe around what the data do show.** Both metals coarsen in the TEM; the honest
   finding may be that nobility does *not* explain the difference, which can be a legitimate
   (and stronger) message than the original claim.

## Status

- R1.C1: **halted at Phase 4** (`contradicts`) — awaiting author decision; no response text drafted.
- R1.C2 (text-only): held — it concerns the same "noble ⇒ robust" conflation and should be
  resolved together with the authors' decision on R1.C1.

Drafting (Phase 5) resumes only after the authors choose a direction.
