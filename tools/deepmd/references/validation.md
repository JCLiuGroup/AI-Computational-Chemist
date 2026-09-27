# Validating DeePMD Models

> Load this when: reading `lcurve.out`, interpreting `dp test`, deciding if a DP model may drive production DPMD, or setting model-deviation thresholds.

## Minimum validation gates

| Gate | What to check |
|---|---|
| Held-out regression | `dp test` on data not used for training; report energy RMSE per atom and force RMSE, and keep detail files for parity plots. |
| Dataset size | By default, at least `10000` filtered DFT-labeled frames before the first production split/training; smaller sets are pilot/exception cases unless explicitly justified. |
| Learning curve | `lcurve.out` training and validation errors both converge; large train/validation gap means overfitting; plot energy, force, and learning-rate traces. |
| Parity/residual plots | Held-out energy parity, force parity, and force residual histogram show no systematic curvature, source-specific bias, or high-temperature-only failure. |
| Physics checks | lattice/volume, a known defect/adsorption/reaction energy, diffusion trend, or barrier vs DFT for the target system. |
| MD stability | short NVE or weakly thermostatted run has no atom loss, unphysical chemistry, or severe energy drift. |
| In-distribution monitor | Optional 4-model DeePMD committee force model deviation when active learning or high-risk extrapolation is requested. |
| Dataset coverage map | Required before DPMD handoff/report use: make a descriptor PCA over all compatible DFT `train`, `val`, and `test` frames to inspect split coverage and duplicates, not to claim accuracy. |

Regression starting points:

- Energy RMSE: target roughly `1-5 meV/atom` for demanding production work.
- Force RMSE: target roughly `50-100 meV/A`; stiffer/reactive systems may need tighter checks.
- Parity plots: no systematic curvature, phase-specific bias, or high-temperature-only failure.

These are not universal pass/fail laws. The real criterion is whether the model reproduces the DFT-level observable the project needs.

## Reading `lcurve.out`

Columns are typically:

```text
step rmse_val rmse_trn rmse_e_val rmse_e_trn rmse_f_val rmse_f_trn lr
```

Use it to detect:

- Undertraining: both training and validation errors still falling.
- Overfitting: training error keeps falling while validation error stalls or rises.
- Bad labels: noisy validation spikes, high force error floor, or inconsistent per-system offsets.
- Learning-rate issues: NaN or early divergence at high starting LR.

Do not report model quality from training error. Use held-out `dp test` and state the dataset path, frame count, and DFT settings.

## `dp test` reporting

Run:

```bash
dp test -m graph.pb -s ./test_data -n 0 -d detail_file
```

Report:

- model path and whether compressed.
- total filtered DFT-labeled frame count before splitting; flag anything below `10000`
  as pilot/exception unless there is a documented special reason.
- test data path, frame count, compositions, and temperature/structure coverage.
- `Energy RMSE/Natoms` in eV/atom or meV/atom.
- `Force RMSE` in eV/A.
- virial RMSE if pressure/stress is part of the target.

Use a true test set for final claims. Validation data can guide model selection; test data is for final evaluation.

## Automatic QA verdict for DPMD handoff

A DP model is not ready for LAMMPS DPMD handoff or report use until the fixed chain QA
package exists and the automatic verdict has been written. This is a machine check in
the DeepMD chain, not an interactive stop after every figure:

- `deepmd_lcurve_energy_force_lr.png` from `lcurve.out`.
- `deepmd_dp_test_energy_parity.png` from held-out `dp test -d` detail files.
- `deepmd_dp_test_force_parity.png` from held-out `dp test -d` detail files.
- `deepmd_dp_test_force_residual_hist.png` from held-out `dp test -d` detail files.
- `deepmd_descriptor_pca_dft_all.png` from all compatible DFT `train`, `val`, and
  `test` split frames.
- `postprocess_summary.json` and `deepmd_descriptor_pca_dft_all/summary.json` with
  model path, dataset paths, frame counts, type_map, plotted files, exclusions, and
  interpretation limits.

Run the default chain after the DFT labels are converted/split:

```bash
python tools/deepmd/scripts/run_deepmd_chain.py --run-dir <run> --data-root data
```

Use the individual helpers only to rerun or debug one part of the chain:

```bash
uv run tools/deepmd/scripts/plot_deepmd_postprocess.py --work-dir <run> --detail-prefix detail_file
uv run tools/deepmd/scripts/deepmd_descriptor_pca.py --model <graph.pb> --data-root <data-root>
uv run tools/deepmd/scripts/check_deepmd_qa.py --project-root .
```

The descriptor PCA scope is DFT labels only by default: every compatible frame in
`train`, `val`, and `test`. If the model/type_map cannot evaluate a subset, split the
PCA by compatible type_map and list the excluded data in the summary. Optional DPMD
trajectory overlays are useful after production runs, but they do not replace the
DFT-all coverage map.

Missing diagnostics or a failed QA verdict give the model a `pilot/incomplete`
**maturity verdict**, not a workflow status, unless the user records an explicit
waiver. In `.research/`, keep the model artifact `draft` while remediation is open or
mark it `rejected` when abandoned; use legal task states such as `blocked` or `failed`.
Never persist `pilot` or `incomplete` in a task/artifact `status` field. A passing QA
package may support artifact status `validated`, but it still does not prove scientific
validity or acceptance; it only clears the fixed DeepMD regression and coverage
diagnostics.

## Model Deviation

Use this when the user asks for active learning/concurrent learning, when DPMD is being
used to explore unknown phase space, or when held-out/physics checks suggest serious
extrapolation risk. It is not the default way to build the initial dataset because
training four comparable models is usually slower than adding targeted AIMD labels from
different initial structures and temperatures.

Train at least four models with identical data/settings but different random seeds. In LAMMPS:

```text
pair_style deepmd graph0.pb graph1.pb graph2.pb graph3.pb out_file md.out out_freq 100
pair_coeff * *
```

DP-GEN-style force-deviation starting points:

| Max force deviation | Interpretation |
|---|---|
| `< 0.05 eV/A` | usually trusted |
| `0.05-0.20 eV/A` | candidate region for DFT labeling |
| `> 0.20 eV/A` | unreliable/extrapolative |

Tune thresholds for the chemistry, force scale, temperature, and target observable. A high-deviation frame is not scientific data; it is a candidate for labeling and retraining.

Default non-committee validation should still include the fixed QA package above, errors
split by data source/temperature/model family where possible, short DPMD stability
checks, and a small number of overlapping AIMD-vs-DPMD structural comparisons such as
RDF, coordination, diffusion trend, or representative local environments.

## Diffusive/Transport DPMD Checks

For diffusion, transport, or high-temperature DPMD, check:

- The diffusing species and host/solvent/interface environment remain chemically
  sensible before interpreting MSD or transport observables.
- The production temperature range is covered by training data from AIMD at multiple
  temperatures or, when explicitly requested, active-learning exploration.
- MSD is computed from unwrapped coordinates after equilibration.
- Diffusion coefficients use the correct dimensionality: 3D `/6`, 2D `/4`, 1D `/2`.
- Activation barriers are fitted from multiple temperatures, not one trajectory.

When DPMD is used to extend AIMD length scales, compare a short overlapping AIMD/DPMD
segment where possible: RDF, MSD slope trend for the target species, and representative
local environments.
