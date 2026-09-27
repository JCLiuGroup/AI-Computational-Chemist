"""Inspect and advance research-orchestrator tasks through existing helpers."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from commands.status import build_status, format_lease
from core.paths import orchestrator_scripts_dir
from lease_utils import now_local, parse_time
from validate_state import load_validated_state


RELEASE_STATUSES = ("blocked", "cancelled", "completed", "failed", "validated")


def add_task_target(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project or .research path (default: current directory)",
    )
    parser.add_argument("task_id", help="Task ID, for example T007")


def run_helper(script_name: str, arguments: list[str]) -> int:
    """Run a canonical orchestrator helper without adding another uv startup."""

    script = orchestrator_scripts_dir() / script_name
    if not script.is_file():
        print(f"aicc task: helper is missing: {script}", file=sys.stderr)
        return 1
    result = subprocess.run([sys.executable, str(script), *arguments])
    return int(result.returncode)


def append_option(arguments: list[str], name: str, value: object | None) -> None:
    if value is not None:
        arguments.extend([name, str(value)])


def register(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "task",
        help="Inspect readiness and manage task execution leases",
        description=(
            "Inspect or advance research-orchestrator tasks. Mutating commands reuse "
            "the canonical lease and event helpers; they do not bypass readiness or "
            "validation gates."
        ),
    )
    commands = parser.add_subparsers(dest="task_command", required=True)

    ready = commands.add_parser("ready", help="List derived ready and blocked tasks")
    ready.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project or .research path (default: current directory)",
    )
    ready.add_argument("--json", action="store_true", help="Emit machine-readable output")
    ready.set_defaults(handler=run_ready)

    show = commands.add_parser("show", help="Show one task and its derived state")
    add_task_target(show)
    show.add_argument("--json", action="store_true", help="Emit machine-readable output")
    show.add_argument("--now", help="ISO timestamp for deterministic lease-age checks")
    show.set_defaults(handler=run_show)

    check = commands.add_parser(
        "check", help="Run a task's declared deterministic required checks"
    )
    add_task_target(check)
    check.add_argument("--dry-run", action="store_true", help="Print checks without running")
    check.add_argument("--now", help="ISO timestamp for deterministic event records")
    check.set_defaults(handler=run_check)

    claim = commands.add_parser(
        "claim", help="Claim a ready single-owner task and create its lease"
    )
    add_task_target(claim)
    claim.add_argument("--owner", help="Owner ID recorded in the lease")
    claim.add_argument("--lease-id", help="Explicit lease ID")
    claim.add_argument("--now", help="ISO timestamp for deterministic operation")
    claim.set_defaults(handler=run_claim)

    heartbeat = commands.add_parser(
        "heartbeat", help="Refresh an active task lease heartbeat"
    )
    add_task_target(heartbeat)
    heartbeat.add_argument("--owner", help="Require the active lease owner to match")
    heartbeat.add_argument("--now", help="ISO timestamp for deterministic operation")
    heartbeat.set_defaults(handler=run_heartbeat)

    release = commands.add_parser(
        "release", help="Release an active lease and set the execution status"
    )
    add_task_target(release)
    release.add_argument("--status", required=True, choices=RELEASE_STATUSES)
    release.add_argument("--owner", help="Require the active lease owner to match")
    release.add_argument("--note", help="Short release note")
    release.add_argument("--now", help="ISO timestamp for deterministic operation")
    release.set_defaults(handler=run_release)

    reconcile = commands.add_parser(
        "reconcile", help="Report stale leases or mark them stale after review"
    )
    reconcile.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project or .research path (default: current directory)",
    )
    reconcile.add_argument(
        "--mark-stale",
        action="store_true",
        help="Mark expired leases stale and block their tasks",
    )
    reconcile.add_argument("--now", help="ISO timestamp for deterministic operation")
    reconcile.set_defaults(handler=run_reconcile)


def run_ready(args: argparse.Namespace) -> int:
    arguments = [args.path]
    if args.json:
        arguments.append("--json")
    return run_helper("ready_tasks.py", arguments)


def task_payload(path: Path, task_id: str, now: str | None) -> dict[str, Any] | None:
    observed_at = parse_time(now) if now else now_local()
    snapshot = build_status(path, observed_at=observed_at, event_limit=0)
    rows = [row for row in snapshot["tasks"] if row.get("task_id") == task_id]
    if not rows:
        return None
    state, _findings = load_validated_state(path)
    row = rows[0]
    return {
        "schema_version": 1,
        "research_dir": snapshot["research_dir"],
        "project": snapshot["project"],
        "task": state.tasks[task_id],
        "derived": {
            "readiness": row.get("readiness"),
            "action": row.get("action"),
            "blockers": row.get("blockers") or [],
            "lease": row.get("lease"),
        },
        "validation": snapshot["validation"],
    }


def print_values(label: str, values: object) -> None:
    if not isinstance(values, list) or not values:
        return
    print(f"{label}")
    for value in values:
        if isinstance(value, dict):
            print(f"  - {json.dumps(value, sort_keys=True)}")
        else:
            print(f"  - {value}")


def emit_task(payload: dict[str, Any]) -> None:
    task = payload["task"]
    derived = payload["derived"]
    print(f"{task.get('id')}  {task.get('title', '')}")
    print(
        f"status={task.get('status')}  action={derived.get('action')}  "
        f"readiness={derived.get('readiness')}"
    )
    print(
        f"role={task.get('role')}  skill={task.get('skill')}  "
        f"approval={task.get('approval')}"
    )
    depends_on = task.get("depends_on") or []
    print(f"depends_on={','.join(map(str, depends_on)) if depends_on else '<none>'}")
    lease = derived.get("lease")
    if isinstance(lease, dict):
        print(f"lease: {format_lease(lease)}")
    print_values("BLOCKERS", derived.get("blockers"))
    print_values("REQUIRED REFS", task.get("required_refs"))
    print_values("REQUIRED CHECKS", task.get("required_checks"))
    print_values("SUCCESS CRITERIA", task.get("success_criteria"))


def run_show(args: argparse.Namespace) -> int:
    try:
        payload = task_payload(Path(args.path), args.task_id, args.now)
    except (TypeError, ValueError) as exc:
        print(f"aicc task show: invalid --now value: {exc}", file=sys.stderr)
        return 2
    if payload is None:
        print(f"unknown task: {args.task_id}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        emit_task(payload)
    return 0 if payload["validation"]["valid"] else 1


def run_check(args: argparse.Namespace) -> int:
    arguments = [args.path, args.task_id]
    if args.dry_run:
        arguments.append("--dry-run")
    append_option(arguments, "--now", args.now)
    return run_helper("run_required_checks.py", arguments)


def run_claim(args: argparse.Namespace) -> int:
    arguments = [args.path, args.task_id]
    append_option(arguments, "--owner", args.owner)
    append_option(arguments, "--lease-id", args.lease_id)
    append_option(arguments, "--now", args.now)
    return run_helper("claim_task.py", arguments)


def run_heartbeat(args: argparse.Namespace) -> int:
    arguments = [args.path, args.task_id]
    append_option(arguments, "--owner", args.owner)
    append_option(arguments, "--now", args.now)
    return run_helper("heartbeat_task.py", arguments)


def run_release(args: argparse.Namespace) -> int:
    arguments = [args.path, args.task_id, "--status", args.status]
    append_option(arguments, "--owner", args.owner)
    append_option(arguments, "--note", args.note)
    append_option(arguments, "--now", args.now)
    return run_helper("release_task.py", arguments)


def run_reconcile(args: argparse.Namespace) -> int:
    arguments = [args.path]
    if args.mark_stale:
        arguments.append("--mark-stale")
    append_option(arguments, "--now", args.now)
    return run_helper("reconcile_leases.py", arguments)
