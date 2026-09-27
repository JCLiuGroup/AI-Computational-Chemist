"""Shared helpers for lease-bound scheduler job attempts."""

from __future__ import annotations

import json
import os
import shutil
import socket
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from lease_utils import iso, load_current_lease, now_local, write_json_atomic
from validate_state import is_safe_project_path, normalize_project_path


ACTIVE_JOB_STATES = {"submitting", "submission_unknown", "pending", "running"}
TERMINAL_JOB_STATES = {"completed", "failed", "cancelled", "timeout"}
JOB_STATES = ACTIVE_JOB_STATES | TERMINAL_JOB_STATES
DEFAULT_LOCK_WAIT_SECONDS = 3.0
LOCK_RETRY_SECONDS = 0.05
# A `submitting` attempt younger than this is presumed to still have a live
# submitter talking to sbatch. Automatic reconcile backs off below this age,
# and submit_job's --timeout must stay below it so a live sbatch can never be
# mistaken for an abandoned one.
SUBMITTING_GRACE_SECONDS = 120.0


def jobs_dir(research_dir: Path) -> Path:
    return research_dir / "jobs"


def job_path(research_dir: Path, attempt_id: str) -> Path:
    return jobs_dir(research_dir) / f"{attempt_id}.json"


def active_pointer_path(run_dir: Path) -> Path:
    return run_dir / ".aicc-active-job.json"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read JSON state {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"JSON state must contain an object: {path}")
    return value


def load_job(research_dir: Path, attempt_id: str) -> dict[str, Any] | None:
    path = job_path(research_dir, attempt_id)
    return load_json(path) if path.is_file() else None


def load_jobs(research_dir: Path) -> list[dict[str, Any]]:
    root = jobs_dir(research_dir)
    if not root.is_dir():
        return []
    return [load_json(path) for path in sorted(root.glob("*.json"))]


def write_job(research_dir: Path, job: dict[str, Any]) -> None:
    write_json_atomic(job_path(research_dir, str(job["attempt_id"])), job)


def new_attempt_id() -> str:
    return f"J-{uuid.uuid4().hex}"


def new_submission_id() -> str:
    return uuid.uuid4().hex


def scheduler_job_name(submission_id: str) -> str:
    return f"aicc-{submission_id[:20]}"


