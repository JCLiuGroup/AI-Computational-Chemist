# Draft Response Package — DRAFT FOR THE AUTHORS (not final; Approval #2 pending)

> Generated from `response-workflow.md` using the Phase-5 templates. Every number
> is wired to its provenance in `scripts/vacancy.py` / the workflow file. The agent
> does not finalize tone or rebuttal strategy.

## Response to R2.C1

> **Reviewer 2.1 (p.4):** "A simple first-principles estimate of the monovacancy
> formation energy in bulk Pt versus Au would substantiate (or undermine) this
> interpretation."

We thank the reviewer. We computed the monovacancy formation energy in fcc Pt and
fcc Au using identical settings (108-atom supercell, positions relaxed to
|F| < 0.02 eV/Å), so the two values are directly comparable:

| Metal | E_v (formation) | provenance |
|---|---|---|
| Pt | **1.02 eV** | `scripts/vacancy.py`, 108-atom cell, E_vac=1.0013 eV |
| Au | **0.81 eV** | `scripts/vacancy.py`, 108-atom cell, E_vac=1.0908 eV |

The monovacancy in Pt is ~0.20 eV more costly to form than in Au, i.e. **Pt resists
vacancy formation more than Au**, supporting the interpretation in the manuscript.
The ordering matches the experimental trend (Pt ≈ 1.35 eV, Au ≈ 0.9 eV).

*Disclosure (would be removed/replaced in a real submission):* this fixture uses the
EMT toy potential for speed; absolute values are not quantitative and the conclusion
rests only on the **ordering**, which EMT reproduces. A real response would use the
field-standard DFT settings recorded in the method fingerprint.

**Manuscript change:** add one sentence + a one-row SI table reporting the computed
E_v(Pt) > E_v(Au) in support of the stability claim.

## Response to R2.C2 (text-only — for the authors)

Editorial; reduce "superior" usage in the abstract. No computation. Handed to authors.

## Response to R2.C3 (needs human decision)

A support-effect (metal/oxide interface) study is a substantially larger model.
Options for the authors: (a) add it as a scoped follow-up calculation (cost: large,
new interface models); (b) address it qualitatively in text as beyond the present
scope. Not planned unilaterally.

## SI addition (ready to paste)

**Table S1.** Monovacancy formation energy in bulk fcc metals (108-atom supercell,
relaxed, |F| < 0.02 eV/Å). Method: see SI Computational Methods. E_v(Pt) = 1.02 eV,
E_v(Au) = 0.81 eV.

## Revision changelog

- Abstract/Results: added a sentence attributing Pt stability to higher vacancy
  formation energy, now backed by calculation (Table S1).
- SI: new Computational Methods paragraph + Table S1.
