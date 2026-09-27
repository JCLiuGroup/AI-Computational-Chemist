# LAMMPS Error Recovery

> Load this when: a LAMMPS run crashed, printed ERROR/WARNING lines, or the dynamics look unphysical.

Fix one thing at a time; most "LAMMPS errors" are setup errors surfacing mid-run.

| Message / symptom | Likely cause | Fix |
|---|---|---|
| `Lost atoms: original N current M` | atoms moving faster than neighbor rebuilds tolerate — exploding dynamics, overlapping initial config, or wrong units/timestep | minimize first; smaller timestep; check initial overlaps; `neigh_modify delay 0 every 1 check yes` while debugging |
| `Unknown pair style` | binary built without the package (REAXFF, ML-IAP, GPU...) | rebuild/load a LAMMPS with the package (`-DPKG_REAXFF=on`), or module with it included |
| `Out of range atoms - cannot compute PPPM` | system exploding, or long-range grid can't track atoms | usually a symptom of instability — fix dynamics (timestep, overlaps) rather than the kspace settings |
| `Bond atoms missing` / `Bond/angle extent > half periodic box` | bonded partners flew apart, or molecule wrapped wrongly across PBC | bad dynamics or bad initial topology; check data-file image flags; smaller timestep |
| `Non-numeric pressure/energy - simulation unstable` (NaN) | overlapping atoms, zero-mass types, wrong pair coefficients | minimize; verify masses and pair_coeff element order |
| Immediate temperature explosion at step ~0 | overlapping atoms or timestep in wrong units (`real` fs vs `metal` ps) | check units line vs timestep value first — the classic 1000× error |
| `Neighbor list overflow` | huge cutoff or dense system vs page settings | `neighbor` skin sanity; `neigh_modify page/one` increase |
| ReaxFF charges all zero / nonsense species | missing `fix qeq/reaxff`, or ffield element order mismatch | add the qeq fix; pair_coeff element list must match data-file types |
| MLP run explodes though training metrics were good | simulation left the training distribution | for DeePMD use `tools/deepmd/references/validation.md`; for other architectures use their dedicated skill or `tools/mlp`; this is a dataset problem, not a LAMMPS integrator problem |
| Thermostat "damping" warnings / T oscillates | damping constant in wrong units (it is *time*, not steps) | damp ≈ 100×dt (thermostat), 1000×dt (barostat), in time units of the unit system |

## Restart rules

- `read_restart` continues a trajectory; changing the potential, units, or ensemble mid-trajectory starts a NEW simulation for provenance purposes.
- After a crash, restart from the last *verified-stable* restart file, not the last written one.
