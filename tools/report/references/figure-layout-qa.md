# Figure Layout QA

> Load this with `figure-contract.md` before writing plotting code or assembling
> multi-panel report figures. It adapts publication-figure layout discipline to AICC:
> final-size-first design, stable fonts, explicit legend strategy, and visible checks
> for text/label overlap.

## Core rule

Size the figure before styling it. The layout contract is part of the figure contract:

```yaml
layout_contract:
  target_output: report-docx | manuscript | si | response-letter | slide
  final_width: single-column | double-column | full-page | custom
  final_width_in: 6.8
  expected_panels: 8
  hero_panel: h
  panel_hierarchy:
    primary: [h]
    validation: [a, b, c, d, e]
    contextual: [f, g]
  legend_strategy: direct-label | shared-legend | legend-panel | per-panel | none
  colorbar_strategy: outside-panel | shared-colorbar | inset-only-if-empty-space | none
  note_strategy: caption | figure-note-band | dedicated-note-panel
  contrast_policy:
    plot_background: white
    dark_background_allowed_for: image-or-structure-plate-only
    min_text_contrast_ratio: 4.5
    annotation_text: auto-black-or-white-from-background
  text_policy:
    font_family: Arial or Helvetica-compatible sans-serif
    min_font_pt: 6
    default_font_pt: 7
    panel_label_pt: 8
    panel_label_style: lowercase-bold
    max_xtick_rotation_deg: 45
  crowding_risks:
    - long category names on the x axis
    - repeated legends in parity plots
    - atom labels near the active site
  qa_exports:
    - png-preview
    - pdf-or-svg-vector
  layout_blockers:
    - long_explanatory_text_inside_data_axes
    - legend_inside_raster_axes
    - sampled_text_contrast_below_4.5
```

For computational chemistry figures, also load
`computational-chemistry-figure-style.md` and add an `aesthetic_contract` before
plotting. It selects the page archetype, visual hierarchy, palette role map, and legend
policy for AICC figure types.

## Final-size defaults

Use these as starting points, then enlarge rather than shrink text.

| Figure type | Starting width | When to enlarge |
|---|---:|---|
| One to three simple plots | 3.3-3.6 in | long labels, colorbar, or more than one legend |
| Multi-panel report figure | 6.5-7.2 in | four or more panels, structures plus plots, or shared colorbars |
| MLP-QA + MD observable | 7.0-7.5 in | lcurve, parity, PCA, structures, and MD statistics in one figure |
| Structure + electronic evidence | 6.5-7.2 in | charge-density difference, DOS/PDOS, Bader map, and structure context |
| Workflow/response summary | 6.5-7.5 in | long reviewer comments or route labels |

Do not force a dense AICC evidence figure into single-column width unless the target
journal requires it. If the figure has more than four panels, use double-column width
by default.

## Text and labels

- Keep body, axis, tick, legend, and colorbar text at 6 pt or larger at final size;
  use 7 pt as the normal default.
- Ordinary plots and diagrams use white backgrounds with dark text. White text is
  allowed only on a declared dark image/structure plate, dark filled region, or dark
  callout box.
- Do not hard-code `color="white"` for annotations unless the background is explicitly
  dark and preserved in export. Use `add_contrast_text()` or `annotate_bars_contrast()`
  from `scripts/aicc_figure_style.py` for labels inside bars, heatmap cells, colored
  regions, or dark panels.
- Text/background contrast should be at least 4.5:1 for normal text. If contrast cannot
  be guaranteed because the text sits over a raster image or structure render, use a
  small semi-transparent dark/light label box or a stroke/halo.
- Use lowercase bold panel labels `(a)`, `(b)`, etc. at about 8 pt.
- Avoid 90-degree tick labels in final figures. Shorten labels, wrap labels, or move
  category names into a legend/table instead.
- Put panel labels in consistent top-left positions, outside the data if possible.
- Label only decisive atoms, bonds, structures, or curves. Too many labels make a
  figure less scientific because the reader cannot find the evidence.
- For structure panels, labels must not cover the active site, key bond, adsorbate, or
  colorbar. Prefer leader lines or a nearby empty region when labels are unavoidable.
- Do not put long explanatory text inside data axes. As a hard rule, reference-state
  notes, method notes, formula definitions, reviewer-comment context, and explanatory
  `ax.text()` boxes longer than about 20 characters go in the caption, `add_note_band()`,
  or a dedicated note/legend panel. If their box overlaps the data axes, treat it as a
  blocker rather than a styling issue.

