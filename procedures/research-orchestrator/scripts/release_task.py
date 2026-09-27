#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML>=6.0"]
# ///
"""Release an active task lease and set the task's execution status."""

from __future__ import annotations

import argparse
import sys

from job_utils import active_jobs_for_lease, project_state_lock
from lease_utils import (
    append_event,
    fail_if_invalid,
    iso,
    lease_path,
    load_current_lease,
    load_tasks,
    now_local,
    parse_time,
    resolve,
    write_json_atomic,
    write_task,
)


ALLOWED_RELEASE_STATUSES = {"completed", "validated", "blocked", "failed", "cancelled"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to .research directory or project root")
    parser.add_argument("task_id", help="Task ID to release")
    parser.add_argument("--status", required=True, choices=sorted(ALLOWED_RELEASE_STATUSES))
    parser.add_argument("--owner", help="If provided, require the lease owner to match")
    parser.add_argument("--note", help="Short release note")
    parser.add_argument("--now", help="ISO timestamp for deterministic tests")
    args = parser.parse_args()

    research_dir, _project_root = resolve(args.path)
    fail_if_invalid(research_dir)
    with project_state_lock(research_dir):
        fail_if_invalid(research_dir)
        tasks = load_tasks(research_dir)
        task = tasks.get(args.task_id)
        if task is None:
            print(f"missing task: {args.task_id}", file=sys.stderr)
            return 1
        lease = load_current_lease(research_dir, args.task_id)
        if not lease or lease.get("status") != "active":
            print(f"task has no active lease: {args.task_id}", file=sys.stderr)
            return 1
        if args.owner and lease.get("owner_id") != args.owner:
            print(f"lease owner mismatch: {lease.get('owner_id')} != {args.owner}", file=sys.stderr)
            return 1
        active_jobs = active_jobs_for_lease(research_dir, str(lease.get("lease_id")))
        if active_jobs:
            attempts = ", ".join(
                f"{job.get('attempt_id')}({job.get('state')})" for job in active_jobs
            )
            print(
                f"cannot release lease while scheduler attempts are active or ambiguous: {attempts}",
                file=sys.stderr,
            )
            return 1
        now = parse_time(args.now) if args.now else now_local()
        old_status = task.get("status")
        task["status"] = args.status
        lease["status"] = "cancelled" if args.status == "cancelled" else "released"
        lease["released_at"] = iso(now)
        lease["release_status"] = args.status
        if args.note:
            lease["notes"] = args.note
        write_json_atomic(lease_path(research_dir, args.task_id), lease)
        write_task(research_dir, task)
        append_event(
            research_dir,
            {
                "event": "task_released",
                "task_id": args.task_id,
                "lease_id": lease.get("lease_id"),
                "owner_id": lease.get("owner_id"),
                "release_status": args.status,
                "created_at": iso(now),
            },
        )
        append_event(
            research_dir,
            {
                "event": "status_changed",
                "task_id": args.task_id,
                "from": old_status,
                "to": args.status,
                "lease_id": lease.get("lease_id"),
                "created_at": iso(now),
            },
        )
    fail_if_invalid(research_dir)
    print(f"released {args.task_id} as {args.status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
