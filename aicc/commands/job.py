"""Submit and inspect lease-bound scheduler job attempts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from core.paths import orchestrator_scripts_dir
from job_utils import ACTIVE_JOB_STATES, load_jobs
from lease_utils import resolve


def run_helper(script_name: str, arguments: list[str]) -> int:
    script = orchestrator_scripts_dir() / script_name
    if not script.is_file():
        print(f"aicc job: helper is missing: {script}", file=sys.stderr)
        return 1
    result = subprocess.run([sys.executable, str(script), *arguments])
    return int(result.returncode)


def register(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "job",
        help="Submit, inspect, and reconcile lease-bound scheduler jobs",
    )
    commands = parser.add_subparsers(dest="job_command", required=True)

    submit = commands.add_parser("submit", help="Safely submit one Slurm job attempt")
    submit.add_argument("path", help="Project or .research path")
    submit.add_argument("task_id", help="Claimed execution task ID")
    submit.add_argument("run_dir", help="Project-relative calculation directory")
    submit.add_argument("--script", default="job.sh", help="Job script relative to run_dir")
    submit.add_argument("--owner", required=True, help="Active lease owner ID")
    submit.add_argument(
        "--timeout", type=float, default=30.0, help="Maximum seconds to wait for sbatch"
    )
    submit.add_argument("--now", help="ISO timestamp for deterministic operation")
    submit.set_defaults(handler=run_submit)

    status = commands.add_parser("status", help="Show recorded job attempts without scheduler queries")
    status.add_argument(
        "path", nargs="?", default=".", help="Project or .research path (default: current directory)"
    )
    status.add_argument("--active", action="store_true", help="Show only non-terminal attempts")
    status.add_argument("--json", action="store_true", help="Emit machine-readable output")
    status.set_defaults(handler=run_status)

    reconcile = commands.add_parser("reconcile", help="Reconcile one attempt with Slurm")
    reconcile.add_argument("path", help="Project or .research path")
    reconcile.add_argument("run_dir", nargs="?", help="Calculation directory containing the active pointer")
    reconcile.add_argument("--attempt", help="Explicit attempt ID instead of run_dir")
    reconcile.add_argument(
        "--mark",
        choices=("failed",),
        help="Operator resolution for an ambiguous pre-submission attempt",
    )
    reconcile.add_argument("--reason", help="Required audit reason with --mark")
    reconcile.add_argument("--confirm", action="store_true", help="Confirm --mark")
    reconcile.add_argument(
        "--timeout", type=float, default=30.0, help="Maximum seconds per scheduler query"
    )
    reconcile.add_argument("--now", help="ISO timestamp for deterministic operation")
    reconcile.set_defaults(handler=run_reconcile)

    unlock = commands.add_parser("unlock", help="Recover a stale AICC state lock")
    unlock.add_argument("path", help="Project or .research path")
    unlock.add_argument(
        "run_dir",
        nargs="?",
        help="Run-directory lock to recover; omit for the project-state lock",
    )
    unlock.add_argument("--reason", required=True, help="Audit reason for recovery")
    unlock.add_argument("--confirm", action="store_true", help="Confirm lock removal")
    unlock.add_argument(
        "--force",
        action="store_true",
        help="Recover a lock whose remote or missing owner cannot be verified",
    )
    unlock.add_argument("--now", help="ISO timestamp for deterministic operation")
    unlock.set_defaults(handler=run_unlock)


def run_submit(args: argparse.Namespace) -> int:
    arguments = [
        args.path,
        args.task_id,
        args.run_dir,
        "--script",
        args.script,
        "--owner",
        args.owner,
        "--timeout",
        str(args.timeout),
    ]
    if args.now:
        arguments.extend(["--now", args.now])
    return run_helper("submit_job.py", arguments)


def job_sort_key(job: dict[str, Any]) -> tuple[str, str]:
    return str(job.get("created_at") or ""), str(job.get("attempt_id") or "")


def run_status(args: argparse.Namespace) -> int:
    research_dir, _project_root = resolve(args.path)
    jobs = sorted(load_jobs(research_dir), key=job_sort_key)
    if args.active:
        jobs = [job for job in jobs if job.get("state") in ACTIVE_JOB_STATES]
    if args.json:
        print(
            json.dumps(
                {"schema_version": 1, "research_dir": research_dir.as_posix(), "jobs": jobs},
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if not jobs:
        print("No recorded jobs.")
        return 0
    for job in jobs:
        print(
            f"{job.get('attempt_id')}  task={job.get('task_id')}  "
            f"job={job.get('job_id') or 'not-recorded'}  state={job.get('state')}  "
            f"workdir={job.get('workdir')}"
        )
    return 0


def run_reconcile(args: argparse.Namespace) -> int:
    arguments = [args.path]
    if args.run_dir:
        arguments.append(args.run_dir)
    if args.attempt:
        arguments.extend(["--attempt", args.attempt])
    if args.mark:
        arguments.extend(["--mark", args.mark])
    if args.reason:
        arguments.extend(["--reason", args.reason])
    if args.confirm:
        arguments.append("--confirm")
    arguments.extend(["--timeout", str(args.timeout)])
    if args.now:
        arguments.extend(["--now", args.now])
    return run_helper("reconcile_jobs.py", arguments)


def run_unlock(args: argparse.Namespace) -> int:
    arguments = [args.path, "--reason", args.reason]
    if args.run_dir:
        arguments.insert(1, args.run_dir)
    if args.confirm:
        arguments.append("--confirm")
    if args.force:
        arguments.append("--force")
    if args.now:
        arguments.extend(["--now", args.now])
    return run_helper("recover_lock.py", arguments)
