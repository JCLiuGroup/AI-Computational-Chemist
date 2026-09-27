# Figure Contract

> Load this before designing, plotting, rendering, or assembling a report-ready figure.
> A figure contract turns a figure from a result collage into a traceable visual
> argument. It is useful for reviewer responses, manuscript support, exploratory
> research reports, benchmarks, and method-validation packages.

## Core rule

Every report-ready figure must answer one question before it is drawn:

```text
What scientific point is this figure responsible for showing, and what evidence
inside the figure supports that point?
```

Reviewer comments are one possible driver, but not the only one. Generic reports use
the same contract with research questions, manuscript claims, benchmark cases,
method-validation tasks, or exploratory hypotheses.

## Minimal schema

Use YAML, JSON, or a Markdown table, but keep these fields visible beside the figure
artifact or report manifest.

```yaml
figure_id: Fig. 4
figure_role: main | supplementary | response-only | stage-synthesis | method-validation
scientific_drivers:
  - driver_type: reviewer_comment
    driver_id: R3.C3
    text: "Does Pt form dimers or trimers in liquid Ga?"
  - driver_type: research_question
    driver_id: rq-pt-dispersion
    text: "Are Pt-Pt contacts persistent or transient in the simulated liquid host?"
linked_claims:
  - claim_id: pt-contact-transience
    status: accepted | inconclusive | contradicts | draft
core_conclusion: >
  Pt-Pt contacts decay within the simulated trajectories, supporting transient
  encounters rather than persistent clusters within the simulated window.
figure_archetype: mlp-qa-plus-md-observable
hero_panel: h
panel_map:
  a: DeePMD energy learning curve
  b: DeePMD force learning curve
  c: descriptor PCA over compatible train/val/test DFT frames
  d: energy parity on held-out test data
  e: force parity on held-out test data
  f: representative dispersed and clustered structures
  g: cluster-dispersion energy comparison
  h: Pt-Pt contact survival probability
evidence_hierarchy:
  primary:
    - h
  validation:
    - a
    - b
    - c
    - d
    - e
  contextual:
    - f
    - g
source_data:
  - runs/deepmd/lcurve.out
  - analysis/deepmd_descriptor_pca_dft_all/summary.json
  - analysis/contact_survival.csv
render_backends:
  structures: ovito
  plots: matplotlib
layout_contract:
  target_output: report-docx
  final_width: double-column
  final_width_in: 7.2
  expected_panels: 8
  legend_strategy: shared-legend
  colorbar_strategy: outside-panel
  contrast_policy:
    plot_background: white
    dark_background_allowed_for: image-or-structure-plate-only
    min_text_contrast_ratio: 4.5
    annotation_text: auto-black-or-white-from-background
  text_policy:
    min_font_pt: 6
    default_font_pt: 7
    panel_label_pt: 8
    max_xtick_rotation_deg: 45
  crowding_risks:
    - Several validation panels repeat train/validation/test labels.
    - Structure labels may crowd the Pt-Pt contact panel.
aesthetic_contract:
  page_archetype: validation-strip
  visual_hierarchy:
    primary:
      - h
    validation:
      - a
      - b
      - c
      - d
      - e
    context:
      - f
      - g
  palette_role_map:
    primary_observable: aicc-blue
    validation: aicc-teal
    reference_or_baseline: neutral-gray
    limitation_or_warning: muted-red
  legend_policy: shared
  panel_size_policy: hero-larger-than-validation
  background_policy: white-plots-dark-plates-only
caption_requirements:
  - define each panel
  - state units and sign conventions
  - state method/provenance in reader-facing form
  - label inconclusive or limited panels explicitly
risk_notes:
  - Simulation length and composition may be smaller than the target experiment.
  - A sign-mixed energy comparison must be described as inconclusive.
```

## Driver types

Use `scientific_drivers` to make the contract work outside peer review:

| `driver_type` | Use when |
|---|---|
| `reviewer_comment` | The figure answers a specific reviewer comment. Keep `driver_id` stable, e.g. `R2.C4`. |
| `research_question` | The figure answers the project's own scientific question. |
| `manuscript_claim` | The figure supports, limits, or revises a manuscript statement. |
| `benchmark_case` | The figure documents a benchmark task or comparison arm. |
| `method_validation` | The figure validates a method, model, dataset, or workflow. |
| `exploratory_analysis` | The figure is interim evidence used to decide what to compute next. |

`linked_reviewer_comments` may be used as a shorthand in review-response packages, but
do not make it required in generic reports. The required field is the broader
`scientific_drivers` list.

## AICC figure archetypes

Pick the closest archetype before choosing panel sizes and order. These are starting
points, not a closed taxonomy. For mixed figures, select one hero panel; validation
panels should support the hero panel rather than compete with it.

