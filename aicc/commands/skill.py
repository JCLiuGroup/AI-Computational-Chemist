"""Manage collection skills through ``aicc skill``."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.paths import skill_source_root as collection_root


MANAGED_START = "<!-- cdx_skill:auto-computational-chemist:start -->"
MANAGED_END = "<!-- cdx_skill:auto-computational-chemist:end -->"
CONFIG_COMMENT = "# auto-computational-chemist skills managed by cdx_skill"
HEADER_RE = re.compile(r"^\s*\[.*\]\s*(?:#.*)?$")
SKILL_HEADER_RE = re.compile(r"^\s*\[\[skills\.config\]\]\s*(?:#.*)?$")
PATH_RE = re.compile(r'^(\s*)path\s*=\s*(".*?"|\'.*?\')\s*(?:#.*)?$')
SCOPES = ("global", "local")


class SkillSourceError(RuntimeError):
    """Raised when the installed AICC collection cannot be read safely."""


@dataclass(frozen=True)
class StaleSymlink:
    """A removable stale link discovered before an explicit confirmation."""

    kind: str
    name: str
    path: Path
    target: Path
    reason: str


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def config_path() -> Path:
    return Path(
        os.environ.get("CDX_SKILL_CONFIG", codex_home() / "config.toml")
    ).expanduser()


def global_skills_dir() -> Path:
    return Path(os.environ.get("CDX_SKILL_DIR", codex_home() / "skills")).expanduser()


def local_skills_dir() -> Path:
    return Path.cwd() / ".agents" / "skills"


def global_agents_path() -> Path:
    return codex_home() / "AGENTS.md"


def local_agents_path() -> Path:
    return Path.cwd() / "AGENTS.md"


def source_agents_path() -> Path:
    return collection_root() / "AGENTS.md"


def source_agents_text() -> str:
    path = source_agents_path()
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise SkillSourceError(
            f"cannot read source instructions at {path}: {exc}"
        ) from exc


def managed_agents_text() -> str:
    return f"{MANAGED_START}\n{source_agents_text()}\n{MANAGED_END}\n"


def skill_sources() -> dict[str, Path]:
    sources: dict[str, Path] = {}
    root = collection_root()
    for parent in ("procedures", "tools"):
        base = root / parent
        if not base.is_dir():
            continue
        try:
            candidates = sorted(base.iterdir())
        except OSError as exc:
            raise SkillSourceError(
                f"cannot inspect skill sources under {base}: {exc}"
            ) from exc
        for candidate in candidates:
            if (candidate / "SKILL.md").is_file():
                sources.setdefault(candidate.name, candidate)
    return sources


def skill_names() -> tuple[str, ...]:
    return tuple(sorted(skill_sources()))


def source_skill_dir(name: str) -> Path | None:
    return skill_sources().get(name)


def lexical_path(path: str | Path) -> Path:
    expanded = os.path.expanduser(os.path.expandvars(str(path)))
    return Path(os.path.abspath(expanded))


def parse_toml_string(value: str) -> str | None:
    try:
        return tomllib.loads(f"value = {value}\n")["value"]
    except tomllib.TOMLDecodeError:
        return None


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def backup_path(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return path.with_name(f"{path.name}.bak.{timestamp}")


def print_diff(path: Path, old: str, new: str, label: str) -> None:
    diff = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=str(path),
        tofile=f"{path} ({label})",
    )
    sys.stdout.writelines(diff)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_name = ""
    original_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            tmp_name = handle.name
            handle.write(text)
        if original_mode is not None:
            os.chmod(tmp_name, original_mode)
        os.replace(tmp_name, path)
    except Exception:
        if tmp_name and Path(tmp_name).exists():
            Path(tmp_name).unlink()
        raise


def write_with_backup(path: Path, text: str, label: str, dry_run: bool) -> str:
    if path.is_symlink():
        raise RuntimeError(f"refusing to replace symlink: {path}")
    old = read_text(path)
    if old == text:
        return f"ok      {path} unchanged"
    if dry_run:
        print_diff(path, old, text, label)
        return f"dryrun  {path}"
    if path.exists():
        backup = backup_path(path)
        shutil.copy2(path, backup)
        atomic_write(path, text)
        return f"updated {path}; backup {backup}"
    atomic_write(path, text)
    return f"created {path}"


def remove_file_with_backup(path: Path, label: str, dry_run: bool) -> str:
    if path.is_symlink():
        raise RuntimeError(f"refusing to remove symlink as a regular file: {path}")
    old = read_text(path)
    if not path.exists():
        return f"ok      {path} absent"
    if dry_run:
        print_diff(path, old, "", label)
        return f"dryrun  remove {path}"
    backup = backup_path(path)
    shutil.copy2(path, backup)
    path.unlink()
    return f"removed {path}; backup {backup}"


def update_managed_block(existing: str, block: str) -> str:
    source = source_agents_text()
    if existing.strip() == source:
        return block

    start = existing.find(MANAGED_START)
    end = existing.find(MANAGED_END)
    if start != -1 and end != -1 and start < end:
        end += len(MANAGED_END)
        suffix_start = end
        if suffix_start < len(existing) and existing[suffix_start] == "\n":
            suffix_start += 1
        prefix = existing[:start].rstrip()
        suffix = existing[suffix_start:]
        if prefix:
            return prefix + "\n\n" + block + suffix
        return block + suffix.lstrip("\n")

    if not existing.strip():
        return block
    return existing.rstrip() + "\n\n" + block


def remove_managed_block(existing: str) -> tuple[str, bool]:
    source = source_agents_text()
    if existing.strip() == source:
        return "", True

    start = existing.find(MANAGED_START)
    end = existing.find(MANAGED_END)
    if start == -1 or end == -1 or start > end:
        return existing, False

    end += len(MANAGED_END)
    suffix_start = end
    if suffix_start < len(existing) and existing[suffix_start] == "\n":
        suffix_start += 1
    prefix = existing[:start].rstrip()
    suffix = existing[suffix_start:].lstrip("\n")
    if prefix and suffix:
        return prefix + "\n\n" + suffix, True
    if prefix:
        return prefix + "\n", True
    if suffix:
        return suffix, True
    return "", True


def managed_marker_error(text: str) -> str | None:
    start_count = text.count(MANAGED_START)
    end_count = text.count(MANAGED_END)
    if start_count == 0 and end_count == 0:
        return None
    if start_count != 1 or end_count != 1:
        return (
            "expected exactly one AICC managed marker pair, found "
            f"start={start_count} end={end_count}"
        )
    if text.find(MANAGED_START) > text.find(MANAGED_END):
        return "AICC managed end marker appears before its start marker"
    return None


def agents_status(path: Path) -> str:
    if path.is_symlink():
        if symlink_is_ours(path, source_agents_path()):
            return "on(link)"
        return "conflict(symlink)"
    if not path.exists():
        return "off"
    text = read_text(path)
    if managed_marker_error(text):
        return "conflict(markers)"
    if MANAGED_START in text:
        return "on(managed)"
    if text.strip() == source_agents_text():
        return "on(legacy)"
    return "custom/no-cdx-block"


def set_agents(path: Path, dry_run: bool, label: str) -> str:
    if path.is_symlink():
        if symlink_is_ours(path, source_agents_path()):
            return f"ok      {path} already links to {source_agents_path()}"
        raise RuntimeError(f"refusing to replace non-AICC instruction symlink: {path}")
    old = read_text(path)
    if error := managed_marker_error(old):
        raise RuntimeError(
            f"refusing to edit malformed AICC markers in {path}: {error}"
        )
    new_text = update_managed_block(old, managed_agents_text())
    return write_with_backup(path, new_text, label, dry_run)


def unset_agents(path: Path, dry_run: bool, label: str) -> str:
    if path.is_symlink():
        if not symlink_is_ours(path, source_agents_path()):
            raise RuntimeError(
                f"refusing to remove non-AICC instruction symlink: {path}"
            )
        backup = backup_path(path)
        if dry_run:
            return f"dryrun  remove {path}; preserve symlink backup {backup}"
        shutil.copy2(path, backup, follow_symlinks=False)
        path.unlink()
        return f"removed {path}; symlink backup {backup}"
    old = read_text(path)
    if error := managed_marker_error(old):
        raise RuntimeError(
            f"refusing to edit malformed AICC markers in {path}: {error}"
        )
    new, changed = remove_managed_block(old)
    if not changed:
        return f"ok      {path} has no AICC managed block"
    if not new.strip():
        return remove_file_with_backup(path, label, dry_run)
    return write_with_backup(path, new, label, dry_run)


def symlink_is_ours(dest: Path, target: Path) -> bool:
    return dest.is_symlink() and dest.resolve(strict=False) == target.resolve()


def symlink_target(dest: Path) -> Path:
    """Return a link target lexically, including when the target is missing."""

    raw_target = Path(os.readlink(dest))
    if not raw_target.is_absolute():
        raw_target = dest.parent / raw_target
    return lexical_path(raw_target)


def ensure_symlink(name: str, dest_dir: Path, dry_run: bool) -> str:
    source = source_skill_dir(name)
    if source is None:
        return f"missing {name}: source skill not found"
    target = source.resolve()
    dest = dest_dir / name
    if symlink_is_ours(dest, target):
        return f"ok      {name} -> {target}"

    if dest.exists() or dest.is_symlink():
        return f"conflict {name}: {dest} (not replaced)"

    if dry_run:
        return f"link    {name}: {dest} -> {target}"

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.symlink_to(target, target_is_directory=True)
    return f"link    {name}: {dest} -> {target}"


def remove_symlink(name: str, dest_dir: Path, dry_run: bool) -> str:
    source = source_skill_dir(name)
    dest = dest_dir / name
    if source is None:
        return f"missing {name}: source skill not found"
    if not dest.exists() and not dest.is_symlink():
        return f"ok      {name} absent"
    if symlink_is_ours(dest, source):
        if dry_run:
            return f"remove  {name}: {dest}"
        dest.unlink()
        return f"removed {name}: {dest}"
    return f"skip    {name}: not an AICC symlink ({dest})"


def symlink_status(name: str, dest_dir: Path) -> tuple[str, str]:
    source = source_skill_dir(name)
    dest = dest_dir / name
    if source is None:
        return "missing-source", str(dest)
    if not dest.exists() and not dest.is_symlink():
        return "off", str(dest)
    if symlink_is_ours(dest, source):
        return "on", str(source.resolve())
    return "conflict", str(dest)


def find_skill_blocks(lines: list[str]) -> list[tuple[int, int]]:
    starts = [idx for idx, line in enumerate(lines) if SKILL_HEADER_RE.match(line)]
    blocks: list[tuple[int, int]] = []
    for start in starts:
        end = len(lines)
        for idx in range(start + 1, len(lines)):
            if HEADER_RE.match(lines[idx]):
                end = idx
                break
        blocks.append((start, end))
    return blocks


def block_path(block: list[str]) -> str | None:
    for line in block:
        match = PATH_RE.match(line)
        if match:
            return parse_toml_string(match.group(2))
    return None


def config_path_matches_skill(raw_path: str) -> bool:
    raw = lexical_path(raw_path)
    for name, source in skill_sources().items():
        if raw == lexical_path(source / "SKILL.md"):
            return True
        installed = global_skills_dir() / name
        if raw == lexical_path(installed / "SKILL.md") and symlink_is_ours(
            installed, source
        ):
            return True
    return False


def config_path_is_retired_aicc_skill(raw_path: str) -> bool:
    """Recognize a managed legacy path without treating same-name user skills as ours."""

    raw = lexical_path(raw_path)
    parts = [part.lower() for part in raw.parts]
    if not ({"aicc", "auto-computational-chemist", ".auto-computational-chemist"} & set(parts)):
        return False
    if raw.name != "SKILL.md" or raw.parent.name not in skill_names():
        return False
    return raw.parent.parent.name in {"procedures", "tools"}


def path_has_aicc_collection_marker(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    return bool(
        {"aicc", "auto-computational-chemist", ".auto-computational-chemist"}
        & parts
    )


def is_verified_live_aicc_collection(root: Path) -> bool:
    """Require collection structure before claiming ownership of a live target."""

    return (
        path_has_aicc_collection_marker(root)
        and (root / "AGENTS.md").is_file()
        and (root / "aicc" / "aicc.py").is_file()
        and (root / "procedures").is_dir()
        and (root / "tools").is_dir()
    )


def is_verified_retired_skill_target(name: str, target: Path) -> bool:
    """Recognize a live skill only through a complete AICC collection root."""

    if target.name != name or target.parent.name not in {"procedures", "tools"}:
        return False
    root = target.parent.parent
    return (target / "SKILL.md").is_file() and is_verified_live_aicc_collection(root)


def stale_skill_symlink_reason(name: str, dest: Path) -> str | None:
    """Classify only an explicitly removable missing or retired AICC skill link."""

    if not dest.is_symlink():
        return None
    source = source_skill_dir(name)
    if source is None or symlink_is_ours(dest, source):
        return None
    target = symlink_target(dest)
    if not dest.exists():
        return "target is missing"
    if is_verified_retired_skill_target(name, target):
        return "target is a retired AICC skill path"
    return None


def stale_agents_symlink_reason(dest: Path) -> str | None:
    """Classify a missing or recognizably retired AICC instruction link."""

    if not dest.is_symlink() or symlink_is_ours(dest, source_agents_path()):
        return None
    target = symlink_target(dest)
    if not dest.exists():
        return "target is missing"
    if target.name == "AGENTS.md" and is_verified_live_aicc_collection(
        target.parent
    ):
        return "target is a retired AICC instruction path"
    return None


def cleaned_config_text(text: str) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    remove_ranges: list[tuple[int, int]] = []
    managed_group = False
    for start, end in find_skill_blocks(lines):
        raw_path = block_path(lines[start:end])
        comment_index = start - 1
        if comment_index >= 0 and not lines[comment_index].strip():
            comment_index -= 1
        if comment_index >= 0 and lines[comment_index].strip() == CONFIG_COMMENT:
            managed_group = True
        path_is_current = bool(raw_path and config_path_matches_skill(raw_path))
        path_is_retired = bool(
            raw_path
            and managed_group
            and config_path_is_retired_aicc_skill(raw_path)
        )
        if path_is_current or path_is_retired:
            remove_start = start
            if remove_start > 0 and lines[remove_start - 1].strip() == "":
                remove_start -= 1
            if remove_start > 0 and lines[remove_start - 1].strip() == CONFIG_COMMENT:
                remove_start -= 1
                if remove_start > 0 and lines[remove_start - 1].strip() == "":
                    remove_start -= 1
            remove_ranges.append((remove_start, end))
        elif managed_group:
            # A managed comment cannot prove ownership of a following arbitrary
            # user block. Stop carrying the group marker at the first unknown path.
            managed_group = False
        next_is_skill_block = end < len(lines) and bool(
            SKILL_HEADER_RE.match(lines[end])
        )
        if not next_is_skill_block:
            managed_group = False

    if not remove_ranges:
        return text, 0

    remove_indexes: set[int] = set()
    for start, end in remove_ranges:
        remove_indexes.update(range(start, end))
    new_text = "".join(
        line for idx, line in enumerate(lines) if idx not in remove_indexes
    )
    return new_text, len(remove_ranges)


def clean_config_blockers(dry_run: bool) -> tuple[str, int]:
    path = config_path()
    if path.is_symlink():
        raise RuntimeError(
            f"refusing to migrate symlinked Codex config: {path}; "
            "edit its target explicitly instead"
        )
    old = read_text(path)
    if not old.strip():
        return f"ok      {path} has no skill config", 0
    new, removed = cleaned_config_text(old)
    if removed == 0:
        return f"ok      {path} has no AICC blockers", 0
    tomllib.loads(new)
    if dry_run:
        print_diff(path, old, new, "clean-aicc-skill-config")
        return f"dryrun  remove {removed} AICC skill config block(s)", removed
    backup = backup_path(path)
    shutil.copy2(path, backup)
    atomic_write(path, new)
    return f"cleaned {removed} AICC skill config block(s); backup {backup}", removed


def config_blocker_count() -> int:
    _new, removed = cleaned_config_text(read_text(config_path()))
    return removed


def source_validation_errors() -> list[str]:
    root = collection_root()
    errors: list[str] = []
    if not root.is_dir():
        errors.append(f"AICC source root does not exist or is not a directory: {root}")
        return errors

    agents = source_agents_path()
    if not agents.is_file():
        errors.append(f"AICC source instructions are missing: {agents}")

    try:
        sources = skill_sources()
    except SkillSourceError as exc:
        errors.append(str(exc))
    else:
        if not sources:
            errors.append(
                f"no skills were discovered under {root}/procedures or {root}/tools"
            )
    return errors


def print_errors(errors: list[str]) -> None:
    for message in errors:
        print(f"aicc skill: {message}", file=sys.stderr)


def scope_paths(scope: str) -> tuple[Path, Path]:
    if scope == "global":
        return global_skills_dir(), global_agents_path()
    if scope == "local":
        return local_skills_dir(), local_agents_path()
    raise ValueError(f"unknown scope: {scope}")


def scope_rows(scope: str) -> list[dict[str, str]]:
    dest_dir, _agents_path = scope_paths(scope)
    return [
        {"name": name, "status": status, "path": path}
        for name in skill_names()
        for status, path in [symlink_status(name, dest_dir)]
    ]


def scope_conflicts(scope: str) -> list[tuple[str, Path]]:
    dest_dir, _agents_path = scope_paths(scope)
    conflicts: list[tuple[str, Path]] = []
    for name in skill_names():
        source = source_skill_dir(name)
        if source is None:
            continue
        dest = dest_dir / name
        if (dest.exists() or dest.is_symlink()) and not symlink_is_ours(dest, source):
            conflicts.append((name, dest))
    return conflicts


def stale_scope_symlinks(scope: str) -> list[StaleSymlink]:
    """Discover removable links without classifying live foreign entries as ours."""

    dest_dir, agents_path = scope_paths(scope)
    stale: list[StaleSymlink] = []
    for name in skill_names():
        dest = dest_dir / name
        reason = stale_skill_symlink_reason(name, dest)
        if reason:
            stale.append(
                StaleSymlink(
                    kind="skill",
                    name=name,
                    path=dest,
                    target=symlink_target(dest),
                    reason=reason,
                )
            )
    agents_reason = stale_agents_symlink_reason(agents_path)
    if agents_reason:
        stale.append(
            StaleSymlink(
                kind="instructions",
                name="AGENTS.md",
                path=agents_path,
                target=symlink_target(agents_path),
                reason=agents_reason,
            )
        )
    return stale


def local_skills_path_errors(dest_dir: Path) -> list[str]:
    """Reject local skill paths that escape the project through parent symlinks."""

    project_root = Path.cwd().resolve()
    errors: list[str] = []
    current = Path.cwd()
    for part in (".agents", "skills"):
        current /= part
        if current.is_symlink():
            errors.append(
                f"local skill path contains a symlink and will not be used: {current}"
            )
            return errors
        if current.exists() and not current.is_dir():
            errors.append(f"local skill path component is not a directory: {current}")
            return errors

    try:
        dest_dir.resolve(strict=False).relative_to(project_root)
    except ValueError:
        errors.append(f"local skill path escapes the current project: {dest_dir}")
    return errors


def scope_preflight_errors(scope: str) -> list[str]:
    errors = source_validation_errors()
    if errors:
        return errors

    dest_dir, agents_path = scope_paths(scope)
    if scope == "local":
        errors.extend(local_skills_path_errors(dest_dir))
        if errors:
            return errors

    for name, path in scope_conflicts(scope):
        errors.append(
            f"{scope} skill target conflicts with the current AICC source: {name} ({path})"
        )

    if agents_path.is_symlink() and not symlink_is_ours(
        agents_path, source_agents_path()
    ):
        errors.append(
            f"{scope} instruction path is a non-AICC symlink and will not be replaced: "
            f"{agents_path}"
        )
    elif agents_path.exists() and not agents_path.is_file():
        errors.append(f"{scope} instruction path is not a regular file: {agents_path}")
    elif agents_path.is_file():
        try:
            marker_error = managed_marker_error(read_text(agents_path))
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {scope} instruction file {agents_path}: {exc}")
        else:
            if marker_error:
                errors.append(
                    f"{scope} instruction file has malformed AICC markers: "
                    f"{agents_path} ({marker_error})"
                )
    return errors


def stale_scope_preflight_errors(scope: str) -> list[str]:
    """Validate source and destination containment without rejecting stale links."""

    errors = source_validation_errors()
    if errors:
        return errors
    dest_dir, _agents_path = scope_paths(scope)
    if scope == "local":
        errors.extend(local_skills_path_errors(dest_dir))
    return errors


def agents_active(status: str) -> bool:
    return status.startswith("on(")


def scope_summary(scope: str) -> dict[str, Any]:
    dest_dir, agents_path = scope_paths(scope)
    rows = scope_rows(scope)
    skill_on = sum(row["status"] == "on" for row in rows)
    conflicts = sum(row["status"] == "conflict" for row in rows)
    missing_sources = sum(row["status"] == "missing-source" for row in rows)
    agents = agents_status(agents_path)

    if rows and skill_on == len(rows) and agents_active(agents):
        state = "on"
    elif (
        skill_on == 0
        and conflicts == 0
        and missing_sources == 0
        and agents in {"off", "custom/no-cdx-block"}
    ):
        state = "off"
    else:
        state = "partial"

    return {
        "scope": scope,
        "state": state,
        "skill_on": skill_on,
        "skill_total": len(rows),
        "agents": agents,
        "conflicts": conflicts,
        "missing_sources": missing_sources,
        "skills_dir": dest_dir.as_posix(),
        "agents_path": agents_path.as_posix(),
    }


def effective_status(
    global_summary: dict[str, Any], local_summary: dict[str, Any], blockers: int
) -> str:
    if blockers:
        return "blocked by legacy config"
    if local_summary["state"] == "on":
        return "on via local"
    if global_summary["state"] == "on":
        if local_summary["state"] == "partial":
            return "on via global (local partial)"
        return "on via global"
    if local_summary["state"] == "partial":
        return "partial via local"
    if global_summary["state"] == "partial":
        return "partial via global"
    return "off"


def status_payload() -> dict[str, Any]:
    global_summary = scope_summary("global")
    local_summary = scope_summary("local")
    blockers = config_blocker_count()
    return {
        "schema_version": 1,
        "source_root": collection_root().as_posix(),
        "global": global_summary,
        "local": local_summary,
        "effective": effective_status(global_summary, local_summary, blockers),
        "legacy_config_blockers": blockers,
        "config_path": config_path().as_posix(),
    }


def format_scope_summary(summary: dict[str, Any]) -> str:
    detail = f"{summary['skill_on']}/{summary['skill_total']} skills, AGENTS {summary['agents']}"
    extras = []
    if summary["conflicts"]:
        extras.append(f"{summary['conflicts']} conflict(s)")
    if summary["missing_sources"]:
        extras.append(f"{summary['missing_sources']} missing source(s)")
    if extras:
        detail += ", " + ", ".join(extras)
    return f"{summary['scope']}: {summary['state']} ({detail})"


def emit_status(payload: dict[str, Any]) -> None:
    print(format_scope_summary(payload["global"]))
    print(format_scope_summary(payload["local"]))
    print(f"effective: {payload['effective']}")
    print(
        f"legacy config blockers: {payload['legacy_config_blockers']} ({payload['config_path']})"
    )


def emit_scope_list(scope: str) -> None:
    dest_dir, agents_path = scope_paths(scope)
    rows = scope_rows(scope)
    print(f"{scope} skills: {dest_dir}")
    print(f"{scope} AGENTS.md: {agents_status(agents_path)} ({agents_path})")
    if scope == "global":
        print(f"legacy config blockers: {config_blocker_count()} ({config_path()})")
    if not rows:
        print("(no skills discovered)")
        return
    name_width = max(len(row["name"]) for row in rows)
    status_width = max(len(row["status"]) for row in rows)
    for row in rows:
        print(
            f"{row['name']:<{name_width}}  {row['status']:<{status_width}}  {row['path']}"
        )


def set_scope(scope: str, dry_run: bool, force: bool = False) -> int:
    dest_dir, agents_path = scope_paths(scope)
    print(f"{scope}: skills -> {dest_dir}")
    if force:
        print(
            "aicc skill: --force does not replace copied or foreign entries; "
            "conflicts remain protected",
            file=sys.stderr,
        )
    errors = scope_preflight_errors(scope)
    if errors:
        print_errors(errors)
        return 1
    for name in skill_names():
        print(ensure_symlink(name, dest_dir, dry_run))
    print(set_agents(agents_path, dry_run, f"{scope}-agents-enable"))
    if scope == "global":
        print("Restart Codex for changes to take effect.")
    else:
        print("Restart or refresh the agent harness for changes to take effect.")
    return 0


def revalidate_stale_scope_symlink(candidate: StaleSymlink) -> None:
    """Refuse a candidate whose directory entry or ownership changed."""

    if not candidate.path.is_symlink() or symlink_target(
        candidate.path
    ) != candidate.target:
        raise RuntimeError(
            f"stale link changed during cleanup and was not removed: {candidate.path}"
        )
    reason = (
        stale_agents_symlink_reason(candidate.path)
        if candidate.kind == "instructions"
        else stale_skill_symlink_reason(candidate.name, candidate.path)
    )
    if reason is None:
        raise RuntimeError(
            f"link is no longer stale and was not removed: {candidate.path}"
        )


def remove_stale_scope_symlink(candidate: StaleSymlink, dry_run: bool) -> str:
    if dry_run:
        return f"dryrun  remove {candidate.kind} link: {candidate.path}"

    # Repeat the check here, rather than relying only on the batch preflight below:
    # another process may have changed a later directory entry in the meantime.
    revalidate_stale_scope_symlink(candidate)
    if candidate.kind == "instructions":
        backup = backup_path(candidate.path)
        shutil.copy2(candidate.path, backup, follow_symlinks=False)
        candidate.path.unlink()
        return f"removed instructions link: {candidate.path}; symlink backup {backup}"
    candidate.path.unlink()
    return f"removed skill link: {candidate.path}"


def cleanup_stale_scope(scope: str, dry_run: bool, confirm: bool) -> int:
    dest_dir, _agents_path = scope_paths(scope)
    print(f"{scope}: stale links under {dest_dir}")
    errors = stale_scope_preflight_errors(scope)
    if errors:
        print_errors(errors)
        return 1

    candidates = stale_scope_symlinks(scope)
    if not candidates:
        print(f"ok      no stale AICC skill or instruction links found in {scope} scope")
        return 0
    for candidate in candidates:
        print(
            f"stale   {candidate.kind} {candidate.name}: {candidate.path} -> "
            f"{candidate.target} ({candidate.reason})"
        )

    if not dry_run and not confirm:
        print(
            "aicc skill: stale cleanup requires --confirm; no links were removed",
            file=sys.stderr,
        )
        return 1

    # Preflight the complete candidate set before changing anything. Each entry is
    # checked again inside remove_stale_scope_symlink at its removal boundary.
    for candidate in candidates:
        revalidate_stale_scope_symlink(candidate)

    for candidate in candidates:
        print(remove_stale_scope_symlink(candidate, dry_run))
    if not dry_run:
        print("Restart or refresh the agent harness for changes to take effect.")
    return 0


def unset_scope(
    scope: str,
    dry_run: bool,
    stale: bool = False,
    confirm: bool = False,
) -> int:
    if confirm and not stale:
        raise RuntimeError("--confirm is only valid together with --stale")
    if stale:
        return cleanup_stale_scope(scope, dry_run, confirm)

    dest_dir, agents_path = scope_paths(scope)
    print(f"{scope}: skills -> {dest_dir}")
    errors = scope_preflight_errors(scope)
    if errors:
        print_errors(errors)
        return 1
    for name in skill_names():
        print(remove_symlink(name, dest_dir, dry_run))
    print(unset_agents(agents_path, dry_run, f"{scope}-agents-disable"))
    if scope == "global":
        print("Restart Codex for changes to take effect.")
    else:
        print("Restart or refresh the agent harness for changes to take effect.")
    return 0


def register(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "skill",
        help="Inspect or manage AICC skills (global scope is Codex-only)",
        description=(
            "Inspect or manage AICC skills. Local scope manages the current project; "
            "global scope manages Codex only."
        ),
    )
    commands = parser.add_subparsers(dest="skill_command", required=True)

    status = commands.add_parser(
        "status", help="Show effective global and local skill state"
    )
    status.add_argument(
        "--json", action="store_true", help="Emit machine-readable status"
    )
    status.set_defaults(handler=run_status)

    listing = commands.add_parser("list", help="List installed AICC skills")
    listing.add_argument(
        "--scope",
        choices=("all", *SCOPES),
        default="all",
        help="Scope to list; global refers to Codex only (default: all)",
    )
    listing.add_argument(
        "--json", action="store_true", help="Emit machine-readable rows"
    )
    listing.set_defaults(handler=run_list)

    for action, handler in (("enable", run_enable), ("disable", run_disable)):
        command = commands.add_parser(
            action,
            help=f"{action.title()} AICC skills (global scope is Codex-only)",
        )
        command.add_argument(
            "--scope",
            choices=SCOPES,
            required=True,
            help="Target scope; global manages Codex only",
        )
        command.add_argument(
            "--dry-run", action="store_true", help="Show changes without writing"
        )
        if action == "enable":
            command.add_argument(
                "--force",
                action="store_true",
                help="Compatibility flag; protected conflicts are never replaced",
            )
        else:
            command.add_argument(
                "--stale",
                action="store_true",
                help=(
                    "Remove only missing-target or verified retired AICC links; "
                    "current and live foreign links remain"
                ),
            )
            command.add_argument(
                "--confirm",
                action="store_true",
                help="Confirm link removal requested by --stale",
            )
        command.set_defaults(handler=handler)

    migrate = commands.add_parser(
        "migrate",
        help="Remove legacy AICC skill entries from the Codex config",
        description=(
            "Remove legacy AICC [[skills.config]] entries from the Codex config. "
            "This is the only skill command that writes the legacy Codex config."
        ),
    )
    migrate.add_argument(
        "--dry-run", action="store_true", help="Show the config diff without writing"
    )
    migrate.set_defaults(handler=run_migrate)


def report_command_error(exc: BaseException) -> int:
    print(f"aicc skill: {exc}", file=sys.stderr)
    return 1


def source_is_ready() -> bool:
    errors = source_validation_errors()
    if errors:
        print_errors(errors)
        return False
    return True


def run_status(args: argparse.Namespace) -> int:
    if not source_is_ready():
        return 1
    try:
        payload = status_payload()
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            emit_status(payload)
        return 0
    except (OSError, UnicodeError, RuntimeError, tomllib.TOMLDecodeError) as exc:
        return report_command_error(exc)


def run_list(args: argparse.Namespace) -> int:
    if not source_is_ready():
        return 1
    scopes = SCOPES if args.scope == "all" else (args.scope,)
    try:
        if args.json:
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source_root": collection_root().as_posix(),
                        "scopes": {
                            scope: {
                                "summary": scope_summary(scope),
                                "skills": scope_rows(scope),
                            }
                            for scope in scopes
                        },
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            for index, scope in enumerate(scopes):
                if index:
                    print()
                emit_scope_list(scope)
        return 0
    except (OSError, UnicodeError, RuntimeError, tomllib.TOMLDecodeError) as exc:
        return report_command_error(exc)


def run_enable(args: argparse.Namespace) -> int:
    try:
        return set_scope(args.scope, args.dry_run, args.force)
    except (OSError, UnicodeError, RuntimeError, tomllib.TOMLDecodeError) as exc:
        return report_command_error(exc)


def run_disable(args: argparse.Namespace) -> int:
    try:
        return unset_scope(args.scope, args.dry_run, args.stale, args.confirm)
    except (OSError, UnicodeError, RuntimeError, tomllib.TOMLDecodeError) as exc:
        return report_command_error(exc)


def run_migrate(args: argparse.Namespace) -> int:
    if not source_is_ready():
        return 1
    try:
        message, removed = clean_config_blockers(args.dry_run)
        print(message)
        if removed and not args.dry_run:
            print("Restart Codex for migrated config changes to take effect.")
        return 0
    except (OSError, UnicodeError, RuntimeError, tomllib.TOMLDecodeError) as exc:
        return report_command_error(exc)
