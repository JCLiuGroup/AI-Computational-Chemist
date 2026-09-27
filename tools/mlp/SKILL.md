---
name: mlp
description: Umbrella routing for machine-learning interatomic potential workflows. Use for general MLP method choice and cross-program validation; route DeePMD-kit/DPMD operation to `deepmd`, and keep MACE, NequIP, GPUMD/NEP, LASP, GemNet-OC, EquiformerV2, and other programs in separate tool skills when detailed commands are needed.
---

# Machine-Learning Potentials

Covers MLP-wide routing and legacy generic notes. DeePMD-kit/DPMD now lives in `tools/deepmd`; future MACE, NequIP, GPUMD/NEP, LASP, GemNet-OC, EquiformerV2 content should live in their own tool skills. MD deployment mechanics live in `lammps`; DFT label generation in `vasp` or `cp2k`; tool-agnostic MLP science lives in `knowledge/machine-learning-potentials.md`.

## Where to find what

| Situation | Go to |
|---|---|
| DeePMD-kit/DPMD dataset prep, `input.json`, `dp train/freeze/test`, model deviation | `tools/deepmd/` |
| general MLP concepts, dataset design, symmetry/equivariance, program taxonomy | `knowledge/machine-learning-potentials.md` |
| generic dataset contracts, provisional MACE notes, deployment, active-learning loop | `references/running.md` |
| is this model production-ready? held-out errors, physics checks, distribution coverage | `references/validation.md` |
| generic training failures or MACE fine-tuning problems | `references/errors.md` |
| example contribution rules | `examples/README.md` |
| external documentation for programs not covered by a dedicated tool skill | `references/resources.md` |

## Hard guardrails

- Only converged DFT frames become labels; one dataset = one method fingerprint (no mixed settings).
- Model quality is quoted from held-out data only — never training-set error.
- A potential is valid only inside its demonstrated distribution. Use the
  architecture-appropriate uncertainty or committee check when the risk or workflow
  requires it; out-of-range frames are retraining candidates, not production evidence.
- Per-iteration provenance: dataset paths/hash, config, seeds, checkpoint, test metrics.
