#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML>=6.0"]
# ///
"""Refresh the heartbeat for an active task lease."""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta

from job_utils import project_state_lock
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
    ttl_minutes,
    write_json_atomic,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to .research directory or project root")
    parser.add_argument("task_id", help="Task ID to heartbeat")
    parser.add_argument("--owner", help="If provided, require the lease owner to match")
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
        now = parse_time(args.now) if args.now else now_local()
        lease["heartbeat_at"] = iso(now)
        lease["expires_at"] = iso(now + timedelta(minutes=ttl_minutes(task)))
        write_json_atomic(lease_path(research_dir, args.task_id), lease)
        append_event(
            research_dir,
            {
                "event": "task_heartbeat",
                "task_id": args.task_id,
                "lease_id": lease.get("lease_id"),
                "owner_id": lease.get("owner_id"),
                "created_at": iso(now),
            },
        )
    fail_if_invalid(research_dir)
    print(f"heartbeat {args.task_id} until {lease['expires_at']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
