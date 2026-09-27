#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML>=6.0"]
# ///
"""Run research-orchestrator fixture and lease CLI smoke tests."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from scaffold_follow_up_tasks import build_task


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
EXAMPLES = SCRIPT_DIR.parent / "examples"

POSITIVE_VALIDATE = [
    "minimal-project",
    "blocked-project",
    "role-handoff-project",
    "structure-review-project",
    "gate-hook-project",
    "iterative-followup-project",
    "claim-ready-project",
    "claimed-execution-project",
    "stale-lease-project",
]
NEGATIVE_VALIDATE = [
    "broken-cycle",
    "broken-missing-artifact",
    "broken-path-escape",
    "broken-role-boundary",
    "broken-running-without-lease",
    "broken-lease-conflict",
]


def run(args: list[str], expect: int = 0, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if result.returncode != expect:
        print("COMMAND FAILED:", " ".join(args))
        print("expected:", expect, "got:", result.returncode)
        if result.stdout:
            print("STDOUT:\n" + result.stdout)
        if result.stderr:
            print("STDERR:\n" + result.stderr)
        raise SystemExit(1)
    return result


def script(name: str) -> str:
    return str(SCRIPT_DIR / name)


def validate_fixtures() -> None:
    for fixture in POSITIVE_VALIDATE:
        run([sys.executable, script("validate_state.py"), str(EXAMPLES / fixture / ".research")])
        print(f"PASS validate positive {fixture}")
    for fixture in NEGATIVE_VALIDATE:
        run([sys.executable, script("validate_state.py"), str(EXAMPLES / fixture / ".research")], expect=1)
        print(f"PASS validate negative {fixture}")


def ready_outputs() -> None:
    checks = {
        "minimal-project": "T003  Build candidate adsorption structures",
        "role-handoff-project": "T004  Critique evidence and decide claim status",
        "structure-review-project": "T003  Audit candidate slab and adsorbate geometry",
        "claim-ready-project": "T001  Submit approved fixture calculation",
    }
    for fixture, needle in checks.items():
        result = run([sys.executable, script("ready_tasks.py"), str(EXAMPLES / fixture / ".research")])
        if needle not in result.stdout:
            print(result.stdout)
            raise SystemExit(f"ready output missing expected task for {fixture}: {needle}")
        print(f"PASS ready {fixture}")


def optional_artifact_input_flow() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        shutil.copytree(EXAMPLES / "claim-ready-project", project)
        research = project / ".research"
        task_path = research / "tasks" / "T001.yaml"
        task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        task["inputs"] = [
            {
                "artifact_id": "supplied-initial-structures",
                "min_status": "accepted",
                "optional": True,
            }
        ]
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")

        run([sys.executable, script("validate_state.py"), str(research)])
        result = run([sys.executable, script("ready_tasks.py"), str(research)])
        if "T001  Submit approved fixture calculation" not in result.stdout:
            print(result.stdout)
            raise SystemExit("optional missing artifact incorrectly blocked a ready task")

        task["inputs"][0].pop("optional")
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
        result = run([sys.executable, script("validate_state.py"), str(research)], expect=1)
        if "input artifact does not exist: supplied-initial-structures" not in result.stdout:
            print(result.stdout)
            raise SystemExit("missing non-optional artifact was not rejected")
        print("PASS optional artifact input")


def approval_matching_flow() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        shutil.copytree(EXAMPLES / "claim-ready-project", project)
        research = project / ".research"
        task_path = research / "tasks" / "T001.yaml"
        task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        task["approval"] = "expensive_hpc_submission"
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")

        decisions_path = research / "decisions.jsonl"
        method_choice = {
            "decision_id": "D001",
            "task_id": "T001",
            "kind": "method-choice",
            "decision": "approved",
            "by": "user",
            "reason": "This must not unlock expensive HPC submission.",
            "created_at": "2026-06-25T00:00:00+08:00",
        }
        decisions_path.write_text(json.dumps(method_choice, sort_keys=True) + "\n", encoding="utf-8")

        result = run([sys.executable, script("ready_tasks.py"), str(research)])
        if "missing approval: expensive_hpc_submission" not in result.stdout:
            print(result.stdout)
            raise SystemExit("method-choice decision incorrectly satisfied expensive_hpc_submission")

        explicit_approval = {
            "decision_id": "D002",
            "task_id": "T001",
            "kind": "approval",
            "approval_type": "expensive_hpc_submission",
            "decision": "approved",
            "by": "user",
            "reason": "Explicitly approve the fixture expensive execution task.",
            "created_at": "2026-06-25T00:01:00+08:00",
        }
        with decisions_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(explicit_approval, sort_keys=True) + "\n")

        result = run([sys.executable, script("ready_tasks.py"), str(research)])
        if "T001  Submit approved fixture calculation" not in result.stdout:
            print(result.stdout)
            raise SystemExit("explicit approval_type did not satisfy expensive_hpc_submission")
        print("PASS approval matching")


def skill_registry_flow() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        shutil.copytree(EXAMPLES / "claim-ready-project", project)
        research = project / ".research"
        task_path = research / "tasks" / "T001.yaml"
        task = yaml.safe_load(task_path.read_text(encoding="utf-8"))

        task["skill"] = "vaspp"
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
        result = run([sys.executable, script("validate_state.py"), str(research)], expect=1)
        if "unknown `skill`: vaspp" not in result.stdout:
            print(result.stdout)
            raise SystemExit("unknown skill was not rejected")

        task["skill"] = "cp2k"
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
        run([sys.executable, script("validate_state.py"), str(research)])
        print("PASS skill registry")


def required_checks_flow() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        shutil.copytree(EXAMPLES / "claim-ready-project", project)
        (project / "work").mkdir(exist_ok=True)
        research = project / ".research"
        task_path = research / "tasks" / "T001.yaml"
        task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        task["required_checks"] = [
            f"{sys.executable} -c \"from pathlib import Path; assert Path('work').is_dir()\""
        ]
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")

        run(
            [
                sys.executable,
                script("run_required_checks.py"),
                str(research),
                "T001",
                "--now",
                "2026-06-25T00:00:00+08:00",
            ]
        )
        run([sys.executable, script("validate_state.py"), str(research)])
        events = [
            json.loads(line)
            for line in (research / "events.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not any(event.get("event") == "required_check_passed" for event in events):
            raise SystemExit("run_required_checks did not record required_check_passed")
        print("PASS required checks")


def rewrite_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def subagent_note_role_outputs_flow() -> None:
    def add_note_outputs(
        research: Path,
        task_id: str,
        note_types: list[str],
        rows: list[dict[str, object]],
    ) -> None:
        task_path = research / "tasks" / f"{task_id}.yaml"
        task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        task.setdefault("can_write", [])
        task.setdefault("outputs_expected", [])
        for note_type in note_types:
            artifact_id = f"{task_id}-{note_type}"
            path = f"work/agents/{artifact_id}.md"
            task["can_write"].append({"artifact_type": note_type})
            task["outputs_expected"].append({"artifact_id": artifact_id, "type": note_type, "path": path})
            rows.append(
                {
                    "artifact_id": artifact_id,
                    "type": note_type,
                    "path": path,
                    "produced_by": task_id,
                    "status": "validated",
                    "created_at": "2026-06-25T00:10:00+08:00",
                    "provenance": [task_id],
                    "summary": f"Smoke-test durable {note_type} from restricted role {task.get('role')}.",
                }
            )
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "structure-project"
        shutil.copytree(EXAMPLES / "structure-review-project", project)
        research = project / ".research"
        artifacts_path = research / "artifacts.jsonl"
        rows = [
            json.loads(line)
            for line in artifacts_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        add_note_outputs(research, "T001", ["subagent-finding"], rows)
        add_note_outputs(research, "T003", ["structure-review-note", "subagent-finding"], rows)
        rewrite_jsonl(artifacts_path, rows)
        run([sys.executable, script("validate_state.py"), str(research)])

    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "critic-project"
        shutil.copytree(EXAMPLES / "role-handoff-project", project)
        research = project / ".research"
        artifacts_path = research / "artifacts.jsonl"
        rows = [
            json.loads(line)
            for line in artifacts_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        add_note_outputs(research, "T004", ["result-review-note", "subagent-finding"], rows)
        add_note_outputs(research, "T005", ["synthesis-note", "handoff-note", "subagent-finding"], rows)
        rewrite_jsonl(artifacts_path, rows)
        run([sys.executable, script("validate_state.py"), str(research)])

    print("PASS subagent note role outputs")


def gate_hooks_flow() -> None:
    def copy_fixture(tmpdir: str) -> Path:
        project = Path(tmpdir) / "project"
        shutil.copytree(EXAMPLES / "gate-hook-project", project)
        return project

    with tempfile.TemporaryDirectory() as tmpdir:
        project = copy_fixture(tmpdir)
        research = project / ".research"
        run([sys.executable, script("validate_gate.py"), str(project / "work/reviews/structure_gate.yaml"), "--research", str(research), "--target-gate", "structure_gate", "--require-passing"])
        run([sys.executable, script("check_pre_submit.py"), str(research), "T002"])
        run([sys.executable, script("check_pre_accept_claim.py"), str(research), "scientific-claim", "--outcome", "addresses", "--gate-artifact", "result-gate"])
        run([sys.executable, script("check_pre_report.py"), str(research), "T005"])
        print("PASS gate hooks positive")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = copy_fixture(tmpdir)
        research = project / ".research"
        artifacts_path = research / "artifacts.jsonl"
        rows = [
            json.loads(line)
            for line in artifacts_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        for row in rows:
            if row.get("artifact_id") == "structure-gate":
                row["produced_by"] = "T002"
        rewrite_jsonl(artifacts_path, rows)
        result = run([sys.executable, script("validate_state.py"), str(research)], expect=1)
        if "structure_gate` artifacts must be produced" not in result.stdout:
            print(result.stdout)
            raise SystemExit("validate_state did not reject a non-reviewer-produced structure gate")
        result = run([sys.executable, script("check_pre_submit.py"), str(research), "T002"], expect=1)
        combined = result.stdout + result.stderr
        if (
            "structure_gate` artifacts must be produced" not in combined
            and "must be produced by an independent reviewer role" not in combined
        ):
            print(combined)
            raise SystemExit("pre-submit hook did not reject a non-reviewer-produced structure gate")
        print("PASS structure gate hooks block non-reviewer gate production")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = copy_fixture(tmpdir)
        research = project / ".research"
        task_path = research / "tasks/T002.yaml"
        task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        task["inputs"] = [
            item for item in task["inputs"] if item.get("artifact_id") != "cluster-guide-read"
        ]
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
        result = run([sys.executable, script("check_pre_submit.py"), str(research), "T002"], expect=1)
        if "no accepted `cluster-guide-read` artifact found" not in result.stderr:
            print(result.stderr)
            raise SystemExit("pre-submit hook did not block missing cluster guide evidence")
        print("PASS pre-submit hook blocks missing cluster guide evidence")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = copy_fixture(tmpdir)
        research = project / ".research"
        guide_evidence = project / "work/cluster-guide-read.md"
        guide_evidence.write_text(
            "\n".join(
                line
                for line in guide_evidence.read_text(encoding="utf-8").splitlines()
                if "Guide size bytes:" not in line
            )
            + "\n",
            encoding="utf-8",
        )
        result = run([sys.executable, script("check_pre_submit.py"), str(research), "T002"], expect=1)
        if "missing positive integer `guide_size_bytes`" not in result.stderr:
            print(result.stderr)
            raise SystemExit("pre-submit hook did not block weak cluster guide evidence")
        print("PASS pre-submit hook blocks weak cluster guide evidence")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = copy_fixture(tmpdir)
        research = project / ".research"
        gate_path = project / "work/reviews/structure_gate.yaml"
        gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
        gate["checks"][1]["metrics"]["min_adsorbate_image_A"] = 2.18
        gate["checks"][1]["metrics"]["target_min_adsorbate_image_A"] = 5.0
        gate_path.write_text(yaml.safe_dump(gate, sort_keys=False), encoding="utf-8")
        result = run(
            [
                sys.executable,
                script("validate_gate.py"),
                str(gate_path),
                "--research",
                str(research),
                "--target-gate",
                "structure_gate",
                "--require-passing",
            ],
            expect=1,
        )
        if "is below `target_min_adsorbate_image_A`" not in result.stdout:
            print(result.stdout)
            raise SystemExit("validate_gate did not reject contradictory finite-size metrics")
        print("PASS validate_gate blocks contradictory finite-size pass")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = copy_fixture(tmpdir)
        work = project / "work"
        shutil.move(project / ".research", work / ".research")
        research = work / ".research"
        run([sys.executable, script("check_pre_submit.py"), str(research), "T002"])
        result = run([sys.executable, script("validate_state.py"), str(research)])
        if "duplicate prefix" not in result.stdout:
            print(result.stdout)
            raise SystemExit("validate_state did not warn on duplicate project-root artifact prefix")
        print("PASS gate hooks tolerate duplicate project-root path prefix")

    with tempfile.TemporaryDirectory() as tmpdir:
        waived_gate = Path(tmpdir) / "waived.yaml"
        waived_gate.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "gate": "structure_gate",
                    "status": "waived",
                    "scope": {"artifacts": ["candidate-structures"]},
                    "checks": [
                        {
                            "id": "model_relevance",
                            "status": "waived",
                            "evidence": "Fixture waiver without state provenance.",
                        }
                    ],
                    "blocking_issues": [],
                    "required_fix": [],
                    "waiver": {"decision_id": "D_DOES_NOT_EXIST"},
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        result = run(
            [
                sys.executable,
                script("validate_gate.py"),
                str(waived_gate),
                "--target-gate",
                "structure_gate",
                "--require-passing",
            ],
            expect=1,
        )
        if "`status: waived` requires `--research`" not in result.stdout:
            print(result.stdout)
            print(result.stderr)
            raise SystemExit("validate_gate did not reject waived gate without research state")
        print("PASS gate hooks block waiver without research")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = copy_fixture(tmpdir)
        research = project / ".research"
        gate_path = project / "work/reviews/structure_gate.yaml"
        gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
        gate["status"] = "block"
        gate["checks"][1]["status"] = "block"
        gate["blocking_issues"] = [
            {
                "id": "finite_size_effects",
                "severity": "block",
                "evidence": "The fixture intentionally withholds finite-size justification.",
            }
        ]
        gate["required_fix"] = ["Record a finite-size rationale or revise the model."]
        gate_path.write_text(yaml.safe_dump(gate, sort_keys=False), encoding="utf-8")
        result = run([sys.executable, script("check_pre_submit.py"), str(research), "T002"], expect=1)
        if "gate status `block` does not allow downstream work" not in result.stderr:
            print(result.stderr)
            raise SystemExit("pre-submit hook did not block a blocking structure gate")
        print("PASS gate hooks block structure submit")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = copy_fixture(tmpdir)
        research = project / ".research"
        gate_path = project / "work/reviews/result_gate.yaml"
        gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
        gate["claim_outcome"] = "inconclusive"
        gate_path.write_text(yaml.safe_dump(gate, sort_keys=False), encoding="utf-8")
        result = run(
            [
                sys.executable,
                script("check_pre_accept_claim.py"),
                str(research),
                "scientific-claim",
                "--outcome",
                "addresses",
                "--gate-artifact",
                "result-gate",
            ],
            expect=1,
        )
        if "gate supports `inconclusive`, requested `addresses`" not in result.stderr:
            print(result.stderr)
            raise SystemExit("pre-accept hook did not block outcome mismatch")
        print("PASS gate hooks block result overclaim")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = copy_fixture(tmpdir)
        research = project / ".research"
        gate_path = project / "work/reviews/result_gate.yaml"
        gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
        gate["scope"]["claims"] = ["other-claim"]
        gate_path.write_text(yaml.safe_dump(gate, sort_keys=False), encoding="utf-8")
        result = run(
            [
                sys.executable,
                script("check_pre_accept_claim.py"),
                str(research),
                "scientific-claim",
                "--outcome",
                "addresses",
                "--gate-artifact",
                "result-gate",
            ],
            expect=1,
        )
        if "result_gate scope does not name claim scientific-claim" not in result.stderr:
            print(result.stderr)
            raise SystemExit("pre-accept hook did not block explicit gate scope mismatch")
        print("PASS gate hooks block result scope mismatch")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = copy_fixture(tmpdir)
        research = project / ".research"
        artifacts_path = research / "artifacts.jsonl"
        rows = [
            json.loads(line)
            for line in artifacts_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        for row in rows:
            if row.get("artifact_id") == "scientific-claim":
                row["status"] = "draft"
        rewrite_jsonl(artifacts_path, rows)
        result = run([sys.executable, script("check_pre_report.py"), str(research), "T005"], expect=1)
        if "scientific-claim is draft, needs accepted" not in result.stderr:
            print(result.stderr)
            raise SystemExit("pre-report hook did not block draft claim")
        print("PASS gate hooks block draft claim report")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = copy_fixture(tmpdir)
        research = project / ".research"
        claims_dir = project / "work" / "claims"
        claims_dir.mkdir(parents=True, exist_ok=True)
        (claims_dir / "claim2.md").write_text(
            "Second fixture claim. This is a protocol example, not a scientific result.\n",
            encoding="utf-8",
        )
        artifacts_path = research / "artifacts.jsonl"
        rows = [
            json.loads(line)
            for line in artifacts_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        rows.append(
            {
                "artifact_id": "scientific-claim-2",
                "type": "scientific-claim",
                "path": "work/claims/claim2.md",
                "produced_by": "external",
                "status": "accepted",
                "created_at": "2026-06-25T00:04:00+08:00",
                "provenance": ["work/claims/claim2.md"],
                "claim_outcome": "addresses",
                "accepted_by": "D001",
                "classified_by": "D001",
                "summary": "Second fixture claim not covered by the report gate scope.",
            }
        )
        rewrite_jsonl(artifacts_path, rows)
        task_path = research / "tasks" / "T005.yaml"
        task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        task["inputs"].insert(1, {"artifact_id": "scientific-claim-2", "min_status": "accepted"})
        task["can_read"].insert(1, {"artifact_id": "scientific-claim-2"})
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
        result = run([sys.executable, script("check_pre_report.py"), str(research), "T005"], expect=1)
        if "report_gate scope does not cover consumed claim(s): scientific-claim-2" not in result.stderr:
            print(result.stderr)
            raise SystemExit("pre-report hook did not block report gate scope gap")
        print("PASS gate hooks block report scope gap")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = copy_fixture(tmpdir)
        research = project / ".research"
        artifacts_path = research / "artifacts.jsonl"
        rows = [
            json.loads(line)
            for line in artifacts_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        rows.append(
            {
                "artifact_id": "bad-chgdiff-figure",
                "type": "figure",
                "path": "work/figures/bad-chgdiff.png",
                "produced_by": "external",
                "status": "accepted",
                "created_at": "2026-06-25T00:04:00+08:00",
                "provenance": [
                    "work/scripts/analyze_vasp_results.py",
                    "combined/CHGCAR",
                    "slab/CHGCAR",
                    "ligand/CHGCAR",
                ],
                "summary": "Charge Density Difference / Delta rho figure plotted directly from CHGCAR files.",
            }
        )
        rewrite_jsonl(artifacts_path, rows)
        task_path = research / "tasks" / "T005.yaml"
        task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        task["inputs"].insert(1, {"artifact_id": "bad-chgdiff-figure", "min_status": "accepted"})
        task["can_read"].insert(1, {"artifact_id": "bad-chgdiff-figure"})
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
        result = run([sys.executable, script("check_pre_report.py"), str(research), "T005"], expect=1)
        if "figure-routing gate" not in result.stderr or "tools/vasp/references/volumetric-visualization.md" not in result.stderr:
            print(result.stderr)
            raise SystemExit("pre-report hook did not block VASP volumetric figure without volumetric-visualization ref")
        if "tools/vasp/references/electronic-analysis.md" not in result.stderr:
            print(result.stderr)
            raise SystemExit("pre-report hook did not require VASP electronic-analysis ref for chgdiff figure")
        print("PASS pre-report blocks unrouted VASP volumetric figure")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = copy_fixture(tmpdir)
        research = project / ".research"
        manifest_path = project / "work" / "report" / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "sections": [
                        {
                            "heading": "Fixture section",
                            "figures": [
                                {
                                    "path": "work/figures/CHGDIFF_slice.png",
                                    "caption": "Charge Density Difference / Delta rho from CHGCAR files.",
                                }
                            ],
                        }
                    ]
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        artifacts_path = research / "artifacts.jsonl"
        rows = [
            json.loads(line)
            for line in artifacts_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        rows.append(
            {
                "artifact_id": "bad-report-manifest",
                "type": "report-manifest",
                "path": "work/report/manifest.json",
                "produced_by": "external",
                "status": "accepted",
                "created_at": "2026-06-25T00:04:00+08:00",
                "provenance": ["work/report/manifest.json"],
                "summary": "Manifest contains an unrouted VASP volumetric figure.",
            }
        )
        rewrite_jsonl(artifacts_path, rows)
        task_path = research / "tasks" / "T005.yaml"
        task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        task["inputs"].insert(1, {"artifact_id": "bad-report-manifest", "min_status": "accepted"})
        task["can_read"].insert(1, {"artifact_id": "bad-report-manifest"})
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
        result = run([sys.executable, script("check_pre_report.py"), str(research), "T005"], expect=1)
        if "bad-report-manifest uses VASP volumetric data" not in result.stderr:
            print(result.stderr)
            raise SystemExit("pre-report hook did not inspect report-manifest figure routing")
        print("PASS pre-report blocks unrouted VASP volumetric figure in manifest")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = copy_fixture(tmpdir)
        research = project / ".research"
        artifacts_path = research / "artifacts.jsonl"
        rows = [
            json.loads(line)
            for line in artifacts_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        rows.append(
            {
                "artifact_id": "good-chgdiff-figure",
                "type": "figure",
                "path": "work/figures/good-chgdiff.png",
                "produced_by": "external",
                "status": "accepted",
                "created_at": "2026-06-25T00:04:00+08:00",
                "provenance": [
                    "work/scripts/make_chgdiff.py recorded Delta rho sign convention and grid checks",
                    "work/figures/CHGDIFF.vasp",
                    "tools/vasp/references/electronic-analysis.md",
                    "tools/vasp/references/volumetric-visualization.md",
                ],
                "knowledge_used": [
                    "tools/vasp/references/electronic-analysis.md",
                    "tools/vasp/references/volumetric-visualization.md",
                ],
                "summary": "Charge-density-difference figure rendered from documented CHGDIFF.vasp source.",
            }
        )
        rewrite_jsonl(artifacts_path, rows)
        task_path = research / "tasks" / "T005.yaml"
        task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        task["inputs"].insert(1, {"artifact_id": "good-chgdiff-figure", "min_status": "accepted"})
        task["can_read"].insert(1, {"artifact_id": "good-chgdiff-figure"})
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
        run([sys.executable, script("check_pre_report.py"), str(research), "T005"])
        print("PASS pre-report allows routed VASP volumetric figure")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = copy_fixture(tmpdir)
        research = project / ".research"
        proposal_path = project / "work" / "followups" / "follow-up-proposal.yaml"
        proposal_path.parent.mkdir(parents=True, exist_ok=True)
        proposal_path.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "proposal_id": "follow-up-proposal",
                    "source_claim_id": "scientific-claim",
                    "recommended_tasks": [
                        {
                            "title": "Fixture follow-up task",
                            "role": "engine-runner",
                            "skill": "vasp",
                            "outputs_expected": [
                                {
                                    "artifact_id": "parser-result-follow-up",
                                    "type": "parser-result",
                                    "path": "work/run-follow-up/parser-result.json",
                                }
                            ],
                        }
                    ],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        artifacts_path = research / "artifacts.jsonl"
        rows = [
            json.loads(line)
            for line in artifacts_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        rows.append(
            {
                "artifact_id": "follow-up-proposal",
                "type": "follow-up-proposal",
                "path": "work/followups/follow-up-proposal.yaml",
                "produced_by": "T003",
                "status": "accepted",
                "created_at": "2026-06-25T00:04:00+08:00",
                "provenance": ["scientific-claim"],
                "source_claim_id": "scientific-claim",
                "blocks_report": True,
                "summary": "Fixture open follow-up proposal.",
            }
        )
        rewrite_jsonl(artifacts_path, rows)

        result = run([sys.executable, script("check_pre_report.py"), str(research), "T005"], expect=1)
        if "unresolved follow-up proposal(s): follow-up-proposal" not in result.stderr:
            print(result.stderr)
            raise SystemExit("pre-report hook did not block unresolved follow-up proposal")
        if "wrote temporary stage-synthesis report: work/report/stage-synthesis-T005.md" not in result.stderr:
            print(result.stderr)
            raise SystemExit("pre-report hook did not write a temporary stage-synthesis report")
        if not (project / "work/report/stage-synthesis-T005.md").is_file():
            raise SystemExit("temporary stage-synthesis report file is missing")
        if not (research / "tasks" / "T006.yaml").is_file():
            raise SystemExit("pre-report hook did not scaffold a follow-up task")
        result = run([sys.executable, script("ready_tasks.py"), str(research)])
        if "unresolved follow-up proposal(s): follow-up-proposal" not in result.stdout:
            print(result.stdout)
            raise SystemExit("ready_tasks did not show final report blocked by unresolved follow-up")
        print("PASS report blocks unresolved follow-up")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        shutil.copytree(EXAMPLES / "iterative-followup-project", project)
        research = project / ".research"
        run([sys.executable, script("check_pre_report.py"), str(research), "T006"])
        result = run([sys.executable, script("ready_tasks.py"), str(research)])
        if "T006  Build final report after follow-up resolution" not in result.stdout:
            print(result.stdout)
            raise SystemExit("ready_tasks did not allow report after follow-up resolution")
        print("PASS report allows resolved follow-up")


def lease_cli_flow() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        shutil.copytree(EXAMPLES / "claim-ready-project", project)
        research = project / ".research"
        run(
            [
                sys.executable,
                script("claim_task.py"),
                str(research),
                "T001",
                "--owner",
                "tester",
                "--lease-id",
                "LTEST",
                "--now",
                "2026-06-25T00:00:00+08:00",
            ]
        )
        run(
            [
                sys.executable,
                script("claim_task.py"),
                str(research),
                "T001",
                "--owner",
                "tester2",
                "--lease-id",
                "LTEST2",
                "--now",
                "2026-06-25T00:01:00+08:00",
            ],
            expect=1,
        )
        run(
            [
                sys.executable,
                script("heartbeat_task.py"),
                str(research),
                "T001",
                "--owner",
                "tester",
                "--now",
                "2026-06-25T00:05:00+08:00",
            ]
        )
        run(
            [
                sys.executable,
                script("release_task.py"),
                str(research),
                "T001",
                "--owner",
                "tester",
                "--status",
                "completed",
                "--now",
                "2026-06-25T00:06:00+08:00",
            ]
        )
        run([sys.executable, script("validate_state.py"), str(research)])
        task = yaml.safe_load((research / "tasks" / "T001.yaml").read_text(encoding="utf-8"))
        lease = json.loads((research / "leases" / "T001.json").read_text(encoding="utf-8"))
        if task["status"] != "completed" or lease["status"] != "released":
            raise SystemExit("lease CLI flow did not complete/release as expected")
        print("PASS lease claim heartbeat release")


def stale_reconcile_flow() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        shutil.copytree(EXAMPLES / "stale-lease-project", project)
        research = project / ".research"
        result = run(
            [
                sys.executable,
                script("reconcile_leases.py"),
                str(research),
                "--now",
                "2026-06-25T00:30:00+08:00",
            ]
        )
        if "STALE T001" not in result.stdout:
            raise SystemExit("stale reconcile did not report stale lease")
        run(
            [
                sys.executable,
                script("reconcile_leases.py"),
                str(research),
                "--mark-stale",
                "--now",
                "2026-06-25T00:30:00+08:00",
            ]
        )
        run([sys.executable, script("validate_state.py"), str(research)])
        task = yaml.safe_load((research / "tasks" / "T001.yaml").read_text(encoding="utf-8"))
        lease = json.loads((research / "leases" / "T001.json").read_text(encoding="utf-8"))
        if task["status"] != "blocked" or lease["status"] != "stale":
            raise SystemExit("stale reconcile did not block task and mark lease stale")
        print("PASS stale reconcile")


def claim_and_report_helpers_flow() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        shutil.copytree(EXAMPLES / "claim-ready-project", project)
        research = project / ".research"
        work = project / "work"
        work.mkdir(exist_ok=True)
        (work / "parser-result.json").write_text('{"value": -0.12, "units": "eV"}\n', encoding="utf-8")
        (work / "claim.md").write_text("Fixture claim.\n", encoding="utf-8")
        artifacts_path = research / "artifacts.jsonl"
        artifacts = [
            {
                "artifact_id": "parser-result",
                "type": "parser-result",
                "path": "work/parser-result.json",
                "produced_by": "external",
                "status": "validated",
                "created_at": "2026-06-25T00:00:00+08:00",
                "provenance": ["work/parser-result.json"],
                "units": "eV",
            },
            {
                "artifact_id": "scientific-claim",
                "type": "scientific-claim",
                "path": "work/claim.md",
                "produced_by": "external",
                "status": "draft",
                "created_at": "2026-06-25T00:00:00+08:00",
                "provenance": ["work/parser-result.json"],
                "summary": "Fixture claim for helper testing.",
            },
        ]
        artifacts_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in artifacts) + "\n", encoding="utf-8")
        run([sys.executable, script("validate_state.py"), str(research)])
        run(
            [
                sys.executable,
                script("accept_artifact.py"),
                str(research),
                "parser-result",
                "--status",
                "accepted",
                "--reason",
                "fixture parser result accepted for smoke test",
                "--now",
                "2026-06-25T00:01:00+08:00",
            ]
        )
        run(
            [
                sys.executable,
                script("classify_claim.py"),
                str(research),
                "scientific-claim",
                "--outcome",
                "addresses",
                "--reason",
                "fixture claim addresses the smoke-test objective",
                "--evidence",
                "parser-result",
                "--now",
                "2026-06-25T00:02:00+08:00",
            ]
        )
        manifest = project / "work" / "report-manifest.json"
        run([sys.executable, script("scaffold_report_manifest.py"), str(research), "-o", str(manifest)])
        run([sys.executable, script("validate_state.py"), str(research)])
        rows = [json.loads(line) for line in artifacts_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        by_id = {row["artifact_id"]: row for row in rows}
        if by_id["parser-result"]["status"] != "accepted":
            raise SystemExit("accept_artifact did not accept parser-result")
        if by_id["scientific-claim"].get("claim_outcome") != "addresses":
            raise SystemExit("classify_claim did not record addresses outcome")
        manifest_obj = json.loads(manifest.read_text(encoding="utf-8"))
        if not manifest_obj.get("sections"):
            raise SystemExit("scaffold_report_manifest did not write sections")
        print("PASS artifact claim report helpers")


def first_submit_boundary_warning_flow() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        shutil.copytree(EXAMPLES / "role-handoff-project", project)
        research = project / ".research"
        task_path = research / "tasks" / "T006.yaml"
        task = {
            "schema_version": 1,
            "id": "T006",
            "title": "Mistakenly gate first submit on result review",
            "role": "engine-runner",
            "role_contract": "procedures/research-orchestrator/references/roles.md#engine-runner",
            "skill": "vasp",
            "status": "approved",
            "depends_on": ["T004"],
            "approval": "promote_claim_to_report",
            "inputs": [{"artifact_id": "model-observable-decision", "min_status": "accepted"}],
            "can_read": [{"artifact_id": "model-observable-decision"}],
            "can_write": [{"artifact_type": "parser-result"}],
            "cannot": ["treat report approval as an execution precondition"],
            "outputs_expected": [
                {
                    "artifact_id": "parser-result-follow-up",
                    "type": "parser-result",
                    "path": "work/parser-result-follow-up.json",
                }
            ],
            "success_criteria": ["fixture only"],
            "knowledge_required": [],
            "required_refs": ["tools/vasp/SKILL.md"],
            "required_checks": [
                "uv run procedures/research-orchestrator/scripts/check_pre_report.py .research T005"
            ],
            "release_gates": ["result_gate"],
            "execution_policy": {"mode": "single_owner", "allow_parallel_subagents": False},
            "assumptions": [],
            "provenance": [],
        }
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")

        result = run([sys.executable, script("validate_state.py"), str(research)])
        if "release-gate/input boundary issue" not in result.stdout:
            print(result.stdout)
            raise SystemExit("validate_state did not warn on post-result first-submit dependency")

        task["stage"] = "follow-up"
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
        result = run([sys.executable, script("validate_state.py"), str(research)])
        if "release-gate/input boundary issue" in result.stdout:
            print(result.stdout)
            raise SystemExit("follow-up stage did not suppress first-submit boundary warning")
        print("PASS first-submit boundary warning")


def structure_gate_input_warning_flow() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        shutil.copytree(EXAMPLES / "gate-hook-project", project)
        research = project / ".research"
        task_path = research / "tasks" / "T002.yaml"
        task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        task["inputs"] = []
        task["can_read"] = []
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")

        result = run([sys.executable, script("validate_state.py"), str(research)])
        if "inputs do not declare a structure_gate/model-structure-review artifact" not in result.stdout:
            print(result.stdout)
            raise SystemExit("validate_state did not warn on missing structure_gate task input")

        task["inputs"] = [{"artifact_id": "structure-gate", "min_status": "accepted"}]
        task["can_read"] = [{"artifact_id": "structure-gate"}]
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
        result = run([sys.executable, script("validate_state.py"), str(research)])
        if "inputs do not declare a structure_gate/model-structure-review artifact" in result.stdout:
            print(result.stdout)
            raise SystemExit("structure_gate task input did not suppress boundary warning")
        print("PASS structure gate input warning")


def scaffold_follow_up_flow() -> None:
    edge_task = build_task(
        {
            "title": "Scaffold edge-case task",
            "role": "engine-runner",
            "skill": "vasp",
            "outputs_expected": [{"artifact_id": "edge-output", "path": "work/edge/output.json"}],
        },
        "T999",
        "edge-follow-up",
        {"artifact_id": "edge-follow-up", "type": "follow-up-proposal", "produced_by": "T003"},
        {},
    )
    if "" in edge_task.get("provenance", []):
        raise SystemExit("scaffold_follow_up_tasks added empty-string provenance")
    if {"artifact_id": "edge-output"} not in edge_task.get("can_write", []):
        raise SystemExit("scaffold_follow_up_tasks did not fall back to can_write artifact_id")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "project"
        shutil.copytree(EXAMPLES / "gate-hook-project", project)
        research = project / ".research"
        proposal_path = project / "work" / "followups" / "follow-up-proposal.yaml"
        proposal_path.parent.mkdir(parents=True, exist_ok=True)
        proposal_path.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "proposal_id": "follow-up-proposal",
                    "source_claim_id": "scientific-claim",
                    "wave_id": "wave-2",
                    "iteration": 2,
                    "recommended_tasks": [
                        {
                            "title": "Run follow-up fixture calculation",
                            "role": "engine-runner",
                            "skill": "vasp",
                            "approval": "none",
                            "outputs_expected": [
                                {
                                    "artifact_id": "parser-result-follow-up",
                                    "type": "parser-result",
                                    "path": "work/run-follow-up/parser-result.json",
                                }
                            ],
                        }
                    ],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        artifacts_path = research / "artifacts.jsonl"
        rows = [
            json.loads(line)
            for line in artifacts_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        rows.append(
            {
                "artifact_id": "follow-up-proposal",
                "type": "follow-up-proposal",
                "path": "work/followups/follow-up-proposal.yaml",
                "produced_by": "T003",
                "status": "accepted",
                "created_at": "2026-06-25T00:04:00+08:00",
                "provenance": ["scientific-claim"],
                "source_claim_id": "scientific-claim",
                "blocks_report": True,
                "summary": "Fixture follow-up proposal for scaffolding.",
            }
        )
        rewrite_jsonl(artifacts_path, rows)

        run(
            [
                sys.executable,
                script("scaffold_follow_up_tasks.py"),
                str(research),
                "follow-up-proposal",
                "--now",
                "2026-06-25T00:05:00+08:00",
            ]
        )
        task_path = research / "tasks" / "T006.yaml"
        if not task_path.is_file():
            raise SystemExit("scaffold_follow_up_tasks did not create T006.yaml")
        task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        if task.get("source_proposal") != "follow-up-proposal":
            raise SystemExit("scaffolded task missing source_proposal")
        if task.get("stage") != "follow-up":
            raise SystemExit("scaffolded task missing follow-up stage")
        if task.get("resolves_follow_up") != "follow-up-proposal":
            raise SystemExit("scaffolded task missing resolves_follow_up")
        print("PASS scaffold follow-up tasks")


def init_project_flow() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir) / "new-project"
        run(
            [
                sys.executable,
                script("init_project.py"),
                str(project),
                "--project-id",
                "smoke-project",
                "--title",
                "Smoke project",
                "--objective",
                "Exercise project initialization",
                "--created-at",
                "2026-06-25T00:00:00+08:00",
                "--with-workflow",
            ]
        )
        run([sys.executable, script("validate_state.py"), str(project / ".research")])
        if not (project / "workflow.md").is_file():
            raise SystemExit("init_project did not create workflow.md")
        print("PASS init_project")


def aicc_cli_smoke_flow() -> None:
    smoke = REPO_ROOT / "aicc" / "tests" / "smoke_test.py"
    result = run([sys.executable, str(smoke)])
    if "== aicc smoke: clean ==" not in result.stdout:
        raise SystemExit("AICC smoke test did not report clean completion")
    print("PASS aicc CLI integration")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-cli", action="store_true", help="Skip mutating temp-directory CLI flows")
    args = parser.parse_args()

    validate_fixtures()
    ready_outputs()
    optional_artifact_input_flow()
    approval_matching_flow()
    skill_registry_flow()
    subagent_note_role_outputs_flow()
    required_checks_flow()
    gate_hooks_flow()
    if not args.skip_cli:
        lease_cli_flow()
        stale_reconcile_flow()
        claim_and_report_helpers_flow()
        first_submit_boundary_warning_flow()
        structure_gate_input_warning_flow()
        scaffold_follow_up_flow()
        init_project_flow()
        aicc_cli_smoke_flow()
    print("== smoke_tests: clean ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
