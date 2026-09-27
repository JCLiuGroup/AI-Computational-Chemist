# Scheduler Job Attempt Contract

> Load this when: submitting, reconciling, or validating scheduler jobs recorded under
> a research-orchestrator lease.

## Boundary

A lease answers **who owns an execution task and its mutable paths**. A job attempt
answers **which scheduler submission currently writes one calculation directory**.
One active lease may own multiple sequential or independent attempts, but one workdir
may have at most one `submitting`, `submission_unknown`, `pending`, or `running`
attempt at a time.

## Files

The authoritative attempt records are:

```text
.research/jobs/J-<uuid>.json
```

Each calculation directory carries only a pointer to its latest attempt:

```text
RUN_DIR/.aicc-active-job.json
```

The pointer is a duplicate-submission guard, not the authoritative job history.

## Required fields

```json
{
  "schema_version": 1,
  "attempt_id": "J-<uuid>",
  "submission_id": "<uuid>",
  "task_id": "T004",
  "lease_id": "L-T004-...",
  "owner_id": "codex-main",
  "scheduler": "slurm",
  "scheduler_job_name": "aicc-<submission-id-prefix>",
  "job_id": "123456",
  "state": "pending",
  "workdir": "work/runs/ads-relax",
  "script": "work/runs/ads-relax/job.sh",
  "parent_attempt_id": null,
  "created_at": "2026-07-12T00:00:00+08:00",
  "updated_at": "2026-07-12T00:00:00+08:00"
}
```

## States

- Non-terminal: `submitting`, `submission_unknown`, `pending`, `running`.
- Terminal: `completed`, `failed`, `cancelled`, `timeout`.

`submission_unknown` is deliberately non-terminal. It means `sbatch` may have created
a job but the Job ID was not durably captured. Automatic retry is forbidden until
`aicc job reconcile` finds one matching scheduler record and records the result. Zero
or multiple matches remain blocked until later scheduler evidence appears or an
operator explicitly resolves the attempt with `--mark failed --reason ... --confirm`.
That resolution is recorded in `events.jsonl`.

`aicc job reconcile` backs off from a `submitting` attempt younger than 120 seconds
(exit 2, no state change): the submitter may still be talking to sbatch. Operator
resolution with `--mark` is allowed at any age.

A completed `sbatch` process with a nonzero return code, explicit stderr, and no Job ID
is an explicit submission failure: the attempt becomes terminal `failed`. Timeouts,
process launch errors, conflicting output, and successful-but-unparseable output remain
`submission_unknown`.

## Submission rules

1. `check_pre_submit.py` must pass.
2. The named task must have an active lease owned by the caller.
3. The workdir must fall within the lease's `exclusive_paths`.
4. Project-state and workdir submission locks are acquired before writing state;
   the `submitting` record and active pointer are written under them.
5. `sbatch` itself runs after both locks are released: the recorded `submitting`
   attempt is what blocks duplicates, and other tasks' claim/heartbeat/release
   stay responsive during scheduler latency. The duplicate guard scans the
   recorded attempts for any active attempt in the workdir; the run-dir pointer
   is a fast-path copy, never the sole guard, so a lost pointer cannot disable
   protection. `--timeout` must stay below the 120 s reconcile grace period.
6. `sbatch` is invoked directly with `--parsable`; no shell or login-shell wrapper is
   used.
7. The outcome is finalized under a re-acquired project-state lock after re-reading
   the record. If the attempt is still `submitting`, the returned Job ID is written
   and bound to the lease only if the same lease is still active. If the attempt was
   advanced or operator-resolved during the sbatch window, that resolution wins:
   the state is not overwritten, the Job ID (if any) is recorded on the attempt, a
   `job_submission_conflict` event is appended, and the operator is told to check
   `squeue`/`sacct` and `scancel` a possible orphan job.
8. Scheduler commands have finite timeouts. Any ambiguous result becomes
   `submission_unknown`; it is never automatically retried.

## Locks and recovery

Project-state and run-directory locks retry briefly to absorb ordinary command
overlap. A leftover lock records host, PID, creation time, and a unique lock ID.
`aicc job unlock PROJECT [RUN_DIR] --reason ... --confirm` refuses a live same-host
owner; an unverifiable remote or malformed owner additionally requires `--force`.
Every successful recovery is appended to `events.jsonl`.

The run-directory pointer is required only while that workdir has a non-terminal
attempt. Terminal Job history remains authoritative under `.research/jobs/`, so a
finished calculation directory may be archived after its evidence is preserved.

A crash between writing the attempt record and the run-dir pointer leaves an active
attempt without its pointer. `validate_state.py` reports this as WARN (not FAIL) so
recovery tooling keeps working, and `reconcile_jobs.py --attempt <id>` restores the
pointer for an active attempt whose workdir still exists (recorded as a
`job_pointer_restored` event); the validator separately FAILs if a workdir ever
accumulates more than one active attempt. Name-based sacct recovery passes
`-S <created_at - 1 day>` so a lost Job ID is still found after midnight.

## Same-directory continuation

A terminal attempt permits a later attempt in the same workdir. For a VASP geometry
continuation, first preserve the prior inputs and outputs, then copy `CONTCAR` to
`POSCAR`, run VASP preflight again, and submit. The new record sets
`parent_attempt_id` to the prior attempt. Non-terminal attempts still block the
continuation.

Scheduler `COMPLETED` means only that the process ended successfully; the VASP parser
still decides whether the structure optimization converged.
