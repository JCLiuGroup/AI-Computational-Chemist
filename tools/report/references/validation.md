# Report readiness checklist

> Load this when: deciding whether a drafted report `.docx` is ready to hand to the authors.

"Near-submission" means a human can read it without decoding raw output and edit it into the manuscript. Gate the document against every item below — these are the recurring failures real reviewers complained about.

## Workflow gate
- [ ] The report task consumes only accepted `scientific-claim` artifacts for formal conclusions.
- [ ] Every consumed claim has a visible outcome: `addresses`, `inconclusive`, or `contradicts`.
- [ ] A machine-readable `report_gate` verdict passed, or a waiver with explicit `.research/decisions.jsonl` provenance is recorded.
- [ ] Claims supported only by weaker evidence than the reviewer/project criterion are labeled `inconclusive` or limitation, not written as resolved.
- [ ] The report mode is explicit: `stage-synthesis` or `final`.
- [ ] For `stage-synthesis`, validated-but-not-accepted evidence is labeled interim and
  all open `needs-follow-up` proposals are listed with task IDs or decision blockers.
- [ ] For `final`, no unresolved `needs-follow-up` proposal blocks a formal conclusion;
  each remaining gap has accepted evidence, a human waiver, or a visible limitation.

## Pre-report soft gate: missing low-cost analyses

Run this before writing the final report manifest. It is a soft gate: it should trigger an analysis or a visible waiver/limitation, not automatic scope creep.

- [ ] **High-temperature or gas-reservoir claim checked for free-energy corrections.** If the result is interpreted at non-ambient/high temperature, variable pressure, catalytic operating conditions, surface stability, oxygen/CO/H2/H2O chemical potentials, defect formation, Wulff/phase diagrams, or reaction/adsorption free energies, decide whether `G(T,p)` is required rather than electronic `E`. For VASP-based work, use `tools/vaspkit/references/thermochemistry.md` for VASPKIT 501/502 where applicable, with the science and equations in `knowledge/thermochemistry-and-free-energy.md` and `knowledge/surface-thermodynamics.md`.
- [ ] **Free-energy omission is explicit.** If only electronic energies are reported for a case where thermal/entropy/chemical-potential terms could matter, the report states the omission and why it is acceptable for the claim. Do not call such a result a Gibbs/free energy.
- [ ] **Electronic-structure mechanism checked for DOS/PDOS or charge evidence.** If the text claims orbital hybridization, d-band shifts, band-gap/band-edge changes, charge transfer, oxidation state, reducibility, work function, or conductive/semiconductive behavior, decide whether DOS/PDOS, Bader/charge-density difference, work function, ELF, or related analysis is needed. Use `tools/vasp/references/dos-band.md`, `tools/vaspkit/references/dos-band.md`, and `knowledge/electronic-structure.md` as appropriate.
- [ ] **Easy post-processing is not silently skipped.** If the required evidence is a low-cost post-processing step from existing validated VASP outputs (VASPKIT DOS/PDOS, gas thermochemistry from completed frequencies, planar average/work function, Bader summary, structure render), do it before report assembly unless there is a recorded reason not to.
- [ ] **Soft-gate decision recorded.** The workflow notes or report provenance record contains one line per trigger: `needed/done`, `not applicable`, or `waived with reason`.

## Energies
- [ ] **No bare total energies.** Every reported energy is a *relative* quantity — adsorption energy, binding energy, reaction energy, barrier, ΔG. (The builder flags table cells > 50 eV in magnitude; resolve each.)
- [ ] Each energy states its **reference state** (gas-phase molecule, clean slab, bulk metal, the appropriate μ reservoir) in the table caption or text.
- [ ] Units on every number; sign convention stated where E_ads/E_bind could be read either way.

## Data shown on the structure
- [ ] Every report-ready figure has a figure contract or equivalent manifest section
  naming its scientific driver, core conclusion, panel map, evidence hierarchy, source
  data, layout contract, aesthetic contract, and risk notes. Reviewer-comment links are
  required only for review-response packages; generic research reports use research
  questions, manuscript claims, benchmark cases, method-validation tasks, or
  exploratory-analysis IDs.
