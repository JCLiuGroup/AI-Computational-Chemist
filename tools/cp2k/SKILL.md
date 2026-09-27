---
name: cp2k
description: Prepare, validate, run, and troubleshoot CP2K calculations for periodic and large molecular systems. Use for Quickstep GPW/GAPW DFT, ENERGY/GEO_OPT/CELL_OPT, k-points and supercells, basis/pseudopotential/grid convergence, SCF with OT or diagonalization, DFT+U, magnetism, hybrid/HFX/ADMM/RI-HFXk, band/DOS/Molden/Multiwfn analysis, cube fields, low-dimensional electrostatics, vibrational analysis/phonons, NEB/BAND reaction paths, AIMD/PIMD/metadynamics, implicit solvent, semiempirical DFTB/xTB, QM/MM, TDDFT/XAS, NMR/EPR/GW/CDFT, and CP2K-specific errors.
---

# CP2K

Task types: **single-point** (`RUN_TYPE ENERGY`), **optimization** (`GEO_OPT`, `CELL_OPT`), **electronic analysis** (DOS/PDOS, band structure, orbitals, charge/population/bonding post-processing), **reaction path** (`RUN_TYPE BAND`, CI-NEB, TS validation), **vibrations** (`VIBRATIONAL_ANALYSIS`, phonons through `phonopy`), **dynamics** (AIMD, thermostats/barostats, PIMD, metadynamics), **semiempirical screening** (DFTB/xTB), and **advanced properties** (hybrids, DFT+U, CDFT, TDDFT/XAS, NMR/EPR, GW, QM/MM).

## Required inputs

- Structure and periodicity: cell vectors, coordinate source, PBC directions, vacuum/slab/low-dimensional intent.
- Method: functional, dispersion, basis/potential file names, per-element `&KIND` basis and pseudopotential, charge/spin/magnetism.
- Numerical policy: `CUTOFF`, `REL_CUTOFF`, k-point/supercell policy, SCF strategy, smearing/added MOs if needed.
- Electrostatics: Poisson/periodicity model for molecules, slabs, 2D/1D systems, charged cells, SCCS, and work functions.
- For reproductions: source settings override local defaults; do not invent U values, basis choices, or convergence criteria.

## Where to find what

| Situation | Go to |
|---|---|
| setting up an input: skeleton, run types, Quickstep, grids, k-points, baseline templates | `references/running.md` |
| cutoff/rel_cutoff, k-point convergence, Gamma-supercell tradeoffs, MPI/OpenMP performance, smoke-test cost | `references/grids-kpoints-performance.md` |
| basis/potential choice, `&KIND` mapping, GTH/MOLOPT/UZH, ADMM/RI auxiliary bases | `references/basis-potential.md` |
| low-dimensional electrostatics: molecule boxes, slabs, 2D/1D, charged cells, dipoles, work functions | `references/low-dimensional-electrostatics.md`; science: `knowledge/periodic-electrostatics.md` |
| semiempirical screening/pre-equilibration: DFTB, SCC-DFTB, GFN-xTB | `references/semiempirical-dftb-xtb.md` |
| advanced electronic methods: hybrid/HFX/ADMM/RI-HFX, MP2/RPA/GW, CDFT, large-system acceleration | `references/advanced-electronic-methods.md` |
| SCF failure or setup choice: OT vs diagonalization, smearing, `ADDED_MOS`, mixing, restarts | `references/scf-convergence.md`; then `references/errors.md` |
| geometry/cell optimization, fixed atoms, slab constraints, stress tensor, stationary-point checks | `references/geometry-cell-optimization.md` |
| DFT+U and magnetic starting states | `references/dftu-magnetism.md`; science: `knowledge/hubbard-u-and-magnetism.md` |
| DOS/PDOS, bands, Molden/Multiwfn, cubes, density difference, charges, bond order, visualization | `references/electronic-analysis.md`; science: `knowledge/electronic-structure.md`, `knowledge/bonding-analysis.md`, and `knowledge/scientific-visualization.md` |
| reproducible cube/Molden/ELF/spin-density/headless PyVista/VESTA/VMD rendering | `references/volumetric-visualization.md`; science: `knowledge/scientific-visualization.md` |
| vibrational analysis, phonons, imaginary modes, IR/Raman prerequisites | `references/vibration-phonon.md`; science: `knowledge/vibrational-phonon-analysis.md`; for finite-displacement phonons use `tools/phonopy/SKILL.md` |
| NEB/BAND reaction paths and transition-state validation | `references/neb-dimer.md`; kinetics science: `knowledge/reaction-kinetics.md` |
| AIMD/PIMD/metadynamics statistics and trajectory analysis | `references/aimd.md`; science: `knowledge/molecular-dynamics.md` |
| adsorption, surface, defect, reaction, and thermal correction energy expressions | science: `knowledge/thermochemistry-and-free-energy.md` and `knowledge/surface-thermodynamics.md`; keep every compared energy on identical settings (`references/validation.md`) |
| SCCS and implicit solvent | `references/sccs-solvation.md`; electrostatics science: `knowledge/periodic-electrostatics.md` |
| TDDFT, UV-Vis, XAS, and excited-state spectra | `references/tddft-xas.md`; science: `knowledge/excited-state-and-core-spectroscopy.md` |
| NMR and magnetic-response properties | `references/nmr.md`; science: `knowledge/excited-state-and-core-spectroscopy.md` |
| QM/MM embedding, boundary atoms, mixed topology, and force-field coupling | `references/qmmm.md` |
| VASP-to-CP2K translation | `references/vasp-to-cp2k-map.md` |
| before submitting: parse-level input checks and smoke-test rules | `uv run scripts/check_inputs.py`, then `references/validation.md` |
| run finished: output summary, convergence checks, provenance | `uv run scripts/parse_cp2k.py`, then `references/validation.md` |
| SCF failure, warnings, memory, unsupported k-point task, opt/MD issues | `references/errors.md` |
| official manual, exercises, forum, Sobereva/Multiwfn tools | `references/resources.md` |
| example contribution rules | `examples/README.md` |

## Workflow

1. Decide the scientific question first; if it is code-agnostic, read the matching `knowledge/` doc before choosing CP2K settings.
2. Build the input from `running.md` or a verified example; keep all compared energies on the same functional, basis/potential, grid, k-policy, SCF, smearing, electrostatics, and correction settings.
3. Preflight: `uv run scripts/check_inputs.py input.inp`; for novel setups, run `cp2k -c input.inp` and a short smoke test.
4. Execute through `hpc-submit` for durable local/Slurm/PBS runs; before writing
   the job script, read the target `~/.cluster-agents.md`.
5. Validate: `uv run scripts/parse_cp2k.py output.out`; apply `validation.md`. On failure, use `errors.md`, change one thing, and rerun.

## Hard guardrails

- `PROGRAM ENDED AT` only proves CP2K terminated; convergence and scientific validity still need task-specific checks.
- `&KIND` basis/potential choices are part of the method. Do not silently mix basis/potential families across compared energies.
- `CUTOFF`/`REL_CUTOFF` converge the auxiliary grid, not the Gaussian basis-set limit.
- CP2K support for k-points, hybrids, DFT+U, print sections, and properties is version-dependent. Check the current manual for the exact CP2K version before asserting an old limitation.
- For cell optimization, slabs, 2D materials, charged systems, U values, spin states, smearing, hybrid truncation radii, and implicit-solvent parameters, ask the user or reproduce the source. These are scientific choices, not harmless defaults.
