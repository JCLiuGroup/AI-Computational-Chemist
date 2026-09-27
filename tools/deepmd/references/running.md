# Running DeePMD Workflows

> Load this when: preparing DeepMD datasets, writing `input.json`, training/freezing/compressing/testing a DP model, or deploying it in LAMMPS.

## Workflow shape

```text
define target simulation -> generate at least 10000 filtered DFT/AIMD labels by default
  -> convert with dpdata -> count/filter frames -> split train/validation/test
  -> train a DP model -> freeze/compress -> dp test on held-out data with detail files
  -> lcurve/parity plots -> DFT-all descriptor PCA -> automatic DeepMD QA verdict
  -> deploy in LAMMPS
  -> physics/stability checks -> add more AIMD labels if needed
```

For DPMD production work the default shape is AIMD-first: run enough AIMD/DFT sampling
across relevant initial models and temperatures, train the DP force field, then use
LAMMPS for longer MD. If the target is high-temperature diffusion, transport, or
reactive sampling, include high-temperature AIMD or annealing frames; do not train only
on low-temperature structures and then run hot DPMD.

## One-chain execution default

DeepMD is a fixed chain by default, not an interactive QA mode. Once DFT labels have
been converted and split into DeepMD `npy` datasets, continue through training,
freezing, held-out testing, required plots, DFT-all PCA, and the machine QA verdict in
one local command or one submitted job. Do not pause after `lcurve`, `dp test`, parity
plotting, or PCA just to ask the user whether to continue. Stop only when a command
fails, required data are missing, a real scientific choice is unresolved, or a
long/expensive DPMD submission has not already been approved.

Use the chain runner inside the DeepMD environment or inside the cluster batch script:

```bash
python tools/deepmd/scripts/run_deepmd_chain.py \
  --run-dir <deepmd-run-dir> \
  --data-root data
```

For an already trained model, keep the same diagnostics and skip only the completed
compute phases:

```bash
python tools/deepmd/scripts/run_deepmd_chain.py \
  --run-dir <deepmd-run-dir> \
  --data-root data \
  --skip-train \
  --skip-freeze
```

The runner performs:

```text
dp train input.json
  -> dp freeze -o graph.pb
  -> dp test on every discovered test split with aggregated detail_file.* outputs
  -> plot_deepmd_postprocess.py
  -> deepmd_descriptor_pca.py over DFT train/val/test frames
  -> check_deepmd_qa.py --json
  -> analysis/deepmd_chain/deepmd_chain_summary.json
```

It discovers common `data/<split>/<system>/set.000` and
`data/<system>/<split>/set.000` layouts. Use repeated `--test-system <path>` only when
the held-out test dataset uses a nonstandard directory name. If the DeepMD Python can
load the model but lacks `matplotlib`, pass a plotting-capable interpreter with
`--plot-python <python>` for lcurve/parity plots and `--pca-plot-python <python>` for
the PCA figure, or run individual helpers only for debugging.

## Label generation and dataset design

Default bootstrap strategy:

- Prefer more VASP/CP2K AIMD labels from several physically plausible initial models
  and several temperatures over a default 4-model committee active-learning loop.
- Unless there is a documented special reason, assemble at least `10000` filtered
  DFT-labeled frames before the first split and production training. This is a default
  floor for usable DeepMD bootstrap data, not a guarantee of sufficiency.
- Use different initial structures to cover composition/order/defect/interface or
  adsorption motifs that the final DPMD may visit. Do not let one relaxed minimum define
  the whole training distribution.
- Use different temperatures to cover the intended production range and nearby higher
  energy configurations. For high-temperature production, include AIMD at or above that
  temperature.
- Keep the DFT label method identical across all AIMD chunks. More frames with mixed
  functionals, POTCARs, k policies, or convergence settings are worse than fewer
  consistent labels.
- Count only converged, chemically sensible frames after filtering. Raw AIMD step count
  is not the dataset size if some electronic steps failed, structures decomposed, or
  duplicate/equilibrating frames are discarded.
- If the project deliberately starts below `10000` labels because the system is
  unusually expensive, the request is only a smoke test/pilot, or the user asked for a
  quick run, record that exception and keep the model out of production reporting until
  more labels are added.
- Only switch to 4-model committee/DP-GEN-style active learning when the user requests
  it, when DPMD exploration is the project goal, or when held-out/physics checks show a
  clear extrapolation gap that targeted AIMD cannot cover efficiently.

Typical sources:

- VASP AIMD/relax outputs: `OUTCAR` with converged electronic steps.
- CP2K AIMD outputs: use the matching dpdata format.
- Deliberate perturbations: rattled structures, strained cells, vacancies, surfaces, interfaces, and high-temperature snapshots.

