---
name: vaspkit
description: Use VASPKIT to generate VASP helper inputs and post-process VASP outputs, including KPOINTS, band paths, DOS/band data, charge-density differences, planar averages, Bader charge coloring helpers, real-space wavefunctions, partial/orbital charge density, work functions, elastic/EOS summaries, thermochemistry/free-energy corrections, AIMD trajectory post-processing (MSD, diffusion, VACF, VDOS, RDF/trajectory conversion), and batch analysis.
---

# VASPKIT

Use this skill when VASP data already exist or VASP helper inputs must be generated with VASPKIT. VASPKIT is an assistant around VASP; it does not replace the `vasp` skill's method selection, convergence checks, or provenance rules.

## Required inputs

- Target task: input generation, electronic post-processing, charge/potential analysis, mechanical properties, thermochemistry/free-energy corrections, MD summary, or file conversion.
- Working directory containing the required VASP files for that task.
- VASPKIT version and `~/.vaspkit` configuration status.
- For any POTCAR-related task: licensed POTCAR path and element-potential mapping. Never commit or print POTCAR contents.
- For figures: final plotting target, axis convention, energy reference, and whether the output is exploratory or publication-ready.

## Where to find what

| Situation | Go to |
|---|---|
| configure VASPKIT, run interactively or non-interactively, choose task families | `references/running.md` |
| preflight a directory before running VASPKIT; validate generated files and parsed outputs | `uv run scripts/check_vaspkit.py`, then `references/validation.md` |
| automate one VASPKIT task across many directories | `uv run scripts/run_vaspkit_task.py`, then `references/running.md` |
| DOS/band postprocessing: TDOS/PDOS, projected bands, d-band center, Fermi-level shift, adsorbate/surface orbital extraction | `references/dos-band.md`; pair with `tools/vasp/references/dos-band.md` |
| electronic-analysis postprocessing: charge-density difference, planar average, work function, Bader coloring, real-space wavefunction, partial/orbital charge | `references/electronic-analysis.md`; pair with `tools/vasp/references/electronic-analysis.md` |
| thermochemistry/free energy: fix atoms for frequencies, VASPKIT 501/502, gas chemical potentials for high-temperature work, surface thermodynamics, reaction profiles, and single-atom/defect stability diagrams | `references/thermochemistry.md`; for the science pair with `knowledge/thermochemistry-and-free-energy.md` and `knowledge/surface-thermodynamics.md` |
| AIMD post-processing: MSD/diffusion, VACF, VDOS, RDF/trajectory conversion, frame cuts and fit windows | `references/aimd-postprocessing.md`; pair with `tools/vasp/references/aimd.md` |
| task fails, menu input hangs, output files are empty, plots look shifted | `references/errors.md` |
| official docs, feature list, citation, VASP links | `references/resources.md` |
| example contribution rules | `examples/README.md` |

## Workflow

1. Use the `vasp` skill to confirm the upstream VASP run is technically valid.
2. Read `running.md` for the relevant VASPKIT task family and required input files.
3. Run `uv run scripts/check_vaspkit.py RUNDIR`; fix missing config, executable, or VASP files first.
4. Run VASPKIT interactively for a new task; record every menu choice. Use `run_vaspkit_task.py` only after the input sequence is known.
5. Validate generated outputs with `validation.md`; record source files, task IDs, energy reference, and version.

## Hard guardrails

- VASPKIT output is post-processing evidence, not proof that the upstream VASP run converged.
- Do not use raw band/DOS axes without recording the energy zero: Fermi level, vacuum level, VBM, or user-provided reference.
- For VASP-based free-energy corrections, prefer this VASPKIT skill as the practical post-processing route after the thermodynamic expression is written in the knowledge references. VASPKIT does not choose the model; it supplies frequency/gas-thermochemistry helper values with provenance.
- Do not trust generated POTCAR files unless species order, functional, and potential mapping are independently checked.
- Do not commit manuals, POTCAR files, WAVECAR/CHGCAR-scale binaries, or bulky generated plot data.
