# Computational Chemistry Figure Style

> Load this with `figure-contract.md` before drawing AICC report figures. This
> reference turns the scientific archetype into a default page composition,
> palette role map, and plot styling choice. It is adapted from publication-figure
> practice but tuned for computational chemistry evidence.
> Use `figure-archetype-atlas.md` first when the figure responsibility or panel roles
> are not already fixed.

## Core rule

Do not make every panel equal. Assign one visual job to the figure:

- a **hero panel** carries the decisive scientific observation;
- **validation panels** show why the calculation/model can be trusted;
- **context panels** show the model, structure, or workflow needed to read the hero;
- legends and colorbars are shared whenever they repeat.

Use alignment, whitespace, and consistent colors to organize the page. Avoid decorative
boxes and unrelated saturated colors.

## Aesthetic contract

Add this block to the figure contract when a report-ready figure is planned:

```yaml
aesthetic_contract:
  page_archetype: validation-strip | structure-plus-property | pathway-hero | screening-grid | response-summary
  hero_panel: h
  visual_hierarchy:
    primary: [h]
    validation: [a, b, c, d]
    context: [e, f]
  palette_role_map:
    primary_observable: aicc-blue
    validation: aicc-teal
    reference_or_baseline: neutral-gray
    limitation_or_warning: muted-red
  legend_policy: direct-label | shared | legend-panel | none
  panel_size_policy: hero-larger-than-validation
  background_policy: white-plots-dark-plates-only
```

## Page archetypes

| AICC archetype | Page archetype | Default composition |
|---|---|---|
| `mlp-qa-plus-md-observable` | `validation-strip` | QA panels in a compact strip; MD observable as the largest/rightmost or bottom hero panel; structures placed next to the MD observable. |
| `dataset-coverage-or-embedding` | `validation-strip` | PCA/UMAP/t-SNE as hero; split/source/outlier summaries as smaller side panels. |
| `electronic-structure-evidence` | `structure-plus-property` | Model structure first, then charge/Bader/ELF/spin map, then DOS/PDOS/work-function; structure and projected atoms stay near the property plot. |
| `model-plus-energy` | `structure-plus-property` | Relative-energy bar/point plot as hero; representative structures in a smaller row/column. |
| `reaction-pathway` | `pathway-hero` | Energy/free-energy profile as hero; decisive intermediates/TS images aligned near their states; TS/NEB/frequency validation smaller. |
| `electrocatalysis-descriptor` | `pathway-hero` | CHE step diagram or limiting-potential bar as hero; active-site structure and descriptor/volcano panels support it. |
| `screening-summary` | `screening-grid` | Ranked metric as hero; representative hits, failures, and filter counts as quieter panels. |
| `workflow-or-response-summary` | `response-summary` | Question/claim -> calculation route -> evidence artifact -> conclusion/status, with minimal quantitative panels. |

## Palette roles

Use colors by role, not by whatever category appears first in a script.

| Role | Default color | Use for |
|---|---|---|
| `primary_observable` | `#0F4D92` | MD observable, final energy comparison, main profile, or the agent's decisive answer. |
| `validation` | `#42949E` | lcurve, parity, PCA, convergence, residuals, model-deviation checks. |
| `reference_or_baseline` | `#767676` | DFT reference, zero lines, experimental/reference baselines, unchanged state. |
| `secondary_context` | `#9A4D8E` | secondary composition, supporting observable, alternate model. |
| `success_or_pass` | `#2E9E44` | pass marks, improvement arrows, stable/accepted status. |
| `limitation_or_warning` | `#B64342` | failed/inconclusive branch, outlier, warning annotation, contradiction. |
| `neutral_fill` | `#CFCECE` | low-priority bars, inactive categories, background grouping. |

Signed fields use diverging maps: red/white/blue for charge/spin/Delta rho, and
blue-white-red or red-white-blue with the sign convention stated in the caption.

## Default layouts

### MLP-QA plus MD observable

Use a 2-row composition:

- row 1: lcurve energy, lcurve force, parity energy, parity force;
- row 2: PCA or model-deviation, representative structures, energy comparison or
  concentration comparison, MD observable hero.

Rules:

