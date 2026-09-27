#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML>=6.0"]
# ///
"""Validate a `.research/` state directory.

Read-only, deterministic checks for the research-orchestrator protocol. The script
checks schema shape, task DAG integrity, artifact references, path safety, JSONL syntax,
role contracts, and obvious secret-like registry fields. It intentionally does not
decide whether a task is ready to run; use `ready_tasks.py` for ready/blocked state.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - reached only outside uv/pep723
    raise SystemExit(
        "PyYAML is required. Run with: uv run "
        "procedures/research-orchestrator/scripts/validate_state.py PATH/.research"
    ) from exc


YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


TASK_STATUSES = {
    "proposed",
    "approved",
    "running",
    "completed",
    "validated",
    "accepted",
    "blocked",
    "failed",
    "cancelled",
}
ARTIFACT_STATUSES = {"draft", "validated", "accepted", "rejected", "superseded"}
LEASE_STATUSES = {"active", "released", "stale", "cancelled", "superseded"}
JOB_STATES = {
    "submitting",
    "submission_unknown",
    "pending",
    "running",
    "completed",
    "failed",
    "cancelled",
    "timeout",
}
ACTIVE_JOB_STATES = {"submitting", "submission_unknown", "pending", "running"}
PROJECT_MODES = {"semi-automatic", "autonomous"}
SECRET_KEY_RE = re.compile(r"(password|passwd|secret|token|api[_-]?key|private[_-]?key)", re.I)
ALLOWED_ROLES = {
    "research-orchestrator",
    "literature-method",
    "surface-literature-reviewer",
    "structure-modeler",
    "structure-critic",
    "engine-runner",
    "scientific-critic",
    "synthesis-report",
}
RESTRICTED_ROLE_OUTPUT_TYPES = {
    "surface-literature-reviewer": {
        "surface-literature-review",
        "model-structure-review",
        "gate-verdict",
        "validation-report",
        "follow-up-proposal",
        "limitation-note",
        "subagent-finding",
    },
    "structure-modeler": {
        "initial-structure-decision",
        "structure-set",
        "validation-report",
        "follow-up-proposal",
    },
    "structure-critic": {
        "structure-audit-report",
        "structure-review-note",
        "model-structure-review",
        "gate-verdict",
        "validation-report",
        "follow-up-proposal",
        "limitation-note",
        "subagent-finding",
    },
    "scientific-critic": {
        "critic-report",
        "result-review-note",
        "scientific-claim",
        "claim-assessment",
        "gate-verdict",
        "validation-report",
        "follow-up-proposal",
        "contradiction-report",
        "limitation-note",
        "subagent-finding",
    },
    "synthesis-report": {
        "report-manifest",
        "synthesis-note",
        "handoff-note",
        "figure",
        "docx-report",
        "calculation-directory-index",
        "response-package",
        "gate-verdict",
        "validation-report",
        "subagent-finding",
    },
}
CONTRACT_ENTRY_KEYS = {"artifact_id", "artifact_type", "path", "role", "skill"}
LEASE_TIME_FIELDS = {"acquired_at", "heartbeat_at", "expires_at", "released_at"}
GATE_ALIASES = {
    "model-observable": "plan_gate",
    "model_observable": "plan_gate",
    "model-structure-review": "structure_gate",
    "model_structure_review": "structure_gate",
    "structure-release": "structure_gate",
    "structure_release": "structure_gate",
    "critic-acceptance": "result_gate",
    "critic_acceptance": "result_gate",
    "report-readiness": "report_gate",
    "report_readiness": "report_gate",
}
STRUCTURE_GATE_PRODUCER_ROLES = {"structure-critic", "surface-literature-reviewer"}
POST_RESULT_ROLES = {"scientific-critic", "synthesis-report"}
POST_RESULT_GATES = {"result_gate", "report_gate"}
POST_RESULT_CHECK_MARKERS = {"check_pre_accept_claim.py", "check_pre_report.py"}
ARTIFACT_TYPE_SUGGESTIONS = {
    "report-docx": "docx-report",
    "docx": "docx-report",
    "structure-gate": "gate-verdict",
    "plan-gate": "gate-verdict",
    "result-gate": "gate-verdict",
    "report-gate": "gate-verdict",
}
POST_RESULT_STAGE_VALUES = {
    "post-result",
    "post_result",
    "post-result-review",
    "post_result_review",
    "follow-up",
    "follow_up",
    "follow-up-execution",
    "follow_up_execution",
    "reanalysis",
    "recovery",
    "post-processing",
    "post_processing",
}

SCRIPT_PATH = Path(__file__).resolve()
SKILL_ROOT = SCRIPT_PATH.parents[1]
SKILLS_ROOT = SCRIPT_PATH.parents[2]


def find_collection_root() -> Path | None:
    for parent in SCRIPT_PATH.parents:
        if (parent / "procedures").is_dir() and (parent / "tools").is_dir():
            return parent
    return None


COLLECTION_ROOT = find_collection_root()
REPO_ROOT = COLLECTION_ROOT or SCRIPT_PATH.parents[3]


@dataclass
class Finding:
    level: str
    path: str
    message: str


@dataclass
class LoadedResearchState:
    """Parsed project state returned alongside validation findings.

    Keeping the parsed records lets read-only consumers such as ``aicc status`` and
    ``ready_tasks.py`` reuse the validator's authoritative view without reparsing the
    same task files and JSONL registries.
    """

    research_dir: Path
    project_root: Path
    project: dict[str, Any]
    tasks: dict[str, dict[str, Any]]
    artifacts: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    events: list[dict[str, Any]]


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_research_dir(path: Path) -> tuple[Path, Path]:
    path = path.resolve()
    if path.name == ".research":
        return path, path.parent
    if (path / ".research").is_dir():
        return (path / ".research"), path
    return path, path.parent


def load_yaml(path: Path, findings: list[Finding], root: Path) -> dict[str, Any]:
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=YAML_LOADER)
    except Exception as exc:  # noqa: BLE001 - report parser detail
        findings.append(Finding("FAIL", rel(path, root), f"YAML parse failed: {exc}"))
        return {}
    if data is None:
        findings.append(Finding("FAIL", rel(path, root), "YAML file is empty"))
        return {}
    if not isinstance(data, dict):
        findings.append(Finding("FAIL", rel(path, root), "YAML root must be a mapping"))
        return {}
    return data


def load_jsonl(path: Path, findings: list[Finding], root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        findings.append(Finding("FAIL", rel(path, root), "required JSONL file is missing"))
        return rows
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError as exc:
            findings.append(Finding("FAIL", f"{rel(path, root)}:{lineno}", f"JSON parse failed: {exc}"))
            continue
        if not isinstance(obj, dict):
            findings.append(Finding("FAIL", f"{rel(path, root)}:{lineno}", "JSONL row must be an object"))
            continue
        rows.append(obj)
    return rows


def load_json_file(path: Path, findings: list[Finding], root: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report parser detail
        findings.append(Finding("FAIL", rel(path, root), f"JSON parse failed: {exc}"))
        return {}
    if not isinstance(obj, dict):
        findings.append(Finding("FAIL", rel(path, root), "JSON root must be an object"))
        return {}
    return obj


def require_fields(obj: dict[str, Any], fields: list[str], where: str, findings: list[Finding]) -> None:
    for field in fields:
        if field not in obj:
            findings.append(Finding("FAIL", where, f"missing required field `{field}`"))


def list_field(obj: dict[str, Any], field: str, where: str, findings: list[Finding]) -> list[Any]:
    value = obj.get(field)
    if value is None:
        return []
    if not isinstance(value, list):
        findings.append(Finding("FAIL", where, f"`{field}` must be a list"))
        return []
    return value


def is_safe_project_path(token: str | None, project_root: Path) -> bool:
    if not token:
        return False
    path = Path(token)
    if path.is_absolute():
        return False
    resolved = (project_root / path).resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError:
        return False
    return True


def file_input_exists(token: str, project_root: Path) -> bool:
    return (project_root / token).is_file() or (project_root / token).is_dir()


def normalize_project_path(token: str, project_root: Path) -> str:
    return (project_root / token).resolve().relative_to(project_root).as_posix()


def duplicated_project_root_prefix_hint(token: str, project_root: Path) -> str | None:
    path = Path(token)
    if path.is_absolute():
        return None
    parts = path.parts
    if not parts or parts[0] != project_root.name or len(parts) <= 1:
        return None
    stripped = Path(*parts[1:])
    original = project_root / path
    candidate = project_root / stripped
    if candidate.exists() and not original.exists():
        return stripped.as_posix()
    return None


def project_paths_conflict(left: str, right: str) -> bool:
    if left == right:
        return True
    return left.startswith(f"{right}/") or right.startswith(f"{left}/")


def normalize_gate_name(gate: Any) -> str:
    if not isinstance(gate, str):
        return ""
    return GATE_ALIASES.get(gate, gate)


def normalized_identifier(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def infer_gate_name(artifact_id: Any = "", artifact_type: Any = "", path: Any = "") -> str:
    if artifact_type == "model-structure-review":
        return "structure_gate"
    if artifact_type != "gate-verdict":
        return ""
    text = "_".join(
        token
        for token in [
            normalized_identifier(artifact_id),
            normalized_identifier(path),
        ]
        if token
    )
    for gate in ["plan_gate", "structure_gate", "result_gate", "report_gate"]:
        if gate in text:
            return gate
    for alias, gate in GATE_ALIASES.items():
        if normalized_identifier(alias) in text:
            return gate
    return ""


def normalized_stage_value(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def allows_post_result_dependencies(task: dict[str, Any]) -> bool:
    if task.get("allow_post_result_dependencies") is True:
        return True
    for field in ["workflow_stage", "workflow_phase", "stage", "phase"]:
        if normalized_stage_value(task.get(field)) in POST_RESULT_STAGE_VALUES:
            return True
    return False


def artifact_project_path(row: dict[str, Any], project_root: Path) -> Path | None:
    path_token = row.get("path")
    if not isinstance(path_token, str) or not is_safe_project_path(path_token, project_root):
        return None
    return (project_root / path_token).resolve()


def artifact_gate_name(row: dict[str, Any], project_root: Path) -> str:
    artifact_type = row.get("type")
    path = artifact_project_path(row, project_root)
    if artifact_type == "model-structure-review":
        return "structure_gate"
    if artifact_type != "gate-verdict" or path is None or path.suffix.lower() not in {".yaml", ".yml"}:
        return ""
    if not path.is_file():
        return ""
    try:
        obj = yaml.load(path.read_text(encoding="utf-8"), Loader=YAML_LOADER)
    except Exception:
        return ""
    if not isinstance(obj, dict):
        return ""
    return normalize_gate_name(obj.get("gate"))


def artifact_gate_name_or_inferred(row: dict[str, Any], project_root: Path) -> str:
    return artifact_gate_name(row, project_root) or infer_gate_name(
        row.get("artifact_id"),
        row.get("type"),
        row.get("path"),
    )


def declared_output_gate_name(output: dict[str, Any]) -> str:
    return infer_gate_name(output.get("artifact_id"), output.get("type"), output.get("path"))


def repo_path_candidates(token: str) -> list[Path]:
    token = token.split("#", 1)[0]
    if not token:
        return []
    path = Path(token)
    if path.is_absolute():
        return [path]

    candidates: list[Path] = []
    if COLLECTION_ROOT is not None:
        candidates.append(COLLECTION_ROOT / path)

    parts = path.parts
    if len(parts) >= 2 and parts[0] in {"procedures", "tools"}:
        suffix = Path(*parts[2:]) if len(parts) > 2 else Path()
        candidates.append(SKILLS_ROOT / parts[1] / suffix)
    if parts:
        suffix = Path(*parts[1:]) if len(parts) > 1 else Path()
        candidates.append(SKILLS_ROOT / parts[0] / suffix)
    candidates.append(SKILL_ROOT / path)
    return candidates


def repo_path_exists(token: str) -> bool:
    return any(path.exists() for path in repo_path_candidates(token))


def discover_repo_skills() -> set[str]:
    names: set[str] = set()
    roots: list[Path] = []
    if COLLECTION_ROOT is not None:
        roots.extend([COLLECTION_ROOT / "procedures", COLLECTION_ROOT / "tools"])
    roots.append(SKILLS_ROOT)

    seen_files: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for skill_file in root.glob("*/SKILL.md"):
            skill_file = skill_file.resolve()
            if skill_file in seen_files:
                continue
            seen_files.add(skill_file)
            names.add(skill_file.parent.name)
            try:
                text = skill_file.read_text(encoding="utf-8")
            except OSError:
                continue
            for line in text.splitlines():
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip().strip("\"'")
                    if name:
                        names.add(name)
                    break
    return names


REPO_SKILLS = discover_repo_skills()


def walk_secret_keys(obj: Any, where: str, findings: list[Finding]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if SECRET_KEY_RE.search(str(key)):
                findings.append(Finding("FAIL", where, f"secret-like key `{key}` must not be stored in state"))
            walk_secret_keys(value, where, findings)
    elif isinstance(obj, list):
        for value in obj:
            walk_secret_keys(value, where, findings)


def is_iso_datetime(token: Any) -> bool:
    if not isinstance(token, str) or not token:
        return False
    try:
        datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def detect_cycle(tasks: dict[str, dict[str, Any]], where_by_id: dict[str, str], findings: list[Finding]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def dfs(task_id: str) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            start = stack.index(task_id) if task_id in stack else 0
            cycle = " -> ".join(stack[start:] + [task_id])
            findings.append(Finding("FAIL", where_by_id.get(task_id, task_id), f"dependency cycle: {cycle}"))
            return
        visiting.add(task_id)
        stack.append(task_id)
        for dep in tasks[task_id].get("depends_on") or []:
            if dep in tasks:
                dfs(dep)
        stack.pop()
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in sorted(tasks):
        dfs(task_id)


def validate_first_submit_boundary(
    tasks: dict[str, dict[str, Any]],
    artifacts: dict[str, dict[str, Any]],
    declared_output_gate_by_id: dict[str, str],
    where_by_id: dict[str, str],
    project_root: Path,
    findings: list[Finding],
) -> None:
    for task_id, task in tasks.items():
        if task.get("role") != "engine-runner":
            continue

        issues: list[str] = []
        allow_post_result = allows_post_result_dependencies(task)
        if not allow_post_result:
            for dep_id in task.get("depends_on") or []:
                dep_task = tasks.get(dep_id)
                if dep_task and dep_task.get("role") in POST_RESULT_ROLES:
                    issues.append(f"depends_on {dep_id} role `{dep_task.get('role')}`")

            post_result_gates = [
                str(gate)
                for gate in task.get("release_gates") or []
                if normalize_gate_name(gate) in POST_RESULT_GATES
            ]
            if post_result_gates:
                issues.append(f"release_gates include post-result gate(s): {', '.join(post_result_gates)}")

            if task.get("approval") == "promote_claim_to_report":
                issues.append("approval is `promote_claim_to_report`")

            check_hits = [
                str(check)
                for check in task.get("required_checks") or []
                if any(marker in str(check) for marker in POST_RESULT_CHECK_MARKERS)
            ]
            if check_hits:
                issues.append("required_checks include post-result/report hook(s)")

        release_gate_names = {normalize_gate_name(gate) for gate in task.get("release_gates") or []}
        input_ids = [
            inp.get("artifact_id")
            for inp in task.get("inputs") or []
            if isinstance(inp, dict) and isinstance(inp.get("artifact_id"), str)
        ]
        input_gate_names: set[str] = set()
        for artifact_id in input_ids:
            row = artifacts.get(artifact_id)
            if row is not None:
                gate_name = artifact_gate_name_or_inferred(row, project_root)
                if gate_name:
                    input_gate_names.add(gate_name)
            gate_name = declared_output_gate_by_id.get(artifact_id)
            if gate_name:
                input_gate_names.add(gate_name)
        if "structure_gate" in release_gate_names and "structure_gate" not in input_gate_names:
            issues.append(
                "release_gates include `structure_gate` but task inputs do not declare "
                "a structure_gate/model-structure-review artifact"
            )

        if issues:
            findings.append(
                Finding(
                    "WARN",
                    where_by_id.get(task_id, task_id),
                    "engine-runner task has release-gate/input boundary issue(s): "
                    + "; ".join(issues)
                    + ". First submission should consume accepted plan/model evidence and, when "
                    "structures are in scope, an explicit structure_gate input. Scientific critics, "
                    "result/report gates, and stage synthesis should run after a calculation wave "
                    "unless this is a follow-up/reanalysis/recovery task.",
                )
            )


def validate_contract_entries(obj: dict[str, Any], field: str, where: str, findings: list[Finding]) -> list[Any]:
    entries = list_field(obj, field, where, findings)
    for entry in entries:
        if isinstance(entry, str):
            continue
        if not isinstance(entry, dict):
            findings.append(Finding("FAIL", where, f"`{field}` entries must be strings or mappings"))
            continue
        if not any(key in entry for key in CONTRACT_ENTRY_KEYS):
            findings.append(
                Finding(
                    "FAIL",
                    where,
                    f"`{field}` mapping must include one of {sorted(CONTRACT_ENTRY_KEYS)}",
                )
            )
        for key in CONTRACT_ENTRY_KEYS:
            if key in entry and not isinstance(entry[key], str):
                findings.append(Finding("FAIL", where, f"`{field}.{key}` must be a string"))
        if "min_status" in entry and entry["min_status"] not in ARTIFACT_STATUSES:
            findings.append(Finding("FAIL", where, f"`{field}.min_status` is not a known artifact status"))
        if "why" in entry and not isinstance(entry["why"], str):
            findings.append(Finding("FAIL", where, f"`{field}.why` must be a string"))
    return entries


def validate_task_role_contract(task: dict[str, Any], where: str, findings: list[Finding]) -> None:
    role = task.get("role")
    if not isinstance(role, str) or not role:
        findings.append(Finding("FAIL", where, "`role` must be a non-empty string"))
    elif role not in ALLOWED_ROLES:
        findings.append(Finding("FAIL", where, f"`role` must be one of {sorted(ALLOWED_ROLES)}"))

    role_contract = task.get("role_contract")
    if role_contract is not None:
        if not isinstance(role_contract, str):
            findings.append(Finding("FAIL", where, "`role_contract` must be a string"))
        elif not repo_path_exists(role_contract):
            findings.append(Finding("FAIL", where, f"`role_contract` path does not exist: {role_contract}"))

    can_write_entries: list[Any] = []
    for field in ["can_read", "can_write", "evidence_packet"]:
        entries = validate_contract_entries(task, field, where, findings)
        if field == "can_write":
            can_write_entries = entries

    for entry in can_write_entries:
        if isinstance(entry, dict) and isinstance(entry.get("artifact_type"), str):
            validate_role_output_type(role, entry["artifact_type"], where, findings, "can_write.artifact_type")

    for entry in list_field(task, "cannot", where, findings):
        if not isinstance(entry, str):
            findings.append(Finding("FAIL", where, "`cannot` entries must be strings"))


def validate_role_output_type(
    role: Any,
    artifact_type: Any,
    where: str,
    findings: list[Finding],
    field: str = "outputs_expected.type",
) -> None:
    if not isinstance(role, str) or role not in RESTRICTED_ROLE_OUTPUT_TYPES:
        return
    if not isinstance(artifact_type, str):
        findings.append(Finding("FAIL", where, "`outputs_expected.type` must be a string"))
        return
    if artifact_type not in RESTRICTED_ROLE_OUTPUT_TYPES[role]:
        suggestion = ARTIFACT_TYPE_SUGGESTIONS.get(artifact_type)
        suggestion_text = f"; did you mean `{suggestion}`?" if suggestion else ""
        findings.append(
            Finding(
                "FAIL",
                where,
                f"role `{role}` cannot write `{field}` artifact type `{artifact_type}`; "
                f"allowed: {sorted(RESTRICTED_ROLE_OUTPUT_TYPES[role])}{suggestion_text}",
            )
        )


def positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def validate_execution_policy(
    task: dict[str, Any],
    where: str,
    project_root: Path,
    findings: list[Finding],
) -> None:
    policy = task.get("execution_policy")
    if policy is None:
        return
    if not isinstance(policy, dict):
        findings.append(Finding("FAIL", where, "`execution_policy` must be a mapping"))
        return

    if policy.get("mode") not in {None, "single_owner"}:
        findings.append(Finding("FAIL", where, "`execution_policy.mode` currently supports only `single_owner`"))

    for field in ["allow_parallel_subagents", "requires_claim"]:
        if field in policy and not isinstance(policy[field], bool):
            findings.append(Finding("FAIL", where, f"`execution_policy.{field}` must be a boolean"))

    for field in ["lease_ttl_minutes", "heartbeat_interval_minutes"]:
        if field in policy and not positive_int(policy[field]):
            findings.append(Finding("FAIL", where, f"`execution_policy.{field}` must be a positive integer"))

    ttl = policy.get("lease_ttl_minutes")
    heartbeat = policy.get("heartbeat_interval_minutes")
    if positive_int(ttl) and positive_int(heartbeat) and heartbeat >= ttl:
        findings.append(
            Finding("FAIL", where, "`execution_policy.heartbeat_interval_minutes` must be smaller than TTL")
        )

    owner_dir = policy.get("owner_dir")
    if owner_dir is not None and (not isinstance(owner_dir, str) or not is_safe_project_path(owner_dir, project_root)):
        findings.append(Finding("FAIL", where, f"`execution_policy.owner_dir` escapes project root: {owner_dir}"))

    exclusive_paths = policy.get("exclusive_paths")
    if exclusive_paths is not None:
        if not isinstance(exclusive_paths, list):
            findings.append(Finding("FAIL", where, "`execution_policy.exclusive_paths` must be a list"))
        else:
            normalized: set[str] = set()
            for path_token in exclusive_paths:
                if not isinstance(path_token, str) or not is_safe_project_path(path_token, project_root):
                    findings.append(
                        Finding("FAIL", where, f"`execution_policy.exclusive_paths` escapes project root: {path_token}")
                    )
                    continue
                normalized_path = normalize_project_path(path_token, project_root)
                if normalized_path in normalized:
                    findings.append(
                        Finding("FAIL", where, f"duplicate `execution_policy.exclusive_paths`: {path_token}")
                    )
                normalized.add(normalized_path)

    if policy.get("requires_claim") is True:
        if not isinstance(owner_dir, str) or not owner_dir:
            findings.append(Finding("FAIL", where, "`execution_policy.requires_claim` requires `owner_dir`"))
        if not isinstance(exclusive_paths, list) or not exclusive_paths:
            findings.append(Finding("FAIL", where, "`execution_policy.requires_claim` requires `exclusive_paths`"))


def task_requires_claim(task: dict[str, Any]) -> bool:
    policy = task.get("execution_policy")
    return isinstance(policy, dict) and policy.get("requires_claim") is True


def validate_lease_times(lease: dict[str, Any], where: str, findings: list[Finding]) -> None:
    for field in LEASE_TIME_FIELDS:
        if field in lease and not is_iso_datetime(lease[field]):
            findings.append(Finding("FAIL", where, f"`{field}` must be an ISO 8601 timestamp"))


def validate_lease_paths(
    lease: dict[str, Any],
    where: str,
    project_root: Path,
    findings: list[Finding],
) -> list[str]:
    normalized: list[str] = []
    owner_dir = lease.get("owner_dir")
    if not isinstance(owner_dir, str) or not is_safe_project_path(owner_dir, project_root):
        findings.append(Finding("FAIL", where, f"`owner_dir` escapes project root: {owner_dir}"))
    exclusive_paths = lease.get("exclusive_paths")
    if not isinstance(exclusive_paths, list) or not exclusive_paths:
        findings.append(Finding("FAIL", where, "`exclusive_paths` must be a non-empty list"))
        return normalized
    seen: set[str] = set()
    for path_token in exclusive_paths:
        if not isinstance(path_token, str) or not is_safe_project_path(path_token, project_root):
            findings.append(Finding("FAIL", where, f"`exclusive_paths` escapes project root: {path_token}"))
            continue
        normalized_path = normalize_project_path(path_token, project_root)
        if normalized_path in seen:
            findings.append(Finding("FAIL", where, f"duplicate `exclusive_paths`: {path_token}"))
        seen.add(normalized_path)
        normalized.append(normalized_path)
    return normalized


def validate_leases(
    research_dir: Path,
    tasks: dict[str, dict[str, Any]],
    where_by_id: dict[str, str],
    project_root: Path,
    findings: list[Finding],
) -> dict[str, list[dict[str, Any]]]:
    leases_dir = research_dir / "leases"
    active_by_task: dict[str, list[dict[str, Any]]] = {}
    if not leases_dir.exists():
        for task_id, task in tasks.items():
            if task.get("status") == "running" and task_requires_claim(task):
                findings.append(Finding("FAIL", where_by_id[task_id], "running task requires an active lease"))
        return active_by_task
    if not leases_dir.is_dir():
        findings.append(Finding("FAIL", rel(leases_dir, research_dir), "leases path must be a directory"))
        return active_by_task

    seen_lease_ids: set[str] = set()
    active_paths: list[tuple[str, str, str]] = []
    for lease_file in sorted(leases_dir.glob("*.json")):
        where = rel(lease_file, research_dir)
        lease = load_json_file(lease_file, findings, research_dir)
        if not lease:
            continue
        require_fields(
            lease,
            [
                "schema_version",
                "lease_id",
                "task_id",
                "owner_id",
                "role",
                "status",
                "acquired_at",
                "heartbeat_at",
                "expires_at",
                "owner_dir",
                "exclusive_paths",
            ],
            where,
            findings,
        )
        if lease.get("schema_version") != 1:
            findings.append(Finding("FAIL", where, "`schema_version` must be 1"))
        lease_id = lease.get("lease_id")
        if not isinstance(lease_id, str) or not lease_id:
            findings.append(Finding("FAIL", where, "`lease_id` must be a non-empty string"))
        elif lease_id in seen_lease_ids:
            findings.append(Finding("FAIL", where, f"duplicate lease_id: {lease_id}"))
        else:
            seen_lease_ids.add(lease_id)
        for field in ["task_id", "owner_id", "role"]:
            if not isinstance(lease.get(field), str) or not lease.get(field):
                findings.append(Finding("FAIL", where, f"`{field}` must be a non-empty string"))
        if lease.get("status") not in LEASE_STATUSES:
            findings.append(Finding("FAIL", where, f"`status` must be one of {sorted(LEASE_STATUSES)}"))
        validate_lease_times(lease, where, findings)
        normalized_paths = validate_lease_paths(lease, where, project_root, findings)
        if "job_ids" in lease and not isinstance(lease["job_ids"], list):
            findings.append(Finding("FAIL", where, "`job_ids` must be a list"))
        if "notes" in lease and not isinstance(lease["notes"], str):
            findings.append(Finding("FAIL", where, "`notes` must be a string"))

        task_id = lease.get("task_id")
        task = tasks.get(task_id) if isinstance(task_id, str) else None
        if task is None:
            findings.append(Finding("FAIL", where, f"`task_id` does not reference a task: {task_id}"))
        else:
            if lease.get("role") != task.get("role"):
                findings.append(Finding("FAIL", where, f"`role` does not match task role: {lease.get('role')}"))
            if lease.get("status") == "active" and task.get("status") != "running":
                findings.append(Finding("FAIL", where, "active lease task status must be running"))

        if lease.get("status") == "active" and isinstance(task_id, str):
            active_by_task.setdefault(task_id, []).append(lease)
            for normalized_path in normalized_paths:
                active_paths.append((normalized_path, str(task_id), where))
        walk_secret_keys(lease, where, findings)

    for task_id, active_leases in active_by_task.items():
        task = tasks.get(task_id, {})
        policy = task.get("execution_policy")
        if isinstance(policy, dict) and policy.get("mode") == "single_owner" and len(active_leases) > 1:
            findings.append(Finding("FAIL", where_by_id.get(task_id, task_id), "single_owner task has multiple active leases"))

    for idx, (left_path, left_task, left_where) in enumerate(active_paths):
        for right_path, right_task, right_where in active_paths[idx + 1 :]:
            if left_task == right_task:
                continue
            if project_paths_conflict(left_path, right_path):
                findings.append(
                    Finding(
                        "FAIL",
                        left_where,
                        f"active lease exclusive path conflicts with {right_where}: {left_path} vs {right_path}",
                    )
                )

    for task_id, task in tasks.items():
        if task.get("status") == "running" and task_requires_claim(task) and task_id not in active_by_task:
            findings.append(Finding("FAIL", where_by_id[task_id], "running task requires an active lease"))

    return active_by_task


def validate_jobs(
    research_dir: Path,
    tasks: dict[str, dict[str, Any]],
    project_root: Path,
    findings: list[Finding],
) -> None:
    root = research_dir / "jobs"
    if not root.exists():
        return
    if not root.is_dir():
        findings.append(Finding("FAIL", rel(root, research_dir), "jobs path must be a directory"))
        return

    leases: dict[str, dict[str, Any]] = {}
    leases_dir = research_dir / "leases"
    if leases_dir.is_dir():
        for path in sorted(leases_dir.glob("*.json")):
            lease = load_json_file(path, [], research_dir)
            lease_id = lease.get("lease_id")
            if isinstance(lease_id, str) and lease_id:
                leases[lease_id] = lease

    seen_attempts: set[str] = set()
    seen_submissions: set[str] = set()
    active_by_workdir: dict[str, list[str]] = {}
    jobs_by_id: dict[str, dict[str, Any]] = {}
    where_by_attempt: dict[str, str] = {}
    for path in sorted(root.glob("*.json")):
        where = rel(path, research_dir)
        job = load_json_file(path, findings, research_dir)
        if not job:
            continue
        require_fields(
            job,
            [
                "schema_version",
                "attempt_id",
                "submission_id",
                "task_id",
                "lease_id",
                "owner_id",
                "scheduler",
                "scheduler_job_name",
                "state",
                "workdir",
                "script",
                "created_at",
                "updated_at",
            ],
            where,
            findings,
        )
        if job.get("schema_version") != 1:
            findings.append(Finding("FAIL", where, "`schema_version` must be 1"))
        attempt_id = job.get("attempt_id")
        if not isinstance(attempt_id, str) or not attempt_id:
            findings.append(Finding("FAIL", where, "`attempt_id` must be a non-empty string"))
        elif attempt_id in seen_attempts:
            findings.append(Finding("FAIL", where, f"duplicate attempt_id: {attempt_id}"))
        else:
            seen_attempts.add(attempt_id)
            jobs_by_id[attempt_id] = job
            where_by_attempt[attempt_id] = where
        submission_id = job.get("submission_id")
        if not isinstance(submission_id, str) or not submission_id:
            findings.append(Finding("FAIL", where, "`submission_id` must be a non-empty string"))
        elif submission_id in seen_submissions:
            findings.append(Finding("FAIL", where, f"duplicate submission_id: {submission_id}"))
        else:
            seen_submissions.add(submission_id)
        task_id = job.get("task_id")
        if task_id not in tasks:
            findings.append(Finding("FAIL", where, f"`task_id` does not reference a task: {task_id}"))
        lease_id = job.get("lease_id")
        lease = leases.get(lease_id) if isinstance(lease_id, str) else None
        if lease is None:
            findings.append(Finding("FAIL", where, f"`lease_id` does not reference a lease: {lease_id}"))
        else:
            if lease.get("task_id") != task_id:
                findings.append(Finding("FAIL", where, "job task_id does not match its lease"))
            if lease.get("owner_id") != job.get("owner_id"):
                findings.append(Finding("FAIL", where, "job owner_id does not match its lease"))
            if job.get("state") in ACTIVE_JOB_STATES and lease.get("status") in {"released", "cancelled", "superseded"}:
                findings.append(Finding("FAIL", where, "active job references a closed lease"))
        state = job.get("state")
        if state not in JOB_STATES:
            findings.append(Finding("FAIL", where, f"`state` must be one of {sorted(JOB_STATES)}"))
        if job.get("scheduler") != "slurm":
            findings.append(Finding("FAIL", where, "`scheduler` must be `slurm` in schema version 1"))
        job_id = job.get("job_id")
        submission_failed = state == "failed" and isinstance(
            job.get("submission_failed_at"), str
        )
        if (
            state not in {"submitting", "submission_unknown"}
            and not submission_failed
            and not isinstance(job_id, str)
        ):
            findings.append(Finding("FAIL", where, "recorded scheduler state requires a string `job_id`"))
        for field in ["created_at", "updated_at", "submitted_at", "submission_failed_at"]:
            if field in job and not is_iso_datetime(job[field]):
                findings.append(Finding("FAIL", where, f"`{field}` must be an ISO 8601 datetime"))
        workdir = job.get("workdir")
        if not isinstance(workdir, str) or not is_safe_project_path(workdir, project_root):
            findings.append(Finding("FAIL", where, f"unsafe project-relative workdir: {workdir}"))
        else:
            normalized = normalize_project_path(workdir, project_root)
            if state in ACTIVE_JOB_STATES:
                active_by_workdir.setdefault(normalized, []).append(str(attempt_id))
        script = job.get("script")
        if not isinstance(script, str) or not is_safe_project_path(script, project_root):
            findings.append(Finding("FAIL", where, f"unsafe project-relative script: {script}"))

    for workdir, attempts in active_by_workdir.items():
        if len(attempts) > 1:
            findings.append(
                Finding("FAIL", "jobs", f"multiple active attempts for {workdir}: {', '.join(attempts)}")
            )

    for attempt_id, job in jobs_by_id.items():
        parent_id = job.get("parent_attempt_id")
        if parent_id is None:
            continue
        parent = jobs_by_id.get(parent_id) if isinstance(parent_id, str) else None
        where = where_by_attempt[attempt_id]
        if parent is None:
            findings.append(Finding("FAIL", where, f"parent_attempt_id does not reference an attempt: {parent_id}"))
            continue
        if parent_id == attempt_id:
            findings.append(Finding("FAIL", where, "attempt cannot be its own parent"))
        if parent.get("task_id") != job.get("task_id") or parent.get("workdir") != job.get("workdir"):
            findings.append(Finding("FAIL", where, "parent attempt must belong to the same task and workdir"))

    for workdir, attempts in active_by_workdir.items():
        pointer_path = project_root / workdir / ".aicc-active-job.json"
        if not pointer_path.exists():
            findings.append(Finding("WARN", rel(pointer_path, research_dir), "job workdir is missing its active-attempt pointer; duplicate-submission protection is degraded until `reconcile_jobs.py --attempt <id>` restores it or the attempt is resolved"))
            continue
        pointer = load_json_file(pointer_path, findings, research_dir)
        pointer_id = pointer.get("attempt_id")
        pointed = jobs_by_id.get(pointer_id) if isinstance(pointer_id, str) else None
        if pointed is None:
            findings.append(Finding("FAIL", rel(pointer_path, research_dir), f"pointer references missing attempt: {pointer_id}"))
        elif pointed.get("workdir") != workdir:
            findings.append(Finding("FAIL", rel(pointer_path, research_dir), "pointer attempt belongs to a different workdir"))
        elif pointer_id not in attempts:
            findings.append(Finding("FAIL", rel(pointer_path, research_dir), "pointer does not reference the active attempt for this workdir"))


def validate_project(project: dict[str, Any], where: str, findings: list[Finding]) -> None:
    require_fields(
        project,
        ["schema_version", "project_id", "title", "mode", "created_at", "objective", "success_criteria", "default_policy"],
        where,
        findings,
    )
    if project.get("schema_version") != 1:
        findings.append(Finding("FAIL", where, "`schema_version` must be 1"))
    if project.get("mode") not in PROJECT_MODES:
        findings.append(Finding("FAIL", where, f"`mode` must be one of {sorted(PROJECT_MODES)}"))
    if not isinstance(project.get("success_criteria"), list):
        findings.append(Finding("FAIL", where, "`success_criteria` must be a list"))
    if not isinstance(project.get("default_policy"), dict):
        findings.append(Finding("FAIL", where, "`default_policy` must be a mapping"))


def validate_task(
    task: dict[str, Any],
    where: str,
    project_root: Path,
    artifact_ids: set[str],
    findings: list[Finding],
) -> list[str]:
    require_fields(
        task,
        [
            "schema_version",
            "id",
            "title",
            "role",
            "skill",
            "status",
            "depends_on",
            "approval",
            "inputs",
            "outputs_expected",
            "success_criteria",
            "assumptions",
            "provenance",
        ],
        where,
        findings,
    )
    if task.get("schema_version") != 1:
        findings.append(Finding("FAIL", where, "`schema_version` must be 1"))
    if task.get("status") == "ready":
        findings.append(Finding("FAIL", where, "`ready` is derived by ready_tasks.py and must not be persisted"))
    elif task.get("status") not in TASK_STATUSES:
        findings.append(Finding("FAIL", where, f"`status` must be one of {sorted(TASK_STATUSES)}"))
    skill = task.get("skill")
    if not isinstance(skill, str) or not skill:
        findings.append(Finding("FAIL", where, "`skill` must be a non-empty string"))
    elif skill not in REPO_SKILLS:
        findings.append(Finding("FAIL", where, f"unknown `skill`: {skill}; known repo skills: {sorted(REPO_SKILLS)}"))
    validate_task_role_contract(task, where, findings)

    for field in ["depends_on", "inputs", "outputs_expected", "success_criteria", "assumptions", "provenance"]:
        list_field(task, field, where, findings)

    for field in ["knowledge_required", "required_refs"]:
        for token in list_field(task, field, where, findings):
            if not isinstance(token, str):
                findings.append(Finding("FAIL", where, f"`{field}` entries must be strings"))
            elif not repo_path_exists(token):
                findings.append(Finding("FAIL", where, f"`{field}` path does not exist: {token}"))

    output_ids: list[str] = []
    for inp in list_field(task, "inputs", where, findings):
        if not isinstance(inp, dict):
            findings.append(Finding("FAIL", where, "`inputs` entries must be mappings"))
            continue
        if "artifact_id" in inp:
            artifact_id = inp.get("artifact_id")
            if not isinstance(artifact_id, str) or not artifact_id:
                findings.append(Finding("FAIL", where, "`inputs.artifact_id` must be a non-empty string"))
            elif artifact_id not in artifact_ids and not inp.get("optional", False):
                findings.append(Finding("FAIL", where, f"input artifact does not exist: {artifact_id}"))
        elif "path" in inp:
            token = inp.get("path")
            if not isinstance(token, str) or not is_safe_project_path(token, project_root):
                findings.append(Finding("FAIL", where, f"input path escapes project root: {token}"))
            elif not inp.get("optional", False) and not file_input_exists(token, project_root):
                findings.append(Finding("FAIL", where, f"input file does not exist: {token}"))
        else:
            findings.append(Finding("FAIL", where, "input must declare `artifact_id` or `path`"))

    for out in list_field(task, "outputs_expected", where, findings):
        if not isinstance(out, dict):
            findings.append(Finding("FAIL", where, "`outputs_expected` entries must be mappings"))
            continue
        require_fields(out, ["artifact_id", "type", "path"], where, findings)
        artifact_id = out.get("artifact_id")
        if isinstance(artifact_id, str):
            output_ids.append(artifact_id)
        validate_role_output_type(task.get("role"), out.get("type"), where, findings)
        token = out.get("path")
        if not isinstance(token, str) or not is_safe_project_path(token, project_root):
            findings.append(Finding("FAIL", where, f"output path escapes project root: {token}"))

    validate_execution_policy(task, where, project_root, findings)

    return output_ids


def validate_artifacts(
    rows: list[dict[str, Any]],
    task_ids: set[str],
    project_root: Path,
    root: Path,
    findings: list[Finding],
) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    active_ids: set[str] = set()
    for idx, obj in enumerate(rows, 1):
        where = f"{rel(root / 'artifacts.jsonl', root)}:{idx}"
        require_fields(obj, ["artifact_id", "type", "path", "produced_by", "status", "created_at", "provenance"], where, findings)
        artifact_id = obj.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id:
            findings.append(Finding("FAIL", where, "`artifact_id` must be a non-empty string"))
            continue
        if obj.get("status") not in ARTIFACT_STATUSES:
            findings.append(Finding("FAIL", where, f"`status` must be one of {sorted(ARTIFACT_STATUSES)}"))
        if artifact_id in artifacts and obj.get("status") != "superseded":
            findings.append(Finding("FAIL", where, f"duplicate active artifact_id: {artifact_id}"))
        artifacts[artifact_id] = obj
        if obj.get("status") != "superseded":
            if artifact_id in active_ids:
                findings.append(Finding("FAIL", where, f"duplicate non-superseded artifact_id: {artifact_id}"))
            active_ids.add(artifact_id)
        produced_by = obj.get("produced_by")
        if produced_by != "external" and produced_by not in task_ids:
            findings.append(Finding("FAIL", where, f"`produced_by` does not reference a task: {produced_by}"))
        path_token = obj.get("path")
        if not isinstance(path_token, str) or not is_safe_project_path(path_token, project_root):
            findings.append(Finding("FAIL", where, f"artifact path escapes project root: {path_token}"))
        else:
            canonical_hint = duplicated_project_root_prefix_hint(path_token, project_root)
            if canonical_hint is not None:
                findings.append(
                    Finding(
                        "WARN",
                        where,
                        "artifact path appears to include the project-root directory "
                        f"`{project_root.name}` as a duplicate prefix; use `{canonical_hint}` "
                        "because paths are relative to the parent of `.research`",
                    )
                )
        if not isinstance(obj.get("provenance"), list):
            findings.append(Finding("FAIL", where, "`provenance` must be a list"))
        if obj.get("status") == "accepted":
            for field in ["path", "provenance", "status"]:
                if not obj.get(field):
                    findings.append(Finding("FAIL", where, f"accepted artifact missing `{field}`"))
        if any(key in obj for key in ["value", "values", "energy", "energies"]) and "units" not in obj:
            findings.append(Finding("FAIL", where, "numeric artifact-like fields require `units`"))
        for field in ["knowledge_used", "validated_by"]:
            if field in obj and not isinstance(obj[field], list):
                findings.append(Finding("FAIL", where, f"`{field}` must be a list"))
        for field in ["lease_id", "job_id"]:
            if field in obj and not isinstance(obj[field], str):
                findings.append(Finding("FAIL", where, f"`{field}` must be a string"))
        walk_secret_keys(obj, where, findings)
    return artifacts


def validate_artifact_role_outputs(
    artifacts: dict[str, dict[str, Any]],
    tasks: dict[str, dict[str, Any]],
    project_root: Path,
    root: Path,
    findings: list[Finding],
) -> None:
    for artifact_id, row in artifacts.items():
        produced_by = row.get("produced_by")
        if not isinstance(produced_by, str) or produced_by == "external":
            continue
        task = tasks.get(produced_by)
        if task is None:
            continue
        where = f"{rel(root / 'artifacts.jsonl', root)}:{artifact_id}"
        validate_role_output_type(task.get("role"), row.get("type"), where, findings, "artifact.type")

        gate_name = artifact_gate_name(row, project_root)
        if gate_name == "structure_gate" and task.get("role") not in STRUCTURE_GATE_PRODUCER_ROLES:
            findings.append(
                Finding(
                    "FAIL",
                    where,
                    "`structure_gate` artifacts must be produced by an independent "
                    "`structure-critic` or `surface-literature-reviewer`, not "
                    f"`{task.get('role')}`",
                )
            )


def validate_decisions(rows: list[dict[str, Any]], task_ids: set[str], artifact_ids: set[str], root: Path, findings: list[Finding]) -> None:
    seen: set[str] = set()
    for idx, obj in enumerate(rows, 1):
        where = f"{rel(root / 'decisions.jsonl', root)}:{idx}"
        require_fields(obj, ["decision_id", "kind", "decision", "by", "reason", "created_at"], where, findings)
        decision_id = obj.get("decision_id")
        if decision_id in seen:
            findings.append(Finding("FAIL", where, f"duplicate decision_id: {decision_id}"))
        if isinstance(decision_id, str):
            seen.add(decision_id)
        if "task_id" in obj and obj["task_id"] not in task_ids:
            findings.append(Finding("FAIL", where, f"`task_id` does not reference a task: {obj['task_id']}"))
        if "artifact_id" in obj and obj["artifact_id"] not in artifact_ids:
            findings.append(Finding("FAIL", where, f"`artifact_id` does not reference an artifact: {obj['artifact_id']}"))
        walk_secret_keys(obj, where, findings)


def validate_events(rows: list[dict[str, Any]], task_ids: set[str], artifact_ids: set[str], root: Path, findings: list[Finding]) -> None:
    seen: set[str] = set()
    for idx, obj in enumerate(rows, 1):
        where = f"{rel(root / 'events.jsonl', root)}:{idx}"
        require_fields(obj, ["event_id", "event", "created_at"], where, findings)
        event_id = obj.get("event_id")
        if event_id in seen:
            findings.append(Finding("FAIL", where, f"duplicate event_id: {event_id}"))
        if isinstance(event_id, str):
            seen.add(event_id)
        if "task_id" in obj and obj["task_id"] not in task_ids:
            findings.append(Finding("FAIL", where, f"`task_id` does not reference a task: {obj['task_id']}"))
        if "artifact_id" in obj and obj["artifact_id"] not in artifact_ids:
            findings.append(Finding("FAIL", where, f"`artifact_id` does not reference an artifact: {obj['artifact_id']}"))
        if obj.get("event") == "status_changed":
            for field in ["from", "to"]:
                if field in obj and obj[field] not in TASK_STATUSES and obj[field] not in ARTIFACT_STATUSES:
                    findings.append(Finding("FAIL", where, f"`{field}` is not a known task/artifact status: {obj[field]}"))
        walk_secret_keys(obj, where, findings)


def load_validated_state(path: Path) -> tuple[LoadedResearchState, list[Finding]]:
    """Load project state once and return it with authoritative validation findings."""

    findings: list[Finding] = []
    research_dir, project_root = resolve_research_dir(path)

    if not research_dir.is_dir():
        state = LoadedResearchState(research_dir, project_root, {}, {}, [], [], [])
        return state, [Finding("FAIL", research_dir.as_posix(), "research state directory does not exist")]

    project_path = research_dir / "project.yaml"
    tasks_dir = research_dir / "tasks"
    if not project_path.is_file():
        findings.append(Finding("FAIL", rel(project_path, research_dir), "project.yaml is missing"))
    if not tasks_dir.is_dir():
        findings.append(Finding("FAIL", rel(tasks_dir, research_dir), "tasks/ directory is missing"))

    project = load_yaml(project_path, findings, research_dir) if project_path.exists() else {}
    if project:
        validate_project(project, rel(project_path, research_dir), findings)

    task_files = sorted(tasks_dir.glob("*.yaml")) if tasks_dir.exists() else []
    if not task_files:
        findings.append(Finding("FAIL", rel(tasks_dir, research_dir), "no task YAML files found"))

    raw_artifacts = load_jsonl(research_dir / "artifacts.jsonl", findings, research_dir)
    raw_decisions = load_jsonl(research_dir / "decisions.jsonl", findings, research_dir)
    raw_events = load_jsonl(research_dir / "events.jsonl", findings, research_dir)

    tasks: dict[str, dict[str, Any]] = {}
    where_by_id: dict[str, str] = {}
    for task_file in task_files:
        task = load_yaml(task_file, findings, research_dir)
        task_id = task.get("id")
        where = rel(task_file, research_dir)
        if not isinstance(task_id, str) or not task_id:
            findings.append(Finding("FAIL", where, "`id` must be a non-empty string"))
            continue
        if task_id in tasks:
            findings.append(Finding("FAIL", where, f"duplicate task id: {task_id}"))
        tasks[task_id] = task
        where_by_id[task_id] = where

    artifacts = validate_artifacts(raw_artifacts, set(tasks), project_root, research_dir, findings)
    artifact_ids = set(artifacts)

    all_output_ids: dict[str, str] = {}
    declared_output_ids: set[str] = set()
    declared_output_gate_by_id: dict[str, str] = {}
    for task in tasks.values():
        for out in task.get("outputs_expected") or []:
            if isinstance(out, dict) and isinstance(out.get("artifact_id"), str):
                declared_output_ids.add(out["artifact_id"])
                gate_name = declared_output_gate_name(out)
                if gate_name:
                    declared_output_gate_by_id[out["artifact_id"]] = gate_name

    known_artifact_ids = artifact_ids | declared_output_ids

    for task_id, task in tasks.items():
        output_ids = validate_task(task, where_by_id[task_id], project_root, known_artifact_ids, findings)
        for output_id in output_ids:
            if output_id in all_output_ids:
                findings.append(Finding("FAIL", where_by_id[task_id], f"duplicate expected output artifact: {output_id}"))
            all_output_ids[output_id] = task_id

    validate_artifact_role_outputs(artifacts, tasks, project_root, research_dir, findings)

    for task_id, task in tasks.items():
        for dep in task.get("depends_on") or []:
            if dep not in tasks:
                findings.append(Finding("FAIL", where_by_id[task_id], f"depends_on references missing task: {dep}"))
    detect_cycle(tasks, where_by_id, findings)
    validate_first_submit_boundary(tasks, artifacts, declared_output_gate_by_id, where_by_id, project_root, findings)
    validate_leases(research_dir, tasks, where_by_id, project_root, findings)
    validate_jobs(research_dir, tasks, project_root, findings)

    validate_decisions(raw_decisions, set(tasks), artifact_ids, research_dir, findings)
    validate_events(raw_events, set(tasks), artifact_ids, research_dir, findings)

    state = LoadedResearchState(
        research_dir=research_dir,
        project_root=project_root,
        project=project,
        tasks=tasks,
        artifacts=raw_artifacts,
        decisions=raw_decisions,
        events=raw_events,
    )
    return state, findings


def validate(path: Path) -> list[Finding]:
    """Validate a project while preserving the original findings-only API."""

    _state, findings = load_validated_state(path)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to .research directory or a project root containing .research")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable findings")
    args = parser.parse_args()

    findings = validate(Path(args.path))
    failures = [finding for finding in findings if finding.level == "FAIL"]

    if args.json:
        print(json.dumps([finding.__dict__ for finding in findings], indent=2, sort_keys=True))
    else:
        for finding in findings:
            print(f"{finding.level}  {finding.path}  {finding.message}")
        if failures:
            print(f"\n== validate_state: {len(failures)} failure(s) ==")
        else:
            print("\n== validate_state: clean ==")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