| Archetype | Typical panels | Primary use |
|---|---|---|
| `structure-model` | clean structure render, top/side views, labeled active site, cell/coverage annotation | Establish what atomistic model was actually computed before any property is interpreted. |
| `model-plus-energy` | structure render + relative energy / adsorption / binding / formation-energy table or plot | Show what model was computed and the energy comparison behind a claim. |
| `thermochemistry-free-energy` | reaction/adsorption/free-energy diagram, reference-state table, correction breakdown | Report Delta E/Delta G, ZPE/entropy/chemical-potential corrections, or gas/reservoir thermodynamics. |
| `surface-stability-phase-diagram` | surface structures + surface energy / Pourbaix / chemical-potential / Wulff or coverage diagram | Support phase, termination, defect, coverage, or stability claims under conditions. |
| `electronic-structure-evidence` | structure + Bader/charge-density difference + DOS/PDOS/work function/ELF/spin density | Support charge transfer, bonding, band, reducibility, spin, or oxidation-state arguments. |
| `bonding-orbital-analysis` | structure with selected bonds + COHP/COOP/ICOHP, orbital-projected DOS, bond-order or overlap metrics | Support local bonding, antibonding, ligand-field, or adsorbate-surface interaction claims. |
| `reaction-pathway` | key structures + reaction/free-energy profile + TS/vibration/IRC/NEB validation | Support mechanism and kinetic/thermodynamic pathway claims. |
| `electrocatalysis-descriptor` | CHE step diagram, limiting-potential/overpotential bar, volcano/descriptors, active-site structure | Support OER/ORR/HER/CO2RR/NRR-style electrochemical activity claims. |
| `phonon-vibration-stability` | phonon dispersion/DOS, imaginary-mode structure, vibrational frequencies, thermodynamic properties | Support dynamic stability, vibrational assignment, ZPE, entropy, or phonon-derived thermodynamics. |
| `md-observable` | trajectory snapshot + RDF/MSD/VACF/VDOS/density/contact survival/diffusion/time-series | Support finite-temperature, liquid, diffusion, transport, aggregation, or equilibration claims. |
| `mlp-qa-plus-md-observable` | lcurve/parity/PCA/model-deviation + MD observable + representative structures | Show an MLP model is credible enough for the MD observable being reported. |
| `dataset-coverage-or-embedding` | PCA/t-SNE/UMAP, split/source labels, coverage gaps, outlier structures | Diagnose whether training/validation/test or active-learning data cover the target chemistry. |
| `benchmark-validation` | parity/residual/error histograms, convergence tests, ablation comparison, method-vs-reference table | Validate a method, parser, workflow, model, or benchmark arm against a reference. |
| `screening-summary` | workflow schematic + ranked metric + representative hits/failures + filter counts | Summarize high-throughput, candidate-selection, or exploratory screening results. |
| `spectroscopy-characterization` | simulated spectrum + experiment/target comparison + model assignment | Support XRD, IR/Raman, NMR, XAS/XPS, UV-vis, STM, or other observable assignment. |
| `workflow-or-response-summary` | question/claim -> calculation route -> evidence artifact -> conclusion/status | Summarize a reviewer response, project status, benchmark case, or multi-stage workflow. |
| `stage-synthesis` | status table + decisive plots + open follow-up map | Help decide the next calculation wave, not final manuscript claims. |

Common pairings:

- Charge-density-difference or Bader panels often need DOS/PDOS or another orthogonal
  observable before supporting a deep electronic-structure claim.
- MLP-driven MD figures should pair the scientific MD observable with the MLP QA needed
  to trust it: learning curve, held-out parity, force residuals, descriptor PCA, and/or
  model deviation.
- Reaction-pathway and electrocatalysis figures should show both the energy/free-energy
  profile and the structures defining the decisive intermediates or transition states.
  The profile uses thick horizontal plateaus for each intermediate/TS energy and thin
  solid or dashed connectors only as sequence guides. The contract should map every
  reported state name to its source structure image or to a recorded reason for
  omitting that structure from the main figure.
- Screening figures should include representative failures or limitations when those
  determine the safe interpretation.

## Contract checklist

- [ ] The core conclusion is one sentence and does not exceed the evidence.
- [ ] Each panel has a named evidence role; no panel is decorative.
- [ ] The hero panel carries the decisive observation.
- [ ] The layout contract names final width, panel hierarchy, legend/colorbar strategy,
  font-size floor, contrast policy, and crowding risks before plotting.
- [ ] The aesthetic contract names page archetype, visual hierarchy, palette role map,
  legend policy, and background policy before plotting. Use
  `computational-chemistry-figure-style.md` for AICC defaults.
- [ ] Validation panels are present when the claim depends on model quality
  (for example, MLP QA before DPMD observables).
- [ ] Every numeric panel has units, reference state, and sign convention where needed.
- [ ] Structure panels use accepted/final structures and record the source path.
- [ ] Reaction-pathway and electrocatalysis profile panels use thick horizontal
  plateaus for intermediate/TS energies; connectors are thin solid/dashed sequence
  guides, not smooth fitted curves.
- [ ] Each reported reaction state or transition state is paired with a corresponding
  final/accepted structure render near the profile, or the contract records why it is
  moved to SI or omitted.
- [ ] Electronic-structure panels are paired with the model/projection they describe.
- [ ] Limitations or inconclusive panels are labeled in the caption, not only in notes.
- [ ] Text, tick labels, legends, colorbars, structure labels, and panel labels are
  checked against `figure-layout-qa.md` at final size; white-on-white or other
  low-contrast text is fixed before report assembly.
- [ ] The figure does not read like an equal-sized dashboard when one panel carries the
  conclusion; hero/validation/context roles are visible in the composition.
- [ ] Source data and scripts are preserved beside the report manifest or artifact log.
