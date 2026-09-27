"""Read-only ``aicc status`` command implementation.

The ``status`` command derives a read-only project snapshot from ``.research/`` and
never updates tasks, leases, artifacts, decisions, or events.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from job_utils import ACTIVE_JOB_STATES, load_jobs
from lease_utils import now_local, parse_time
from ready_tasks import derive_ready_from_state
from validate_state import load_json_file, load_validated_state


TASK_STATUS_ORDER = [
    "proposed",
    "approved",
    "running",
    "completed",
    "validated",
    "accepted",
    "blocked",
    "failed",
    "cancelled",
]
FINISHED_TASK_STATUSES = {"accepted", "cancelled"}
SUMMARY_BLOCKED_LIMIT = 10


def positive_interval(value: str) -> float:
    interval = float(value)
    if not math.isfinite(interval) or interval <= 0:
        raise argparse.ArgumentTypeError(
            "watch interval must be a finite number greater than zero"
        )
    return interval


def natural_sort_key(value: object) -> tuple[tuple[int, object], ...]:
    """Sort task IDs naturally, so T2 appears before T10."""

    return tuple(
        (0, int(token)) if token.isdigit() else (1, token.casefold())
        for token in re.split(r"(\d+)", str(value))
        if token
    )


def task_requires_claim(task: dict[str, Any]) -> bool:
    policy = task.get("execution_policy")
    return isinstance(policy, dict) and policy.get("requires_claim") is True


def parse_optional_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return parse_time(value)
    except (TypeError, ValueError):
        return None


def seconds_between(later: datetime, earlier: datetime | None) -> int | None:
    if earlier is None:
        return None
    try:
        return int((later - earlier).total_seconds())
    except TypeError:  # aware/naive timestamps cannot be compared safely
        return None


def human_duration(seconds: int | None) -> str:
    if seconds is None:
        return "unknown"
    seconds = max(0, seconds)
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def normalize_job_ids(value: object) -> list[str]:
    if isinstance(value, (str, int)):
        return [str(value)]
    if isinstance(value, list):
        return [str(item) for item in value if isinstance(item, (str, int))]
    return []


def load_active_leases(
    research_dir: Path, observed_at: datetime
) -> list[dict[str, Any]]:
    leases_dir = research_dir / "leases"
    if not leases_dir.is_dir():
        return []
    leases: list[dict[str, Any]] = []
    for path in sorted(leases_dir.glob("*.json")):
        lease = load_json_file(path, [], research_dir)
        if lease.get("status") != "active":
            continue
        heartbeat = parse_optional_time(lease.get("heartbeat_at"))
        expires = parse_optional_time(lease.get("expires_at"))
        heartbeat_age = seconds_between(observed_at, heartbeat)
        expires_in = (
            seconds_between(expires, observed_at) if expires is not None else None
        )
        stale = expires_in is not None and expires_in < 0
        leases.append(
            {
                "task_id": lease.get("task_id"),
                "lease_id": lease.get("lease_id"),
                "owner_id": lease.get("owner_id"),
                "state": "stale" if stale else "active",
                "heartbeat_at": lease.get("heartbeat_at"),
                "heartbeat_age_seconds": heartbeat_age,
                "expires_at": lease.get("expires_at"),
                "expires_in_seconds": expires_in,
                "job_ids": normalize_job_ids(lease.get("job_ids")),
                "owner_dir": lease.get("owner_dir"),
                "source": path.relative_to(research_dir).as_posix(),
            }
        )
    return leases


def task_status_counts(tasks: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(task.get("status", "unknown")) for task in tasks.values())
    ordered = {status: counts.pop(status, 0) for status in TASK_STATUS_ORDER}
    ordered.update({status: counts[status] for status in sorted(counts)})
    return ordered


def artifact_status_counts(artifacts: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(artifact.get("status", "unknown")) for artifact in artifacts)
    return {status: counts[status] for status in sorted(counts)}


def derive_action(status: object, readiness: str) -> str:
    if status in {"accepted", "cancelled"}:
        return "done"
    if status == "running":
        return "active"
    if status == "completed":
        return "validate"
    if status == "validated":
        return "accept"
    if status == "failed":
        return "attention"
    if status == "blocked" or readiness == "blocked":
        return "blocked"
    if readiness == "ready":
        return "ready"
    return "waiting"


def build_status(
    path: Path, *, observed_at: datetime, event_limit: int
) -> dict[str, Any]:
    state, findings = load_validated_state(path)
    research_dir = state.research_dir
    failures = [finding for finding in findings if finding.level == "FAIL"]

    project = state.project
    tasks = state.tasks
    artifacts = state.artifacts
    events = state.events

    ready_by_id: dict[str, dict[str, Any]] = {}
    blocked_by_id: dict[str, dict[str, Any]] = {}
    if not failures:
        ready, blocked = derive_ready_from_state(state)
        ready_by_id = {item.task_id: item.__dict__ for item in ready}
        blocked_by_id = {item.task_id: item.__dict__ for item in blocked}

    leases = load_active_leases(research_dir, observed_at)
    lease_by_task = {
        str(lease["task_id"]): lease
        for lease in leases
        if isinstance(lease.get("task_id"), str)
    }
    try:
        jobs = load_jobs(research_dir)
    except SystemExit:
        jobs = []
    jobs_by_task: dict[str, list[dict[str, Any]]] = {}
    for job in jobs:
        task_id = job.get("task_id")
        if isinstance(task_id, str):
            jobs_by_task.setdefault(task_id, []).append(job)

    task_rows: list[dict[str, Any]] = []
    for task_id in sorted(tasks, key=natural_sort_key):
        task = tasks[task_id]
        readiness = "inactive"
        blockers: list[str] = []
        if task_id in ready_by_id:
            readiness = "ready"
        elif task_id in blocked_by_id:
            readiness = "blocked"
            blockers = list(blocked_by_id[task_id].get("reasons") or [])
        status = task.get("status")
        task_rows.append(
            {
                "task_id": task_id,
                "title": task.get("title", ""),
                "status": status,
                "readiness": readiness,
                "action": derive_action(status, readiness),
                "blockers": blockers,
                "role": task.get("role"),
                "skill": task.get("skill"),
                "lease": lease_by_task.get(task_id),
                "jobs": jobs_by_task.get(task_id, []),
            }
        )

    status_counts = task_status_counts(tasks)
    running = [task for task in task_rows if task.get("status") == "running"]
    needs_review = [
        task for task in task_rows if task.get("status") in {"completed", "validated"}
    ]
    ready_rows = [task for task in task_rows if task.get("readiness") == "ready"]
    blocked_rows = [task for task in task_rows if task.get("readiness") == "blocked"]
    failed_rows = [task for task in task_rows if task.get("status") == "failed"]
    stale_leases = [lease for lease in leases if lease.get("state") == "stale"]
    active_jobs = [job for job in jobs if job.get("state") in ACTIVE_JOB_STATES]
    unknown_jobs = [job for job in jobs if job.get("state") == "submission_unknown"]
    unfinished = [
        task for task in task_rows if task.get("status") not in FINISHED_TASK_STATUSES
    ]

    attention: list[str] = []
    for lease in stale_leases:
        attention.append(
            f"{lease.get('task_id')} lease {lease.get('lease_id')} expired "
            f"{human_duration(abs(int(lease.get('expires_in_seconds') or 0)))} ago"
        )
    for task in failed_rows:
        attention.append(f"{task['task_id']} is failed: {task['title']}")
    for job in unknown_jobs:
        attention.append(
            f"{job.get('task_id')} attempt {job.get('attempt_id')} has unknown submission state"
        )
    missing_required_leases = []
    for task in running:
        source_task = tasks.get(str(task.get("task_id")), {})
        if task_requires_claim(source_task) and task.get("lease") is None:
            missing_required_leases.append(task)
            attention.append(f"{task['task_id']} is running without an active lease")

    if failures:
        health = "INVALID"
    elif stale_leases or failed_rows or missing_required_leases or unknown_jobs:
        health = "ATTENTION"
    elif running:
        health = "ACTIVE"
    elif needs_review:
        health = "REVIEW"
    elif ready_rows:
        health = "READY"
    elif unfinished:
        health = "BLOCKED"
    else:
        health = "COMPLETE"

    recent_events = events[-event_limit:] if event_limit > 0 else []
    return {
        "schema_version": 1,
        "observed_at": observed_at.replace(microsecond=0).isoformat(),
        "research_dir": research_dir.as_posix(),
        "project": {
            "project_id": project.get("project_id"),
            "title": project.get("title"),
            "mode": project.get("mode"),
            "objective": project.get("objective"),
        },
        "health": health,
        "summary": {
            "tasks_total": len(task_rows),
            "task_statuses": status_counts,
            "ready": len(ready_rows),
            "derived_blocked": len(blocked_rows),
            "active_leases": len(leases) - len(stale_leases),
            "stale_leases": len(stale_leases),
            "active_jobs": len(active_jobs),
            "unknown_jobs": len(unknown_jobs),
            "artifact_statuses": artifact_status_counts(artifacts),
        },
        "tasks": task_rows,
        "active_leases": leases,
        "attention": attention,
        "recent_events": recent_events,
        "validation": {
            "valid": not failures,
            "failure_count": len(failures),
            "findings": [finding.__dict__ for finding in findings],
        },
    }


def format_lease(lease: dict[str, Any]) -> str:
    heartbeat_age = lease.get("heartbeat_age_seconds")
    expires_in = lease.get("expires_in_seconds")
    if isinstance(expires_in, int) and expires_in < 0:
        expiry = f"expired={human_duration(abs(expires_in))} ago"
    else:
        expiry = f"expires_in={human_duration(expires_in if isinstance(expires_in, int) else None)}"
    job_ids = lease.get("job_ids") or []
    jobs = ",".join(job_ids) if job_ids else "not-recorded"
    scheduler = "recorded-only" if job_ids else "unknown"
    return (
        f"owner={lease.get('owner_id')}  lease={lease.get('lease_id')}  "
        f"heartbeat_age={human_duration(heartbeat_age if isinstance(heartbeat_age, int) else None)}  "
        f"{expiry}  jobs={jobs}  scheduler={scheduler}"
    )


def event_line(event: dict[str, Any]) -> str:
    created_at = str(event.get("created_at") or "unknown-time")
    kind = str(event.get("event") or "unknown-event")
    task_id = str(event.get("task_id") or "-")
    detail = ""
    if event.get("from") is not None or event.get("to") is not None:
        detail = f" {event.get('from', '?')}->{event.get('to', '?')}"
    elif event.get("lease_id"):
        detail = f" lease={event.get('lease_id')}"
    return f"{created_at}  {task_id}  {kind}{detail}"


def print_task_detail(task: dict[str, Any]) -> None:
    print(f"{task['task_id']}  {task['title']}")
    print(
        f"      status={task.get('status')}  action={task.get('action')}  readiness={task.get('readiness')}  "
        f"role={task.get('role')}  skill={task.get('skill')}"
    )
    lease = task.get("lease")
    if isinstance(lease, dict):
        print(f"      {format_lease(lease)}")
    for job in task.get("jobs") or []:
        print(
            f"      attempt={job.get('attempt_id')}  "
            f"job={job.get('job_id') or 'not-recorded'}  "
            f"state={job.get('state')}  workdir={job.get('workdir')}"
        )
    for blocker in task.get("blockers") or []:
        print(f"      blocked: {blocker}")


def print_task_counts(summary: dict[str, Any]) -> None:
    counts = summary["task_statuses"]
    count_tokens = [f"total={summary['tasks_total']}"]
    count_tokens.extend(
        f"{status}={count}" for status, count in counts.items() if count
    )
    count_tokens.extend(
        [f"ready={summary['ready']}", f"derived_blocked={summary['derived_blocked']}"]
    )
    print("\nTASKS")
    print("  ".join(count_tokens))


def print_task_ledger(
    task_rows: list[dict[str, Any]], *, label: str = "TASK LEDGER"
) -> None:
    print(f"\n{label} ({len(task_rows)})")
    print(f"{'ID':<7} {'STATUS':<11} {'ACTION':<10} TITLE")
    for task in task_rows:
        task_id = str(task.get("task_id") or "-")
        status = str(task.get("status") or "unknown")
        action = str(task.get("action") or "unknown")
        title = " ".join(str(task.get("title") or "").split())
        print(f"{task_id:<7} {status:<11} {action:<10} {title}")


def print_summary_view(task_rows: list[dict[str, Any]]) -> None:
    running = [task for task in task_rows if task.get("status") == "running"]
    needs_validation = [task for task in task_rows if task.get("status") == "completed"]
    needs_acceptance = [task for task in task_rows if task.get("status") == "validated"]
    ready = [task for task in task_rows if task.get("action") == "ready"]
    failed = [task for task in task_rows if task.get("status") == "failed"]
    blocked = [task for task in task_rows if task.get("action") == "blocked"]

    if running:
        print("\nRUNNING")
        for task in running:
            print_task_detail(task)
    if needs_validation:
        print("\nNEEDS VALIDATION")
        for task in needs_validation:
            print(f"{task['task_id']}  {task['title']}")
    if needs_acceptance:
        print("\nNEEDS ACCEPTANCE")
        for task in needs_acceptance:
            print(f"{task['task_id']}  {task['title']}")
    if ready:
        print("\nREADY")
        for task in ready:
            print(f"{task['task_id']}  {task['title']}")
    if failed:
        print("\nFAILED")
        for task in failed:
            print(f"{task['task_id']}  {task['title']}")
    if blocked:
        print(f"\nBLOCKED ({len(blocked)})")
        for task in blocked[:SUMMARY_BLOCKED_LIMIT]:
            blockers = task.get("blockers") or []
            first = blockers[0] if blockers else "status is blocked"
            suffix = f" (+{len(blockers) - 1} more)" if len(blockers) > 1 else ""
            print(f"{task['task_id']}  {task['title']}  --  {first}{suffix}")
        remaining = len(blocked) - SUMMARY_BLOCKED_LIMIT
        if remaining > 0:
            print(
                f"... {remaining} more blocked task(s); omit --summary to see the complete ledger"
            )


def render_text(
    snapshot: dict[str, Any],
    *,
    task_filter: str | None,
    status_filter: str | None,
    summary_only: bool,
) -> None:
    project = snapshot["project"]
    summary = snapshot["summary"]
    print("AICC PROJECT STATUS")
    print()
    print(
        f"Project   {project.get('project_id') or '<unknown>'}  {project.get('title') or ''}".rstrip()
    )
    print(f"Health    {snapshot['health']}")
    print(f"Mode      {project.get('mode') or '<unknown>'}")
    print(f"Observed  {snapshot['observed_at']}")
    print(f"State     {snapshot['research_dir']}")

    print_task_counts(summary)
    task_rows = snapshot["tasks"]
    if task_filter:
        task_rows = [task for task in task_rows if task.get("task_id") == task_filter]
        print("\nTASK DETAIL")
        print_task_detail(task_rows[0])
    elif status_filter:
        filtered = [task for task in task_rows if task.get("status") == status_filter]
        print_task_ledger(filtered, label=f"TASK LEDGER status={status_filter}")
    elif summary_only:
        print_summary_view(task_rows)
    else:
        print_task_ledger(task_rows)
        running = [task for task in task_rows if task.get("status") == "running"]
        if running:
            print("\nRUNNING DETAIL")
            for task in running:
                print_task_detail(task)

    attention = snapshot.get("attention") or []
    findings = snapshot["validation"]["findings"]
    if attention or findings:
        print("\nATTENTION")
        for message in attention:
            print(f"- {message}")
        for finding in findings[:10]:
            print(f"- {finding['level']} {finding['path']}: {finding['message']}")

    events = snapshot.get("recent_events") or []
    if events:
        print("\nRECENT EVENTS")
        for event in events:
            print(event_line(event))


def watch_fingerprint(snapshot: dict[str, Any]) -> str:
    """Return a stable fingerprint that ignores continuously changing age counters."""

    tasks = []
    for task in snapshot.get("tasks") or []:
        lease = task.get("lease")
        stable_lease = None
        if isinstance(lease, dict):
            stable_lease = {
                key: lease.get(key)
                for key in (
                    "task_id",
                    "lease_id",
                    "owner_id",
                    "state",
                    "heartbeat_at",
                    "expires_at",
                    "job_ids",
                    "owner_dir",
                    "source",
                )
            }
        tasks.append(
            {
                "task_id": task.get("task_id"),
                "title": task.get("title"),
                "status": task.get("status"),
                "readiness": task.get("readiness"),
                "action": task.get("action"),
                "blockers": task.get("blockers"),
                "role": task.get("role"),
                "skill": task.get("skill"),
                "lease": stable_lease,
            }
        )
    stable = {
        "project": snapshot.get("project"),
        "health": snapshot.get("health"),
        "summary": snapshot.get("summary"),
        "tasks": tasks,
        "recent_events": snapshot.get("recent_events"),
        "validation": snapshot.get("validation"),
    }
    return json.dumps(stable, sort_keys=True, separators=(",", ":"))


def watch_status(
    path: Path,
    *,
    interval: float,
    event_limit: int,
    task_filter: str | None,
    status_filter: str | None,
    summary_only: bool,
    max_iterations: int | None = None,
    sleep: Any = time.sleep,
) -> int:
    """Watch a project and redraw only when its derived state changes."""

    previous: str | None = None
    iterations = 0
    interactive = sys.stdout.isatty()
    try:
        while True:
            snapshot = build_status(
                path, observed_at=now_local(), event_limit=event_limit
            )
            if task_filter and not any(
                task.get("task_id") == task_filter for task in snapshot["tasks"]
            ):
                print(f"unknown task: {task_filter}", file=sys.stderr)
                return 2
            fingerprint = watch_fingerprint(snapshot)
            if fingerprint != previous:
                if interactive:
                    print("\033[2J\033[H", end="")
                elif previous is not None:
                    print("\n--- AICC STATUS UPDATE ---")
                render_text(
                    snapshot,
                    task_filter=task_filter,
                    status_filter=status_filter,
                    summary_only=summary_only,
                )
                print(
                    f"\nWatching every {interval:g}s; Ctrl-C to stop.",
                    flush=True,
                )
                previous = fingerprint
            iterations += 1
            if max_iterations is not None and iterations >= max_iterations:
                return 0
            sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped watching AICC project status.")
        return 0


def register(subparsers: Any) -> None:
    status = subparsers.add_parser(
        "status", help="Show a read-only derived project status snapshot"
    )
    status.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to .research or a project containing it (default: current directory)",
    )
    status.add_argument(
        "--json",
        action="store_true",
        help="Emit the complete machine-readable snapshot",
    )
    view = status.add_mutually_exclusive_group()
    view.add_argument(
        "--summary",
        action="store_true",
        help="Show only actionable tasks and a short blocker list",
    )
    view.add_argument("--task", help="Show one task in the text/JSON view")
    view.add_argument(
        "--status",
        dest="status_filter",
        choices=TASK_STATUS_ORDER,
        help="Show tasks with one status",
    )
    status.add_argument(
        "--events",
        type=int,
        default=5,
        help="Number of recent events to include (default: 5)",
    )
    status.add_argument(
        "--now", help="ISO timestamp for deterministic status and lease-age checks"
    )
    status.add_argument(
        "--watch",
        type=positive_interval,
        metavar="SECONDS",
        help="Keep watching and redraw when project state changes",
    )
    status.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    if args.events < 0:
        raise SystemExit("--events must be zero or greater")
    if args.json and args.summary:
        raise SystemExit(
            "--summary is a text-only view; JSON already contains the complete snapshot"
        )
    if args.watch is not None and args.json:
        raise SystemExit("--watch is a text-only view; omit --json")
    if args.watch is not None and args.now:
        raise SystemExit("--now cannot be combined with --watch")
    if args.watch is not None:
        return watch_status(
            Path(args.path),
            interval=args.watch,
            event_limit=args.events,
            task_filter=args.task,
            status_filter=args.status_filter,
            summary_only=args.summary,
        )
    try:
        observed_at = parse_time(args.now) if args.now else now_local()
    except (TypeError, ValueError) as exc:
        print(f"aicc status: invalid --now value: {exc}", file=sys.stderr)
        return 2
    snapshot = build_status(
        Path(args.path), observed_at=observed_at, event_limit=args.events
    )
    if args.task:
        matches = [
            task for task in snapshot["tasks"] if task.get("task_id") == args.task
        ]
        if not matches:
            print(f"unknown task: {args.task}", file=sys.stderr)
            return 2
        if args.json:
            snapshot = {**snapshot, "tasks": matches}
    elif args.status_filter and args.json:
        matches = [
            task
            for task in snapshot["tasks"]
            if task.get("status") == args.status_filter
        ]
        snapshot = {**snapshot, "tasks": matches}
    if args.json:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    else:
        render_text(
            snapshot,
            task_filter=args.task,
            status_filter=args.status_filter,
            summary_only=args.summary,
        )
    return 1 if snapshot["health"] == "INVALID" else 0
