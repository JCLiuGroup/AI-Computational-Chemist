# Gate Contract

> Load this when: a task output should decide whether the workflow may move from
> planning to execution, from structure preparation to engine submission, from parser
> result to scientific claim, or from accepted claims to a human-facing report.

## Purpose

A gate is a machine-readable critic verdict. It is not a chat summary and not a
recommendation-only note. Downstream release steps consume the verdict as an artifact
and must stop when the verdict is missing, malformed, or blocking.

Use gates to turn multi-agent or critic work into enforceable workflow state:

```text
subagent/critic judgment -> gate verdict artifact -> hook/check script -> release action allowed or blocked
```

Match each gate to the release action it governs. `plan_gate` and `structure_gate`
belong on the first engine/HPC submission path. `result_gate` and `report_gate` are
post-result gates: they consume validated parser/analysis evidence and accepted or
waived claims, so they must not be prerequisites for the first Slurm submission.

## Gate Types

Use these gate names:

- `plan_gate` — the computational plan and observables cover the registered question.
- `structure_gate` — generated models are technically valid and scientifically
  relevant enough for engine input or HPC submission. It gates engine handoff; it does
  not gate the earlier act of inspecting supplied structures or self-building candidate
  structures.
- `result_gate` — validated parser/analysis evidence supports a claim outcome.
- `report_gate` — the report package does not overstate or consume unsupported claims.
  It gates final report generation, not engine input generation, HPC submission, or
  the act of building an interim stage synthesis after a calculation wave.

Domain-specific checks belong inside `checks`; do not encode a material, catalyst,
adsorbate, supercell label, or case-specific threshold into the protocol itself.

## Minimal YAML

Store gate verdicts as YAML, usually under `work/reviews/`, and register them in
`.research/artifacts.jsonl` as `type: gate-verdict` or the more specific artifact type
such as `model-structure-review`.

```yaml
schema_version: 1
gate: structure_gate
status: pass
scope:
  reviewer_comments: [R1.C1]
  artifacts: [candidate-structures]
checks:
  - id: model_relevance
    status: pass
    evidence: model represents the stated question within recorded assumptions
  - id: finite_size_effects
    status: pass
    metrics:
      min_adsorbate_image_A: 6.0
      target_min_adsorbate_image_A: 5.0
      surface_cell: p(3x3)-equivalent
    evidence: lateral cell, coverage/concentration, and image separation are justified
blocking_issues: []
required_fix: []
```

Allowed `status` values:

- `pass` — the next stage may proceed.
- `request_revision` — revise the upstream artifact before proceeding.
- `block` — do not proceed; the evidence or model is invalid or mismatched.
- `waived` — proceed only because an explicit decision accepted the risk.

`waived` requires a `waiver.decision_id` that resolves to an approved or accepted
decision in `.research/decisions.jsonl`. Waivers are exceptional and must state the
scope and limitation that downstream report text must carry.

## Required Checks by Gate

`plan_gate` checks:

- reviewer or project question has a written satisfaction criterion;
- proposed observable matches the question, including whether the question asks for
  energy, free energy, kinetic barrier, vibration, charge/oxidation state, coverage,
  concentration, dynamics, or stability;
- model and method origin are declared as manuscript/archive-derived, reconstructed,
  designed, or exploratory. Missing original source structures or complete method
  settings is not a block by itself; it requires an explicit designed/reconstructed
  route with assumptions, provenance, cost, and downstream limitations. The
  initial-structure search scope must be bounded to the project root/current working
  directory and user-explicit input paths, not unbounded filesystem scans;
- surrogate models or reduced methods are labeled with their limitations;
- planned calculations and reference states can actually decide the criterion.

`structure_gate` checks:

- `structure-prep` validation and provenance exist;
- slab, cluster, defect, molecule, adsorbate, or supported species matches the
  registered model purpose;
- when original structure files are absent, the structure was built from declared
  sources such as database crystals, manuscript characterization, literature precedent,
  or documented builder assumptions. Absence of an original POSCAR/CIF after bounded
  project-local discovery is not a blocking issue by itself;
- Miller index and termination are checked against available precedent, and any
  departure from commonly used/synthesized/modeled facets is justified or labeled
  exploratory;
- lateral cell size, finite-size effects, coverage/concentration, and periodic image
  distances are adequate or explicitly justified;