- [ ] Every report-ready figure has an archetype route from
  `references/figure-archetype-atlas.md`: selected archetype, hero panel, support
  panels, and panels to drop if crowded.
- [ ] Every charge / oxidation-state / bond claim is **shown on a structure figure** (atoms colored by the quantity + colorbar; decisive atoms labeled), not presented only as a table cell.
- [ ] Electronic-structure arguments (charge transfer, reducibility, band character) are backed by the **paired figure** (structure + charge, and DOS/PDOS where the argument needs it) — not asserted from a number alone.
- [ ] Every **adsorption / binding energy reported in a table** (e.g. each H2O or CO adsorption configuration) has an **accompanying structure figure** of that adsorption geometry (ball-and-stick, side + top), so the reader sees the binding site and orientation behind each number — not a bare energy.
- [ ] Every **DOS / PDOS figure is paired with a small structure figure** of the same model placed beside it (which atoms are being projected), so the projection is unambiguous.

## Model figures
- [ ] For VASP relaxation products, report model figures use the relaxed final
  `CONTCAR` as the source structure, not the initial `POSCAR`. If a `POSCAR` path is
  used, provenance states that it was copied from the final `CONTCAR` or explains why
  no `CONTCAR`/final structure exists.
- [ ] **Orthographic top + side views** for every model — no perspective projection. Always render *both* (a single view hides the site), and assemble them into one two-panel figure labeled `(a)` and `(b)` rather than two disconnected figures, unless the target journal/template forces a different layout.
- [ ] The two-panel model figure is laid out left-to-right: `(a)` top view on the
  left and `(b)` side view on the right.
- [ ] **Ball-and-stick by default** (`ovito_render.py --ball-stick`), not filled spheres — bonds make it clear which atom is which and how they coordinate. Reserve CPK/filled spheres for space-filling/coverage arguments.
- [ ] Cell/periodic images sensible; the adsorbate/site of interest is visible and unambiguous in at least one view. For a *single-atom* model, render the actual (super)cell so the reader sees the SA is isolated, not a dense array.
- [ ] Color scheme is legible (distinct elements; charge colorbar has a stated range and units). For a **charge** map use the diverging **red-white-blue** scale (red = +, white = 0, blue = −) on a symmetric range, and **label the decisive atoms with their value on the image** (`--label-elems Fe,O`) so the reader sees which atom is which and its charge — not just a gradient.
- [ ] Bader-charge or other property-colored structure figures include the same-view plain element-colored companion image in the same two-panel figure, labeled `(a)` and `(b)`, so recoloring by charge does not hide element identity. Prefer `(a)` plain element colors and `(b)` property-colored map unless the caption clearly states the opposite order.
- [ ] Side-view panels are zoomed or cropped to the slab/adsorbate/active-site region
  so empty vacuum does not dominate the image. Crop out vacuum for ordinary model
  figures; show the full vacuum/cell height only when the vacuum, dipole,
  work-function plateau, or periodic-boundary geometry is itself the point of the
  figure.

## Figure layout and readability

- [ ] Each report-ready figure has been checked at its final inserted width using
  `references/figure-layout-qa.md`.
- [ ] Body, axis, tick, legend, and colorbar text remain readable at final size; text is
  not shrunk below the figure contract's font-size floor.
- [ ] Tick labels, axis labels, legends, colorbars, panel labels, and annotations do not
  overlap each other or cover plotted evidence.
- [ ] Text has adequate foreground/background contrast: no white text on white or pale
  backgrounds, no dark text on dark plates, and no annotation color chosen without
  considering the cell/bar/structure background.
- [ ] Formula definitions, reference-state notes, method notes, reviewer-comment context,
  and other long explanatory text boxes are not placed inside data axes. They belong in
  the caption, a figure-level note band, or a dedicated note panel.
- [ ] Heatmap, charge-density, contour, and other raster/data-image panels do not have
  legends placed over the image unless a recorded waiver states the region is empty and
  the legend has an opaque high-contrast box.
