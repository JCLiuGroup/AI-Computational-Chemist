# Review-Response State Templates

> Load this when: creating the method fingerprint, comment triage, or the optional
> human-readable review scoreboard. For letter, SI, changelog, and
> `AUTHOR_INPUT_NEEDED` drafting, load `response-package.md`.

Structured state belongs in `.research/` through `research-orchestrator`; the Markdown
files below are evidence summaries, not a second source of truth.

## `method-fingerprint.md`

```markdown
# Method fingerprint
- origin: manuscript-derived | source-paper-derived | related-literature-derived | designed | mixed
- reproduction_mode: reproduction | exploration
- source_evidence: <sections, input archive, or evidence-map artifact IDs>

## Experiment correspondence
| choice | evidence | assumption/limitation |
|---|---|---|

## Verified settings
| setting | value | provenance |
|---|---|---|

## Assumed settings
| setting | chosen value | rationale | approval |
|---|---|---|---|

## Comparison contract
- settings that must match: <functional, cutoff/basis, k-density, U, dispersion, corrections>
- energy/free-energy convention: <E, E+ZPE, H, G, CHE, ...>

## Unresolved
- <item and dependent comment IDs, or none>
```

Use the origin and reproduction semantics from
`procedures/literature-to-calculation/references/research-artifacts.md`. A method
deviation is recorded and disclosed; a comment explicitly challenging the method may
require the deviation as the comparison itself.

## `triage.md`

Create one section per atomic comment using the fields and enums in
`comment-taxonomy.md`:

```markdown
## R1.C2
> "<verbatim reviewer comment>"
- route: compute-new | reanalyze | method-challenge | add-figure | text-only | needs-human-decision
- severity: minor | major | blocking | unclear
- category: <comment-taxonomy category>
- action: <comment-taxonomy action>
- readiness: ready-to-plan | needs-source-data | needs-author-input | blocked | out-of-scope
- directness: exact-question | adjacent-question-risk | insufficiently-specified
- target_quantity: <observable>
- satisfaction_criterion: <falsifiable threshold, with units where possible>
- minimum_evidence: [...]
- scale_bar: <composition/cell/time/seeds scope or not-applicable>
- route_skills: [...]
- method_delta: <none or disclosed difference>
- reuses: [...]
- cost: <tier or estimate>
- approved: no
```

Run the taxonomy's directness gate before approval. An adjacent proxy remains visible
as a limitation or `PARTIAL`; it is not silently promoted to a direct answer.

## `response-workflow.md`

This optional scoreboard is derived from `.research/`:

```markdown
# Response workflow
- manuscript: <path or identifier>
- fingerprint: <artifact ID or path>

| comment | status | outcome | evidence | next action |
|---|---|---|---|---|
| R1.C2 | running | pending | <task/artifact IDs> | <next step> |
```

Use orchestrator task statuses. The four internal claim outcomes are `addresses`,
`contradicts`, `inconclusive`, and `needs-follow-up`. In semi-automatic mode,
`contradicts` pauses for author review; in explicitly requested autonomous mode it is
recorded prominently and carried into the draft. `needs-follow-up` is not reportable
until resolved, waived, or converted to an accepted limitation.
