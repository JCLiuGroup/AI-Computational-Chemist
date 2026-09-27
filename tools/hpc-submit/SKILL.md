---
name: hpc-submit
description: Submit, monitor, and recover computational chemistry jobs locally, over approved SSH targets, or through Slurm/PBS schedulers. Use for job scripts, dry runs, queue checks, job arrays, log monitoring, resume decisions, and durable execution of long-running calculations.
---

# HPC Submit

Use this scheduler gate only after the producing engine's scientific preflight passes.

## Required inputs

- Target execution context (already local or an explicitly approved remote), scheduler,
  site operating guide, and configured transfer route when remote.
- Validated engine inputs, launch command, resources, wall time, work directory, and
  expected logs/artifacts.
- Submission approval and, when `.research/` requires it, an active execution lease.

## Route map

| Need | Load or run |
|---|---|
| discover the site, draft Slurm/PBS/local jobs, arrays, monitoring, or remote workspaces | `references/running.md` |
| create/update the private cluster operating guide | `references/cluster-guide-template.md` |
| run execution preflight and record submission/recovery evidence | `references/validation.md` |
| maintain a persistent remote shell | `tools/rsess/SKILL.md` |
| wait for a terminal Slurm state in a chained workflow | `scripts/wait_for_job.sh` |
| diagnose queue, resource, MPI/module, transfer, or session failures | `references/errors.md` |
| claim/reconcile durable execution ownership | `procedures/research-orchestrator/references/ownership-protocol.md`; `procedures/research-orchestrator/references/recovery-protocol.md` |
| consult scheduler documentation | `references/resources.md` |

## Workflow

1. Determine whether execution is local or remote. Follow the discovery and private
   guide procedure in `references/running.md`; read the target
   `~/.cluster-agents.md` before drafting the job.
2. Confirm the engine preflight and accepted release gates. Claim the task when
   required, then run the execution preflight in `references/validation.md`.
3. Obtain approval for an expensive batch, submit through one owner, and immediately
   record the command, job ID, script, workdir, outputs, and lease ID.
4. Monitor through scheduler accounting. After a terminal state, run the engine parser;
   on failure, consult `references/errors.md`, change one cause, and reconcile state
   before any rerun.

## Hard guardrails

- Never guess a host, partition, account, module, launcher, resource request, or
  licensed-data path. Confirm it from the approved target and its operating guide.
- For remote work, use the configured persistent session and file-transfer routes; do
  not transmit files through a terminal pane or expose secrets in commands/logs.
- Do not submit before accepted structure/engine gates, expensive-run approval, and any
  required active lease. Structure-generation code must never submit jobs.
- Scheduler `COMPLETED` means process completion, not scientific convergence. Only the
  engine parser can release results.
- Run long work through the site scheduler when one exists. On a target without a
  scheduler, use managed tmux/nohup only with the PID, log, workdir, and stop/recovery
  procedure recorded; never leave an untracked long process on a login shell.
- Never resubmit blindly. Reconcile leases/jobs/files after disconnects, diagnose the
  exact failure, change one thing, and record it.
- Do not delete or overwrite outside the job workdir. Keep site facts in the private
  cluster guide, not the repository or report.
