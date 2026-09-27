#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML>=6.0"]
# ///
"""Safely submit one lease-bound Slurm job attempt and record its job ID."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from job_utils import (
    ACTIVE_JOB_STATES,
    SUBMITTING_GRACE_SECONDS,
    TERMINAL_JOB_STATES,
    active_attempts_for_workdir,
    append_job_id_to_lease,
    current_attempt,
    load_job,
    new_attempt_id,
    new_submission_id,
    project_relative,
    project_state_lock,
    require_active_lease,
    require_run_dir_owned,
    run_submission_lock,
    scheduler_job_name,
    write_active_pointer,
    write_job,
)
from lease_utils import (
    append_event,
    fail_if_invalid,
    iso,
    load_current_lease,
    now_local,
    parse_time,
    resolve,
)


DEFAULT_SCHEDULER_TIMEOUT_SECONDS = 30.0


def run_pre_submit_check(research_dir: Path, task_id: str) -> int:
    checker = Path(__file__).with_name("check_pre_submit.py")
    result = subprocess.run(
        [sys.executable, str(checker), str(research_dir), task_id],
        text=True,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return int(result.returncode)


def resolve_under(base: Path, token: str) -> Path:
    path = Path(token).expanduser()
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def parse_job_id(stdout: str) -> str | None:
    first_line = next((line.strip() for line in stdout.splitlines() if line.strip()), "")
    job_id = first_line.split(";", 1)[0].strip()
    return job_id if job_id.isdigit() else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to .research directory or project root")
    parser.add_argument("task_id", help="Claimed execution task ID")
    parser.add_argument("run_dir", help="Project-relative calculation directory")
    parser.add_argument("--script", default="job.sh", help="Job script relative to run_dir")
    parser.add_argument("--owner", required=True, help="Active lease owner ID")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_SCHEDULER_TIMEOUT_SECONDS,
        help="Maximum seconds to wait for sbatch (default: 30)",
    )
    parser.add_argument("--now", help="ISO timestamp for deterministic tests")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    if args.timeout >= SUBMITTING_GRACE_SECONDS:
        parser.error(
            "--timeout must stay below the reconcile submitting-grace period "
            f"({SUBMITTING_GRACE_SECONDS:g}s), or a live sbatch could be "
            "reconciled as abandoned"
        )

    research_dir, project_root = resolve(args.path)
    fail_if_invalid(research_dir)
    if run_pre_submit_check(research_dir, args.task_id) != 0:
        return 1

    run_dir = resolve_under(project_root, args.run_dir)
    if not run_dir.is_dir():
        print(f"run directory does not exist: {run_dir}", file=sys.stderr)
        return 1
    script = resolve_under(run_dir, args.script)
    if not script.is_file():
        print(f"job script does not exist: {script}", file=sys.stderr)
        return 1
    try:
        script.relative_to(run_dir)
    except ValueError:
        print(f"job script escapes run directory: {script}", file=sys.stderr)
        return 1

    now = parse_time(args.now) if args.now else now_local()
    with project_state_lock(research_dir):
        fail_if_invalid(research_dir)
        if run_pre_submit_check(research_dir, args.task_id) != 0:
            return 1
        lease = require_active_lease(research_dir, args.task_id, args.owner)
        run_dir_token = require_run_dir_owned(project_root, run_dir, lease)
        script_token = project_relative(script, project_root)
        with run_submission_lock(run_dir):
            previous = current_attempt(research_dir, run_dir)
            # Guard on the authoritative records, not the pointer: a lost
            # pointer (crash window, archived dir) must not disable
            # duplicate-submission protection.
            active_conflicts = active_attempts_for_workdir(research_dir, run_dir_token)
            if active_conflicts:
                conflict = active_conflicts[0]
                print(
                    "job submission blocked: active or ambiguous attempt "
                    f"{conflict.get('attempt_id')} state={conflict.get('state')} "
                    f"job_id={conflict.get('job_id') or 'not-recorded'}",
                    file=sys.stderr,
                )
                if current_attempt(research_dir, run_dir) is None:
                    print(
                        "the run-dir pointer is missing for this active attempt; "
                        "restore it with reconcile_jobs.py --attempt "
                        f"{conflict.get('attempt_id')}",
                        file=sys.stderr,
                    )
                return 1

            attempt_id = new_attempt_id()
            submission_id = new_submission_id()
            job_name = scheduler_job_name(submission_id)
            job = {
                "schema_version": 1,
                "attempt_id": attempt_id,
                "submission_id": submission_id,
                "task_id": args.task_id,
                "lease_id": lease.get("lease_id"),
                "owner_id": args.owner,
                "scheduler": "slurm",
                "scheduler_job_name": job_name,
                "job_id": None,
                "state": "submitting",
                "workdir": run_dir_token,
                "script": script_token,
                "parent_attempt_id": previous.get("attempt_id") if previous else None,
                "created_at": iso(now),
                "updated_at": iso(now),
            }
            write_job(research_dir, job)
            write_active_pointer(run_dir, job)

    # sbatch runs OUTSIDE both locks: the recorded `submitting` attempt already
    # blocks duplicate submissions for this workdir, and holding the project
    # state lock across a slow scheduler call would stall every other task's
    # claim/heartbeat/release/reconcile behind controller latency.
    command = [
        "sbatch",
        "--parsable",
        f"--job-name={job_name}",
        f"--chdir={run_dir}",
        str(script),
    ]
    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=args.timeout,
        )
    except subprocess.TimeoutExpired as exc:
        result = None
        error_summary = f"sbatch timed out after {args.timeout:g} seconds"
        if exc.stderr:
            error_summary += f": {str(exc.stderr).strip()[:400]}"
    except OSError as exc:
        result = None
        error_summary = str(exc)
    else:
        error_summary = (result.stderr or result.stdout).strip()[:500]

    parsed_job_id = parse_job_id(result.stdout) if result is not None else None
    explicit_rejection = bool(
        result is not None
        and result.returncode != 0
        and result.stderr.strip()
        and parsed_job_id is None
    )
    job_id = (
        parsed_job_id
        if result is not None and result.returncode == 0
        else None
    )

    finalize_now = parse_time(args.now) if args.now else now_local()
    with project_state_lock(research_dir):
        # Re-read the record: a reconcile or an operator may have touched it
        # while sbatch ran.
        job = load_job(research_dir, attempt_id) or job
        reloaded_state = str(job.get("state"))
        if reloaded_state != "submitting":
            # The attempt was advanced or resolved during the sbatch window.
            # That decision wins - finalize must never resurrect a resolved
            # attempt. Record the scheduler identity so a real job is not lost.
            if job_id is not None and not job.get("job_id"):
                job["job_id"] = job_id
                job["updated_at"] = iso(finalize_now)
                write_job(research_dir, job)
            append_event(
                research_dir,
                {
                    "event": "job_submission_conflict",
                    "task_id": args.task_id,
                    "lease_id": lease.get("lease_id"),
                    "attempt_id": attempt_id,
                    "job_id": job_id,
                    "recorded_state": reloaded_state,
                    "created_at": iso(finalize_now),
                },
            )
            if job_id is not None and reloaded_state in TERMINAL_JOB_STATES:
                print(
                    f"submission conflict: attempt {attempt_id} was resolved to "
                    f"`{reloaded_state}` while sbatch ran, but sbatch created Slurm "
                    f"job {job_id}. Verify with squeue/sacct and `scancel {job_id}` "
                    "if it is an orphan.",
                    file=sys.stderr,
                )
            else:
                print(
                    f"submission conflict: attempt {attempt_id} advanced to "
                    f"`{reloaded_state}` during submission; the record was left "
                    "as-is.",
                    file=sys.stderr,
                )
            return 1
        if explicit_rejection:
            job["state"] = "failed"
            job["submission_failed_at"] = iso(finalize_now)
            job["updated_at"] = iso(finalize_now)
            job["scheduler_returncode"] = result.returncode
            if error_summary:
                job["error_summary"] = error_summary
            write_job(research_dir, job)
            append_event(
                research_dir,
                {
                    "event": "job_submission_failed",
                    "task_id": args.task_id,
                    "lease_id": lease.get("lease_id"),
                    "attempt_id": attempt_id,
                    "returncode": result.returncode,
                    "created_at": iso(finalize_now),
                },
            )
            print(
                "job submission was rejected by sbatch; this attempt is terminal "
                f"and may be retried safely: {error_summary or f'exit {result.returncode}'}",
                file=sys.stderr,
            )
            return 1

        if job_id is None:
            job["state"] = "submission_unknown"
            job["updated_at"] = iso(finalize_now)
            if error_summary:
                job["error_summary"] = error_summary
            write_job(research_dir, job)
            append_event(
                research_dir,
                {
                    "event": "job_submission_unknown",
                    "task_id": args.task_id,
                    "lease_id": lease.get("lease_id"),
                    "attempt_id": attempt_id,
                    "created_at": iso(finalize_now),
                },
            )
            print(
                "job submission result is unknown; automatic retry is blocked. "
                f"Reconcile attempt {attempt_id} before retrying.",
                file=sys.stderr,
            )
            return 1

        job["job_id"] = job_id
        job["state"] = "pending"
        job["submitted_at"] = iso(finalize_now)
        job["updated_at"] = iso(finalize_now)
        write_job(research_dir, job)
        lease_now = load_current_lease(research_dir, args.task_id)
        if (
            lease_now
            and lease_now.get("status") == "active"
            and lease_now.get("lease_id") == lease.get("lease_id")
        ):
            append_job_id_to_lease(
                research_dir,
                args.task_id,
                str(lease.get("lease_id")),
                args.owner,
                job_id,
            )
        else:
            print(
                "warning: lease changed during submission; the Job ID is recorded "
                "on the attempt but was not bound to a lease",
                file=sys.stderr,
            )
        append_event(
            research_dir,
            {
                "event": "job_submitted",
                "task_id": args.task_id,
                "lease_id": lease.get("lease_id"),
                "attempt_id": attempt_id,
                "job_id": job_id,
                "workdir": run_dir_token,
                "created_at": iso(finalize_now),
            },
        )

    fail_if_invalid(research_dir)
    print(f"submitted {attempt_id} as Slurm job {job_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
