# Scientific Critic Contract

> Load this when: creating or reviewing a `scientific-critic` task, accepting a
> calculation result as a claim, or deciding whether a report may consume a result.

## Purpose

The critic is a scientific adversarial pass. It does not rerun the workflow or edit
producer artifacts. It checks whether an evidence packet supports the intended claim
and records the result as a critic artifact. It is also the normal way a project loops:
when evidence is incomplete, the critic writes a concrete `follow-up-proposal` instead
of allowing a premature final report.

Schedule `scientific-critic` tasks after a calculation wave has produced validated
parser or analysis evidence. They should not be dependencies of the first engine/HPC
submission task. Before first submission, use plan/model review and structure gates;
after results exist, use this critic contract to decide claim outcomes and follow-up
work.

## Required Inputs

A critic task should receive an evidence packet that includes:

- the accepted method fingerprint or model-observable decision;
- the relevant validated parser result or accepted analysis artifact;
- structure/model validation evidence when geometry matters;
- units, reference states, and provenance for all numeric values;
- known assumptions and limitations.

## Checks

- Does the observable answer the registered objective?
- Does the computed observable match the requested observable, rather than a weaker
  surrogate that should be labeled `inconclusive` or `needs-follow-up`?
- Are structures, charge/spin/oxidation assumptions, and reference states explicit?
- Did the engine parser or checker validate technical convergence?
- Are units and signs consistent with the claim?
- If the objective requires a thermodynamic quantity, are ZPE, thermal, entropy,
  configurational, pressure, pH, potential, reservoir, or other required corrections
  included or explicitly ruled out?
- Are alternative explanations or decisive missing calculations documented?
- Does any evidence contradict the planned manuscript/report claim?

## Outcomes

Use one of these outcome labels:

- `addresses` — evidence supports the registered question within stated limits.
- `contradicts` — evidence undermines the planned claim.
- `inconclusive` — evidence is valid but does not decide the question.
- `needs-follow-up` — a specific missing calculation or validation blocks acceptance.

For `needs-follow-up`, include the smallest concrete next task: target observable,
model/input dependency, suggested engine skill, success criterion, expected cost tier,
and which current claim it would unblock. The orchestrator converts accepted proposals
into new `.research/tasks/*.yaml` nodes.

## Machine-Readable Result Gate

Before a `scientific-claim` is accepted or classified as `addresses`, the critic should
write a gate verdict following `references/gate-contract.md` with `gate: result_gate`.
The verdict should include the intended `claim_outcome`:

```yaml
schema_version: 1
gate: result_gate
status: pass
scope:
  claims: [scientific-claim]
  reviewer_comments: [R1.C1]
claim_outcome: inconclusive
checks:
  - id: parser_validation
    status: pass
    evidence: parser result is validated and units/provenance are present
  - id: observable_matches_question
    status: pass
    evidence: computed observable is valid but weaker than the requested criterion
blocking_issues: []
required_fix: []
```

`status: pass` means the critic completed the gate and the stated outcome is supported.
It does not mean the outcome must be `addresses`. If decisive evidence is missing, the
supported outcome should be `inconclusive` or `needs-follow-up`; it must not be promoted
to `addresses`.

## Write Boundary

`scientific-critic` may write only critic or claim-facing artifacts:

- `critic-report`
- `scientific-claim`
- `claim-assessment`
- `validation-report`
- `follow-up-proposal`
- `contradiction-report`
- `limitation-note`

It must not write engine inputs, job records, raw parser results, structure sets, or
final `.docx` reports.
