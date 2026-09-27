# Research State Files

> Load this when: creating or reviewing a `.research/` directory, deciding what the
> project source of truth is, or writing `project.yaml`.

The `.research/` directory is the machine-readable state record for a computational
research project. It complements, but supersedes, human-readable `workflow.md` summaries.

```text
.research/
  project.yaml
  tasks/
    T001.yaml
    T002.yaml
  jobs/
    J-<uuid>.json
  leases/
    T002.json
  artifacts.jsonl
  decisions.jsonl
  events.jsonl
```

## Source of Truth

- `.research/` is authoritative for structured state.
- `workflow.md` and `response-workflow.md` are human-readable summaries and must be
  reconciled from `.research/`, filesystem state, scheduler state, and parser outputs.
- `.research/leases/*.json` records execution ownership. A lease is an execution claim,
  not scientific validation and not permission to resubmit after expiry.
- `.research/jobs/*.json` is the authoritative scheduler-attempt history. Run-directory
  `.aicc-active-job.json` files are duplicate-submission pointers only; follow
  `job-contract.md`.
- If a task file and event log disagree, report the discrepancy and reconcile from
  evidence: files on disk, scheduler accounting, and engine parser results.

## `project.yaml`

Required fields:

```yaml
schema_version: 1
project_id: rr-example-2026-06
title: Reviewer-response calculations for example manuscript
mode: semi-automatic
created_at: "2026-06-25T00:00:00+08:00"
objective: >
  Plan, execute, validate, and report calculations responding to reviewer comments.
success_criteria:
  - every approved computable comment has an accepted outcome
  - every quantitative claim has provenance and units
  - contradictions are surfaced before report drafting
default_policy:
  approval_required_for:
    - expensive_hpc_submission
    - scientific_model_choice
    - overwrite_existing_data
    - promote_claim_to_report
```

`mode` is one of:

- `semi-automatic` — stop at approval breakpoints.
- `autonomous` — use documented defaults at approval breakpoints and keep
  `contradicts` as flagged findings.

## Path Rules

- Paths in `.research/` are relative to the project root, except references to repo
  files such as `tools/vasp/SKILL.md` or `knowledge/electrochemistry.md`.
- The project root is the parent directory of `.research`. If `.research` lives under
  `work/.research`, artifact paths are relative to `work/`; write
  `reviews/structure_gate.yaml`, not `work/reviews/structure_gate.yaml`.
- Artifact paths must stay inside the project root.
- Registry content must not include secrets, tokens, full POTCAR contents, licensed
  force-field contents, or private cluster connection details.
- Lease `owner_dir` and `exclusive_paths` must stay inside the project root.

## Human Summaries

When a workflow summary exists, keep it small:

- objective and success criteria;
- current accepted artifacts;
- current ready and blocked tasks;
- scheduler/job IDs;
- next action.

Do not make Markdown the only copy of a dependency, approval, or artifact status.