Sampling strategies:

- Anneal from low to high temperature, such as 100 K to the upper target temperature, to sample a broad part of the potential-energy surface.
- Run multiple constant-temperature trajectories covering the target range, such as
  600, 800, 1000, 1200, and 1400 K for high-temperature diffusion or transport studies.
- Add new AIMD data when validation shows gaps: under-covered structures,
  high-temperature failure, unstable DPMD, poor held-out errors by source, or physics
  checks that disagree with DFT. Model deviation/DP-GEN can automate this loop, but is
  not the default path because 4-model committee training is usually slower.

Hard filter before conversion:

- Remove unconverged or chemically nonsensical frames.
- Keep DFT settings consistent across all chunks.
- Record structure source, temperature, timestep, frame stride, and DFT settings for each system.

## Convert labels with dpdata

Single VASP trajectory:

```python
import dpdata

data = dpdata.LabeledSystem("OUTCAR", fmt="vasp/outcar")
data.to_deepmd_npy("training_data")
```

CP2K trajectory:

```python
import dpdata

data = dpdata.LabeledSystem("aimd", fmt="cp2k/aimd_output")
data.to_deepmd_npy("training_data")
```

Combine multiple VASP trajectories:

```python
import dpdata

data600 = dpdata.LabeledSystem("./600/OUTCAR", fmt="vasp/outcar")
data1400 = dpdata.LabeledSystem("./1400/OUTCAR", fmt="vasp/outcar")
data600.append(data1400)
data600.to_deepmd_npy("all_data")
```

Train/validation split:

```python
import numpy as np
import dpdata

data = dpdata.LabeledSystem("OUTCAR", fmt="vasp/outcar")
nframes = len(data)
rng = np.random.default_rng(20240620)
idx_val = rng.choice(nframes, size=max(1, int(0.1 * nframes)), replace=False)
idx_train = np.array(sorted(set(range(nframes)) - set(idx_val)))

data.sub_system(idx_train).to_deepmd_npy("training_data")
data.sub_system(idx_val).to_deepmd_npy("validation_data")
```

For multiple converted `deepmd/npy` folders, count filtered labeled frames before
splitting/training:

```python
import dpdata

systems = [
    "data/model_A_600K",
    "data/model_A_1000K",
    "data/model_B_600K",
    "data/model_B_1000K",
]
nframes = sum(len(dpdata.LabeledSystem(path, fmt="deepmd/npy")) for path in systems)
if nframes < 10000:
    raise SystemExit(f"Need >=10000 filtered DFT frames by default; found {nframes}")
print(f"filtered DFT-labeled frames: {nframes}")
```

DeepMD npy layout to inspect when debugging:

| File | Meaning |
|---|---|
| `set.000/box.npy` | cell matrices |
| `set.000/coord.npy` | atomic coordinates |
| `set.000/energy.npy` | total energies |
| `set.000/force.npy` | atomic forces |
| `set.000/virial.npy` | virials, if present |
| `type_map.raw` | element names in type order |
| `type.raw` | atom type index for each atom |

For VASP-derived data, keep the element order consistent with POSCAR and `type_map.raw`. In LAMMPS, atom type 1 corresponds to the first element in `type_map`, atom type 2 to the second, and so on.

## `input.json` essentials

Starting point for DeepPot-SE:

```json
{
  "_comment": "starting template; edit type_map, sel, paths, and training length",
  "model": {
    "type_map": ["Elem1", "Elem2", "Elem3", "Elem4"],
    "descriptor": {
      "type": "se_e2_a",
      "sel": "auto",
      "rcut_smth": 0.50,
      "rcut": 6.00,
      "neuron": [25, 50, 100],
      "resnet_dt": false,
      "axis_neuron": 16,
      "seed": 1
    },
    "fitting_net": {
      "neuron": [100, 100, 100],
      "resnet_dt": false,
      "seed": 1
    }
  },
  "learning_rate": {
    "type": "exp",
    "decay_steps": 100,
    "start_lr": 0.001,
    "stop_lr": 3.51e-8
  },
  "loss": {
    "start_pref_e": 0.02,
    "limit_pref_e": 1,
    "start_pref_f": 1000,
    "limit_pref_f": 1,
    "start_pref_v": 0,
    "limit_pref_v": 0
  },
  "training": {
    "training_data": {
      "systems": ["../00.data/training_data"],
      "batch_size": "auto"
    },
    "validation_data": {
      "systems": ["../00.data/validation_data"],
      "batch_size": "auto",
      "numb_btch": 3
    },
    "numb_steps": 100000,
    "seed": 10,
    "disp_file": "lcurve.out",
    "disp_freq": 1000,
    "save_freq": 10000
  }
}
```

