# Execution-Side Validation

> Load this when: about to submit a job (preflight) or recording what was submitted.

## Preflight (after the engine skill's scientific preflight passed)

- Target `~/.cluster-agents.md` read in the current execution context before preparing
  or submitting the job script. If `.research/` is in use, register an accepted
  `cluster-guide-read` artifact and list it in the engine/HPC task inputs so
  `check_pre_submit.py` can enforce it. The evidence file records only the guide path,
  target host/context, read timestamp, guide size, and site settings used; it must not
  copy private guide contents. The execution owner or a dedicated pre-submit/bootstrap
  task normally produces this artifact; `external` is acceptable for a read recorded
  before `.research/` existed. For remote guide reads, include the remote `stat` size or
  hash command output as process evidence; the hook cannot independently re-stat the
  remote file unless it is running in that remote context.
- Working directory confirmed, writable, and on a filesystem visible to compute nodes.
- Executable/module available in the *compute* environment, not just the login node (`module avail`, or a 1-minute test job).
- Slurm scripts make `--dry-run` exit before modules or launchers and reject direct
  execution without `SLURM_JOB_ID`; use `sbatch --test-only job.sh` for the real
  scheduler preflight.
- Resource request matches the engine's parallelization: VASP `NCORE`/`KPAR` vs cores and k-points; GROMACS MPI/OpenMP/GPU layout; LAMMPS MPI ranks; Gaussian = single node with `%nprocshared` = requested cores.
- GPU jobs: the script uses a GPU-enabled build of the engine, requests the intended GPU type/count, matches MPI ranks to the engine's GPU model (see the engine skill's GPU reference), and passes `sbatch --test-only` on the target partition. On mixed GPU partitions, untyped `--gpus=N` is not enough unless the cluster guide says it is safe.
- Walltime ≥ 2× the estimate; checkpointing enabled for runs that might exceed it (CONTCAR/WAVECAR, GROMACS `.cpt`, LAMMPS restart, .chk).
- Scratch/quota checked for WAVECAR-, CHGCAR-, or trajectory-heavy jobs.
- stdout/stderr paths defined and distinct per job.
- On a scheduler-free target, the site guide/probe confirms that no managed scheduler
  exists; the persistent session, workdir, exact command/environment, PID file, log,
  checkpoints, and stop/recovery procedure are recorded before launch. Verify that the
  process is not being placed on a shared login node.

## Immediately after submission or launch (non-optional)

Record into `workflow.md` (if one exists) and the session report:

- scheduler job ID, or scheduler-free PID plus command/log/workdir
- the first-minutes check: stderr + engine output scanned for input errors — catching a doomed job early saves the whole walltime.

## Before declaring a job "done"

Scheduler `COMPLETED` ≠ success. The engine's own parser (`tools/vasp/scripts/parse_vasp.py`, etc.) decides whether the calculation is usable; the scheduler only tells you the process exited.

Reach that `COMPLETED` reliably with `scripts/wait_for_job.sh` (it confirms the terminal state via `sacct`, so a transient `squeue` hiccup can't fake "done"), **then** run the engine parser. A job leaving the queue is never, by itself, evidence of convergence.

**Do not hand-roll `until [ -z "$(squeue -h -j ID)" ]; do sleep; done`.** A single transient empty `squeue` poll (ssh drop, slurmctld timeout) then reads as "job done" and fires analysis on a still-running or unconverged job — this is a real failure mode that shipped numbers from an incomplete run. `wait_for_job.sh` already debounces exactly this; use it.

For a scheduler-free run, first verify the recorded PID and command/workdir. A live
process is still running; a missing process is only an exit signal. Inspect its log and
expected files, then run the engine parser. Never infer convergence from a vanished PID
or a closed tmux/SSH session. When `.research/` is active, reconcile the task lease and
registered `job-record` artifact using the legal task/artifact status mapping in
`references/running.md`; do not create a scheduler-attempt record for a bare PID.