- The MD observable must be the largest panel when it is the scientific answer.
- lcurve/parity/PCA panels share colors for train/validation/test.
- Do not repeat the same train/validation/test legend in every QA panel.
- Show the model limitation in a muted red annotation if coverage, statistics, or
  trajectory length limits the claim.

### Electronic-structure evidence

Use a structure-plus-property composition:

- small structure/context panel on the left;
- property map or Bader/charge panel next;
- DOS/PDOS/work-function/ELF/spin panel as the mechanistic support.

Rules:

- Projection labels in DOS/PDOS must correspond to atoms marked on the structure.
- Charge-density difference alone should not be styled as a decisive deep-state claim;
  pair it with DOS/PDOS or another orthogonal observable when the conclusion needs it.
- Use a shared colorbar when charge/spin maps are comparable.

### Model plus energy

Use the relative-energy panel as the visual anchor:

- x labels should be short model names; long model details go in the caption or table;
- sort bars by the comparison logic, not alphabetically;
- annotate values with contrast-aware text or outside labels;
- keep structures aligned with the same order as bars where possible.

### Reaction pathway

Use the energy/free-energy profile as the hero:

- draw each intermediate or transition-state energy as a thick horizontal plateau,
  not as a smooth curve or point-only line;
- connect neighboring states with thin solid or dashed guide lines. These connectors
  show reaction order only; they must not imply a continuous dynamical trajectory or
  an optimized minimum-energy path unless NEB/IRC data support that claim;
- align structures near the states they define;
- keep state names identical across profile, table, caption, and structure labels;
- mark TS validation or imaginary frequency as a smaller validation panel;
- use a dashed zero/reference line and state the reference.

For catalytic reaction-pathway figures, place the structure image for every reported
intermediate and transition state directly below, above, or beside its energy plateau
whenever space allows. Structure panels should follow the report structure rules:
relaxed/final structures, orthographic top+side views where geometry matters,
ball-and-stick by default, cropped/zoomed to the active site rather than dominated by
vacuum, and labels only for decisive atoms/bonds/sites. If the path has too many
states for a readable main figure, show the decisive states in the main panel and move
the full state-by-state structure strip to the SI or a stage-synthesis detail figure.

### Screening summary

Use a ranked metric plus examples:

- ranked metric or volcano/descriptor plot is the hero;
- show at least one representative hit and one representative failure/limitation when
  the safe interpretation depends on screening filters;
- use neutral colors for filtered-out entries and one accent for the selected set.

## Legend and label economy

- Use direct labels for a few stable curves or regions.
- Use one shared legend when validation panels repeat the same categories.
- Use a legend-only axis when the legend would cover data.
- Use outside legends for heatmaps, charge-density maps, contour/field panels, and
  raster structure panels unless a documented empty region makes an in-panel legend safe.
- Hide x-tick labels when the legend or nearby table already names methods/models.
- Put warnings and limitations as small muted-red annotations, not as large badges.

## Plot polish defaults

- Use white outer canvases for ordinary docx/report figures so the figure blends into
  the document page. Light neutral gray may be used inside an axes or structure plate
  only when it serves readability; do not export the whole figure as a gray block on a
  white Word page. Use black only inside dark image or structure plates.
- Remove top and right spines; use sparse ticks; avoid dense grids.
- Use SVG/PDF as editable vector outputs plus PNG preview.
- Tighten y-limits to the relevant data range unless zero is scientifically required.
- Use line widths around 1.2-1.8 pt for report-width plots; use larger markers only
  when points are sparse.
- Prefer alpha bands for uncertainty and muted fills for context.

## Anti-patterns

- Equal-sized dashboard grids where the key observation is visually buried.
- Large white screenshot/PIL collages where small plots and structure renders float in
  blank space.
- Repeating the same legend in every subplot.
- Saturated category colors that change meaning between panels.
- White text on pale bars or dark text on dark structure plates.
- Formula definitions, method notes, or reference-state explanations placed inside data
  axes instead of captions, note bands, or note panels.
- In-panel legends over heatmaps, charge-density maps, or contour/raster panels.
- Bare total-energy tables without relative-energy plots.
- DOS/PDOS panels detached from the structure/projection they describe.
- PCA/UMAP panels without split/source/outlier labels.
