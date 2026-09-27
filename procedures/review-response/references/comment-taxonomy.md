# Computational Review Comment Taxonomy

> Load this in Phase 2 before planning calculations. It adapts reviewer-response
> action mapping to AICC's computational workflow. The goal is to answer the
> reviewer question that was actually asked, not merely an adjacent computable
> question.

## Required Triage Record

Each atomic comment should produce a record like this:

```yaml
comment_id: R2.C3
reviewer: Reviewer 2
verbatim_quote: "..."
severity: minor | major | blocking | unclear
category: mechanism | model-validity | scale-statistics | method-challenge | electronic-structure | kinetics-thermodynamics | data-figure-readability | text-only | scope-strategy
route: compute-new | reanalyze | method-challenge | add-figure | text-only | needs-human-decision
action: ACCEPT_ANALYSIS | ACCEPT_FIGURE | CLARIFY_EXISTING | SOFTEN_CLAIM | PARTIAL | DISAGREE | AUTHOR_INPUT_NEEDED | BLOCKING
readiness: ready-to-plan | needs-source-data | needs-author-input | blocked | out-of-scope
directness: exact-question | adjacent-question-risk | insufficiently-specified
target_quantity: "Pt-Pt contact survival probability at experimental composition"
satisfaction_criterion: "persistent contacts absent within stated trajectory/statistical limit"
minimum_evidence: ["MLP QA", "multi-Pt MD statistics", "random-baseline comparison"]
scale_bar: "composition, cell size, trajectory length, number of independent seeds"
dependencies: ["R2.C1"]
risk_notes:
  - "Two-Pt dilute cell cannot bound dimer fraction at experimental composition."
```

## Severity

| Severity | Meaning | Default handling |
|---|---|---|
| `minor` | Presentation, figure readability, missing method wording, or a small clarification | Usually `ACCEPT_FIGURE` or `CLARIFY_EXISTING` |
| `major` | Evidence, model validity, scale, method, interpretation, or mechanism issue that can affect the response | Requires explicit target quantity and satisfaction criterion |
| `blocking` | Missing central evidence, impossible claim, compliance/integrity issue, or contradiction | Do not draft a confident response without author decision |
| `unclear` | The comment is too vague to define a falsifiable computational target | Ask one focused question or mark `needs-human-decision` |

## Categories

| Category | Use when | Typical evidence |
|---|---|---|
| `mechanism` | The reviewer asks why/how a process occurs | reaction/free-energy path, competing pathway, electronic/bonding evidence, control model |
| `model-validity` | The reviewer challenges whether the atomistic model represents the experiment | structure provenance, facet/termination/composition correspondence, sensitivity model |
| `scale-statistics` | The reviewer asks for long-time, concentration, aggregation, diffusion, stability, or sampling evidence | MD statistics, independent seeds, composition/cell-size match, uncertainty |
| `method-challenge` | The reviewer questions functional, U, dispersion, cutoff, force field, MLP, or benchmark choice | method comparison on representative subset |
| `electronic-structure` | Claim concerns charge transfer, oxidation state, band states, DOS, bonding, spin, or work function | paired structure + CDD/Bader/DOS/PDOS/COHP/ELF/spin/work-function |
| `kinetics-thermodynamics` | Claim concerns stability, barrier, free energy, temperature, pressure, or electrochemical potential | Delta E/Delta G, CHE diagram, TS/NEB/frequency, thermochemistry |
| `data-figure-readability` | Reviewer asks for clearer figures, tables, labels, or evidence presentation | figure contract, revised plot/table/caption |
| `text-only` | No computation is needed | hand to author/report text only |
| `scope-strategy` | Requested work is infeasible, out of scope, or strategically risky | `AUTHOR_INPUT_NEEDED`, limitation, or scoped disagreement |

## Action Labels

| Action | Meaning |
|---|---|
| `ACCEPT_ANALYSIS` | New or reprocessed computational analysis will answer the comment. |
| `ACCEPT_FIGURE` | A new/revised figure or table is the main response artifact. |
| `CLARIFY_EXISTING` | Existing evidence is enough but must be presented more clearly. |
| `SOFTEN_CLAIM` | The manuscript claim is broader than the evidence. |
| `PARTIAL` | The response addresses part of the concern and states the remaining limitation. |
| `DISAGREE` | The reviewer premise is not supported; response must be evidence-based and narrow. |
| `AUTHOR_INPUT_NEEDED` | The agent cannot choose a model, scope, or strategy credibly. |
| `BLOCKING` | Any final response would be misleading without new author action. |

## Directness Gate

Before approving a calculation plan, ask:

1. What exact reviewer concern is being answered?
2. What target quantity would satisfy the reviewer if the result is favorable?
3. What result would falsify or weaken the manuscript claim?
4. Does the planned calculation measure that target quantity, or only a related proxy?
5. Is the calculation scale credible for the asked question?

If the answer to 4 is "proxy", set `directness: adjacent-question-risk` and either
revise the plan or state the limitation before execution. If the answer to 5 is no,
do not hide the scale issue inside the report; either enlarge the calculation or mark
the response `PARTIAL`.

## Category-Specific Defaults

### MLP/MD Scale and Statistics

Minimum triage fields:

- target composition and experimental condition;
- number of atoms and target species count;
- trajectory length and equilibration policy;
- number of seeds/windows if statistics are central;
- model QA required: lcurve, parity, force residuals, PCA/coverage, model deviation
  when available;
- observable definition: RDF, contact survival, cluster-size distribution, diffusion,
  coordination, density, or another explicit statistic.

Two-atom dilute cells, short smoke trajectories, or single snapshots can support
workflow validation, but not strong claims about rare clusters or long-time stability.

### Electronic Structure

Do not let a single scalar charge analysis carry a broad mechanism claim. Route claims
like deep-level suppression, orbital hybridization, reducibility, or oxidation state to
paired evidence: structure/projection context plus at least one discriminating
observable such as DOS/PDOS, COHP, ELF, spin density, work function, vibrational shift,
or experiment-anchored proxy.

### Kinetics and Thermodynamics

Adsorption energies answer binding trends, not automatically activity or mechanism.
For catalytic steps, ask whether the reviewer needs a barrier, CHE/free-energy diagram,
limiting potential, or stability under chemical potentials. If only Delta E is feasible,
mark the response `PARTIAL` unless the reviewer asked only for a relative binding trend.

### Figure/Presentation Requests

Use `ACCEPT_FIGURE` only when the revised figure has a figure contract and passes final
layout QA. Do not answer a readability concern by adding a crowded figure.

## Readiness Labels

| Readiness | Meaning |
|---|---|
| `ready-to-plan` | The target quantity, route, and satisfaction criterion are clear. |
| `needs-source-data` | Existing archive/manuscript/SI data may answer it, but files are missing. |
| `needs-author-input` | A scientific or strategic choice cannot be inferred. |
| `blocked` | A credible response cannot proceed without new author action. |
| `out-of-scope` | The request is valid but should be handled as limitation/disagreement, not calculation. |

## Triage QA Checklist

- [ ] Every comment has a stable ID and verbatim quote.
- [ ] Every computational comment has a target quantity and satisfaction criterion.
- [ ] `directness` is `exact-question` or the adjacent-question limitation is explicit.
- [ ] Scale/statistics are recorded when the reviewer asks about rare events, stability,
  concentration, clustering, diffusion, or time.
- [ ] Method deviations from the fingerprint are explicit.
- [ ] Shared structures, references, and calculations are planned once and reused.
- [ ] `AUTHOR_INPUT_NEEDED` appears for real scientific or strategic forks, not routine
  file paths or command choices.
