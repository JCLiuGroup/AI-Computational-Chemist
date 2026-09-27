---
name: lammps
description: Prepare, run, and validate LAMMPS molecular dynamics. Use for classical MD (EAM, Lennard-Jones, Tersoff), reactive MD (ReaxFF), machine-learning potentials in LAMMPS (DeePMD, MACE), minimization, NVE/NVT/NPT, equilibration, and trajectory production.
---

# LAMMPS

Workflow shape for every MD task: validate setup → minimize → equilibrate (verified) → production → stability checks. Observables come only from verified production segments.

## Required inputs

- Structure as a data file (atom-type → element mapping is provenance)
- Force field: pair_style + parameter files that exist on disk — never invented or substituted; record file, source, fitted scope
- Units + atom_style consistent with the pair style (the #1 silent error)
- Ensemble, T/P, timestep, run length, output intervals

## Where to find what

| Situation | Go to |
|---|---|
| writing an input: units/atom_style table, templates (EAM, ReaxFF, DeePMD, MACE), timestep/damping guidance | `references/running.md` |
| scheduler/job script, partition/account, module/binary/launcher | `tools/hpc-submit/SKILL.md`; read the target `~/.cluster-agents.md` before writing the script |
| crashed, ERROR lines, lost atoms, unstable dynamics | `references/errors.md` |
| run finished — equilibration evidence, drift bars, what may be computed | `uv run scripts/parse_lammps.py`, then `references/validation.md` |
| validate the driving MLP or diagnose extrapolation | DeePMD/DPMD: `tools/deepmd/SKILL.md`; other architectures: `tools/mlp/SKILL.md` or their dedicated skill |
| example contribution rules | `examples/README.md` |
| not covered locally (manual, forums, potential repositories) | `references/resources.md` |

## Hard guardrails

- No production observables from a trajectory whose equilibration was not verified.
- Zero lost atoms — any loss invalidates the trajectory.
- An MLP driving MD must be validated for the declared composition and state range.
  Route DeePMD model deviation and QA to `deepmd`; use the matching dedicated or
  umbrella MLP skill for other architectures.
- Do not mix unit systems between data file, parameters, and script.