- [ ] Repeated legends are replaced by direct labels, a shared legend, or a legend-only
  panel when they crowd data panels.
- [ ] The figure's aesthetic contract is visible in the result: one hero panel or clear
  primary axis carries the conclusion, validation/context panels are quieter, and the
  palette follows semantic roles rather than arbitrary category colors.
- [ ] Long category labels are shortened, wrapped, angled no more than 45 degrees, moved
  to a legend/table, or the figure is widened.
- [ ] For Matplotlib plots, `scripts/aicc_figure_style.py` or an equivalent final-size
  check has been run when practical. Warnings for overlap, low contrast, sampled raster
  contrast, long text inside axes, or in-raster legends block a final report until fixed
  or waived with a visible reason.

## Completeness & rigor
- [ ] **The actual system of interest is in the comparison, not only ablation/sub-models.** If the real catalyst/material is a multi-component system (e.g. the full promoter-loaded site), every comparison table reports *that* system's value too — not just the simplified one-variable-at-a-time sub-models. Readers need the real number, not only the trend.
- [ ] **Derived reference potentials show their derivation.** Any reference chemical potential obtained from an equilibrium (e.g. μ_O from `CO + ½O₂ ⇌ CO₂` or `H₂ + ½O₂ ⇌ H₂O`, μ_H from H₂) is reported with its **defining reaction + formula + the numeric substitution**, not just the final eV value — so a reader can check it.
- [ ] **Unexpected scatter was re-verified, not reported at face value.** A large spread across values that should be similar (e.g. several adsorption configurations of the same molecule differing by ≳1 eV) is a flag to re-check the sites/convergence *before* the number ships, with the check noted.

## Captions & provenance
- [ ] Every figure and table has a complete caption: what it shows, method (one line confirming the manuscript's settings), units, convergence/provenance.
- [ ] Figures are real renders (`tools/ovito`, Tachyon) — not ASE previews — at print resolution (`knowledge/scientific-visualization.md`).
- [ ] Figure artifacts keep rendering provenance: source structure/data path, render script/command, software/version, view/projection, panel assembly command, crop/zoom choice, color range or isovalue, and a nonblank image check. These details can live in sidecar metadata or workflow notes; the caption carries the reader-facing subset.
- [ ] VASP volumetric figures route through the proper visualization reference. If a
  final-report figure uses `CHGCAR`, `CHGDIFF`, `PARCHG`, `ELFCAR`, spin density,
  Delta rho / charge-density difference, wavefunction/WAVECAR-derived grids, or other
  CHGCAR-like VASP data, its accepted `figure` artifact or consumed
  `report-manifest` records `tools/vasp/references/volumetric-visualization.md`.
  Charge-density-difference figures also record
  `tools/vasp/references/electronic-analysis.md`. If VASPKIT was used, record its
  task/log/menu provenance; VASPKIT is not required for every volumetric figure.
- [ ] Multi-panel captions identify each panel explicitly, e.g. `(a) orthographic top view, (b) zoomed side view` or `(a) element-colored structure, (b) Bader-charge-colored structure`.
- [ ] **Defect/vacancy formation energies name the exact site removed or added** (e.g. *which* O was pulled for E_vac(O) — bridging vs in-plane vs sub-surface), not just "E_vac(O)". Inequivalent sites give different energies, so identify the site (mark it on a structure figure) and, where it matters, report the range over symmetry-distinct sites rather than a single unlabeled value.
- [ ] **The report ends with a calculation-directory table** mapping every Figure/Table to the directory its data came from (Figure 1 → `calc/...`, Table 2 → `calc/...`), so a human can find the raw inputs/outputs to check and archive (see `references/running.md`).
- [ ] The final package checklist has been run for `.docx` integrity, figure/caption
  counts, unresolved placeholders, and handoff notes.

## Integrity (inherits the workflow rules)
- [ ] `contradicts`/`inconclusive` outcomes are stated with the same prominence as supportive ones; nothing spun.
- [ ] No sentence claims more than a validated calculation backs; exploratory/assumption-laden results are labeled in the text.
- [ ] The document is a **draft for the authors** — tone not finalized, nothing sent.
