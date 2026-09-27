# Workflow State and Validation Ladder

> Load this when: resuming a multi-stage calculation, interpreting workflow status, or
> deciding whether an engine result is scientifically usable.

## State ownership

`research-orchestrator` owns the durable `.research/` schema, task DAG, leases, job
attempts, gates, and recovery protocol. Use its `references/state-files.md`,
`references/task-protocol.md`, and `references/job-contract.md`; do not maintain a
second schema here.

`workflow.md` and `response-workflow.md` are optional, derived summaries for humans.
When present, keep only the objective, success criteria, assumptions, reusable assets,
current statuses, job IDs, and next action. Reconcile them from `.research/`, files,
scheduler evidence, and parser results. Never make Markdown the sole record of a
dependency, approval, artifact status, or job attempt.

Before planning new work, reuse an existing accepted asset only when its recorded
method fingerprint and intended scope match the new task. On resume, reconcile active
leases and scheduler attempts before any rerun or resubmission.

## Status meanings

The canonical transitions and exceptional states live in the orchestrator task
protocol. These three labels must remain distinct:

- `completed`: expected work or files exist.
- `validated`: the required technical/scientific checks passed.
- `accepted`: an authorized reviewer accepted the evidence or claim for downstream
  use. Final reports consume accepted claims by default.

Acceptance is claim-level, not proof that the whole project is complete.
`needs-follow-up` creates a concrete proposed task; `inconclusive` remains visible
unless an accepted limitation or waiver resolves it.

## Validation ladder

Engine skills parse and validate their own outputs. The cross-engine discipline is:

1. **Files exist** — expected artifacts were produced.
2. **Terminated normally** — otherwise identify the exact failure through the engine's
   `references/errors.md`.
3. **Technically converged** — the engine-specific SCF, optimization, or MD criteria
   passed.
4. **Scientifically valid** — reference states and corrections are appropriate,
   compared runs use aligned settings, magnitudes are plausible, and the final
   structure still represents the declared chemical model.

Rung 3 without rung 4 is a converged number, not a scientific result. A validated
result without acceptance is not yet a reportable claim.

For every comparison, verify the actual inputs share the required functional,
cutoff/basis, k-density, U, dispersion, and convergence conventions. Record the energy
type (`E`, `E+ZPE`, `H`, or `G`), unit, and file provenance for every value.

## Checks and release gates

Validation checks surface evidence; they do not silently rewrite inputs or promote a
claim. A failed or unmet check stays visible and routes to recovery, follow-up, or an
explicit limitation.

The orchestrator's named pre-submit, pre-accept, and pre-report hooks are hard only at
their corresponding release points. Contradicting scientific outcomes are always
prominent: semi-automatic mode pauses for author review, while explicitly requested
autonomous mode records the contradiction and continues with a flagged draft.
