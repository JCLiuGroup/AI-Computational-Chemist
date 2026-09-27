# Triage

- **manuscript:** Noble-metal advantage: superior sinter-resistance of Au vs Cu (FAKE fixture)
- **fingerprint:** `method-fingerprint.md`

## R1.C1 — compute-new

> "A straightforward first-principles estimate of the monovacancy formation energy
> in bulk Au versus Cu would either substantiate this central argument or expose it
> as a non sequitur." (p.3)

- **target:** monovacancy formation energy E_v in fcc Au and fcc Cu, identical settings
- **satisfaction criterion:** both E_v positive and physically sane (~1 eV). The claim
  is supported only if **E_v(Au) > E_v(Cu)**. Reported either way — **E_v(Au) ≤ E_v(Cu)
  would contradict the manuscript's central argument and halt for the authors** (Phase 4).
- **route:** structure build (ASE) → `comp-chem-workflow`
- **method delta:** none (uses the fingerprint as-is)
- **cost:** seconds, local, no scheduler

## R1.C2 — text-only

> "'noble' is used as if it implied mechanical or thermodynamic robustness; define the
> term where first used." (p.6)

Editorial/definitional; hand to authors, out of computational scope. (Note: R1.C2 and the
R1.C1 result point at the same conceptual slip — conflating chemical nobility with defect
resistance — so the authors will likely want to address them together.)
