# Running Cross-Program MLP Workflows

> Load this when: defining a generic MLP dataset/training contract, using the
> provisional MACE notes, or planning deployment and active learning. For any DeePMD
> operation, use `tools/deepmd/SKILL.md` and its references instead.

## Dataset contract

- Only technically converged, provenance-linked electronic-structure frames become
  labels.
- One dataset uses one method fingerprint. Do not mix functionals, cutoff/basis,
  k-point policy, U, or incompatible reference-energy conventions as if they were
  statistical noise.
- Split train/validation/test data before fitting. Sample all relevant compositions,
  structures, and state points; do not use only the tail of one trajectory as the test
  set.
- Record dataset paths or hashes, split method, configuration, random seeds,
  checkpoint identity, and held-out metrics.

## Provisional MACE notes

- Train with `mace_run_train --config config.yml`; obtain architecture and cutoff
  choices from the current MACE documentation and record them.
- For a foundation-model fine-tune, record the exact checkpoint and license. Monitor
  held-out behavior for overfitting or catastrophic forgetting.
- Keep isolated-atom/reference-energy conventions consistent with the labeling
  calculations.
- Export for LAMMPS only after the held-out and physics gates in `validation.md` pass.

Detailed commands for another MLP family belong in its own tool skill rather than in
this umbrella reference.

## Deployment and active learning

Use `tools/lammps/references/running.md` for LAMMPS mechanics. Before production,
validate the model on the target composition, temperature/pressure range, defects, and
relevant reactions or barriers.

A generic active-learning cycle is: train independent models or an
architecture-appropriate uncertainty estimator; explore the declared state space;
select uncertain frames; label them with the same electronic-structure fingerprint;
retrain; then re-evaluate held-out and physics gates. Program-specific thresholds and
commands come from the dedicated tool skill. A model checkpoint without its dataset,
configuration, and provenance is not reproducible.
