"""Shared helpers for research-orchestrator lease scripts."""

from __future__ import annotations

import json
import os
import shutil
import socket
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from validate_state import (
    Finding,
    is_safe_project_path,
    load_json_file,
    load_jsonl,
    load_yaml,
    normalize_project_path,
    project_paths_conflict,
    rel,
    resolve_research_dir,
    validate,
)


def now_local() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)


def parse_time(token: str | None) -> datetime:
    if token:
        parsed = datetime.fromisoformat(token.replace("Z", "+00:00"))
        return parsed.astimezone() if parsed.tzinfo is None else parsed
    return now_local()


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def default_owner_id() -> str:
    return f"codex-{socket.gethostname()}-{os.getpid()}"


def load_tasks(research_dir: Path) -> dict[str, dict[str, Any]]:
    tasks: dict[str, dict[str, Any]] = {}
    for task_file in sorted((research_dir / "tasks").glob("*.yaml")):
        task = load_yaml(task_file, [], research_dir)
        if isinstance(task.get("id"), str):
            tasks[task["id"]] = task
    return tasks


def task_path(research_dir: Path, task_id: str) -> Path:
    return research_dir / "tasks" / f"{task_id}.yaml"


def write_task(research_dir: Path, task: dict[str, Any]) -> None:
    path = task_path(research_dir, task["id"])
    write_text_atomic(
        path, yaml.safe_dump(task, sort_keys=False, allow_unicode=False)
    )


def load_current_lease(research_dir: Path, task_id: str) -> dict[str, Any] | None:
    path = research_dir / "leases" / f"{task_id}.json"
    if not path.exists():
        return None
    return load_json_file(path, [], research_dir)


def lease_path(research_dir: Path, task_id: str) -> Path:
    return research_dir / "leases" / f"{task_id}.json"


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def write_json_atomic(path: Path, obj: dict[str, Any]) -> None:
    write_text_atomic(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")


def archive_released_current_lease(research_dir: Path, task_id: str) -> None:
    current = lease_path(research_dir, task_id)
    if not current.exists():
        return
    lease = load_json_file(current, [], research_dir)
    if lease.get("status") == "active":
        raise SystemExit(f"task already has an active lease: {rel(current, research_dir)}")
    lease_id = str(lease.get("lease_id") or "archived").replace("/", "_")
    archive = current.with_name(f"{task_id}.{lease_id}.json")
    if not archive.exists():
        shutil.copy2(current, archive)


def append_event(research_dir: Path, event: dict[str, Any]) -> str:
    events_path = research_dir / "events.jsonl"
    rows = load_jsonl(events_path, [], research_dir)
    event.setdefault("event_id", f"E{len(rows) + 1:03d}")
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return str(event["event_id"])


def append_decision(research_dir: Path, decision: dict[str, Any]) -> str:
    decisions_path = research_dir / "decisions.jsonl"
    rows = load_jsonl(decisions_path, [], research_dir)
    decision.setdefault("decision_id", f"D{len(rows) + 1:03d}")
    with decisions_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(decision, sort_keys=True) + "\n")
    return str(decision["decision_id"])


def fail_if_invalid(research_dir: Path) -> None:
    findings = validate(research_dir)
    failures = [finding for finding in findings if finding.level == "FAIL"]
    if not failures:
        return
    for finding in findings:
        print(f"{finding.level}  {finding.path}  {finding.message}")
    raise SystemExit(f"state is invalid ({len(failures)} failure(s))")


def task_execution_policy(task: dict[str, Any]) -> dict[str, Any]:
    policy = task.get("execution_policy")
    return policy if isinstance(policy, dict) else {}


def task_requires_claim(task: dict[str, Any]) -> bool:
    return task_execution_policy(task).get("requires_claim") is True


def ttl_minutes(task: dict[str, Any]) -> int:
    policy = task_execution_policy(task)
    ttl = policy.get("lease_ttl_minutes")
    return ttl if isinstance(ttl, int) and ttl > 0 else 60


def owner_dir(task: dict[str, Any]) -> str:
    token = task_execution_policy(task).get("owner_dir")
    return token if isinstance(token, str) and token else "."


def exclusive_paths(task: dict[str, Any]) -> list[str]:
    policy = task_execution_policy(task)
    raw = policy.get("exclusive_paths")
    if isinstance(raw, list) and raw:
        return [path for path in raw if isinstance(path, str)]
    return [owner_dir(task)]


def lease_id_for(task_id: str, now: datetime) -> str:
    compact = now.astimezone().strftime("%Y%m%dT%H%M%S%z")
    return f"L-{task_id}-{compact}"


def active_leases(research_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    leases_dir = research_dir / "leases"
    if not leases_dir.is_dir():
        return []
    rows: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(leases_dir.glob("*.json")):
        lease = load_json_file(path, [], research_dir)
        if lease.get("status") == "active":
            rows.append((path, lease))
    return rows


def assert_no_active_conflict(
    research_dir: Path,
    project_root: Path,
    task_id: str,
    paths: list[str],
) -> None:
    normalized = [normalize_project_path(path, project_root) for path in paths if is_safe_project_path(path, project_root)]
    for path, lease in active_leases(research_dir):
        other_task = lease.get("task_id")
        if other_task == task_id:
            raise SystemExit(f"task already has an active lease: {rel(path, research_dir)}")
        for other_path in lease.get("exclusive_paths") or []:
            if not isinstance(other_path, str) or not is_safe_project_path(other_path, project_root):
                continue
            other_normalized = normalize_project_path(other_path, project_root)
            for candidate in normalized:
                if project_paths_conflict(candidate, other_normalized):
                    raise SystemExit(
                        "active lease path conflict: "
                        f"{candidate} conflicts with {other_normalized} in {rel(path, research_dir)}"
                    )


def print_findings(findings: list[Finding]) -> None:
    for finding in findings:
        print(f"{finding.level}  {finding.path}  {finding.message}")


def resolve(path: str) -> tuple[Path, Path]:
    return resolve_research_dir(Path(path))
