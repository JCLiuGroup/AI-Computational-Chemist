#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML>=6.0"]
# ///
"""List derived READY and BLOCKED tasks for a `.research/` state directory."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from follow_up_utils import format_follow_up_blockers, unresolved_follow_up_proposals
from validate_state import (
    ARTIFACT_STATUSES,
    Finding,
    LoadedResearchState,
    file_input_exists,
    is_safe_project_path,
    load_jsonl,
    load_yaml,
    load_validated_state,
)


CANDIDATE_STATUSES = {"proposed", "approved"}
TERMINAL_OR_INACTIVE = {"running", "completed", "validated", "accepted", "failed", "cancelled"}
ARTIFACT_RANK = {
    "draft": 0,
    "validated": 1,
    "accepted": 2,
    "rejected": -1,
    "superseded": -1,
}
APPROVAL_KIND_ALIASES = {
    "scientific_model_choice": {"method-choice"},
}
APPROVAL_MATCH_FIELDS = {"approval_type", "approval", "policy"}
STAGE_SYNTHESIS_MODES = {"stage-synthesis", "stage_synthesis", "interim"}


@dataclass
class TaskState:
    task_id: str
    title: str
    status: str
    reasons: list[str]


def load_state(research_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    tasks: dict[str, dict[str, Any]] = {}
    for task_file in sorted((research_dir / "tasks").glob("*.yaml")):
        task = load_yaml(task_file, [], research_dir)
        if isinstance(task.get("id"), str):
            tasks[task["id"]] = task
    artifacts = {
        row["artifact_id"]: row
        for row in load_jsonl(research_dir / "artifacts.jsonl", [], research_dir)
        if isinstance(row.get("artifact_id"), str)
    }
    decisions = load_jsonl(research_dir / "decisions.jsonl", [], research_dir)
    return tasks, artifacts, decisions


def approval_exists(task: dict[str, Any], decisions: list[dict[str, Any]]) -> bool:
    required = task.get("approval")
    if required in (None, "", "none"):
        return True
    for decision in decisions:
        if decision.get("task_id") != task.get("id"):
            continue
        if decision.get("decision") not in {"approved", "accepted"}:
            continue
        kind = decision.get("kind")
        if kind == required:
            return True
        if kind in APPROVAL_KIND_ALIASES.get(str(required), set()):
            return True
        if kind == "approval" and any(decision.get(field) == required for field in APPROVAL_MATCH_FIELDS):
            return True
    return False


def artifact_satisfies(artifact: dict[str, Any], min_status: str) -> bool:
    status = artifact.get("status")
    if status not in ARTIFACT_STATUSES:
        return False
    if min_status not in ARTIFACT_RANK:
        min_status = "accepted"
    return ARTIFACT_RANK.get(status, -1) >= ARTIFACT_RANK[min_status]


def active_accepted_output_conflict(task: dict[str, Any], artifacts: dict[str, dict[str, Any]]) -> list[str]:
    conflicts: list[str] = []
    for output in task.get("outputs_expected") or []:
        if not isinstance(output, dict):
            continue
        artifact_id = output.get("artifact_id")
        if not isinstance(artifact_id, str):
            continue
        existing = artifacts.get(artifact_id)
        if not existing:
            continue
        if existing.get("status") == "accepted" and not output.get("supersedes"):
            conflicts.append(f"output artifact already accepted: {artifact_id}")
    return conflicts


def is_report_task(task: dict[str, Any]) -> bool:
    return task.get("role") == "synthesis-report" or task.get("skill") == "report"


def is_stage_synthesis(task: dict[str, Any]) -> bool:
    for field in ["report_mode", "mode", "stage", "workflow_stage"]:
        value = task.get(field)
        if isinstance(value, str) and value.strip().lower() in STAGE_SYNTHESIS_MODES:
            return True
    return False


def blocked_reasons(
    task: dict[str, Any],
    tasks: dict[str, dict[str, Any]],
    artifacts: dict[str, dict[str, Any]],
    decisions: list[dict[str, Any]],
    project_root: Path,
) -> list[str]:
    reasons: list[str] = []
    status = task.get("status")

    if status == "blocked":
        reasons.append("status is blocked")
    elif status in TERMINAL_OR_INACTIVE:
        return []
    elif status not in CANDIDATE_STATUSES:
        reasons.append(f"status is not runnable: {status}")

    for dep in task.get("depends_on") or []:
        dep_task = tasks.get(dep)
        if not dep_task:
            reasons.append(f"missing dependency task: {dep}")
        elif dep_task.get("status") != "accepted":
            reasons.append(f"waiting for {dep} accepted")

    # If upstream dependencies are not accepted, missing downstream artifacts are expected.
    dependency_blocked = any(reason.startswith("waiting for ") for reason in reasons)

    if not approval_exists(task, decisions):
        reasons.append(f"missing approval: {task.get('approval')}")

    if not dependency_blocked:
        for inp in task.get("inputs") or []:
            if not isinstance(inp, dict):
                continue
            if "artifact_id" in inp:
                artifact_id = inp.get("artifact_id")
                artifact = artifacts.get(artifact_id)
                if artifact is None:
                    if inp.get("optional", False):
                        continue
                    reasons.append(f"input artifact is not registered: {artifact_id}")
                    continue
                min_status = inp.get("min_status", "accepted")
                if not artifact_satisfies(artifact, min_status):
                    reasons.append(
                        f"input artifact {artifact_id} is {artifact.get('status')}, needs {min_status}"
                    )
            elif "path" in inp:
                path = inp.get("path")
                if not isinstance(path, str) or not is_safe_project_path(path, project_root):
                    reasons.append(f"input path escapes project root: {path}")
                elif not inp.get("optional", False) and not file_input_exists(path, project_root):
                    reasons.append(f"input file does not exist: {path}")

    reasons.extend(active_accepted_output_conflict(task, artifacts))

    if is_report_task(task) and not is_stage_synthesis(task):
        blockers = unresolved_follow_up_proposals(artifacts, decisions, tasks)
        if blockers:
            reasons.append(
                "unresolved follow-up proposal(s): "
                + format_follow_up_blockers(blockers)
                + "; run check_pre_report.py to write a stage-synthesis report and scaffold follow-up tasks"
            )

    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for reason in reasons:
        if reason not in seen:
            unique.append(reason)
            seen.add(reason)
    return unique


def derive_ready_from_state(state: LoadedResearchState) -> tuple[list[TaskState], list[TaskState]]:
    """Derive task readiness from an already parsed, valid state snapshot."""

    tasks = state.tasks
    artifacts = {
        row["artifact_id"]: row
        for row in state.artifacts
        if isinstance(row.get("artifact_id"), str)
    }
    ready: list[TaskState] = []
    blocked: list[TaskState] = []

    for task_id in sorted(tasks):
        task = tasks[task_id]
        status = task.get("status", "")
        if status not in CANDIDATE_STATUSES and status != "blocked":
            continue
        reasons = blocked_reasons(task, tasks, artifacts, state.decisions, state.project_root)
        task_state = TaskState(task_id, task.get("title", ""), status, reasons)
        if reasons:
            blocked.append(task_state)
        else:
            ready.append(task_state)

    return ready, blocked


def derive_ready(path: Path) -> tuple[list[TaskState], list[TaskState], list[Finding]]:
    state, findings = load_validated_state(path)
    failures = [finding for finding in findings if finding.level == "FAIL"]
    if failures:
        return [], [], findings

    ready, blocked = derive_ready_from_state(state)
    return ready, blocked, []


def emit_text(ready: list[TaskState], blocked: list[TaskState]) -> None:
    print("READY")
    if ready:
        for task in ready:
            print(f"{task.task_id}  {task.title}")
    else:
        print("(none)")

    print("\nBLOCKED")
    if blocked:
        for task in blocked:
            print(f"{task.task_id}  {task.title}       {'; '.join(task.reasons)}")
    else:
        print("(none)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to .research directory or a project root containing .research")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable ready/blocked output")
    args = parser.parse_args()

    ready, blocked, findings = derive_ready(Path(args.path))
    failures = [finding for finding in findings if finding.level == "FAIL"]
    if failures:
        for finding in findings:
            print(f"{finding.level}  {finding.path}  {finding.message}", file=sys.stderr)
        print(f"\n== ready_tasks: state invalid ({len(failures)} failure(s)) ==", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "ready": [task.__dict__ for task in ready],
                    "blocked": [task.__dict__ for task in blocked],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        emit_text(ready, blocked)

    return 0


if __name__ == "__main__":
    sys.exit(main())
