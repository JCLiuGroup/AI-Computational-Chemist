# AICC Figure Archetype Atlas

> Load this after `figure-contract.md` and before plotting. It is a routing
> table: choose the closest archetype, then use `computational-chemistry-figure-style.md`
> and `figure-layout-qa.md` for styling and QA. The goal is to stop report figures
> from becoming equal-sized result collages.

## How to Use

1. Write the figure's one-sentence responsibility.
2. Select the archetype whose primary evidence matches that responsibility.
3. Assign a hero panel and panel roles before writing plotting code.
4. Drop panels that do not support the responsibility.
5. Run `save_aicc_figure()` or equivalent final-size QA before report assembly.

## Routing Table

| Scientific responsibility | Figure archetype | Hero panel | Required support panels | Common failure |
|---|---|---|---|---|
| Show what model was computed | `structure-model` | relaxed top/side model | active site labels, cell/coverage note | property plot appears before the reader knows the model |
| Compare relative stability or binding | `model-plus-energy` | relative energy / adsorption energy plot | representative structures, reference-state note | bare total energies or long labels on x axis |
| Support charge transfer, oxidation state, band, or bonding claim | `electronic-structure-evidence` | DOS/PDOS, CDD, Bader, ELF, spin, or work-function panel matching the claim | structure with projected/labelled atoms; orthogonal observable when needed | charge-density difference alone used for a deep-state claim |
| Support a reaction or catalytic pathway | `reaction-pathway` | Delta E/Delta G profile or barrier comparison | key intermediate/TS structures, TS/NEB/frequency validation | state names differ across plot/table/caption |
| Support electrocatalytic activity | `electrocatalysis-descriptor` | CHE step diagram, limiting potential, or overpotential bar | active-site structure, descriptor/volcano where relevant | adsorption energy reported without potential-limiting step |
| Support finite-temperature/liquid/diffusion/aggregation conclusion | `md-observable` | RDF/MSD/contact survival/diffusion/time-series | trajectory snapshot, equilibration/statistics note | representative snapshot overinterpreted as statistics |
| Support MLP-driven MD | `mlp-qa-plus-md-observable` | MD observable that answers the scientific question | lcurve, parity, PCA/coverage, force errors, structures | QA panels dominate while the MD answer is visually buried |
| Diagnose dataset coverage | `dataset-coverage-or-embedding` | PCA/UMAP/t-SNE coverage plot | split/source/outlier labels, target-chemistry markers | train/val/test shown without target domain |
| Validate method/workflow/parser | `benchmark-validation` | parity/residual/convergence benchmark | baseline/reference, split/seed/error definition | metric shown without uncertainty or split definition |
| Summarize screening | `screening-summary` | ranked metric, volcano, or descriptor map | representative hits and failures, filter counts | only winners shown, limitations hidden |
| Summarize reviewer response | `workflow-or-response-summary` | question-to-evidence-to-answer flow | comment ID, route, evidence artifacts, outcome | response figure repeats prose but carries no evidence |

## Panel Responsibility Patterns

### MLP-QA + MD Observable

Recommended order:

1. `a,b`: energy and force lcurve.
2. `c,d`: held-out energy and force parity or residuals.
3. `e`: descriptor PCA or model-deviation/coverage.
4. `f`: representative structures or trajectory snapshots.
5. `g`: relative energy/composition/control comparison when it affects interpretation.
6. `h`: MD observable that directly answers the question.

The MD observable is the hero. If the figure answers clustering, diffusion, stability,
aggregation, or solvation, the observable panel must be larger or visually stronger
than the training diagnostics.

### Electronic-Structure Evidence

Recommended order:

1. `a`: element-colored structure with the relevant atoms labelled.
2. `b`: property-colored structure or field map.
3. `c`: DOS/PDOS, COHP, work function, ELF, spin density, or another orthogonal
   observable selected by the claim.
4. `d`: relative energy or control model only if it is needed for the conclusion.

Use paired evidence. Bader charge and charge-density difference generally show charge
redistribution; they do not by themselves prove deep-level defect suppression, orbital
hybridization, or oxidation-state assignment unless the claim is deliberately limited.

### Reaction Pathway

Recommended order:

1. Hero: profile with reference state, units, and sign convention.
2. Structures: placed near or below the state labels they define.
3. Validation: TS imaginary frequency, NEB image convergence, IRC, or vibration check.
4. Controls: alternate pathway or surface only when it changes the conclusion.

Keep state names identical across figure, table, caption, and report text.

### Response Summary

Use only when it helps the reader navigate a response package:

```text
Reviewer question -> computed route -> evidence artifact -> outcome/limitation
```

The figure must still point to real evidence artifacts. A decorative flowchart without
numbers, structures, or artifact IDs belongs in the text, not as a scientific figure.

## Figure Contract Add-On

When an archetype is chosen, add this block to the figure contract:

```yaml
archetype_route:
  selected: mlp-qa-plus-md-observable
  rejected_alternatives:
    - md-observable
  reason: >
    The MD observable answers the reviewer question, but the result depends on MLP
    quality, so lcurve/parity/PCA validation must travel with the observable.
  hero_panel_must_answer: "Are Pt-Pt contacts persistent or transient?"
  panels_to_drop_if_crowded:
    - duplicate validation legend
    - secondary training metric not used in interpretation
```

## QA Before Plotting

- [ ] The chosen archetype matches the figure responsibility.
- [ ] The hero panel answers the claim in one glance.
- [ ] Validation panels are quieter than the hero panel.
- [ ] Context panels explain model/projection/source identity.
- [ ] No panel is included only because it is easy to plot.
- [ ] Long method/reference notes are routed to caption or note band, not data axes.
- [ ] Heatmap/field/raster legends are outside the data panel unless waived.
