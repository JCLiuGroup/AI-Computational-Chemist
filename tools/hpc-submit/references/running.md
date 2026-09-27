# Running Jobs: Scheduler Templates and Command Reference

> Load this when: writing a job script, translating scheduler commands, monitoring
> execution, or managing a long run on a target that has no scheduler.

Adapt partition/queue names, module names, and MPI launchers to the actual cluster — these vary everywhere and must be recorded in that cluster's `~/.cluster-agents.md` once learned.

## Submission-script preflight (all engines)

Before drafting a job script for any code (VASP, CP2K, Gaussian, LAMMPS,
DeePMD, phonopy arrays, GROMACS if present, or analysis jobs), read or re-read
the target `~/.cluster-agents.md` in the current execution context:

1. If already running on the target cluster, read the local file directly.
2. If driving a remote cluster, open the persistent session first, read the MOTD,
   then read the remote user's `~/.cluster-agents.md`.
3. Apply `Custom Instructions`, `Scheduler`, `Storage`, `Software Environment`,
   `Computational Codes`, and `Job Script Patterns` before choosing headers,
   modules, launchers, scratch paths, GPU requests, or Python/conda/uv setup.
4. If a required fact is absent or ambiguous, ask/probe for that fact before
   writing or submitting the script. Do not borrow settings from another engine
   or another cluster.

## Slurm: MPI engine job (generic template)

```bash
#!/bin/bash
#SBATCH --job-name=<job-name>
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=48        # = total MPI ranks per node
#SBATCH --time=24:00:00
#SBATCH --partition=<partition>     # from ~/.cluster-agents.md
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err

[[ "${1:-}" != "--dry-run" ]] || { echo "Use: sbatch --test-only $0"; exit 0; }
[[ -n "${SLURM_JOB_ID:-}" ]] || { echo "ERROR: use: sbatch $0" >&2; exit 2; }

module purge
module load <engine-module>          # from ~/.cluster-agents.md

cd "$SLURM_SUBMIT_DIR"
srun <engine-binary>                 # or mpirun -np $SLURM_NTASKS <engine-binary>
```

Keep these two guards in generated Slurm scripts: `./job.sh --dry-run` remains
harmless, direct execution without an allocation is rejected, and the scheduler's
real preflight remains `sbatch --test-only job.sh`.

Engine-specific knowledge — binary variants, input parallelization tags, shared-memory vs MPI models, scratch handling — lives in the engine skill's `running.md` (`vasp`, `gromacs`, `lammps`, `gaussian`, ...); this file owns only the scheduler mechanics.


## Slurm: GPU jobs (engine-neutral mechanics)

Before writing a GPU script, inspect what the site exposes through Slurm and record the actual partition/module choices in the cluster's `~/.cluster-agents.md`, not in committed workflow notes:

```bash
sinfo -o '%P %N %G %c %m'
scontrol show partition <gpu-partition>
scontrol show node <gpu-node>
module avail <engine>
sbatch --test-only <candidate-script>
```

Look for `GRES`/`--gpus` support and GPU type names such as `gpu:v100:8`, `gpu:a100:4`, `gpu:4090:2`, or similar. On clusters with mixed GPU partitions, choose the partition first, then request the exact GPU type. Prefer typed requests such as `--gres=gpu:<type>:4` or the site's equivalent over untyped `--gpus=4`, because an untyped request may land on a different GPU model than intended or even span multiple node types. Use `sbatch --test-only` to verify the script selects a sensible node before real submission.

Generic GPU-job rules, regardless of engine:

- Use a GPU-enabled build of the engine, never a CPU-only MPI build, on GPU nodes.
- Follow the engine's GPU parallelization model for ranks/threads per GPU (for most DFT/MD codes: one MPI rank per GPU); the engine skill carries the launch template.
- Avoid `--gpu-bind=single:1` or any binding that hides peer GPUs unless the site's tested template requires it; GPU-aware MPI/NCCL often needs all peer GPUs visible.
- If the site's documented policy says not to set `--ntasks`, `--cpus-per-task`, or `--mem` for GPU jobs, respect it — some clusters derive CPU/memory allocation from the GPU request, and conflicting directives cause rejection or bad placement.
- Check early stdout/stderr for CUDA/MPI binding errors before letting a long job run.
- Record GPU partition, GPU count/type, module, binary, and launch command in the run notes.

Engine-specific GPU launch templates and INCAR/input parallelization caveats live in the engine skill — for VASP, `tools/vasp/references/gpu-openacc.md`.

## Slurm: job array (phonon displacements, NEB-adjacent batches, conformers)

```bash
#SBATCH --array=1-24%8              # 24 tasks, max 8 concurrent
cd "$(printf 'disp-%03d' "$SLURM_ARRAY_TASK_ID")"
srun vasp_std
```

## PBS/Torque equivalent header

```bash
#PBS -N vasp-relax
#PBS -l select=1:ncpus=48:mpiprocs=48
#PBS -l walltime=24:00:00
#PBS -j oe
cd "$PBS_O_WORKDIR"
mpirun vasp_std
```

## Command translation table

