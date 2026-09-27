"""Read-only environment diagnostics for ``aicc doctor``."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from core.paths import collection_root, orchestrator_scripts_dir


def discover_skills(root: Path) -> list[str]:
    skills: list[str] = []
    for parent in ("procedures", "tools"):
        base = root / parent
        if not base.is_dir():
            continue
        skills.extend(
            path.name for path in base.iterdir() if (path / "SKILL.md").is_file()
        )
    return sorted(skills)


def build_report() -> dict[str, Any]:
    root = collection_root()
    scripts_dir = orchestrator_scripts_dir()
    uv_path = shutil.which("uv")
    skills = discover_skills(root)
    checks = {
        "collection_root": root.is_dir(),
        "procedures": (root / "procedures").is_dir(),
        "tools": (root / "tools").is_dir(),
        "orchestrator_scripts": scripts_dir.is_dir(),
        "status_helper": (scripts_dir / "validate_state.py").is_file(),
        "uv": uv_path is not None,
        "python": sys.version_info >= (3, 11),
        "skills": bool(skills),
    }
    return {
        "schema_version": 1,
        "healthy": all(checks.values()),
        "collection_root": root.as_posix(),
        "orchestrator_scripts": scripts_dir.as_posix(),
        "uv": uv_path,
        "python": sys.version.split()[0],
        "skill_count": len(skills),
        "skills": skills,
        "checks": checks,
    }


def register(subparsers: Any) -> None:
    parser = subparsers.add_parser("doctor", help="Check the local AICC installation")
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable diagnostics"
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("AICC DOCTOR")
        print(f"Collection  {report['collection_root']}")
        print(f"Python      {report['python']}")
        print(f"uv          {report['uv'] or '<missing>'}")
        print(f"Skills      {report['skill_count']}")
        for name, passed in report["checks"].items():
            print(f"{'PASS' if passed else 'FAIL':<5}  {name}")
    return 0 if report["healthy"] else 1