- computational economy is reviewed: atom count, lattice lengths, vacuum thickness, and
  candidate count are not inflated beyond the stated finite-size or convergence need.
  For large lateral cells or systems with vacuum in two or three directions, the gate
  may request reducing noninteracting vacuum to about 10 Å unless the target property,
  dipole/charge treatment, convergence evidence, or source method requires more. If a
  reduced threshold is accepted, the gate evidence should cite the explicit
  `audit_structure.py --min-vacuum ...` / `--min-vacuum-adsorbate ...` setting and the
  rationale, rather than treating a default audit failure as pass;
- vacuum, fixed/free regions, termination, charge/spin/oxidation assumptions, and
  surface normal are consistent with the plan;
- top/bottom slab symmetry is treated as a modeling choice, not a universal hard
  requirement. Asymmetric slabs may pass when the top/bottom terminations, polarity or
  dipole risk, fixed layers, vacuum, and downstream electrostatic handling are recorded;
- stoichiometry and charge balance are consistent with the declared chemical
  environment. Effectively fixed-valence/non-redox-active systems stay close to expected
  stoichiometry unless a compensating mechanism or source evidence is recorded, while
  redox-active/variable-valence systems may use environment-dependent
  non-stoichiometry with an explicit oxidation-state rationale;
- adsorption/anchoring motif or structural site represents the scientific question.

Structure-gate checks should include machine-checkable metrics when a numeric threshold
is decisive. For example, if `min_adsorbate_image_A` is lower than
`target_min_adsorbate_image_A`, the check must be `request_revision`, `block`, or
`waived`. A waiver must be top-level `status: waived` with a valid
`waiver.decision_id`; the check cannot be marked `pass`, `warn`, or `not_applicable`.

`result_gate` checks:

- parser or analysis validation passed and units/provenance are present;
- the computed observable is the registered observable;
- reference states, signs, and thermodynamic expressions are explicit;
- free-energy claims include the needed ZPE, thermal, entropy, configurational,
  pressure, pH, potential, or reservoir terms, as relevant to the registered criterion;
- if evidence only supports a weaker observable, the claim outcome is `inconclusive`
  or `needs-follow-up`, not `addresses`.

`report_gate` checks:

- every formal conclusion consumes accepted scientific-claim artifacts;
- each consumed claim has outcome `addresses`, `inconclusive`, or `contradicts`;
- `inconclusive` and `contradicts` outcomes are presented with full prominence;
- unsupported, exploratory, or waived evidence is labeled as such;
- any final-report figure that uses VASP volumetric data (`CHGCAR`, `CHGDIFF`,
  `PARCHG`, `ELFCAR`, spin density, Delta rho / charge-density difference,
  wavefunction/WAVECAR-derived grids, or CHGCAR-like outputs) has accepted figure or
  report-manifest provenance showing `tools/vasp/references/volumetric-visualization.md`;
  charge-density-difference figures also show `tools/vasp/references/electronic-analysis.md`;
- the report builder readiness checklist in `tools/report/references/validation.md`
  is satisfied.

## Hook Scripts

The shipped hooks are deliberately generic:

```text
uv run procedures/research-orchestrator/scripts/validate_gate.py work/reviews/result_gate.yaml --research .research --require-passing
uv run procedures/research-orchestrator/scripts/check_pre_submit.py .research T_ENGINE
uv run procedures/research-orchestrator/scripts/check_pre_accept_claim.py .research CLAIM_ID --outcome addresses
uv run procedures/research-orchestrator/scripts/check_pre_report.py .research T_REPORT
```

They check state, artifact status, gate syntax, gate status, waiver provenance, the
pre-submit `cluster-guide-read` evidence, final-report VASP volumetric figure reference
routing, and generic metric contradictions such as periodic-image distance below the
declared target. They do not know about any specific material system, cell choice, or
reviewer case.

## Default Policy

Gate hooks are deny-by-default at release points:

- missing gate verdict: block the release action;
- missing accepted `cluster-guide-read` evidence on a pre-submit task: block HPC submission;
- malformed gate verdict: block the release action;
- `request_revision` or `block`: block the release action and route back to the
  upstream task that can fix the artifact;
- `waived` without a valid decision: block the release action;
- report generation from non-accepted claims: block.

Do not apply this deny-by-default rule globally to every project task. In particular,
absence of supplied initial coordinates or a missing `structure_gate` should leave the
structure-inspection/model-building task runnable; it blocks only engine/HPC handoff
until candidate structures and an accepted structure verdict exist. Likewise, a missing
`result_gate`, `report_gate`, scientific-critic task, or stage-synthesis packet should
not block the first engine/HPC submission; those checks start after a calculation wave
has produced parser or analysis evidence.

Autonomous mode may replace interactive approval with documented decisions, but it does
not bypass gate verdicts or allow unsupported claims to be promoted silently.
