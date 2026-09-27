#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML>=6.0"]
# ///
"""Run AICC CLI, skill-safety, and installer smoke tests."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / "procedures" / "research-orchestrator" / "scripts"
EXAMPLES = REPO_ROOT / "procedures" / "research-orchestrator" / "examples"
sys.path.insert(0, str(SCRIPT_DIR))


def run(
    args: list[str],
    expect: int = 0,
    cwd: Path = REPO_ROOT,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode != expect:
        print("COMMAND FAILED:", " ".join(args))
        print("expected:", expect, "got:", result.returncode)
        if result.stdout:
            print("STDOUT:\n" + result.stdout)
        if result.stderr:
            print("STDERR:\n" + result.stderr)
        raise SystemExit(1)
    return result


def aicc_cli_flow() -> None:
    cli = REPO_ROOT / "aicc" / "aicc.py"
    fixture = EXAMPLES / "minimal-project"
    status_args = [
        "status",
        str(fixture),
        "--events",
        "0",
        "--now",
        "2026-07-11T16:30:00+08:00",
        "--json",
    ]
    research_dir = fixture / ".research"

    def research_digest(root: Path = research_dir) -> str:
        digest = hashlib.sha256()
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
        return digest.hexdigest()

    digest_before = research_digest()
    direct = run([sys.executable, str(cli), *status_args])
    if json.loads(direct.stdout).get("health") != "READY":
        raise SystemExit("top-level AICC status did not read the fixture project")
    if research_digest() != digest_before:
        raise SystemExit("aicc status modified the project .research state")

    naive_status = json.loads(
        run(
            [
                sys.executable,
                str(cli),
                "status",
                str(fixture),
                "--now",
                "2026-07-11T16:30:00",
                "--json",
            ]
        ).stdout
    )
    if naive_status.get("observed_at") is None:
        raise SystemExit("aicc status did not normalize a timezone-naive --now")
    malformed_now = run(
        [sys.executable, str(cli), "status", str(fixture), "--now", "not-a-time"],
        expect=2,
    )
    if "Traceback" in malformed_now.stderr or "invalid --now" not in malformed_now.stderr:
        raise SystemExit("aicc status malformed --now diagnostics are not actionable")
    malformed_task_now = run(
        [
            sys.executable,
            str(cli),
            "task",
            "show",
            str(fixture),
            "T003",
            "--now",
            "not-a-time",
        ],
        expect=2,
    )
    if "Traceback" in malformed_task_now.stderr or "invalid --now" not in malformed_task_now.stderr:
        raise SystemExit("aicc task show malformed --now diagnostics are not actionable")

    default_status = json.loads(
        run(
            [sys.executable, str(cli), "status", "--events", "0", "--json"],
            cwd=fixture,
        ).stdout
    )
    if default_status.get("research_dir") != research_dir.as_posix():
        raise SystemExit("aicc status did not default to the current project")

    ready = json.loads(
        run(
            [sys.executable, str(cli), "task", "ready", "--json"], cwd=fixture
        ).stdout
    )
    if [item["task_id"] for item in ready["ready"]] != ["T003"]:
        raise SystemExit("aicc task ready did not reuse derived readiness")
    shown = json.loads(
        run(
            [sys.executable, str(cli), "task", "show", "T003", "--json"],
            cwd=fixture,
        ).stdout
    )
    if (
        shown["task"].get("skill") != "structure-prep"
        or shown["derived"].get("action") != "ready"
    ):
        raise SystemExit("aicc task show omitted task protocol or derived state")
    run(
        [sys.executable, str(cli), "task", "check", "T003", "--dry-run"],
        cwd=fixture,
    )
    if research_digest() != digest_before:
        raise SystemExit("read-only AICC task commands modified project state")

    doctor = json.loads(run([sys.executable, str(cli), "doctor", "--json"]).stdout)
    if not doctor.get("healthy") or doctor.get("skill_count", 0) == 0:
        raise SystemExit("aicc doctor did not recognize the source collection")

    status_spec = importlib.util.spec_from_file_location(
        "aicc_status_smoke", REPO_ROOT / "aicc" / "commands" / "status.py"
    )
    if status_spec is None or status_spec.loader is None:
        raise SystemExit("could not load the AICC status module for smoke testing")
    status_module = importlib.util.module_from_spec(status_spec)
    status_spec.loader.exec_module(status_module)
    if sorted(["T10", "T2", "T1"], key=status_module.natural_sort_key) != [
        "T1",
        "T2",
        "T10",
    ]:
        raise SystemExit("aicc status task IDs are not naturally sorted")
    watch_output = io.StringIO()
    with contextlib.redirect_stdout(watch_output):
        watch_result = status_module.watch_status(
            fixture,
            interval=0.01,
            event_limit=0,
            task_filter=None,
            status_filter=None,
            summary_only=True,
            max_iterations=2,
            sleep=lambda _seconds: None,
        )
    if watch_result != 0 or watch_output.getvalue().count("AICC PROJECT STATUS") != 1:
        raise SystemExit("aicc status watch redrew an unchanged snapshot")

    with tempfile.TemporaryDirectory(prefix="aicc-status-") as tmpdir:
        status_project = Path(tmpdir).resolve() / "project"
        shutil.copytree(fixture, status_project)
        task_path = status_project / ".research" / "tasks" / "T003.yaml"
        base_task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        status_cases = {
            "running": ("ACTIVE", "active", "RUNNING"),
            "completed": ("REVIEW", "validate", "NEEDS VALIDATION"),
            "validated": ("REVIEW", "accept", "NEEDS ACCEPTANCE"),
            "failed": ("ATTENTION", "attention", "FAILED"),
        }
        for task_status, (health, action, heading) in status_cases.items():
            task = dict(base_task)
            task["status"] = task_status
            task["execution_policy"] = {
                **(base_task.get("execution_policy") or {}),
                "requires_claim": False,
            }
            task_path.write_text(
                yaml.safe_dump(task, sort_keys=False), encoding="utf-8"
            )
            command = [
                sys.executable,
                str(cli),
                "status",
                str(status_project),
                "--events",
                "0",
                "--now",
                "2026-07-11T16:30:00+08:00",
            ]
            payload = json.loads(run([*command, "--json"]).stdout)
            row = next(item for item in payload["tasks"] if item["task_id"] == "T003")
            if payload["health"] != health or row["action"] != action:
                raise SystemExit(
                    f"aicc status semantics mismatch for {task_status}: "
                    f"health={payload['health']} action={row['action']}"
                )
            if heading not in run([*command, "--summary"]).stdout:
                raise SystemExit(
                    f"aicc status --summary omitted {heading} for {task_status}"
                )
            if task_status == "running" and any(
                "without an active lease" in message
                for message in payload.get("attention", [])
            ):
                raise SystemExit(
                    "aicc status incorrectly requires a lease for a cognitive task"
                )

    with tempfile.TemporaryDirectory(prefix="aicc-task-") as tmpdir:
        task_project = Path(tmpdir).resolve() / "project"
        shutil.copytree(EXAMPLES / "claim-ready-project", task_project)
        task_research = task_project / ".research"
        before_dry_run = research_digest(task_research)
        run(
            [sys.executable, str(cli), "task", "check", "T001", "--dry-run"],
            cwd=task_project,
        )
        run(
            [sys.executable, str(cli), "task", "reconcile"], cwd=task_project
        )
        if research_digest(task_research) != before_dry_run:
            raise SystemExit("read-only task lifecycle commands modified state")

        owner = "aicc-smoke-owner"
        run(
            [
                sys.executable,
                str(cli),
                "task",
                "claim",
                "T001",
                "--owner",
                owner,
                "--now",
                "2026-07-11T10:00:00+08:00",
            ],
            cwd=task_project,
        )
        active = json.loads(
            run(
                [
                    sys.executable,
                    str(cli),
                    "task",
                    "show",
                    "T001",
                    "--now",
                    "2026-07-11T10:01:00+08:00",
                    "--json",
                ],
                cwd=task_project,
            ).stdout
        )
        if (
            active["task"].get("status") != "running"
            or active["derived"].get("action") != "active"
            or active["derived"].get("lease", {}).get("owner_id") != owner
        ):
            raise SystemExit("aicc task claim did not expose the active lease")
        run(
            [
                sys.executable,
                str(cli),
                "task",
                "heartbeat",
                "T001",
                "--owner",
                owner,
                "--now",
                "2026-07-11T10:05:00+08:00",
            ],
            cwd=task_project,
        )
        run(
            [
                sys.executable,
                str(cli),
                "task",
                "release",
                "T001",
                "--status",
                "completed",
                "--owner",
                owner,
                "--note",
                "smoke lifecycle complete",
                "--now",
                "2026-07-11T10:10:00+08:00",
            ],
            cwd=task_project,
        )
        released = json.loads(
            run(
                [sys.executable, str(cli), "task", "show", "T001", "--json"],
                cwd=task_project,
            ).stdout
        )
        if (
            released["task"].get("status") != "completed"
            or released["derived"].get("action") != "validate"
            or released["derived"].get("lease") is not None
        ):
            raise SystemExit("aicc task release did not preserve status semantics")
        event_kinds = {
            json.loads(line)["event"]
            for line in (task_research / "events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        }
        if not {"task_claimed", "task_heartbeat", "task_released"}.issubset(
            event_kinds
        ):
            raise SystemExit("aicc task lifecycle did not retain audit events")

    with tempfile.TemporaryDirectory(prefix="aicc-skill-") as tmpdir:
        root = Path(tmpdir).resolve()
        project = root / "project"
        project.mkdir()
        agents = project / "AGENTS.md"
        original_agents = "# Custom fixture instructions\n\nKeep this text.\n"
        agents.write_text(original_agents, encoding="utf-8")
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(root / "home"),
                "CODEX_HOME": str(root / "codex"),
                "AICC_SOURCE": str(REPO_ROOT),
            }
        )
        skill_sources = {
            skill_dir.name: skill_dir
            for parent in ("procedures", "tools")
            for skill_dir in sorted((REPO_ROOT / parent).iterdir())
            if (skill_dir / "SKILL.md").is_file()
        }

        config_path = root / "codex" / "config.toml"
        config_path.parent.mkdir(parents=True)
        legacy_config = (
            'model = "fixture"\n\n'
            "[[skills.config]]\n"
            f"path = {json.dumps(str(REPO_ROOT / 'tools' / 'vasp' / 'SKILL.md'))}\n"
            "enabled = false\n"
        )
        config_path.write_text(legacy_config, encoding="utf-8")

        run(
            [
                sys.executable,
                str(cli),
                "skill",
                "enable",
                "--scope",
                "local",
                "--dry-run",
            ],
            cwd=project,
            env=env,
        )
        if agents.read_text(encoding="utf-8") != original_agents:
            raise SystemExit("aicc skill dry-run modified AGENTS.md")
        if (project / ".agents").exists():
            raise SystemExit("aicc skill enable --dry-run created local skill paths")

        run(
            [sys.executable, str(cli), "skill", "enable", "--scope", "local"],
            cwd=project,
            env=env,
        )
        enabled = json.loads(
            run(
                [sys.executable, str(cli), "skill", "status", "--json"],
                cwd=project,
                env=env,
            ).stdout
        )
        if enabled["local"]["state"] != "on":
            raise SystemExit("aicc skill local enable did not produce an on state")

        run(
            [sys.executable, str(cli), "skill", "disable", "--scope", "local"],
            cwd=project,
            env=env,
        )
        if agents.read_text(encoding="utf-8") != original_agents:
            raise SystemExit(
                "aicc skill local disable did not preserve custom AGENTS.md text"
            )
        remaining_links = list((project / ".agents" / "skills").iterdir())
        if remaining_links:
            raise SystemExit("aicc skill local disable left managed skill links behind")

        if config_path.read_text(encoding="utf-8") != legacy_config:
            raise SystemExit(
                "aicc skill local enable/disable modified global Codex config"
            )
        if list(config_path.parent.glob("config.toml.bak.*")):
            raise SystemExit(
                "aicc skill local enable/disable backed up global Codex config"
            )

        global_skills = root / "codex" / "skills"
        global_skills.mkdir(parents=True)
        global_agents = root / "codex" / "AGENTS.md"
        retired_collection = root / "retired" / "auto-computational-chemist"
        retired_cli = retired_collection / "aicc" / "aicc.py"
        retired_cli.parent.mkdir(parents=True)
        retired_cli.write_text("# Retired AICC CLI fixture\n", encoding="utf-8")
        for name, source in skill_sources.items():
            retired_source = retired_collection / source.relative_to(REPO_ROOT)
            retired_source.mkdir(parents=True)
            (retired_source / "SKILL.md").write_text(
                f"# Retired {name} fixture\n", encoding="utf-8"
            )
            (global_skills / name).symlink_to(
                retired_source, target_is_directory=True
            )
        retired_agents = retired_collection / "AGENTS.md"
        retired_agents.write_text("# Retired AICC instructions\n", encoding="utf-8")
        global_agents.symlink_to(retired_agents)

        moved_collection = root / "moved" / "auto-computational-chemist"
        moved_collection.parent.mkdir()
        retired_collection.rename(moved_collection)

        # Keep one retired target live to exercise path-based ownership, and one
        # live foreign same-name target to prove stale cleanup leaves it alone.
        live_retired_name = "vasp"
        live_retired_link = global_skills / live_retired_name
        live_retired_link.unlink()
        live_retired_link.symlink_to(
            moved_collection / skill_sources[live_retired_name].relative_to(REPO_ROOT),
            target_is_directory=True,
        )
        global_agents.unlink()
        global_agents.symlink_to(moved_collection / "AGENTS.md")

        foreign_name = "cp2k"
        foreign_root = root / "personal" / "aicc"
        foreign_target = foreign_root / "tools" / foreign_name
        foreign_target.mkdir(parents=True)
        (foreign_target / "SKILL.md").write_text(
            "# Live foreign skill in an AICC-shaped path\n", encoding="utf-8"
        )
        foreign_agents = foreign_root / "AGENTS.md"
        foreign_agents.write_text(
            "# Live foreign instructions in an AICC-shaped path\n", encoding="utf-8"
        )
        foreign_link = global_skills / foreign_name
        foreign_link.unlink()
        foreign_link.symlink_to(foreign_target, target_is_directory=True)

        stale_preview = run(
            [
                sys.executable,
                str(cli),
                "skill",
                "disable",
                "--scope",
                "global",
                "--stale",
                "--dry-run",
            ],
            cwd=project,
            env=env,
        )
        if (
            "target is missing" not in stale_preview.stdout
            or "retired AICC skill path" not in stale_preview.stdout
            or "retired AICC instruction path" not in stale_preview.stdout
        ):
            raise SystemExit("aicc skill stale dry-run missed recovery candidates")
        unconfirmed = run(
            [
                sys.executable,
                str(cli),
                "skill",
                "disable",
                "--scope",
                "global",
                "--stale",
            ],
            expect=1,
            cwd=project,
            env=env,
        )
        if "--confirm" not in unconfirmed.stderr:
            raise SystemExit("aicc skill stale cleanup did not require confirmation")
        if not all(path.is_symlink() for path in global_skills.iterdir()):
            raise SystemExit("unconfirmed stale cleanup removed a skill link")
        if not global_agents.is_symlink():
            raise SystemExit("unconfirmed stale cleanup removed AGENTS.md")

        run(
            [
                sys.executable,
                str(cli),
                "skill",
                "disable",
                "--scope",
                "global",
                "--stale",
                "--confirm",
            ],
            cwd=project,
            env=env,
        )
        stale_remaining = {
            path.name
            for path in global_skills.iterdir()
            if path.name != foreign_name
        }
        if stale_remaining:
            raise SystemExit(
                "aicc skill stale cleanup left retired links behind: "
                + ", ".join(sorted(stale_remaining))
            )
        if not foreign_link.is_symlink() or foreign_link.resolve() != foreign_target:
            raise SystemExit("aicc skill stale cleanup removed a live foreign link")
        if global_agents.exists() or global_agents.is_symlink():
            raise SystemExit("aicc skill stale cleanup left retired AGENTS.md behind")
        stale_agents_backups = list(
            global_agents.parent.glob("AGENTS.md.bak.*")
        )
        if len(stale_agents_backups) != 1 or not stale_agents_backups[0].is_symlink():
            raise SystemExit("aicc skill stale cleanup did not back up AGENTS.md link")

        global_agents.symlink_to(foreign_agents)
        foreign_cleanup = run(
            [
                sys.executable,
                str(cli),
                "skill",
                "disable",
                "--scope",
                "global",
                "--stale",
                "--confirm",
            ],
            cwd=project,
            env=env,
        )
        if "no stale AICC skill or instruction links" not in foreign_cleanup.stdout:
            raise SystemExit(
                "aicc skill stale cleanup misclassified live foreign marker paths"
            )
        if not foreign_link.is_symlink() or not global_agents.is_symlink():
            raise SystemExit("stale cleanup removed a live foreign link")

        aicc_module_dir = REPO_ROOT / "aicc"
        if str(aicc_module_dir) not in sys.path:
            sys.path.insert(0, str(aicc_module_dir))
        from core.paths import ensure_orchestrator_imports

        ensure_orchestrator_imports()
        from commands import skill as skill_command

        changed_name = next(name for name in skill_sources if name != foreign_name)
        changed_path = global_skills / changed_name
        changed_target = root / "missing" / changed_name
        changed_path.symlink_to(changed_target, target_is_directory=True)
        changed_candidate = skill_command.StaleSymlink(
            kind="skill",
            name=changed_name,
            path=changed_path,
            target=skill_command.symlink_target(changed_path),
            reason="target is missing",
        )
        changed_path.unlink()
        changed_path.write_text("important foreign file\n", encoding="utf-8")
        try:
            skill_command.remove_stale_scope_symlink(
                changed_candidate, dry_run=False
            )
        except RuntimeError:
            pass
        else:
            raise SystemExit("stale cleanup removed a post-preflight replacement")
        if changed_path.read_text(encoding="utf-8") != "important foreign file\n":
            raise SystemExit("stale cleanup changed a post-preflight replacement")
        changed_path.unlink()

        foreign_link.unlink()
        global_agents.unlink()
        run(
            [sys.executable, str(cli), "skill", "enable", "--scope", "global"],
            cwd=project,
            env=env,
        )
        global_enabled = json.loads(
            run(
                [sys.executable, str(cli), "skill", "status", "--json"],
                cwd=project,
                env=env,
            ).stdout
        )
        if global_enabled["global"]["state"] != "on":
            raise SystemExit("aicc skill global enable did not produce an on state")
        for name, source in skill_sources.items():
            installed_skill = global_skills / name
            if (
                not installed_skill.is_symlink()
                or installed_skill.resolve() != source.resolve()
            ):
                raise SystemExit(
                    f"aicc skill global enable did not link the {name} skill"
                )
        global_agents_text = global_agents.read_text(encoding="utf-8")
        if (
            "<!-- cdx_skill:auto-computational-chemist:start -->"
            not in global_agents_text
            or "<!-- cdx_skill:auto-computational-chemist:end -->"
            not in global_agents_text
        ):
            raise SystemExit("aicc skill global enable did not create its managed block")
        run(
            [sys.executable, str(cli), "skill", "disable", "--scope", "global"],
            cwd=project,
            env=env,
        )
        if any(global_skills.iterdir()) or global_agents.exists():
            raise SystemExit("aicc skill global disable left managed entries behind")


        run(
            [sys.executable, str(cli), "skill", "migrate", "--dry-run"],
            cwd=project,
            env=env,
        )
        if config_path.read_text(encoding="utf-8") != legacy_config:
            raise SystemExit("aicc skill migrate --dry-run modified Codex config")
        if list(config_path.parent.glob("config.toml.bak.*")):
            raise SystemExit("aicc skill migrate --dry-run created a config backup")
        run([sys.executable, str(cli), "skill", "migrate"], cwd=project, env=env)
        if config_path.read_text(encoding="utf-8") != 'model = "fixture"\n':
            raise SystemExit("aicc skill migrate did not remove legacy skill config")
        config_backups = list(config_path.parent.glob("config.toml.bak.*"))
        if len(config_backups) != 1:
            raise SystemExit("aicc skill migrate did not back up Codex config")
        if config_backups[0].read_text(encoding="utf-8") != legacy_config:
            raise SystemExit(
                "aicc skill migrate backup did not preserve original config"
            )

        foreign_skill = root / "codex" / "skills" / "vasp"
        foreign_skill.mkdir(parents=True)
        (foreign_skill / "SKILL.md").write_text(
            "# Foreign VASP skill\n", encoding="utf-8"
        )
        foreign_config = (
            'model = "foreign"\n\n'
            "[[skills.config]]\n"
            f"path = {json.dumps(str(foreign_skill / 'SKILL.md'))}\n"
            "enabled = false\n"
        )
        config_path.write_text(foreign_config, encoding="utf-8")
        backups_before = set(config_path.parent.glob("config.toml.bak.*"))
        run([sys.executable, str(cli), "skill", "migrate"], cwd=project, env=env)
        if config_path.read_text(encoding="utf-8") != foreign_config:
            raise SystemExit(
                "aicc skill migrate removed a foreign same-name skill block"
            )
        if set(config_path.parent.glob("config.toml.bak.*")) != backups_before:
            raise SystemExit("aicc skill migrate backed up an unchanged foreign config")

        stale_config = (
            'model = "stale"\n\n'
            "# auto-computational-chemist skills managed by cdx_skill\n"
            "[[skills.config]]\n"
            'path = "/retired/aicc/tools/vasp/SKILL.md"\n'
            "enabled = false\n"
            "\n[[skills.config]] # retired cp2k\n"
            'path = "/retired/aicc/tools/cp2k/SKILL.md"\n'
            "enabled = false\n"
        )
        config_path.write_text(stale_config, encoding="utf-8")
        backups_before = set(config_path.parent.glob("config.toml.bak.*"))
        run([sys.executable, str(cli), "skill", "migrate"], cwd=project, env=env)
        if config_path.read_text(encoding="utf-8") != 'model = "stale"\n':
            raise SystemExit("aicc skill migrate missed a managed retired-source block")
        new_backups = set(config_path.parent.glob("config.toml.bak.*")) - backups_before
        if (
            len(new_backups) != 1
            or new_backups.pop().read_text(encoding="utf-8") != stale_config
        ):
            raise SystemExit(
                "aicc skill migrate did not back up a retired-source config"
            )

        personal_skill = root / "personal" / "vasp" / "SKILL.md"
        mixed_config = (
            'model = "mixed"\n'
            'prompt = """alpha\n\n\nbeta"""\n\n'
            "# auto-computational-chemist skills managed by cdx_skill\n"
            "[[skills.config]]\n"
            'path = "/retired/aicc/tools/vasp/SKILL.md"\n'
            "enabled = false\n\n"
            "[[skills.config]]\n"
            f"path = {json.dumps(str(personal_skill))}\n"
            "enabled = false\n"
        )
        config_path.write_text(mixed_config, encoding="utf-8")
        run([sys.executable, str(cli), "skill", "migrate"], cwd=project, env=env)
        migrated_mixed = config_path.read_text(encoding="utf-8")
        if "/retired/aicc/tools/vasp/SKILL.md" in migrated_mixed:
            raise SystemExit("aicc skill migrate retained a marked retired AICC block")
        if str(personal_skill) not in migrated_mixed:
            raise SystemExit("aicc skill migrate removed an adjacent personal skill block")
        if 'prompt = """alpha\n\n\nbeta"""' not in migrated_mixed:
            raise SystemExit("aicc skill migrate changed a TOML multi-line string")
        parsed_mixed = tomllib.loads(migrated_mixed)
        if parsed_mixed.get("prompt") != "alpha\n\n\nbeta":
            raise SystemExit("aicc skill migrate corrupted parsed TOML prompt content")

        linked_project = root / "linked-project"
        linked_project.mkdir()
        linked_agents = linked_project / "AGENTS.md"
        linked_agents.symlink_to(REPO_ROOT / "AGENTS.md")
        linked_before = json.loads(
            run(
                [sys.executable, str(cli), "skill", "status", "--json"],
                cwd=linked_project,
                env=env,
            ).stdout
        )
        if linked_before["local"]["state"] != "partial":
            raise SystemExit(
                "instruction-only AICC local state was not reported as partial"
            )
        run(
            [sys.executable, str(cli), "skill", "enable", "--scope", "local"],
            cwd=linked_project,
            env=env,
        )
        if not linked_agents.is_symlink():
            raise SystemExit("aicc skill enable replaced an owned AGENTS.md symlink")
        run(
            [sys.executable, str(cli), "skill", "disable", "--scope", "local"],
            cwd=linked_project,
            env=env,
        )
        linked_backups = list(linked_project.glob("AGENTS.md.bak.*"))
        if linked_agents.exists() or linked_agents.is_symlink():
            raise SystemExit("aicc skill disable did not remove its AGENTS.md symlink")
        if len(linked_backups) != 1 or not linked_backups[0].is_symlink():
            raise SystemExit("aicc skill disable did not preserve a symlink backup")

        foreign_project = root / "foreign-project"
        foreign_project.mkdir()
        foreign_target = root / "foreign-agents.md"
        foreign_target.write_text("# Foreign instructions\n", encoding="utf-8")
        foreign_agents = foreign_project / "AGENTS.md"
        foreign_agents.symlink_to(foreign_target)
        run(
            [sys.executable, str(cli), "skill", "enable", "--scope", "local"],
            expect=1,
            cwd=foreign_project,
            env=env,
        )
        if foreign_agents.resolve() != foreign_target.resolve():
            raise SystemExit("aicc skill enable changed a foreign AGENTS.md symlink")
        if (foreign_project / ".agents").exists():
            raise SystemExit(
                "aicc skill enable wrote skills before AGENTS conflict preflight"
            )

        copy_project = root / "copy-project"
        copied_skill = copy_project / ".agents" / "skills" / "catmap"
        copied_skill.mkdir(parents=True)
        run(
            [sys.executable, str(cli), "skill", "disable", "--scope", "local"],
            expect=1,
            cwd=copy_project,
            env=env,
        )
        if not copied_skill.is_dir() or (copy_project / "AGENTS.md").exists():
            raise SystemExit("aicc skill disable modified a copy-mode conflict")

        escaped_project = root / "escaped-project"
        escaped_project.mkdir()
        outside_agents = root / "outside-agents"
        outside_agents.mkdir()
        (escaped_project / ".agents").symlink_to(
            outside_agents, target_is_directory=True
        )
        run(
            [sys.executable, str(cli), "skill", "enable", "--scope", "local"],
            expect=1,
            cwd=escaped_project,
            env=env,
        )
        if (outside_agents / "skills").exists() or (
            escaped_project / "AGENTS.md"
        ).exists():
            raise SystemExit(
                "aicc skill local enable followed .agents outside the project"
            )

        malformed_project = root / "malformed-project"
        malformed_project.mkdir()
        malformed_agents = malformed_project / "AGENTS.md"
        malformed_text = (
            "<!-- cdx_skill:auto-computational-chemist:end -->\n"
            "broken\n"
            "<!-- cdx_skill:auto-computational-chemist:start -->\n"
        )
        malformed_agents.write_text(malformed_text, encoding="utf-8")
        run(
            [sys.executable, str(cli), "skill", "enable", "--scope", "local"],
            expect=1,
            cwd=malformed_project,
            env=env,
        )
        if malformed_agents.read_text(encoding="utf-8") != malformed_text:
            raise SystemExit("aicc skill enable rewrote malformed managed markers")
        if (malformed_project / ".agents").exists():
            raise SystemExit("aicc skill enable wrote skills before marker preflight")

        missing_env = {**env, "AICC_SOURCE": str(root / "missing-source")}
        missing = run(
            [sys.executable, str(cli), "skill", "status"],
            expect=1,
            cwd=project,
            env=missing_env,
        )
        if "Traceback" in missing.stderr or "source root" not in missing.stderr:
            raise SystemExit("aicc skill missing-source diagnostics are not actionable")

    print("PASS aicc command routing and skill management")


def aicc_job_flow() -> None:
    cli = REPO_ROOT / "aicc" / "aicc.py"
    with tempfile.TemporaryDirectory(prefix="aicc-job-") as tmpdir:
        root = Path(tmpdir).resolve()
        project = root / "project"
        shutil.copytree(EXAMPLES / "gate-hook-project", project)
        research = project / ".research"
        task_path = research / "tasks" / "T002.yaml"
        task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        task["execution_policy"] = {
            "mode": "single_owner",
            "allow_parallel_subagents": False,
            "requires_claim": True,
            "lease_ttl_minutes": 60,
            "heartbeat_interval_minutes": 10,
            "owner_dir": "work/run/",
            "exclusive_paths": ["work/run/"],
        }
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")

        run_dir = project / "work" / "run"
        run_dir.mkdir(parents=True)
        (run_dir / "job.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (run_dir / "POSCAR").write_text("initial\n", encoding="utf-8")
        (run_dir / "CONTCAR").write_text("continued\n", encoding="utf-8")

        fake_bin = root / "bin"
        fake_bin.mkdir()
        counter = root / "sbatch-counter"
        fake_sbatch = fake_bin / "sbatch"
        fake_sbatch.write_text(
            f"#!{sys.executable}\n"
            "import os, sys, time\n"
            "from pathlib import Path\n"
            "time.sleep(float(os.environ.get('FAKE_SBATCH_DELAY', '0')))\n"
            "path = Path(os.environ['FAKE_SBATCH_COUNTER'])\n"
            "count = int(path.read_text() if path.exists() else '0') + 1\n"
            "path.write_text(str(count))\n"
            "if os.environ.get('FAKE_SBATCH_FAIL'):\n"
            "    print('invalid partition', file=sys.stderr)\n"
            "    raise SystemExit(1)\n"
            "if os.environ.get('FAKE_SBATCH_AMBIGUOUS'):\n"
            "    print('accepted without a parsable id')\n"
            "else:\n"
            "    print(700000 + count)\n",
            encoding="utf-8",
        )
        fake_sbatch.chmod(0o755)
        fake_squeue = fake_bin / "squeue"
        fake_squeue.write_text(
            f"#!{sys.executable}\n"
            "import os, sys, time\n"
            "time.sleep(float(os.environ.get('FAKE_SQUEUE_DELAY', '0')))\n"
            "sys.exit(int(os.environ.get('FAKE_SQUEUE_RC', '0')))\n",
            encoding="utf-8",
        )
        fake_squeue.chmod(0o755)
        fake_sacct = fake_bin / "sacct"
        fake_sacct.write_text(
            f"#!{sys.executable}\n"
            "import os, sys, time\n"
            "time.sleep(float(os.environ.get('FAKE_SACCT_DELAY', '0')))\n"
            "log = os.environ.get('FAKE_SACCT_ARGS_LOG')\n"
            "if log:\n"
            "    with open(log, 'a') as handle:\n"
            "        handle.write(' '.join(sys.argv[1:]) + '\\n')\n"
            "if os.environ.get('FAKE_SACCT_EMPTY'):\n    raise SystemExit(0)\n"
            "args = sys.argv[1:]\n"
            "job_id = args[args.index('-j') + 1] if '-j' in args else os.environ.get('FAKE_JOB_ID', '700001')\n"
            "print(f\"{job_id}|{os.environ.get('FAKE_JOB_STATE', 'COMPLETED')}\")\n",
            encoding="utf-8",
        )
        fake_sacct.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
        env["FAKE_SBATCH_COUNTER"] = str(counter)

        owner = "aicc-job-owner"
        run(
            [sys.executable, str(cli), "task", "claim", str(project), "T002", "--owner", owner],
            env=env,
        )
        submit = [
            sys.executable,
            str(cli),
            "job",
            "submit",
            str(project),
            "T002",
            "work/run",
            "--script",
            "job.sh",
            "--owner",
            owner,
        ]
        run(submit, env=env)
        run(submit, expect=1, env=env)
        if counter.read_text(encoding="utf-8") != "1":
            raise SystemExit("duplicate aicc job submit invoked sbatch more than once")

        payload = json.loads(
            run([sys.executable, str(cli), "job", "status", str(project), "--json"], env=env).stdout
        )
        first = payload["jobs"][0]
        if first.get("state") != "pending" or first.get("job_id") != "700001":
            raise SystemExit("aicc job submit did not record the first Slurm attempt")
        lease = json.loads((research / "leases" / "T002.json").read_text(encoding="utf-8"))
        if lease.get("job_ids") != ["700001"]:
            raise SystemExit("aicc job submit did not bind the Job ID to its lease")
        run(
            [
                sys.executable,
                str(cli),
                "task",
                "release",
                str(project),
                "T002",
                "--status",
                "completed",
                "--owner",
                owner,
            ],
            expect=1,
            env=env,
        )

        run(
            [sys.executable, str(cli), "job", "reconcile", str(project), "work/run"],
            env={**env, "FAKE_SQUEUE_RC": "1"},
        )
        shutil.copyfile(run_dir / "CONTCAR", run_dir / "POSCAR")
        run(submit, env=env)
        if counter.read_text(encoding="utf-8") != "2":
            raise SystemExit("terminal job did not allow a same-directory continuation")
        jobs = json.loads(
            run([sys.executable, str(cli), "job", "status", str(project), "--json"], env=env).stdout
        )["jobs"]
        by_job_id = {job.get("job_id"): job for job in jobs}
        first_attempt = by_job_id.get("700001")
        continuation = by_job_id.get("700002")
        if (
            len(jobs) != 2
            or first_attempt is None
            or continuation is None
            or continuation.get("parent_attempt_id") != first_attempt.get("attempt_id")
        ):
            raise SystemExit("same-directory continuation did not retain attempt lineage")
        run(
            [sys.executable, str(cli), "job", "reconcile", str(project), "work/run"],
            env=env,
        )
        rejected_dir = run_dir / "rejected"
        rejected_dir.mkdir()
        (rejected_dir / "job.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        rejected_submit = [
            sys.executable,
            str(cli),
            "job",
            "submit",
            str(project),
            "T002",
            "work/run/rejected",
            "--owner",
            owner,
        ]
        run(rejected_submit, expect=1, env={**env, "FAKE_SBATCH_FAIL": "1"})
        rejected_jobs = json.loads(
            run([sys.executable, str(cli), "job", "status", str(project), "--json"], env=env).stdout
        )["jobs"]
        rejected_attempts = [
            job
            for job in rejected_jobs
            if job.get("state") == "failed" and job.get("job_id") is None
        ]
        if len(rejected_attempts) != 1:
            raise SystemExit("clean sbatch rejection was not recorded as terminal failed")
        run(rejected_submit, env=env)
        run(
            [sys.executable, str(cli), "job", "reconcile", str(project), "work/run/rejected"],
            env=env,
        )
        if counter.read_text(encoding="utf-8") != "4":
            raise SystemExit("terminal sbatch rejection did not permit a safe retry")

        unknown_dir = run_dir / "unknown"
        unknown_dir.mkdir()
        (unknown_dir / "job.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        unknown_submit = [
            sys.executable,
            str(cli),
            "job",
            "submit",
            str(project),
            "T002",
            "work/run/unknown",
            "--owner",
            owner,
        ]
        ambiguous_env = {**env, "FAKE_SBATCH_AMBIGUOUS": "1"}
        run(unknown_submit, expect=1, env=ambiguous_env)
        run(unknown_submit, expect=1, env=ambiguous_env)
        if counter.read_text(encoding="utf-8") != "5":
            raise SystemExit("submission_unknown did not block an automatic retry")
        unknown_jobs = json.loads(
            run([sys.executable, str(cli), "job", "status", str(project), "--active", "--json"], env=env).stdout
        )["jobs"]
        if len(unknown_jobs) != 1 or unknown_jobs[0].get("state") != "submission_unknown":
            raise SystemExit("ambiguous sbatch result was not retained as submission_unknown")
        recovered_env = {**env, "FAKE_JOB_ID": "700005"}
        run(
            [sys.executable, str(cli), "job", "reconcile", str(project), "work/run/unknown"],
            env=recovered_env,
        )
        concurrent_dir = run_dir / "concurrent"
        concurrent_dir.mkdir()
        (concurrent_dir / "job.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        concurrent_submit = [
            sys.executable,
            str(cli),
            "job",
            "submit",
            str(project),
            "T002",
            "work/run/concurrent",
            "--owner",
            owner,
        ]
        concurrent_env = {**env, "FAKE_SBATCH_DELAY": "0.2"}
        processes = [
            subprocess.Popen(
                concurrent_submit,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=concurrent_env,
            )
            for _ in range(2)
        ]
        results = [process.communicate() + (process.returncode,) for process in processes]
        if sorted(result[2] for result in results) != [0, 1]:
            raise SystemExit(f"concurrent submits did not produce one winner: {results}")
        if counter.read_text(encoding="utf-8") != "6":
            raise SystemExit("concurrent aicc job submit invoked sbatch more than once")
        run(
            [sys.executable, str(cli), "job", "reconcile", str(project), "work/run/concurrent"],
            env=env,
        )
        timeout_dir = run_dir / "timeout"
        timeout_dir.mkdir()
        (timeout_dir / "job.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        timeout_submit = [
            sys.executable,
            str(cli),
            "job",
            "submit",
            str(project),
            "T002",
            "work/run/timeout",
            "--owner",
            owner,
            "--timeout",
            "0.05",
        ]
        run(timeout_submit, expect=1, env={**env, "FAKE_SBATCH_DELAY": "0.2"})
        timeout_attempt = json.loads(
            run([sys.executable, str(cli), "job", "status", str(project), "--active", "--json"], env=env).stdout
        )["jobs"][0]
        if timeout_attempt.get("state") != "submission_unknown":
            raise SystemExit("sbatch timeout was not recorded as submission_unknown")
        run(
            [
                sys.executable,
                str(cli),
                "job",
                "reconcile",
                str(project),
                "--attempt",
                timeout_attempt["attempt_id"],
            ],
            expect=2,
            env={**env, "FAKE_SACCT_EMPTY": "1"},
        )
        resolve_timeout = [
            sys.executable,
            str(cli),
            "job",
            "reconcile",
            str(project),
            "--attempt",
            timeout_attempt["attempt_id"],
            "--mark",
            "failed",
            "--reason",
            "scheduler has no submission record",
        ]
        run(resolve_timeout, expect=2, env=env)
        run([*resolve_timeout, "--confirm"], env=env)
        resolved_jobs = json.loads(
            run([sys.executable, str(cli), "job", "status", str(project), "--json"], env=env).stdout
        )["jobs"]
        resolved_timeout = next(
            (
                job
                for job in resolved_jobs
                if job.get("attempt_id") == timeout_attempt["attempt_id"]
            ),
            None,
        )
        if resolved_timeout is None or resolved_timeout.get("state") != "failed":
            raise SystemExit("operator resolution did not terminate submission_unknown")

        state_lock = research / ".locks" / "state.lock"
        state_lock.mkdir(parents=True)
        (state_lock / "owner.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "purpose": "project state",
                    "host": __import__("socket").gethostname(),
                    "pid": os.getpid(),
                    "created_at": "2026-07-13T00:00:00+08:00",
                }
            ),
            encoding="utf-8",
        )
        unlock = [
            sys.executable,
            str(cli),
            "job",
            "unlock",
            str(project),
            "--reason",
            "smoke-test crash recovery",
            "--confirm",
        ]
        run(unlock, expect=1, env=env)
        shutil.rmtree(state_lock)
        state_lock.mkdir(parents=True)
        (state_lock / "owner.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "purpose": "project state",
                    "host": __import__("socket").gethostname(),
                    "pid": 999999999,
                    "created_at": "2026-07-13T00:00:00+08:00",
                }
            ),
            encoding="utf-8",
        )
        run(unlock, env=env)
        if state_lock.exists():
            raise SystemExit("explicit stale-lock recovery left the lock behind")

        orphan_dir = run_dir / "orphan"
        orphan_dir.mkdir()
        (orphan_dir / "job.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        run(
            [
                sys.executable, str(cli), "job", "submit", str(project), "T002",
                "work/run/orphan", "--script", "job.sh", "--owner", owner,
            ],
            env=env,
        )
        orphan_pointer = orphan_dir / ".aicc-active-job.json"
        if not orphan_pointer.is_file():
            raise SystemExit("submit did not write the orphan-test pointer")
        orphan_jobs = json.loads(
            run([sys.executable, str(cli), "job", "status", str(project), "--json"], env=env).stdout
        )["jobs"]
        orphan_attempt = next(
            (job for job in orphan_jobs if job.get("workdir") == "work/run/orphan"),
            None,
        )
        if orphan_attempt is None or orphan_attempt.get("state") != "pending":
            raise SystemExit("orphan-test submission did not record a pending attempt")
        orphan_pointer.unlink()
        validate_cmd = [
            sys.executable,
            str(REPO_ROOT / "procedures/research-orchestrator/scripts/validate_state.py"),
            str(research),
        ]
        result = run(validate_cmd)
        if "missing its active-attempt pointer" not in result.stdout:
            raise SystemExit("validate_state did not WARN about the orphaned active attempt")
        run(
            [
                sys.executable, str(cli), "job", "reconcile", str(project),
                "--attempt", orphan_attempt["attempt_id"],
            ],
            env=env,
        )
        if not orphan_pointer.is_file():
            raise SystemExit("reconcile --attempt did not restore the active pointer")
        restored = json.loads(orphan_pointer.read_text(encoding="utf-8"))
        if restored.get("attempt_id") != orphan_attempt["attempt_id"]:
            raise SystemExit("restored pointer references the wrong attempt")
        result = run(validate_cmd)
        if "missing its active-attempt pointer" in result.stdout:
            raise SystemExit("pointer WARN persisted after restore and reconcile")
        print("PASS orphaned pointer WARN and reconcile restore")

        grace_dir = run_dir / "grace"
        grace_dir.mkdir()
        (grace_dir / "job.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        run(
            [
                sys.executable, str(cli), "job", "submit", str(project), "T002",
                "work/run/grace", "--script", "job.sh", "--owner", owner,
            ],
            env=env,
        )
        grace_jobs = json.loads(
            run([sys.executable, str(cli), "job", "status", str(project), "--json"], env=env).stdout
        )["jobs"]
        grace_attempt = next(
            (job for job in grace_jobs if job.get("workdir") == "work/run/grace"),
            None,
        )
        if grace_attempt is None:
            raise SystemExit("grace-test submission was not recorded")
        grace_record = research / "jobs" / f"{grace_attempt['attempt_id']}.json"
        record = json.loads(grace_record.read_text(encoding="utf-8"))
        record["state"] = "submitting"
        record["job_id"] = None
        record.pop("submitted_at", None)
        record["created_at"] = "2026-07-20T10:00:00+08:00"
        record["updated_at"] = "2026-07-20T10:00:00+08:00"
        grace_record.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
        reconcile_grace = [
            sys.executable, str(cli), "job", "reconcile", str(project),
            "--attempt", grace_attempt["attempt_id"],
        ]
        result = run(
            [*reconcile_grace, "--now", "2026-07-20T10:01:00+08:00"], expect=2, env=env
        )
        if "still submitting" not in result.stderr:
            raise SystemExit("reconcile did not back off from a young submitting attempt")
        record_after = json.loads(grace_record.read_text(encoding="utf-8"))
        if record_after.get("state") != "submitting":
            raise SystemExit("grace backoff changed the attempt state")
        sacct_log = root / "sacct-args.log"
        run(
            [*reconcile_grace, "--now", "2026-07-20T10:30:00+08:00"],
            expect=2,
            env={**env, "FAKE_SACCT_EMPTY": "1", "FAKE_SACCT_ARGS_LOG": str(sacct_log)},
        )
        logged = sacct_log.read_text(encoding="utf-8")
        if "--name" not in logged or "-S 2026-07-19T10:00:00" not in logged:
            raise SystemExit("name-based sacct recovery did not pass the -S start window")
        record_after = json.loads(grace_record.read_text(encoding="utf-8"))
        if record_after.get("state") != "submission_unknown":
            raise SystemExit("post-grace reconcile did not mark the attempt submission_unknown")
        run(
            [
                *reconcile_grace, "--mark", "failed", "--reason",
                "smoke-test operator resolution after grace", "--confirm",
                "--now", "2026-07-20T10:31:00+08:00",
            ],
            env=env,
        )
        print("PASS submitting grace period and sacct start window")

        dup_dir = run_dir / "dup"
        dup_dir.mkdir()
        (dup_dir / "job.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        dup_submit = [
            sys.executable, str(cli), "job", "submit", str(project), "T002",
            "work/run/dup", "--script", "job.sh", "--owner", owner,
        ]
        run(dup_submit, env=env)
        (dup_dir / ".aicc-active-job.json").unlink()
        counter_before = counter.read_text(encoding="utf-8")
        result = run(dup_submit, expect=1, env=env)
        if "active or ambiguous attempt" not in result.stderr:
            raise SystemExit("record-scan guard did not block a pointerless resubmission")
        if counter.read_text(encoding="utf-8") != counter_before:
            raise SystemExit("blocked pointerless resubmission still invoked sbatch")
        dup_jobs = json.loads(
            run([sys.executable, str(cli), "job", "status", str(project), "--json"], env=env).stdout
        )["jobs"]
        dup_attempt = next(
            job for job in dup_jobs if job.get("workdir") == "work/run/dup"
        )
        run(
            [
                sys.executable, str(cli), "job", "reconcile", str(project),
                "--attempt", dup_attempt["attempt_id"],
            ],
            env=env,
        )
        print("PASS pointerless duplicate guard")

        conflict_dir = run_dir / "conflict"
        conflict_dir.mkdir()
        (conflict_dir / "job.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        conflict_proc = subprocess.Popen(
            [
                sys.executable, str(cli), "job", "submit", str(project), "T002",
                "work/run/conflict", "--script", "job.sh", "--owner", owner,
            ],
            env={**env, "FAKE_SBATCH_DELAY": "5"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            time.sleep(1.0)
            conflict_jobs = json.loads(
                run(
                    [sys.executable, str(cli), "job", "status", str(project), "--json"],
                    env=env,
                ).stdout
            )["jobs"]
            conflict_attempt = next(
                (job for job in conflict_jobs if job.get("workdir") == "work/run/conflict"),
                None,
            )
            if conflict_attempt is None or conflict_attempt.get("state") != "submitting":
                raise SystemExit("mid-sbatch attempt was not observable as submitting")
            run(
                [
                    sys.executable, str(cli), "job", "reconcile", str(project),
                    "--attempt", conflict_attempt["attempt_id"],
                    "--mark", "failed", "--reason", "smoke-test operator race",
                    "--confirm",
                ],
                env=env,
            )
        except BaseException:
            conflict_proc.kill()
            conflict_proc.wait()
            raise
        conflict_stdout, conflict_stderr = conflict_proc.communicate(timeout=60)
        if conflict_proc.returncode != 1 or "submission conflict" not in conflict_stderr:
            raise SystemExit(
                "finalize did not surface the submission conflict: "
                f"rc={conflict_proc.returncode} stderr={conflict_stderr[-300:]}"
            )
        conflict_record = json.loads(
            (research / "jobs" / f"{conflict_attempt['attempt_id']}.json").read_text(
                encoding="utf-8"
            )
        )
        if conflict_record.get("state") != "failed":
            raise SystemExit("finalize clobbered the operator resolution")
        if not conflict_record.get("job_id"):
            raise SystemExit("conflict finalize did not record the orphan Job ID")
        if "scancel" not in conflict_stderr:
            raise SystemExit("conflict message did not advise scancel for the orphan job")
        print("PASS finalize preserves operator resolution during sbatch window")

        run(
            [
                sys.executable,
                str(cli),
                "task",
                "release",
                str(project),
                "T002",
                "--status",
                "completed",
                "--owner",
                owner,
            ],
            env=env,
        )
        shutil.rmtree(run_dir)
        run(
            [
                sys.executable,
                str(REPO_ROOT / "procedures/research-orchestrator/scripts/validate_state.py"),
                str(research),
            ]
        )
    print("PASS aicc lease-bound job submission and continuation")


def aicc_installer_flow() -> None:
    if shutil.which("uv") is None:
        print("SKIP aicc installer launcher (uv unavailable)")
        return
    with tempfile.TemporaryDirectory(prefix="aicc-install-") as tmpdir:
        root = Path(tmpdir).resolve()
        home = root / "home"
        home.mkdir()
        env = os.environ.copy()
        for name in (
            "AICC_COLLECTION",
            "AICC_SOURCE",
            "CODEX_HOME",
            "XDG_STATE_HOME",
        ):
            env.pop(name, None)
        env["HOME"] = str(home)
        target = home / ".codex" / "skills"
        run(
            ["sh", str(REPO_ROOT / "install.sh"), "--target", str(target), "--force"],
            env=env,
        )
        installed_cli = home / ".local" / "bin" / "aicc"
        if not installed_cli.is_file():
            raise SystemExit("install.sh did not install the aicc launcher")
        if (
            installed_cli.read_bytes()
            != (REPO_ROOT / "aicc" / "launcher.sh").read_bytes()
        ):
            raise SystemExit(
                "install.sh did not install the canonical locator launcher"
            )
        installed = json.loads(
            run(
                [
                    str(installed_cli),
                    "status",
                    str(EXAMPLES / "minimal-project"),
                    "--events",
                    "0",
                    "--json",
                ],
                env=env,
            ).stdout
        )
        if installed.get("health") != "READY":
            raise SystemExit("installed aicc launcher did not run status successfully")

        state_dir = home / ".local" / "state" / "aicc"
        registry = state_dir / "registry"
        default_file = state_dir / "default"
        if state_dir.stat().st_mode & 0o777 != 0o700:
            raise SystemExit("install.sh did not protect the AICC state directory")
        if registry.stat().st_mode & 0o777 != 0o600:
            raise SystemExit("install.sh did not protect the AICC registry")
        if default_file.stat().st_mode & 0o777 != 0o600:
            raise SystemExit("install.sh did not protect the AICC default file")
        shared_collection = (home / ".codex" / ".auto-computational-chemist").resolve()
        if (
            Path(default_file.read_text(encoding="utf-8").strip()).resolve()
            != shared_collection
        ):
            raise SystemExit(
                "shared install did not register the expected AICC default"
            )
        default_before_projects = default_file.read_bytes()

        invalid_env = {**env, "AICC_COLLECTION": str(root / "missing")}
        run([str(installed_cli), "doctor"], expect=2, env=invalid_env)

        launcher_before = installed_cli.read_bytes()
        for name in ("project-a", "project-b"):
            self_contained = root / name
            self_contained.mkdir()
            run(["sh", str(REPO_ROOT / "install.sh")], cwd=self_contained, env=env)
            discovered = json.loads(
                run(
                    [str(installed_cli), "doctor", "--json"],
                    cwd=self_contained,
                    env=env,
                ).stdout
            )
            expected_root = (self_contained / ".auto-computational-chemist").resolve()
            if Path(discovered["collection_root"]).resolve() != expected_root:
                raise SystemExit(
                    f"aicc launcher did not discover self-contained collection for {name}"
                )
        if installed_cli.read_bytes() != launcher_before:
            raise SystemExit(
                "self-contained installs rebound the managed aicc launcher"
            )
        if default_file.read_bytes() != default_before_projects:
            raise SystemExit("self-contained install changed the shared AICC default")
        registry_text = registry.read_text(encoding="utf-8")
        for name in ("project-a", "project-b"):
            if f"project\t{root / name}\t" not in registry_text:
                raise SystemExit(f"self-contained install did not register {name}")

        dual_env = {
            **env,
            "AICC_COLLECTION": str(shared_collection),
            "AICC_SOURCE": str(root / "project-b" / ".auto-computational-chemist"),
        }
        dual = json.loads(
            run(
                [str(installed_cli), "skill", "list", "--scope", "local", "--json"],
                cwd=root,
                env=dual_env,
            ).stdout
        )
        if Path(dual["source_root"]).resolve() != shared_collection:
            raise SystemExit(
                "AICC_COLLECTION and AICC_SOURCE selected different sources"
            )

        evil_root = root / "unregistered"
        evil_collection = evil_root / ".auto-computational-chemist"
        (evil_collection / "aicc").mkdir(parents=True)
        (evil_collection / "procedures").mkdir()
        (evil_collection / "tools").mkdir()
        malicious_marker = root / "unregistered-executed"
        (evil_collection / "aicc" / "aicc.py").write_text(
            "from pathlib import Path\n"
            f"Path({json.dumps(str(malicious_marker))}).write_text('executed')\n",
            encoding="utf-8",
        )
        evil_child = evil_root / "child"
        evil_child.mkdir()
        safe = json.loads(
            run(
                [str(installed_cli), "doctor", "--json"], cwd=evil_child, env=env
            ).stdout
        )
        if malicious_marker.exists():
            raise SystemExit(
                "aicc launcher executed an unregistered ancestor collection"
            )
        if Path(safe["collection_root"]).resolve() != shared_collection:
            raise SystemExit(
                "aicc launcher did not fall back to the registered shared default"
            )

    with tempfile.TemporaryDirectory(prefix="aicc-unmanaged-") as tmpdir:
        root = Path(tmpdir).resolve()
        home = root / "home"
        bin_dir = home / ".local" / "bin"
        bin_dir.mkdir(parents=True)
        unmanaged = bin_dir / "aicc"
        unmanaged_bytes = b"#!/bin/sh\necho unrelated-aicc\n"
        unmanaged.write_bytes(unmanaged_bytes)
        unmanaged.chmod(0o751)
        unmanaged_mode = unmanaged.stat().st_mode
        env = os.environ.copy()
        for name in (
            "AICC_COLLECTION",
            "AICC_SOURCE",
            "CODEX_HOME",
            "XDG_STATE_HOME",
        ):
            env.pop(name, None)
        env["HOME"] = str(home)
        run(
            [
                "sh",
                str(REPO_ROOT / "install.sh"),
                "--target",
                str(home / ".codex" / "skills"),
                "--force",
            ],
            env=env,
        )
        if (
            unmanaged.read_bytes() != unmanaged_bytes
            or unmanaged.stat().st_mode != unmanaged_mode
        ):
            raise SystemExit("install.sh --force overwrote an unmanaged aicc command")

    with tempfile.TemporaryDirectory(prefix="aicc-copy-") as tmpdir:
        root = Path(tmpdir).resolve()
        home = root / "home"
        home.mkdir()
        env = os.environ.copy()
        for name in (
            "AICC_COLLECTION",
            "AICC_SOURCE",
            "CODEX_HOME",
            "XDG_STATE_HOME",
        ):
            env.pop(name, None)
        env["HOME"] = str(home)
        target = home / ".codex" / "skills"
        run(
            [
                "sh",
                str(REPO_ROOT / "install.sh"),
                "--target",
                str(target),
                "--mode",
                "copy",
                "--force",
            ],
            env=env,
        )
        installed_cli = home / ".local" / "bin" / "aicc"
        run(
            [str(installed_cli), "skill", "disable", "--scope", "global"],
            expect=1,
            env=env,
        )
        if not (target / "catmap").is_dir():
            raise SystemExit("aicc skill disable removed a copy-mode skill")

    with tempfile.TemporaryDirectory(prefix="aicc-relative-") as tmpdir:
        root = Path(tmpdir).resolve()
        home = root / "home"
        work = root / "work"
        neutral = root / "neutral"
        home.mkdir()
        work.mkdir()
        neutral.mkdir()
        env = os.environ.copy()
        for name in (
            "AICC_COLLECTION",
            "AICC_SOURCE",
            "CODEX_HOME",
            "XDG_STATE_HOME",
        ):
            env.pop(name, None)
        env["HOME"] = str(home)
        run(
            [
                "sh",
                str(REPO_ROOT / "install.sh"),
                "--target",
                "relative-skills",
                "--force",
            ],
            cwd=work,
            env=env,
        )
        expected_collection = (work / ".auto-computational-chemist").resolve()
        linked_skill = work / "relative-skills" / "research-orchestrator"
        if not linked_skill.is_symlink() or not linked_skill.resolve().is_relative_to(
            expected_collection
        ):
            raise SystemExit("relative --target produced an invalid skill link")
        installed_cli = home / ".local" / "bin" / "aicc"
        relative_doctor = json.loads(
            run([str(installed_cli), "doctor", "--json"], cwd=neutral, env=env).stdout
        )
        if Path(relative_doctor["collection_root"]).resolve() != expected_collection:
            raise SystemExit(
                "relative custom target was not registered as shared default"
            )

    with tempfile.TemporaryDirectory(prefix="aicc-preexisting-") as tmpdir:
        root = Path(tmpdir).resolve()
        home = root / "home"
        project = root / "project"
        home.mkdir()
        project.mkdir()
        collection = project / ".auto-computational-chemist"
        (collection / "aicc").mkdir(parents=True)
        (collection / "procedures").mkdir()
        (collection / "tools").mkdir()
        malicious = "print('MALICIOUS_SENTINEL')\n"
        (collection / "aicc" / "aicc.py").write_text(malicious, encoding="utf-8")
        env = os.environ.copy()
        for name in (
            "AICC_COLLECTION",
            "AICC_SOURCE",
            "CODEX_HOME",
            "XDG_STATE_HOME",
        ):
            env.pop(name, None)
        env["HOME"] = str(home)
        run(["sh", str(REPO_ROOT / "install.sh")], expect=1, cwd=project, env=env)
        if (collection / "aicc" / "aicc.py").read_text(encoding="utf-8") != malicious:
            raise SystemExit(
                "install.sh changed an existing collection without --force"
            )
        if (home / ".local" / "state" / "aicc" / "registry").exists():
            raise SystemExit(
                "install.sh registered an untrusted pre-existing collection"
            )

        run(
            ["sh", str(REPO_ROOT / "install.sh"), "--force"],
            cwd=project,
            env=env,
        )
        refreshed = (collection / "aicc" / "aicc.py").read_text(encoding="utf-8")
        if "MALICIOUS_SENTINEL" in refreshed:
            raise SystemExit("install.sh --force did not refresh the collection")
        installed_cli = home / ".local" / "bin" / "aicc"
        trusted = json.loads(
            run([str(installed_cli), "doctor", "--json"], cwd=project, env=env).stdout
        )
        if Path(trusted["collection_root"]).resolve() != collection.resolve():
            raise SystemExit("refreshed self-contained collection was not registered")
    print("PASS aicc installer launcher")


def main() -> int:
    aicc_cli_flow()
    aicc_job_flow()
    aicc_installer_flow()
    print("== aicc smoke: clean ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