Key choices:

- `type_map`: element order contract with dataset and LAMMPS data file.
- `descriptor.type`: `se_e2_a` is the standard DeepPot-SE angular descriptor starting point.
- `sel`: use `"auto"` if supported by the installed DeePMD-kit; otherwise set a per-element neighbor upper bound large enough for the cutoff, commonly tens of neighbors, but not blindly above the cell atom count.
- `rcut`: usually around 6 A for condensed materials; increase only when the physics requires it because cost grows.
- `resnet_dt`: compression support depends on model/version; if compression is required, test early with the intended settings.
- `numb_steps`: use short exploratory runs first; final models are commonly much longer than a smoke test.

## Dataset distribution map after training

After the first model is trained, frozen, and tested, make a descriptor PCA map over all
compatible DFT-labeled `train`, `val`, and `test` split frames before LAMMPS handoff or
report use. Color by split at minimum and keep source/system labels in sidecar data.
This is mandatory for the fixed DeepMD QA package even when the dataset comes from only
one apparent family; it is the fastest way to catch duplicated, missing, or
non-representative validation/test splits.

A practical DeepMD-specific method is to short-train a DPA1/attention descriptor model,
freeze it as `graph-dpa1.pb`, extract `eval_descriptor()` embeddings for every
`deepmd/npy` dataset, and plot a 2D PCA colored by data source. When a trained
production model already exposes useful descriptors, it may be reused for this
diagnostic if the summary states that choice. See `references/dataset-embedding.md` for
the full workflow and caveats.

This embedding model is deliberately short-trained and is not a production potential.
Use it to decide whether the dataset distribution is reasonable, whether validation/test
sets really probe distinct regions, and where the next AIMD labels should come from.
For very heterogeneous data, the same diagnostic can also be run before committing to a
long final training job. Optional DPMD trajectory overlays can be plotted after
production runs, but they do not replace the required DFT train/val/test PCA.

## Training, restart, freeze, compress, test

```bash
dp train input.json
dp train input.json > log
dp train --restart model.ckpt input.json
```

For long `dp train`/`dp test` jobs or GPU training, prepare the batch script
through `tools/hpc-submit`: read the target `~/.cluster-agents.md` before writing
the script, and take the module/conda environment, GPU partition, launcher,
scratch, and checkpoint/restart policy from that guide.

Expected outputs:

- `checkpoint` and `model.ckpt*`: restart/checkpoint files.
- `lcurve.out`: training/validation loss, energy RMSE, force RMSE, learning rate.
- `log`: DeePMD runtime messages.

Freeze and optionally compress:

```bash
dp freeze -o graph.pb
dp compress -i graph.pb -o graph-compress.pb
```

Test on a held-out set and request detail files for plotting:

```bash
dp test -m graph-compress.pb -s ./test_data -n 0 -d detail_file
```

`dp test` reports energy RMSE, energy RMSE per atom, force RMSE, and virial RMSE. For
many condensed-phase production models, values on the order of a few `meV/atom` and
~`0.1 eV/A` are common starting points; whether that is acceptable depends on the
downstream observable and validation gates.

## Automatic post-training diagnostics

Before deploying the model in LAMMPS DPMD or using it in a report, the default is to run
the one-chain command above and let it produce the fixed diagnostics plus a
machine-readable verdict. The individual helper commands below are fallback/debug
commands for rerunning one part of the chain, not approval breakpoints:

```bash
uv run tools/deepmd/scripts/plot_deepmd_postprocess.py \
  --work-dir <deepmd-run-dir> \
  --lcurve lcurve.out \
  --detail-prefix detail_file \
  --fig-dir figures \
  --out-dir analysis/deepmd_postprocess

uv run tools/deepmd/scripts/deepmd_descriptor_pca.py \
  --model <deepmd-run-dir>/graph.pb \
  --data-root <deepmd-run-dir>/data \
  --out-dir analysis/deepmd_descriptor_pca_dft_all \
  --figure figures/deepmd_descriptor_pca_dft_all.png

uv run tools/deepmd/scripts/check_deepmd_qa.py \
  --project-root . \
  --model <deepmd-run-dir>/graph.pb \
  --postprocess-summary analysis/deepmd_postprocess/postprocess_summary.json \
  --pca-summary analysis/deepmd_descriptor_pca_dft_all/summary.json
```

Expected reportable artifacts:

