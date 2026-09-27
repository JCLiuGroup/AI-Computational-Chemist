---
name: review-response
description: Orchestrate semi-automatic computational responses to peer review. Use when a manuscript and reviewer comments are provided and the agent must identify which comments require computation, plan and run calculations consistent with the manuscript's methods, validate whether each result actually addresses the concern, and draft response-letter and SI material.
---

# Peer-Review Response Orchestrator

This procedure owns **reviewer-comment triage, method consistency, per-comment
satisfaction criteria, scientific outcome semantics, and response-package decisions**.
It coordinates `literature-to-calculation`, `comp-chem-workflow`,
`research-orchestrator`, engine skills, and `report`; it does not replace them or run
engines itself.

```text
Phase 0  ingest manuscript/SI/reviews/archive
  -> Phase 1  establish method fingerprint
  -> Phase 2  triage all comments and approve one coherent plan       [APPROVAL #1]
  -> Phase 3  execute approved work through comp-chem-workflow
  -> Phase 4  judge each result against its registered reviewer bar
  -> Phase 5  iterate follow-up work or draft letter/SI package       [APPROVAL #2]
```

## Phase 0 — Ingestion contract

Request the manuscript, SI, all reviewer reports, author constraints, and the original
calculation archive. Search the manuscript/SI for its computational methods before
deciding whether a method must be designed. Produce one stable ingestion object:

- atomic comments `{id, reviewer, page, verbatim_quote}` using IDs `R#.C#`;
- whether a computational methods section exists and where;
- whether original inputs, outputs, and structures are available.

All downstream triage, state, and drafting keys off this object, not ad hoc PDF
locations. Register it as an `ingestion-object` when using `.research/`.
The operational PDF-extraction recipe (methods-section probe, per-page comment
scan) lives in `references/ingestion.md`.

## Phase 1 — Method baseline

Create one `method-fingerprint` using the canonical provenance fields:

- `origin`: `manuscript-derived`, `source-paper-derived`,
  `related-literature-derived`, `designed`, or `mixed`;
- `reproduction_mode`: `reproduction` or `exploration`.

Use `manuscript-derived` when the manuscript/archive supplies the settings; original
inputs outrank prose and unknown values remain `unknown`. If a computational
manuscript's settings must be reconstructed, preserve each surviving value and label
every literature-derived or designed assumption. That route is normally `mixed` and
`exploration`, never an undisclosed reproduction. For an experimental manuscript with
no computational method, use source/related-literature provenance where applicable or
`designed`, anchor the smallest credible model to experiment, and record limitations.

The fingerprint is a comparability contract, not a demand for byte-identical inputs.
All response calculations preserve comparable scientific knobs and reference states.
Any necessary deviation is pre-registered, justified, and disclosed; a
`method-challenge` may intentionally benchmark a changed setting.

Missing archives or structures change provenance and may require new model building;
it does not justify invented details. Route model construction and review through
`comp-chem-workflow` and `structure-prep`.

## Phase 2 — Comment triage

Read all comments before planning. Split them into atomic `R#.C#` items and build one
coherent plan that reuses models, references, and calculations. Classify each item with
`references/comment-taxonomy.md`:

| Class | Meaning | Route |
|---|---|---|
| `compute-new` | New calculation is needed. | `comp-chem-workflow` |
| `reanalyze` | Existing archive can answer it. | Producing engine's parser/analysis |
| `method-challenge` | The method itself is questioned. | Controlled representative benchmark |
| `add-figure` | Existing evidence needs a new or revised figure/table. | `report` figure contract and QA |
| `text-only` | No computation is needed. | Return to the authors |
| `needs-human-decision` | Ambiguous, infeasible, strategic, or out of scope. | Present options, evidence, and cost |

For each computable item, record the verbatim concern, target observable, falsifiable
satisfaction criterion, directness, method delta, route, cost, scale/statistics need,
dependencies, and reusable artifacts. Mark proxies as `adjacent-question-risk`; do not
silently substitute an easier question.

**Approval #1:** present the complete triage table and shared calculation plan before
execution. Partial approval is tracked per comment. Autonomous mode records the
documented default decision instead of pausing, as defined in `AGENTS.md`.

## Phase 3–4 — Execution and reviewer-bar validation

Route each approved calculation through `comp-chem-workflow`; use
`research-orchestrator` for the task DAG, reuse, gates, and single-owner execution.
Technical convergence is necessary but does not answer the reviewer. Judge each
validated result against its pre-registered satisfaction criterion using exactly one
of four outcomes:

| Outcome | Meaning and next action |
|---|---|
| `addresses` | Valid evidence satisfies the criterion; it may proceed to claim acceptance. |
| `contradicts` | Evidence undermines a manuscript claim; surface it immediately and request an author decision before semi-automatic drafting continues. The halt deliverable is an `escalation.md` (convention: `examples/toy-contradicts-au-vs-cu/`). |
| `inconclusive` | Evidence cannot decide the criterion; propose a bounded next step or an honest limitation. |
| `needs-follow-up` | A specific missing calculation, analysis, or validation blocks acceptance; create a follow-up task. |

In autonomous mode, a contradiction is recorded and carried prominently into the draft
rather than hidden or spun. Interim stage synthesis may summarize open outcomes, but
final response drafting waits until every comment is addressed, explicitly limited,
waived, or resolved by an author decision.

## Phase 5 — Response semantics

For each comment, the draft package must include:

1. the verbatim comment and stable `R#.C#` ID;
2. what was calculated or reanalyzed, with fingerprint consistency or disclosed delta;
3. the result with units, provenance, validation status, and an interpretation no
   broader than the evidence;
4. the exact manuscript/SI change, supporting table/figure/caption, and revision-log
   entry;
5. an `AUTHOR_INPUT_NEEDED[...]` block for contradictions, strategic ambiguity, or
   optional expensive work.

Use `report` for the near-submission `.docx`, figure/readiness checks, and final package
assembly.

**Approval #2:** the assembled package remains an author draft. Do not finalize the
authors' tone or rebuttal strategy and do not send it. Autonomous mode may finish the
draft package but still sends nothing.

## Where to find what

| Situation | Open |
|---|---|
| Routing and participating skills | `manifest.yaml` |
| Comment categories, action/readiness, directness | `references/comment-taxonomy.md` |
| PDF text extraction, methods-section probe, per-page comment scan | `references/ingestion.md` |
| Fingerprint, triage, and workflow state schemas | `references/response-templates.md` |
| Response letter, cover letter, changelog, author-decision blocks | `references/response-package.md` |
| Durable DAG, approvals, artifacts, gates, claims | `procedures/research-orchestrator/SKILL.md` |
| Calculation lifecycle and cross-engine validation | `procedures/comp-chem-workflow/SKILL.md` |
| Paper/SI method extraction | `procedures/literature-to-calculation/SKILL.md` |
| Report readiness, figure contracts, and `.docx` assembly | `tools/report/SKILL.md` |
| Supporting and contradicting worked paths | `examples/toy-vacancy-pt-vs-au/`, `examples/toy-contradicts-au-vs-cu/` |

## Integrity guardrails

- Method deviations are visible in planning and response text; never silently mix
  incomparable calculations.
- Contradicting evidence receives the same prominence as supporting evidence.
- An idealized or reconstructed model cannot by itself “confirm” an experiment; state
  experiment-model correspondence and limits in the response.
- Exploratory assumptions and inconclusive evidence remain labeled in author-facing
  text, not only internal state.
- Scientific correctness outranks reviewer appeasement. If the evidence requires the
  manuscript claim to change, that is the response.