def project_relative(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise SystemExit(f"path escapes project root: {path}") from exc


def require_run_dir_owned(
    project_root: Path, run_dir: Path, lease: dict[str, Any]
) -> str:
    relative = project_relative(run_dir, project_root)
    candidate = normalize_project_path(relative, project_root)
    owned = False
    for token in lease.get("exclusive_paths") or []:
        if not isinstance(token, str) or not is_safe_project_path(token, project_root):
            continue
        protected = normalize_project_path(token, project_root).rstrip("/")
        if (
            protected in {"", "."}
            or candidate == protected
            or candidate.startswith(protected + "/")
        ):
            owned = True
            break
    if not owned:
        raise SystemExit(
            f"run directory is outside lease exclusive_paths: {relative}"
        )
    return relative


def require_active_lease(
    research_dir: Path, task_id: str, owner_id: str
) -> dict[str, Any]:
    lease = load_current_lease(research_dir, task_id)
    if not lease or lease.get("status") != "active":
        raise SystemExit(f"task has no active lease: {task_id}")
    if lease.get("owner_id") != owner_id:
        raise SystemExit(
            f"lease owner mismatch: {lease.get('owner_id')} != {owner_id}"
        )
    return lease


def append_job_id_to_lease(
    research_dir: Path, task_id: str, lease_id: str, owner_id: str, job_id: str
) -> None:
    lease = require_active_lease(research_dir, task_id, owner_id)
    if lease.get("lease_id") != lease_id:
        raise SystemExit(
            f"lease changed during submission: {lease.get('lease_id')} != {lease_id}"
        )
    job_ids = [str(value) for value in lease.get("job_ids") or []]
    if job_id not in job_ids:
        job_ids.append(job_id)
    lease["job_ids"] = job_ids
    from lease_utils import lease_path

    write_json_atomic(lease_path(research_dir, task_id), lease)


def current_attempt(research_dir: Path, run_dir: Path) -> dict[str, Any] | None:
    pointer_path = active_pointer_path(run_dir)
    if not pointer_path.is_file():
        return None
    pointer = load_json(pointer_path)
    attempt_id = pointer.get("attempt_id")
    if not isinstance(attempt_id, str) or not attempt_id:
        raise SystemExit(f"active job pointer has no attempt_id: {pointer_path}")
    job = load_job(research_dir, attempt_id)
    if job is None:
        raise SystemExit(
            f"active job pointer references missing attempt {attempt_id}: {pointer_path}"
        )
    return job


def write_active_pointer(run_dir: Path, job: dict[str, Any]) -> None:
    write_json_atomic(
        active_pointer_path(run_dir),
        {
            "schema_version": 1,
            "attempt_id": job["attempt_id"],
            "submission_id": job["submission_id"],
        },
    )


def active_attempts_for_workdir(
    research_dir: Path, workdir_token: str
) -> list[dict[str, Any]]:
    """All active attempts recorded for a workdir, independent of the pointer.

    The run-dir pointer is a fast-path copy that can be lost (crash between the
    two writes, archived directory); the duplicate-submission guard must scan
    the authoritative records instead of trusting it.
    """
    return [
        job
        for job in load_jobs(research_dir)
        if job.get("workdir") == workdir_token
        and job.get("state") in ACTIVE_JOB_STATES
    ]


def active_jobs_for_lease(research_dir: Path, lease_id: str) -> list[dict[str, Any]]:
    return [
        job
        for job in load_jobs(research_dir)
        if job.get("lease_id") == lease_id and job.get("state") in ACTIVE_JOB_STATES
    ]


def read_lock_owner(lock_dir: Path) -> dict[str, Any] | None:
    path = lock_dir / "owner.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def process_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def lock_status(lock_dir: Path) -> tuple[str, dict[str, Any] | None]:
    if not lock_dir.is_dir():
        return "absent", None
    owner = read_lock_owner(lock_dir)
    if owner is None:
        return "unknown", None
    host = owner.get("host")
    pid = owner.get("pid")
    if host != socket.gethostname() or not isinstance(pid, int) or pid <= 0:
        return "unknown", owner
    return ("busy" if process_is_running(pid) else "stale"), owner


def lock_conflict_message(lock_dir: Path, purpose: str) -> str:
    status, owner = lock_status(lock_dir)
    details = ""
    if owner:
        details = (
            f" owner={owner.get('host', '?')}:{owner.get('pid', '?')}"
            f" created_at={owner.get('created_at', '?')}"
        )
    if status == "stale":
        return (
            f"stale {purpose} lock detected: {lock_dir};{details} "
            "recover it explicitly with `aicc job unlock`"
        )
    if status == "unknown":
        return (
            f"{purpose} lock owner cannot be verified: {lock_dir};{details} "
            "inspect it before using `aicc job unlock --force`"
        )
    return f"{purpose} is busy: {lock_dir};{details} retry later"


def recover_directory_lock(
    lock_dir: Path, purpose: str, *, force: bool = False
) -> tuple[str, dict[str, Any] | None]:
    status, owner = lock_status(lock_dir)
    if status == "absent":
        raise SystemExit(f"{purpose} lock does not exist: {lock_dir}")
    if status == "busy":
        raise SystemExit(
            f"refusing to recover an active {purpose} lock: {lock_dir} "
            f"owner={owner.get('host')}:{owner.get('pid')}"
        )
    if status != "stale" and not force:
        raise SystemExit(
            f"{purpose} lock owner cannot be proven stale: {lock_dir}; "
            "inspect owner.json and pass --force only when recovery is safe"
        )

    current_owner = read_lock_owner(lock_dir)
    if current_owner != owner:
        raise SystemExit(f"{purpose} lock owner changed during recovery: {lock_dir}")

    tombstone = lock_dir.with_name(
        f".{lock_dir.name}.recovered.{os.getpid()}.{uuid.uuid4().hex}"
    )
    try:
        lock_dir.rename(tombstone)
    except OSError as exc:
        raise SystemExit(f"could not recover {purpose} lock {lock_dir}: {exc}") from exc
    shutil.rmtree(tombstone, ignore_errors=True)
    return status, owner


@contextmanager
def directory_lock(
    lock_dir: Path,
    purpose: str,
    wait_seconds: float = DEFAULT_LOCK_WAIT_SECONDS,
) -> Iterator[None]:
    deadline = time.monotonic() + max(wait_seconds, 0.0)
    while True:
        try:
            lock_dir.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError as exc:
            if time.monotonic() >= deadline:
                raise SystemExit(lock_conflict_message(lock_dir, purpose)) from exc
            time.sleep(LOCK_RETRY_SECONDS)
    owner = {
        "schema_version": 1,
        "lock_id": uuid.uuid4().hex,
        "purpose": purpose,
        "host": socket.gethostname(),
        "pid": os.getpid(),
        "created_at": iso(now_local()),
    }
    write_json_atomic(lock_dir / "owner.json", owner)
    try:
        yield
    finally:
        shutil.rmtree(lock_dir, ignore_errors=True)


@contextmanager
def project_state_lock(research_dir: Path) -> Iterator[None]:
    with directory_lock(research_dir / ".locks" / "state.lock", "project state"):
        yield


@contextmanager
def run_submission_lock(run_dir: Path) -> Iterator[None]:
    with directory_lock(run_dir / ".aicc-submit.lock", "job submission"):
        yield
