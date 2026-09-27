---
name: gaussian
description: Prepare, validate, and troubleshoot Gaussian molecular quantum chemistry jobs. Use for single-point, geometry optimization, frequency/thermochemistry, transition states, IRC, scans, solvation, weak interactions, TD-DFT spectra, wavefunction stability, and Gaussian input/output handling for finite molecules.
---

# Gaussian

Job types: SP, Opt, Freq, Opt+Freq, TS search, IRC, scans, solvent models, counterpoise, wavefunction stability, and TD-DFT spectra — route templates and operational details are in the references below.

## Required inputs

- 3D coordinates (from `structure-prep` if starting from SMILES)
- **Charge and multiplicity, never guessed silently** — derived with stated origin, or asked
- Method + basis (reproductions: the source paper's level wins); job type; solvent/dispersion if required

## Where to find what

| Situation | Go to |
|---|---|
| tool-agnostic molecular QC decisions: method/basis, SCF state, Opt/Freq/TS/IRC, solvent/BSSE, TD-DFT | `knowledge/molecular-qc-practical-rules.md` |
| writing an input: header, route per job type, level-of-theory policy | `references/running.md` |
| reading energies, thermal corrections, SP//opt values, barriers, conformer weights, standard-state corrections | `references/energy-thermochemistry.md` |
| Gaussian property keywords and utilities: `formchk`, `cubegen`, `cubman`, NMR, Polar, Pop, ESP/density cubes | `references/properties-utilities.md` |
| Gaussian basis syntax, diffuse/ECP/Gen/GenECP, mixed basis | `references/basis-ecp-genecp.md` |
| SCF convergence failure, hard open-shell systems, broken-symmetry singlets, stability checks | `references/scf-stability.md`, then `references/errors.md` |
| geometry optimization, frequency checks, TS, IRC, relaxed scans, restart choices | `references/opt-ts-irc.md` |
| solvation, SMD/PCM, custom solvent parameters, counterpoise/BSSE | `references/solvation-bsse.md` |
| TD-DFT, UV-Vis, ECD, fluorescence, oscillator strengths, NTO handoff | `references/td-dft.md`; deeper analysis: `tools/multiwfn/SKILL.md` |
| GaussView model setup, fragments, `.chk`/`.fchk`, quick visualization | `references/gaussview.md` |
| Multiwfn wavefunction analysis: charges, spin density, MOs/NTOs, ESP/ELF/NCI/IRI, spectra | `tools/multiwfn/SKILL.md`; interpretation: `knowledge/electronic-structure.md`, `knowledge/scientific-visualization.md` |
| job error-terminated (link number) or generic opt won't converge | `references/errors.md`; for exact log parsing use `uv run scripts/parse_gaussian.py` |
| run finished — termination, imaginary modes, S², energy discipline | `uv run scripts/parse_gaussian.py`, then `references/validation.md` |
| example contribution rules | `examples/README.md` |
| not covered locally (keyword docs, basis sets, community error guides) | `references/resources.md` |

## Workflow

1. Decide the scientific quantity before choosing Gaussian keywords; consult `knowledge/molecular-qc-practical-rules.md` when the issue is code-agnostic.
2. Build the route from `running.md` plus the relevant topic reference. State charge/multiplicity origin.
3. Submit via `hpc-submit` (single-node unless a site-specific Linda setup is explicitly approved).
4. Validate: `uv run scripts/parse_gaussian.py JOB.log`; rules in `validation.md`. On error → exact link/message in `errors.md`, then the topic reference.
5. Extract energies and properties only after validation, using `energy-thermochemistry.md` or `properties-utilities.md`.
6. For post-processing beyond Gaussian's own output, hand off validated `.log`/`.fchk`/cube files to `tools/multiwfn/`.

## Hard guardrails

- Opt before Freq, always at the same level — thermochemistry across mismatched levels is invalid.
- Minimum: 0 imaginary modes. TS: exactly 1, and its motion must match the intended reaction coordinate; validate important TSs with IRC.
- State the quoted energy type (E, E+ZPE, H, G) and units on every value.
- Do not carry unconverged SCF/Opt results into frequencies, post-SCF energies, or mechanistic conclusions.
- Preserve `.log` and `.chk`/`.fchk`.
