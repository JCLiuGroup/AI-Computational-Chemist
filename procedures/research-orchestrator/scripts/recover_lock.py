#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML>=6.0"]
# ///
"""Explicitly recover a stale project-state or run-directory lock."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from job_utils import project_state_lock, recover_directory_lock
from lease_utils import append_event, iso, now_local, parse_time, resolve


def resolve_run_dir(project_root: Path, token: str) -> Path:
    path = Path(token).expanduser()
    resolved = path.resolve() if path.is_absolute() else (project_root / path).resolve()
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise SystemExit(f"run directory escapes project root: {resolved}") from exc
    return resolved


def append_recovery_event(
    research_dir: Path,
    lock_path: Path,
    purpose: str,
    status: str,
    owner: dict[str, object] | None,
    reason: str,
    forced: bool,
    created_at: str,
) -> None:
    append_event(
        research_dir,
        {
            "event": "lock_recovered",
            "lock": lock_path.as_posix(),
            "purpose": purpose,
            "prior_status": status,
            "prior_owner": owner,
            "reason": reason,
            "forced": forced,
            "created_at": created_at,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to a project or .research directory")
    parser.add_argument(
        "run_dir",
        nargs="?",
        help="Run directory lock to recover; omit to recover the project-state lock",
    )
    parser.add_argument("--reason", required=True, help="Audit reason for lock recovery")
    parser.add_argument(
        "--confirm", action="store_true", help="Confirm that the lock should be removed"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow recovery when the owner host/PID cannot be verified",
    )
    parser.add_argument("--now", help="ISO timestamp for deterministic tests")
    args = parser.parse_args()
    if not args.confirm:
        parser.error("lock recovery requires --confirm")
    if not args.reason.strip():
        parser.error("--reason must not be empty")

    research_dir, project_root = resolve(args.path)
    created_at = iso(parse_time(args.now) if args.now else now_local())

    if args.run_dir:
        run_dir = resolve_run_dir(project_root, args.run_dir)
        lock_path = run_dir / ".aicc-submit.lock"
        with project_state_lock(research_dir):
            status, owner = recover_directory_lock(
                lock_path, "job submission", force=args.force
            )
            append_recovery_event(
                research_dir,
                lock_path,
                "job submission",
                status,
                owner,
                args.reason.strip(),
                args.force,
                created_at,
            )
    else:
        lock_path = research_dir / ".locks" / "state.lock"
        status, owner = recover_directory_lock(
            lock_path, "project state", force=args.force
        )
        with project_state_lock(research_dir):
            append_recovery_event(
                research_dir,
                lock_path,
                "project state",
                status,
                owner,
                args.reason.strip(),
                args.force,
                created_at,
            )

    print(f"recovered {purpose_label(args.run_dir)} lock: {lock_path}")
    return 0


def purpose_label(run_dir: str | None) -> str:
    return "job submission" if run_dir else "project state"


if __name__ == "__main__":
    sys.exit(main())
