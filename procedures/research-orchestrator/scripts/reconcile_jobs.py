#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML>=6.0"]
# ///
"""Reconcile one recorded Slurm attempt with squeue and sacct."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

from job_utils import (
    ACTIVE_JOB_STATES,
    SUBMITTING_GRACE_SECONDS,
    active_pointer_path,
    append_job_id_to_lease,
    current_attempt,
    load_job,
    project_state_lock,
    run_submission_lock,
    write_active_pointer,
    write_job,
)
from lease_utils import append_event, fail_if_invalid, iso, now_local, parse_time, resolve


SLURM_STATE_MAP = {
    "PENDING": "pending",
    "CONFIGURING": "pending",
    "REQUEUED": "pending",
    "RESIZING": "pending",
    "RUNNING": "running",
    "COMPLETING": "running",
    "SUSPENDED": "running",
    "COMPLETED": "completed",
    "FAILED": "failed",
    "BOOT_FAIL": "failed",
    "DEADLINE": "failed",
    "NODE_FAIL": "failed",
    "OUT_OF_MEMORY": "failed",
    "PREEMPTED": "failed",
    "REVOKED": "failed",
    "CANCELLED": "cancelled",
    "TIMEOUT": "timeout",
}
DEFAULT_SCHEDULER_TIMEOUT_SECONDS = 30.0
# Widen the sacct name-lookup window below the attempt's creation time to
# absorb clock skew between the submit host and slurmctld.
SACCT_WINDOW_SLACK = timedelta(days=1)


def sacct_start_time(job: dict[str, Any]) -> str | None:
    created = job.get("created_at")
    if not isinstance(created, str) or not created:
        return None
    try:
        created_dt = parse_time(created)
    except (ValueError, TypeError):
        return None
    return (created_dt - SACCT_WINDOW_SLACK).strftime("%Y-%m-%dT%H:%M:%S")


def run_scheduler(
    command: list[str], timeout_seconds: float
) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def parse_rows(text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        fields = [field.strip() for field in line.strip().split("|")]
        if len(fields) < 2 or not fields[0]:
            continue
        job_id = fields[0].split(".", 1)[0]
        state = fields[1].split()[0].split("+", 1)[0].upper()
        if job_id.isdigit() and state:
            rows.append((job_id, state))
    unique: dict[str, str] = {}
    for job_id, state in rows:
        unique.setdefault(job_id, state)
    return list(unique.items())


def scheduler_rows(
    job: dict[str, Any], timeout_seconds: float
) -> list[tuple[str, str]] | None:
    job_id = job.get("job_id")
    if isinstance(job_id, str) and job_id:
        queue = run_scheduler(
            ["squeue", "-h", "-j", job_id, "-o", "%A|%T"], timeout_seconds
        )
        if queue is not None and queue.returncode == 0:
            rows = parse_rows(queue.stdout)
            if rows:
                return rows
        accounting = run_scheduler(
            ["sacct", "-X", "-n", "-j", job_id, "-o", "JobIDRaw,State", "-P"],
            timeout_seconds,
        )
    else:
        name = str(job.get("scheduler_job_name") or "")
        if not name:
            return []
        queue = run_scheduler(
            ["squeue", "-h", "-n", name, "-o", "%A|%T"], timeout_seconds
        )
        if queue is not None and queue.returncode == 0:
            rows = parse_rows(queue.stdout)
            if rows:
                return rows
        accounting_command = [
            "sacct", "-X", "-n", "--name", name, "-o", "JobIDRaw,State", "-P",
        ]
        # Without -S, sacct's default window starts at 00:00 today and a
        # next-day recovery of a lost Job ID silently matches nothing.
        start_time = sacct_start_time(job)
        if start_time:
            accounting_command += ["-S", start_time]
        accounting = run_scheduler(accounting_command, timeout_seconds)
    if accounting is None or accounting.returncode != 0:
        return None
    return parse_rows(accounting.stdout)


def resolve_run_dir(project_root: Path, token: str) -> Path:
    path = Path(token).expanduser()
    return path.resolve() if path.is_absolute() else (project_root / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to .research directory or project root")
    parser.add_argument("run_dir", nargs="?", help="Calculation directory containing the active pointer")
    parser.add_argument("--attempt", help="Explicit attempt ID instead of run_dir")
    parser.add_argument(
        "--mark",
        choices=("failed",),
        help="Operator resolution for an ambiguous pre-submission attempt",
    )
    parser.add_argument("--reason", help="Required audit reason with --mark")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm the operator resolution requested by --mark",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_SCHEDULER_TIMEOUT_SECONDS,
        help="Maximum seconds per scheduler query (default: 30)",
    )
    parser.add_argument("--now", help="ISO timestamp for deterministic tests")
    args = parser.parse_args()
    if not args.run_dir and not args.attempt:
        parser.error("provide run_dir or --attempt")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    if args.mark and (not args.confirm or not args.reason or not args.reason.strip()):
        parser.error("--mark requires both --reason and --confirm")
    if (args.reason or args.confirm) and not args.mark:
        parser.error("--reason and --confirm require --mark")

    research_dir, project_root = resolve(args.path)
    fail_if_invalid(research_dir)
    run_dir = resolve_run_dir(project_root, args.run_dir) if args.run_dir else None
    now = parse_time(args.now) if args.now else now_local()

    with project_state_lock(research_dir):
        if run_dir is not None:
            if not run_dir.is_dir():
                print(f"run directory does not exist: {run_dir}", file=sys.stderr)
                return 1
            lock_context = run_submission_lock(run_dir)
        else:
            from contextlib import nullcontext

            lock_context = nullcontext()
        with lock_context:
            job = (
                current_attempt(research_dir, run_dir)
                if run_dir is not None
                else load_job(research_dir, str(args.attempt))
            )
            if job is None:
                print("recorded job attempt was not found", file=sys.stderr)
                return 1
            if args.attempt and job.get("state") in ACTIVE_JOB_STATES:
                # Repair the crash window between the attempt record and the
                # run-dir pointer: restore the duplicate-submission guard for
                # an active attempt whose workdir still exists.
                workdir_token = job.get("workdir")
                if isinstance(workdir_token, str) and workdir_token:
                    workdir_path = (project_root / workdir_token).resolve()
                    pointer_path = active_pointer_path(workdir_path)
                    if workdir_path.is_dir() and not pointer_path.is_file():
                        write_active_pointer(workdir_path, job)
                        append_event(
                            research_dir,
                            {
                                "event": "job_pointer_restored",
                                "task_id": job.get("task_id"),
                                "lease_id": job.get("lease_id"),
                                "attempt_id": job.get("attempt_id"),
                                "workdir": workdir_token,
                                "created_at": iso(now),
                            },
                        )
                        print(f"restored active-attempt pointer in {workdir_token}")
            if args.mark:
                previous_state = str(job.get("state"))
                if previous_state not in {"submitting", "submission_unknown"}:
                    print(
                        "operator resolution is only allowed for submitting or "
                        f"submission_unknown attempts, not {previous_state}",
                        file=sys.stderr,
                    )
                    return 1
                job["state"] = args.mark
                job["updated_at"] = iso(now)
                job["submission_failed_at"] = iso(now)
                job["operator_resolution_reason"] = args.reason.strip()
                write_job(research_dir, job)
                append_event(
                    research_dir,
                    {
                        "event": "job_operator_resolved",
                        "task_id": job.get("task_id"),
                        "lease_id": job.get("lease_id"),
                        "attempt_id": job.get("attempt_id"),
                        "from": previous_state,
                        "to": args.mark,
                        "reason": args.reason.strip(),
                        "created_at": iso(now),
                    },
                )
                fail_if_invalid(research_dir)
                print(
                    f"resolved {job.get('attempt_id')} from {previous_state} "
                    f"to {args.mark}"
                )
                return 0

            if str(job.get("state")) == "submitting":
                created = job.get("created_at")
                age_seconds = None
                if isinstance(created, str) and created:
                    try:
                        age_seconds = (now - parse_time(created)).total_seconds()
                    except (ValueError, TypeError):
                        age_seconds = None
                if age_seconds is not None and age_seconds < SUBMITTING_GRACE_SECONDS:
                    print(
                        f"attempt {job.get('attempt_id')} is still submitting "
                        f"({age_seconds:.0f}s old); the submitter may be mid-sbatch. "
                        f"Retry reconcile after {SUBMITTING_GRACE_SECONDS:.0f}s "
                        "or resolve explicitly with --mark.",
                        file=sys.stderr,
                    )
                    return 2

            rows = scheduler_rows(job, args.timeout)
            if rows is None:
                print("scheduler query failed; attempt state was not changed", file=sys.stderr)
                return 2
            if not rows:
                print(
                    "scheduler has no matching queue or accounting record; attempt remains ambiguous",
                    file=sys.stderr,
                )
                if job.get("state") in {"submitting", "submission_unknown"}:
                    job["state"] = "submission_unknown"
                    job["updated_at"] = iso(now)
                    write_job(research_dir, job)
                return 2
            if len(rows) > 1:
                job["state"] = "submission_unknown"
                job["updated_at"] = iso(now)
                job["reconcile_note"] = "multiple scheduler jobs matched the submission identity"
                write_job(research_dir, job)
                print(
                    "multiple scheduler jobs matched this attempt; automatic retry remains blocked: "
                    + ",".join(job_id for job_id, _state in rows),
                    file=sys.stderr,
                )
                return 2

            job_id, slurm_state = rows[0]
            state = SLURM_STATE_MAP.get(slurm_state)
            if state is None:
                print(f"unrecognized Slurm state: {slurm_state}", file=sys.stderr)
                return 2
            previous_state = str(job.get("state"))
            job["job_id"] = job_id
            job["state"] = state
            job["scheduler_state"] = slurm_state
            job["updated_at"] = iso(now)
            write_job(research_dir, job)
            from lease_utils import load_current_lease

            lease = load_current_lease(research_dir, str(job.get("task_id")))
            if (
                lease
                and lease.get("status") == "active"
                and lease.get("lease_id") == job.get("lease_id")
            ):
                append_job_id_to_lease(
                    research_dir,
                    str(job.get("task_id")),
                    str(job.get("lease_id")),
                    str(job.get("owner_id")),
                    job_id,
                )
            append_event(
                research_dir,
                {
                    "event": "job_reconciled",
                    "task_id": job.get("task_id"),
                    "lease_id": job.get("lease_id"),
                    "attempt_id": job.get("attempt_id"),
                    "job_id": job_id,
                    "from": previous_state,
                    "to": state,
                    "created_at": iso(now),
                },
            )
            if previous_state in ACTIVE_JOB_STATES and state not in ACTIVE_JOB_STATES:
                append_event(
                    research_dir,
                    {
                        "event": "job_finished",
                        "task_id": job.get("task_id"),
                        "lease_id": job.get("lease_id"),
                        "attempt_id": job.get("attempt_id"),
                        "job_id": job_id,
                        "scheduler_state": slurm_state,
                        "created_at": iso(now),
                    },
                )

    fail_if_invalid(research_dir)
    print(
        f"reconciled {job.get('attempt_id')} job={job.get('job_id')} "
        f"state={job.get('state')}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