## Legend and colorbar strategy

- Use direct labels for a few stable series when lines do not cross heavily.
- Use one shared legend when multiple panels repeat the same categories.
- Use a dedicated legend panel when the legend is large enough to cover data.
- Avoid per-panel legends unless each panel has genuinely different categories.
- Put colorbars outside the data panel unless the inset region is demonstrably empty.
- Use one shared colorbar for comparable charge, density, spin, or error maps.
- For heatmaps, charge-density maps, contour/field plots, and raster structure panels,
  put legends outside the data axes by default (`legend_outside()` or a legend panel).
  An in-panel legend is acceptable only with an explicit waiver and a high-contrast
  opaque box placed in genuinely empty space.

## Color and contrast

- Prefer one neutral family, one signal family, and one accent family. Avoid assigning
  unrelated saturated colors to every panel.
- Keep the same category/method/composition color across all panels in one figure.
- Reserve red/green mainly for directional cues such as positive/negative change,
  enriched/depleted states, or pass/fail flags.
- Avoid rainbow colormaps for quantitative evidence. Use perceptually ordered maps for
  scalar fields and diverging maps for signed quantities.
- For heatmap or bar annotations, choose text color from the actual cell/bar color; do
  not rely on a global white/black choice.
- For dark image plates, make the axis background black and remove ticks/spines. Put
  labels, scale bars, and channel names in high-contrast white/cyan/magenta; do not mix
  dark plates and ordinary white plot panels without visible gutters.

## AICC-specific layout patterns

### MLP-QA + MD observable

Recommended hierarchy:

1. Put the decisive MD observable in the largest or rightmost/bottom hero panel.
2. Put learning curves, parity plots, PCA, and residual diagnostics in a compact
   validation strip.
3. Keep structures near the MD observable they contextualize.
4. Use shared axis labels for parity/residual panels where possible.
5. Use a shared legend or direct labels for train/validation/test; do not repeat the
   same legend in every QA panel.
6. Prefer `make_aicc_layout("validation-strip")` and the plot helpers in
   `scripts/aicc_figure_style.py` when generating Matplotlib panels.

### Electronic-structure evidence

Recommended hierarchy:

1. Show the exact model/active site before the property plot.
2. Pair Bader/charge-density difference with DOS/PDOS, work function, ELF, spin
   density, or another orthogonal observable when the claim needs mechanism-level
   support.
3. Keep projection labels short and traceable to atoms marked on the structure.
4. Put isovalue/colorbar units in the caption and sidecar provenance.
5. Prefer `make_aicc_layout("structure-plus-property")` when Matplotlib panels are
   assembled with structure/property context.

### Reaction pathway or electrocatalysis

Recommended hierarchy:

1. Make the energy/free-energy profile the hero panel.
2. Draw each intermediate or transition-state energy as a thick horizontal plateau.
   Use thin solid or dashed connectors between plateaus only to show sequence; do not
   use smoothed curves unless the plotted data are a true path coordinate from NEB/IRC.
3. Place the structure for every reported intermediate and transition state directly
   below, above, or beside the corresponding plateau where practical. The structure
   strip should share state names with the x axis and caption.
4. Show TS/NEB/frequency validation as a smaller validation panel.
5. Use consistent state names across the profile, table, caption, and structure labels.
6. Prefer `make_aicc_layout("pathway-hero")` for reaction/free-energy profiles.

For crowded catalytic paths, preserve readability by showing the decisive structures in
the main figure and moving the full structure strip to SI. Do not shrink structures so
far that adsorption sites, bond breaking/forming events, or TS motifs become illegible.
Structure subpanels inherit the report model-figure rules: accepted final structures,
orthographic top+side views when needed, ball-and-stick by default, cropped active-site
views, and no labels covering the decisive bond or site.

## Automated Matplotlib helper

For Matplotlib figures, import `tools/report/scripts/aicc_figure_style.py` from the
plotting script when practical:

```python
from aicc_figure_style import (
    set_aicc_matplotlib_style,
    make_aicc_layout,
    plot_lcurve,
    plot_parity,
    plot_pca_embedding,
    plot_relative_energy_bar,
    plot_dos_pdos,
    plot_reaction_profile,
    add_panel_label,
    add_note_band,
    add_contrast_text,
    annotate_bars_contrast,
    legend_outside,
    find_text_overlaps,
    save_aicc_figure,
)

set_aicc_matplotlib_style()
fig, axes = make_aicc_layout("validation-strip")
plot_lcurve(axes["a"], steps, train_rmse, val_rmse)
add_note_band(fig, "Reference: DFT-labelled train/validation/test sets; RMSE in eV/A.")
warnings = save_aicc_figure(fig, "fig4_mlp_md", width_in=7.2)
```