- `deepmd_lcurve_energy_force_lr.png`: train/validation energy and force RMSE plus learning rate.
- `deepmd_dp_test_energy_parity.png`: held-out DFT-vs-DP energy parity.
- `deepmd_dp_test_force_parity.png`: held-out DFT-vs-DP force-component parity.
- `deepmd_dp_test_force_residual_hist.png`: held-out force residual distribution.
- `deepmd_descriptor_pca_dft_all.png`: descriptor PCA for all compatible DFT
  `train`, `val`, and `test` frames.
- `analysis/deepmd_postprocess/postprocess_summary.json` and
  `analysis/deepmd_descriptor_pca_dft_all/summary.json`: machine-readable provenance,
  frame counts, plotted files, and exclusions.

If the run is inside a preconfigured DeepMD conda/module environment and `uv` cannot
resolve `deepmd-kit`, run the same scripts with that environment's `python`. If that
DeepMD environment can load the model but lacks `matplotlib`, run the PCA in two steps:

```bash
<deepmd-python> tools/deepmd/scripts/deepmd_descriptor_pca.py \
  --model <deepmd-run-dir>/graph.pb \
  --data-root <deepmd-run-dir>/data \
  --out-dir analysis/deepmd_descriptor_pca_dft_all \
  --figure figures/deepmd_descriptor_pca_dft_all.png \
  --skip-plot

uv run tools/deepmd/scripts/deepmd_descriptor_pca.py \
  --out-dir analysis/deepmd_descriptor_pca_dft_all \
  --figure figures/deepmd_descriptor_pca_dft_all.png \
  --skip-extract --skip-pca
```

Keep the command, environment, and summaries as provenance. Apply the maturity and
legal `.research` status mapping in `references/validation.md`; `pilot/incomplete` is
never a persisted workflow status. A passing verdict permits technical handoff to the
next approved stage; it does not replace physics/stability checks for the target
observable.

## LAMMPS DPMD deployment

The model file from `dp freeze` or `dp compress` can be used with LAMMPS built with DeePMD support.

Minimal input:

```text
units           metal
boundary        p p p
atom_style      atomic
neighbor        1.0 bin
neigh_modify    every 10 delay 0 check no
read_data       system.lmp

mass            1 <mass_type_1>
mass            2 <mass_type_2>
mass            3 <mass_type_3>
mass            4 <mass_type_4>

pair_style      deepmd graph-compress.pb
pair_coeff      * *

velocity        all create 600.0 23456789 dist gaussian mom yes rot yes
fix             1 all nvt temp 600.0 600.0 0.5
timestep        0.001
thermo_style    custom step pe ke etotal temp press vol
thermo          100
dump            1 all custom 100 output.dump id type xu yu zu
run             10000
```

Notes:

- `units metal` means `timestep 0.001` is 1 fs.
- Use unwrapped coordinates (`xu yu zu`) for diffusion/MSD.
- The LAMMPS data atom types must match `type_map`; wrong order gives wrong chemistry without necessarily crashing.
- For optional model-deviation monitoring, train multiple frozen models with different
  seeds and use them together:

```text
pair_style deepmd graph0.pb graph1.pb graph2.pb graph3.pb out_file md.out out_freq 100
pair_coeff * *
```

This is an active-learning/extrapolation diagnostic, not the default initial dataset
builder. Without an explicit request, first spend the compute budget on more AIMD label
coverage from distinct initial models and temperatures.

LAMMPS mechanics live in `tools/lammps`; MD statistical interpretation lives in `knowledge/molecular-dynamics.md`.
Batch scripts for DPMD deployment inherit the LAMMPS + `hpc-submit` rule: read
the target `~/.cluster-agents.md` before writing the script.

## Diffusion post-processing

For species diffusion or migration, the workflow is:

1. Relax the structure.
2. Anneal from about 100 K to each target temperature.
3. Run equilibrated AIMD/DPMD at each target temperature.
4. Discard equilibration and analyze production frames.
5. Compute MSD and diffusion coefficient.
6. Fit `log(D)` versus `1000/T` or `ln(D)` versus `1/T` for an activation barrier, using several temperatures.

For 3D diffusion:

```text
D = slope(MSD) / 6
D(cm^2/s) = slope(A^2/ps) / 6 * 1e-4
```

For LAMMPS dumps with MDAnalysis:

```python
import numpy as np
import MDAnalysis as mda
import MDAnalysis.analysis.msd as msd

u = mda.Universe("output.dump")
MSD = msd.EinsteinMSD(u, select="type <diffusing_type>", msd_type="xyz", fft=True)
MSD.run(start=100)
times_ps = np.arange(MSD.n_frames) * 0.1
msd_a2 = MSD.results.timeseries
```

Check the dump stride: if `dump` writes every 100 steps and `timestep` is 0.001 ps, the frame spacing is 0.1 ps.
