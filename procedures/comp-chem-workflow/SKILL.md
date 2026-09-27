---
name: comp-chem-workflow
description: Entry point and controller for computational chemistry and materials workflows. Use when the agent must design, prepare, run, monitor, resume, validate, or report multi-stage atomistic work - DFT, quantum chemistry, MD, machine-learning potentials, phonons, HPC pipelines, benchmarks, reproductions, or literature/reviewer-derived calculations.
---

# Computational Chemistry Workflow Controller

Use this skill first for nontrivial computational work. It owns the **scientific
lifecycle and cross-engine validation discipline**. It does not own durable project
state or execution permissions (`research-orchestrator`), engine input/output details
(the relevant tool skill), scheduler operation (`hpc-submit`), or publication assembly
(`report`). Repository-wide rules in `AGENTS.md` always apply.

## Entry decision

| Starting point | Route |
|---|---|
| Scientific question or new calculation | Scope the full lifecycle below. |
| Existing inputs/run directory | Inspect in place, then use the producing engine skill and `hpc-submit` if execution is needed. |
| Existing outputs | Use the producing engine skill's parser and analysis guidance. |
| Third-party paper/SI/report | Start with `literature-to-calculation`. |
| Manuscript plus reviewer comments | Start with `review-response`; it invokes this procedure for approved calculations. |
| Multi-stage, HPC, resumable, or multi-owner project | Add `research-orchestrator` before execution. |
| Existing job to resume or monitor | Reconcile durable state, scheduler state, logs, and parser verdicts; never resubmit blindly. |

## Core decisions before input generation

Record:

- the scientific objective and falsifiable success criteria;
- a code-independent proposal for the calculations that answer it;
- model, method, reference states, assumptions, and explicit non-goals;
- the downstream code chosen from availability and group convention;
- execution target, approximate cost, and required approval.

Choose the science first and the engine second. Missing structures or incomplete source
methods change the route to a disclosed designed/reconstructed model; they do not
license invented inputs. Use `structure-prep` and, for surface/defect/adsorbate models,
the orchestrator's model-structure review. For an unresolved scientific fork with
material cost or interpretive impact, stop at the applicable approval breakpoint.

## Workflow

```text
intake -> scope and success criteria -> structure preparation -> method selection
  -> input generation -> preflight -> execution/monitoring/recovery
  -> parsing -> scientific validation -> evidence review
  -> accepted claim, explicit limitation, or follow-up task
```

Before every generated job, run the engine skill's prescribed input checks. Use
`hpc-submit` for submission/monitoring/recovery and the engine's exact-error guidance
for failures. On resume, continue from the earliest unfinished or unaccepted evidence,
not from chat memory.

## Validation and iteration

Report every result at its actual rung:

```text
files exist -> terminated normally -> technically converged -> scientifically valid
```

The engine parser/checker decides technical convergence. Scientific validation checks
that references and settings are comparable, magnitudes and structures are sane, and
the result still answers the registered objective. A converged number is not
automatically a valid or accepted claim.

After each coherent calculation wave, assemble evidence and classify the scientific
outcome as `addresses`, `contradicts`, `inconclusive`, or `needs-follow-up`.
Follow-up outcomes create new work; they are not repaired by drafting. Final reporting
uses accepted claims or visibly recorded limitations.

## Where to find what

| Situation | Open or run |
|---|---|
| Lifecycle states, validation ladder, comparison/reuse rules | `references/state-and-validation.md` |
| Durable DAG, artifacts, gates, leases, permissions, recovery | `procedures/research-orchestrator/SKILL.md` |
| Structure building and numerical checks | `tools/structure-prep/SKILL.md` |
| Surface/defect/adsorbate review gate | `procedures/research-orchestrator/references/model-structure-review.md` |
| Engine inputs, validation, parsing, and exact failure recovery | the selected engine's `SKILL.md`, `references/running.md`, `references/validation.md`, and `references/errors.md` |
| Local/SSH/scheduler submission and monitoring | `tools/hpc-submit/SKILL.md` |
| Literature-derived targets and method evidence | `procedures/literature-to-calculation/SKILL.md` |
| Reviewer-comment planning and response semantics | `procedures/review-response/SKILL.md` |
| Interim synthesis and final deliverables | `tools/report/SKILL.md` and `tools/report/references/validation.md` |
| Scientific interpretation | the relevant flat `knowledge/*.md` reference |

## Workflow handoff

At a pause or handoff, record:

```text
Stage: <id> (<status>)
Did: <what was actually executed/generated>
Evidence: <files, job ids, log paths>
Validation: <parser/checker verdict, command, exit status>
Acceptance: <accepted by user/critic/orchestrator, or pending>
Assumptions: <anything not user-confirmed>
Next: <next stage or the single question blocking it>
```

## Hard guardrails

- Never skip structure, engine-input, parser, or scientific validation gates merely
  because a scheduler or executable reports success.
- Keep `completed`, `validated`, and `accepted` distinct.
- Do not promote smoke tests, unrelaxed models, failed runs, or exploratory assumptions
  into production conclusions.
- A `contradicts` result is surfaced with its evidence; it is never softened or hidden.
- Preserve commands, inputs, outputs, logs, units, and provenance for every reported
  quantity.
