---
name: gromacs
description: Prepare, validate, run, resume, troubleshoot, and analyze GROMACS molecular dynamics. Use for biomolecular and molecular-condensed-phase classical MD; PDB/GRO/ITP/TOP/MDP/TPR workflows; force-field/topology integration; EM/NVT/NPT/production; checkpoint continuation; PBC repair; RMSD/RMSF/RDF/MSD/SASA/hydrogen-bond/density/membrane analysis; and VMD handoff.
---

# GROMACS

GROMACS owns the code-specific path for classical molecular dynamics: build a chemically and topologically consistent system, compile each stage with `gmx grompp`, run with `gmx mdrun`, validate every stage, and analyze only verified production segments. Tool-agnostic force-field and sampling science lives in `knowledge/force-fields.md` and `knowledge/molecular-dynamics.md`.

Command examples use the modern `gmx` wrapper. On MPI installations the executable may be `gmx_mpi`; the actual binary/module/launcher comes from the cluster guide. Always record `gmx --version`. Course-era syntax is not assumed: for example, old `do_dssp` workflows map to current `gmx dssp`, old `gmx hbond` map/lifetime examples may require `gmx hbond-legacy`, and removed `.mdp` keys must not be silently copied into modern inputs.

## Required inputs

- Scientific objective and target observable, not merely "run MD".
- Starting structure provenance; intended protonation, termini, disulfides, missing atoms/residues, ligands, ions and non-standard components.
- Force-field family/version, water model, ion parameters, small-molecule parameters and charge method with compatibility rationale.
- Ensemble, target temperature/pressure, timestep/constraints, simulation length, output cadence, non-bonded settings and boundary conditions.
- Execution target and rough cost; for multi-stage/HPC work start with `comp-chem-workflow` and use `hpc-submit` after preflight.

## Where to find what

| Situation | Go to |
|---|---|
| clean PDB/GRO input, choose protonation/termini/disulfides, box, solvate, add ions, mixtures or membranes | `references/system-preparation.md` |
| set up a protein / nucleic-acid / biomolecular system: `pdb2gmx`, protonation, termini, disulfides, cofactors, analysis groups | `references/biomolecules.md` |
| parameterize a small molecule / ligand and integrate it into the topology and force field | `references/ligands-small-molecules.md` |
| set up bulk liquids, solvent mixtures, or liquid/vapor and solid/liquid interfaces | `references/liquids-interfaces.md` |
| build and equilibrate a lipid bilayer / membrane (optionally with an embedded protein) | `references/membranes.md` |
| understand `.top`/`.itp`, `[defaults]`, atom types, 1-4 interactions, include order, water/ligand integration | `references/topology-and-force-fields.md`; science: `knowledge/force-fields.md` |
| choose `.mdp` parameters: integrator, timestep, outputs, PME/cutoffs, thermostat/barostat, constraints, restraints, pull/electric fields | `references/mdp-options.md`; science: `knowledge/molecular-dynamics.md` |
| run EM -> equilibration -> production, checkpoint continuation, rerun energies, GPU/MPI launch handoff | `references/running.md` |
| before `grompp`/submission: static consistency checks, stage gates, smoke test | `python scripts/check_gromacs_inputs.py ...`, then `references/validation.md` |
| run finished: technical parser and validation | `python scripts/parse_gromacs_log.py md.log`, then `references/validation.md` |
| LINCS/SETTLE/Fatal error, topology mismatch, missing parameters, NaN, exploding box, checkpoint append failure | `references/errors.md` |
| PBC repair, energy/structure/diffusion/interface/membrane/protein-ligand analysis | `references/analysis.md` |
| load GROMACS trajectories in VMD; Tcl `atomselect`, dynamic `within`, pbctools, unit trap | `references/vmd-handoff.md` |
| example contribution rules | `examples/README.md` |
| official manuals, forums, force-field and parameterization links | `references/resources.md` |

## Workflow

1. Inspect the structure before converting. Resolve alternate locations/models, missing atoms/residues, protonation, termini, special bonds, cofactors and intended assembly.
2. Choose one coherent parameter family. Record force field, water/ion model, ligand parameter source, charge method and every compatibility assumption.
3. Build the system. Generate topology, define the box, add solvent/ions/other components, and make coordinate order match `[ molecules ]` exactly.
4. Static preflight. Run the checker; then run `gmx grompp -pp processed.top -po mdout.mdp` and inspect warnings, processed topology and actual defaults. Never normalize `-maxwarn`.
5. Energy minimize. Validate finite energy, convergence criterion and absence of severe clashes.
6. Equilibrate in explicit stages. Stabilize temperature, then pressure/density/box as required, with restraints reduced according to a recorded schedule.
7. Production. Continue from checkpoint/state, do not regenerate velocities, and preserve raw outputs.
8. Validate technically and scientifically. A clean `mdrun` is not evidence of equilibration or adequate sampling.
9. Derive analysis-specific trajectories. Keep the raw trajectory immutable; make separate whole/centered/fitted/unwrapped copies for observables.
10. Report provenance: force field, water/ions, topology sources, GROMACS version, full `.mdp`, equilibration cut, production interval, selections, PBC treatment, fitting windows, units and uncertainty.

## Hard guardrails

- **No invented or casually mixed parameters.** Force-field bonded terms, charges, Lennard-Jones parameters, water models, ion sets and 1-4 rules are a coupled model.
- **Coordinate/topology identity is exact.** Atom count, atom order, molecule block order and `[ molecules ]` counts must match the coordinate file used by `grompp`.
- **Warnings are evidence, not paperwork.** Read every `grompp` warning; `-maxwarn` is an exceptional documented override, never a routine flag.
- **No observables from unverified equilibration.** Production analysis begins only after the relevant state variables and target structural metrics are stationary.
- **No structural metric on a broken trajectory.** PBC repair, unwrapping, centering and fitting are observable-specific preprocessing.
- **A LINCS/SETTLE warning is a failed stability gate.** Do not hide it by only increasing numerical-order settings; find the bad geometry, timestep, force, restraint or topology.
- **For new protocols, avoid Berendsen production coupling.** If an older source protocol requires it, preserve it for comparability and disclose that fluctuations are not those of the target ensemble.
- **Preserve the complete state.** Keep `.mdp`, `mdout.mdp`, processed topology, `.tpr`, `.log`, `.edr`, trajectory, final structure, `.cpt`, index files, commands, seeds and parameter-file identities.
