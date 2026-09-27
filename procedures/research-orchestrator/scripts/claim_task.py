#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML>=6.0"]
# ///
"""Claim a ready task by creating an active execution lease."""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta

from job_utils import project_state_lock
from lease_utils import (
    append_event,
    archive_released_current_lease,
    assert_no_active_conflict,
    default_owner_id,
    exclusive_paths,
    fail_if_invalid,
    iso,
    lease_id_for,
    lease_path,
    load_tasks,
    now_local,
    owner_dir,
    parse_time,
    resolve,
    task_requires_claim,
    ttl_minutes,
    write_json_atomic,
    write_task,
)
from ready_tasks import derive_ready


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to .research directory or project root")
    parser.add_argument("task_id", help="Task ID to claim")
    parser.add_argument("--owner", default=default_owner_id(), help="Owner ID recorded in the lease")
    parser.add_argument("--lease-id", help="Explicit lease ID; defaults to L-<task>-<timestamp>")
    parser.add_argument("--now", help="ISO timestamp for deterministic tests")
    args = parser.parse_args()

    research_dir, project_root = resolve(args.path)
    fail_if_invalid(research_dir)
    with project_state_lock(research_dir):
        fail_if_invalid(research_dir)
        tasks = load_tasks(research_dir)
        task = tasks.get(args.task_id)
        if task is None:
            print(f"missing task: {args.task_id}", file=sys.stderr)
            return 1
        if not task_requires_claim(task):
            print(f"task does not declare execution_policy.requires_claim: {args.task_id}", file=sys.stderr)
            return 1

        ready, blocked, findings = derive_ready(research_dir)
        if findings:
            print("state is invalid", file=sys.stderr)
            return 1
        ready_ids = {item.task_id for item in ready}
        if args.task_id not in ready_ids:
            reasons = []
            for item in blocked:
                if item.task_id == args.task_id:
                    reasons = item.reasons
                    break
            print(f"task is not ready to claim: {args.task_id}", file=sys.stderr)
            if reasons:
                print("; ".join(reasons), file=sys.stderr)
            return 1

        paths = exclusive_paths(task)
        assert_no_active_conflict(research_dir, project_root, args.task_id, paths)
        now = parse_time(args.now) if args.now else now_local()
        ttl = ttl_minutes(task)
        lease_id = args.lease_id or lease_id_for(args.task_id, now)
        archive_released_current_lease(research_dir, args.task_id)
        lease = {
            "schema_version": 1,
            "lease_id": lease_id,
            "task_id": args.task_id,
            "owner_id": args.owner,
            "role": task.get("role"),
            "status": "active",
            "acquired_at": iso(now),
            "heartbeat_at": iso(now),
            "expires_at": iso(now + timedelta(minutes=ttl)),
            "owner_dir": owner_dir(task),
            "exclusive_paths": paths,
            "job_ids": [],
        }
        old_status = task.get("status")
        task["status"] = "running"
        write_json_atomic(lease_path(research_dir, args.task_id), lease)
        write_task(research_dir, task)
        append_event(
            research_dir,
            {
                "event": "task_claimed",
                "task_id": args.task_id,
                "lease_id": lease_id,
                "owner_id": args.owner,
                "created_at": iso(now),
            },
        )
        append_event(
            research_dir,
            {
                "event": "status_changed",
                "task_id": args.task_id,
                "from": old_status,
                "to": "running",
                "lease_id": lease_id,
                "created_at": iso(now),
            },
        )
    fail_if_invalid(research_dir)
    print(f"claimed {args.task_id} with {lease_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