| Action | Slurm | PBS |
|---|---|---|
| submit | `sbatch job.sh` | `qsub job.sh` |
| queue (mine) | `squeue -u $USER` | `qstat -u $USER` |
| job detail | `scontrol show job ID` | `qstat -f ID` |
| history/exit code | `sacct -j ID --format=JobID,State,Elapsed,ExitCode,MaxRSS` | `tracejob ID` |
| cancel | `scancel ID` | `qdel ID` |
| hold/release | `scontrol hold/release ID` | `qhold/qrls ID` |

## Scheduler-free long runs

Use this branch only after the target guide or a direct probe confirms that no
scheduler is available. A scheduler, service manager, or site-provided batch mechanism
always takes precedence over ad hoc background execution.

Before launch, record the owner/lease (when `.research/` is active), exact workdir,
validated launch command and environment, start time, expected outputs/checkpoints,
stdout/stderr log paths, and the intended stop/recovery procedure. Then:

1. Open a persistent `rsess`/tmux session for a remote target, or use a local persistent
   session on the target.
2. Start the validated command in the recorded workdir with `nohup ... >run.log 2>&1 &`
   (or the site's approved equivalent), capture `$!` immediately in `run.pid`, and
   verify that PID is alive and the log has started.
3. On reconnect, verify the recorded PID **and** its command/workdir before acting; a
   reused PID or missing process is not permission to launch another copy.
4. If the process is live, continue monitoring the log and checkpoints. If it exited,
   inspect the log and run the engine parser before deciding whether recovery is
   needed. If state is ambiguous, stop and reconcile rather than relaunch.

When `.research/` is active, `.research/jobs/` remains reserved for the scheduler
attempt contract. Represent a scheduler-free process with the claimed execution task
plus a project-local process record registered as a `job-record` artifact: store the
PID as its local `job_id`, and list the command, workdir, log, start time, lease, and
checkpoints as provenance. While live it remains `draft` and the task remains
`running`. After reconciliation, a clean process exit with expected files maps to task
`completed` plus a `validated` process record; an explicit process failure maps to task
`failed` while retaining a `validated` failure record; ambiguous identity maps to task
`blocked` plus a `draft` record. Append the launch and reconciliation events.

`nohup` provides neither resource allocation nor scientific validation. Do not use
this path to run heavy work on a shared login node, and never leave an untracked
process. Stopping a run requires confirming the recorded PID/command/workdir and
recording the termination.

## Monitoring patterns

- First minutes after start: check stderr and engine output for input errors — catching a doomed job early saves the whole walltime.
- Long runs: poll at meaningful intervals (SCF loop in OUTCAR, `mdrun` log/energy output, thermo lines in log.lammps) rather than continuously; `tail -f` only interactively.
- On `TIMEOUT`: VASP relax -> CONTCAR->POSCAR restart; GROMACS -> resume from `.cpt`; LAMMPS -> read restart file; Gaussian opt -> `opt=restart`. Record that the result is a continuation.

## Remote workspace setup (once per campaign)

0. Open a persistent remote session using the local bootstrap (connection command/alias), then read the MOTD and the remote `~/.cluster-agents.md` operating guide. Use the `rsess` skill (`rsess open <topic> <target>`) — it runs tmux on the remote, so state (cwd, loaded modules, venvs) survives across calls and connection drops, and `run` output is captured faithfully in per-command files. If rsess is not available, use whatever persistent-session tool the local bootstrap specifies; never rely on one-shot `ssh host cmd` which loses state between calls.
1. Create the campaign directory tree on the remote.
2. Copy the engine skills' preflight/parser scripts there via the configured transfer route.
3. Ensure a modern Python per the remote `~/.cluster-agents.md` Python recipe (e.g. load conda/uv, or create an agent env and `pip/uv install` what the scripts need, when allowed). Never assume the system interpreter is recent. Repo helper scripts with third-party deps run via `uv run` (inline PEP 723) — but **compute nodes are usually offline**: point `UV_CACHE_DIR` at a shared filesystem and **warm each script's env once on the login node** (just run it once where there is connectivity — first use populates the cache), then jobs run with `uv run --offline` and fetch nothing. Without a warmed cache, a first-ever `uv run` inside a batch job on an air-gapped node will hang trying to reach the index. uv is preferred (point it at a PyPI mirror via `UV_DEFAULT_INDEX` if the default index is slow); as a fallback, prepare a **conda/mamba** env that has the deps and run the scripts with its `python` — use it when a package installs more reliably from conda-forge (ovito has its own channel) or uv/PyPI is blocked. Index/channel mirror URLs come from `~/.cluster-agents.md`.
4. Every stage then runs: stage inputs -> remote preflight script -> submit -> parse with the remote parser script.

## Watcher idiom (chaining stages without polling by hand)

Use the shipped waiter — it confirms a **terminal** state via `sacct` and treats a transient query failure or the job's mere absence from `squeue` as "unknown, keep waiting", never as success:

```bash
scripts/wait_for_job.sh "$JOBID" --poll 120   # exit 0 only on COMPLETED
```

Do **not** hand-roll `until [ -z "$(squeue -h -j "$JOBID")" ]; do sleep; done` — a transient ssh/slurmctld hiccup makes `squeue` return empty and the loop fires a false positive on a still-running job (advancing the next stage onto an unconverged structure).

On wake: a scheduler-terminal state is not convergence — run the engine's own parser (failure outcomes already non-zero-exit the waiter, but silence still looks like success to a parser), then build and submit the next stage.
