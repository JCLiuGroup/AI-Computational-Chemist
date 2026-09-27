---
name: research-orchestrator
description: Define and maintain machine-readable research project state for multi-stage computational chemistry work. Use when a project needs task DAGs, artifact registries, decision logs, ready/blocked task checks, or structured handoff between cognitive roles and deterministic tool skills.
---

# Research Orchestrator

This procedure owns **durable project state, handoffs, readiness, permissions, gates,
and execution ownership**. It does not own the scientific lifecycle
(`comp-chem-workflow`), reviewer-response semantics (`review-response`), or any engine,
structure, HPC, visualization, or report operation. A task's `skill` remains
authoritative for doing and validating that task.

Use it when work is multi-stage, resumable, HPC-backed, shared across agents, or needs
auditable approvals and claims. Skip it for a quick, isolated parse or conversion.

## Control plane

`.research/` is the machine-readable source of truth:

```text
.research/
  project.yaml
  tasks/*.yaml
  artifacts.jsonl
  decisions.jsonl
  events.jsonl
  leases/*.json
  jobs/*.json
```

`workflow.md` or `response-workflow.md` may summarize this state for humans but must
not override it. The protocol records state; it is not a scheduler, database, worker,
or substitute for tool execution.

Core semantics:

- readiness is derived from task state, dependencies, inputs, approvals, leases, and
  output conflicts;
- `completed` records producer completion, `validated` requires the named deterministic
  checker/parser, and `accepted` requires an authorized scientific or human decision;
- plan, structure, result, and report gates release only their matching downstream
  action;
- cognitive review may be parallel, but expensive execution has one claimed owner and
  one exclusive run directory;
- stale leases or recorded jobs are reconciled before any continuation or resubmission;
- critic outcomes can add follow-up nodes, so the DAG may cycle through new evidence.

## Workflow

1. Initialize the project with objective, success criteria, mode, and approval policy.
2. Create task nodes with dependencies, role/permission contract, routed skill,
   required knowledge/checks, inputs, outputs, and execution policy.
3. Register source and generated artifacts; append decisions and events instead of
   rewriting history.
4. Validate state and derive ready/blocked tasks.
5. Before expensive execution, satisfy the applicable plan/structure/pre-submit gates,
   claim the task, and hand execution to its engine and `hpc-submit` skills.
6. Register parser evidence, run result criticism, and either accept a claim, record a
   limitation, or scaffold follow-up tasks.
7. Release final reporting only after its claims and report gate are ready.

Do not put result critics or report gates before the first calculation wave: those
consume evidence that does not yet exist. Candidate structure construction may proceed
before a structure verdict, but engine/HPC consumption waits for the applicable
accepted structure review.

## Where to find the contract

| Situation | Reference |
|---|---|
| State layout and source-of-truth rules | `references/state-files.md` |
| Task schema, statuses, skill/knowledge binding, execution policy | `references/task-protocol.md` |
| Roles, permissions, output boundaries | `references/roles.md` |
| Producer/consumer handoffs and durable subagent findings | `references/handoff-contracts.md`, `references/subagent-artifacts.md` |
| Artifact provenance and acceptance | `references/artifact-contract.md` |
| Decisions, assumptions, events, reconciliation | `references/event-log.md` |
| Ready/blocked derivation | `references/ready-rules.md` |
| Plan/structure/result/report gate schema | `references/gate-contract.md` |
| Surface/defect/adsorbate structure review | `references/model-structure-review.md` |
| Critic responsibilities and evidence packets | `references/critic-contract.md`, `references/evidence-packets.md` |
| Owner directories and exclusive outputs | `references/ownership-protocol.md` |
| Leases, scheduler attempts, and recovery | `references/lease-contract.md`, `references/job-contract.md`, `references/recovery-protocol.md` |

## Script map

Run paths below from `procedures/research-orchestrator/`.

| Action | Command |
|---|---|
| Initialize | `uv run scripts/init_project.py PROJECT --project-id ID --title TITLE --objective OBJECTIVE` |
| Validate / inspect readiness | `uv run scripts/validate_state.py PATH/.research`; `uv run scripts/ready_tasks.py PATH/.research` |
| Run declared deterministic checks | `uv run scripts/run_required_checks.py PATH/.research TASK_ID` |
| Validate a gate | `uv run scripts/validate_gate.py GATE.yaml --research PATH/.research` |
| Enforce release hooks | `uv run scripts/check_pre_submit.py PATH/.research TASK_ID`; `uv run scripts/check_pre_accept_claim.py PATH/.research CLAIM_ID --outcome OUTCOME`; `uv run scripts/check_pre_report.py PATH/.research TASK_ID` |
| Claim / heartbeat / release execution | `uv run scripts/claim_task.py PATH/.research TASK_ID`; `uv run scripts/heartbeat_task.py PATH/.research TASK_ID`; `uv run scripts/release_task.py PATH/.research TASK_ID --status completed` |
| Reconcile leases or jobs | `uv run scripts/reconcile_leases.py PATH/.research`; `uv run scripts/reconcile_jobs.py PROJECT RUN_DIR` |
| Submit one claimed Slurm attempt | `uv run scripts/submit_job.py PROJECT TASK_ID RUN_DIR --script job.sh --owner OWNER` |
| Recover an explicit stale lock | `uv run scripts/recover_lock.py PROJECT [RUN_DIR] --reason REASON --confirm` |
| Record artifact status / claim outcome | `uv run scripts/accept_artifact.py PATH/.research ARTIFACT_ID --status accepted --reason REASON`; `uv run scripts/classify_claim.py PATH/.research CLAIM_ID --outcome OUTCOME --reason REASON` |
| Create follow-up tasks / report manifest | `uv run scripts/scaffold_follow_up_tasks.py PATH/.research PROPOSAL_ID`; `uv run scripts/scaffold_report_manifest.py PATH/.research -o work/report-manifest.json` |
| Check structure-generator boundary | `uv run scripts/check_structure_generator_boundary.py --forbid-engine-inputs PATH/TO/SCRIPTS` |
| Run protocol smoke tests | `uv run scripts/smoke_tests.py` |

Working state examples live under `examples/minimal-project/`,
`examples/role-handoff-project/`, and the claim/lease example directories.

## Hard guardrails

- Never use state or gate metadata to bypass the routed tool skill's validation.
- Never allow two active owners to write the same run directory or submit the same
  attempt.
- Never resubmit from a stale lease, vanished queue entry, or ambiguous job record
  without reconciliation.
- Structure producers cannot approve their own structure review; claim producers cannot
  self-assert acceptance.
- Final reports consume accepted claims by default. Stage synthesis must remain visibly
  interim and list pending, waived, inconclusive, and `needs-follow-up` items.
- Never store secrets, private connection details, full POTCAR data, or licensed
  potential/force-field contents in `.research/`.
