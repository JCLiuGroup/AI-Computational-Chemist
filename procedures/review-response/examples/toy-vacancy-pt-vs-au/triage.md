# Triage

- **manuscript:** Enhanced thermal stability of Pt vs Au nanoparticle catalysts (FAKE fixture)
- **fingerprint:** `method-fingerprint.md`

## R2.C1 — compute-new

> "A simple first-principles estimate of the monovacancy formation energy in bulk Pt
> versus Au would substantiate (or undermine) this interpretation." (p.4)

- **target:** monovacancy formation energy E_v in fcc Pt and fcc Au, identical settings
- **satisfaction criterion:** both E_v positive and physically sane (~1 eV), and
  **E_v(Pt) > E_v(Au)** → supports the claim. Reported either way — a smaller or equal
  Pt value would **contradict** the claim and halt for the authors.
- **route:** structure build (ASE) → `comp-chem-workflow`
- **method delta:** none (uses the fingerprint as-is)
- **cost:** seconds, local, no scheduler

## R2.C2 — text-only

> "temper the language in the abstract; 'superior' is used three times." (p.5)

Editorial; hand to authors, out of computational scope.

## R2.C3 — needs-human-decision

> "comment on whether support effects influence the observed coarsening." (p.5)

A support-effect study is a much larger model (metal/oxide interface) and may exceed
what this rebuttal warrants. Present as an option with cost; do not plan unilaterally.