Treat all warnings from `save_aicc_figure()` as report blockers until fixed or until a
human-readable waiver is recorded. This includes text overlap, low contrast, sampled
low contrast over rendered pixels, long explanatory text inside data axes, and legends
inside raster axes. The helper only detects Matplotlib text objects; structure-render
labels and post-assembly labels still need visual inspection.

## Raster/post-assembly QA

Many report figures are final composites rather than pure Matplotlib figures: OVITO
renders plus plots, PIL/ImageMagick montages, screenshots, slide exports, or images
reinserted after a docx/PDF conversion. Those figures can bypass Matplotlib checks, so
run a final raster check on the exact PNG/JPEG/TIFF that will enter the report:

```bash
uv run tools/report/scripts/check_figure_images.py \
  --final-width-in 6.8 \
  --fail-on-warnings \
  path/to/fig1.png path/to/fig2.png
```

Warnings from this script are not a substitute for visual inspection, but they are
report blockers until the figure is opened at final inserted size and either fixed or
waived with a reason. Treat these patterns as hard failures for final reports:

- outer figure canvas that does not match the document background, normally pure
  white `#ffffff` for Word/docx reports;
- very wide, short canvases where structure labels or tick labels become unreadable;
- excessive blank white background from a screenshot/PIL collage;
- panel labels drawn as large boxed badges that cover or dominate the evidence;
- repeated element legends inside every structure panel;
- formula/reference/method notes baked into the raster image instead of captions or
  note bands;
- charge-density, heatmap, contour, or structure legends placed on top of image data.

## Manual QA checklist

- [ ] Open the PNG/PDF/SVG preview at the final report width, not zoomed to a giant
  monitor view.
- [ ] No tick labels overlap; long labels are wrapped, shortened, angled <=45 degrees,
  or moved to a legend/table.
- [ ] No white text appears on white/light backgrounds; no dark text appears on
  dark-filled regions. Text contrast warnings from `save_aicc_figure()` are resolved.
- [ ] The outer figure canvas matches the document/page background. For docx reports,
  the final PNG/PDF border should normally be `#ffffff`, not a neutral gray block.
- [ ] Legends and colorbars do not cover data.
- [ ] No formula, reference-state explanation, method note, or long explanatory text box
  sits inside a data axes; it has been moved to the caption, note band, or note panel.
- [ ] Heatmap/charge-density/contour/raster panels do not place legends over the image
  unless a documented waiver explains why the location is empty and high-contrast.
- [ ] Panel labels are present, consistent, and not covering plotted evidence.
- [ ] Structure labels do not cover the active site, decisive bond, adsorbate, or
  property colorbar.
- [ ] The same condition/category uses the same color or marker across panels.
- [ ] The palette follows role mapping: primary observable, validation, reference,
  secondary context, warning/limitation, and neutral fills are visually distinct and
  consistent.
- [ ] The figure has a visible hero/validation/context hierarchy when the contract
  declares one; support plots do not compete with the decisive panel.
- [ ] Shared axes and shared legends are used where they reduce repeated text.
- [ ] Text remains readable after the figure is inserted into the `.docx`.
- [ ] Raster composites have a `check_figure_images.py` JSON report or an explicit
  visual waiver; large blank canvases and thin-strip layouts are fixed.
- [ ] The final export bundle keeps a high-resolution preview plus vector output when
  possible.

## Fix order for crowded figures

1. Increase final width/height within the target output.
2. Change the panel hierarchy so the hero panel gets more space.
3. Move repeated legends to a shared legend or legend-only panel.
4. Move formula definitions, reference notes, and method explanations to the caption,
   `add_note_band()`, or a dedicated note panel.
5. Shorten, wrap, or remove nonessential labels.
6. Fix contrast by using automatic black/white label selection, a small label box, or a
   halo/stroke; do not hand-pick white text without checking the background.
7. Split a figure into a main figure plus supplementary/detail figure if the evidence
   is no longer readable.
8. Only after these fixes, make small font-size adjustments; never use unreadably tiny
   text to rescue an overcrowded figure.
