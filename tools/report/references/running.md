# Building the report

> Load this when: assembling a stage-synthesis review packet or the final `.docx`
> deliverable from computed results.

## Report modes

- **Stage synthesis**: use after a calculation wave to brief the user/critic. It may
  include validated evidence that is not yet accepted, but every claim must show its
  status (`validated`, `accepted`, `inconclusive`, `needs-follow-up`, `waived`) and
  list the follow-up task or decision needed. It is not a final deliverable and not a
  prerequisite for first engine input generation or HPC submission.
- **Final report**: use only after relevant claims are accepted or explicitly waived as
  limitations, no open `needs-follow-up` blocks final conclusions, and the report gate
  passes. It consumes accepted claims by default.

## Flow

1. Choose the report mode. If any critic outcome is `needs-follow-up` and no human
   waiver exists, write a stage synthesis and create/point to the follow-up tasks.
2. Run the pre-report soft gate in `validation.md`: decide whether free-energy corrections, DOS/PDOS, charge/work-function, or another low-cost analysis is needed before claims are drafted. Do the analysis when it is needed, or record a visible waiver/limitation.
3. Create a short figure contract for each report-ready figure using
   `figure-contract.md`. The contract names the scientific driver (reviewer comment,
   research question, manuscript claim, benchmark case, method-validation task, or
   exploratory-analysis ID), core conclusion, panel map, source data, backend choices,
   layout contract, aesthetic contract, and risk notes. Reviewer-comment links are
   optional and only required for review-response packages. Use
   `figure-archetype-atlas.md` first to select the figure responsibility, hero panel,
   required support panels, and any panels to drop if crowded. Then use
   `computational-chemistry-figure-style.md` and `figure-layout-qa.md` to choose the
   AICC page archetype, visual hierarchy, semantic palette roles, final width,
   font-size floor, legend/colorbar strategy, hero-panel size, and known crowding risks
   before plotting.
4. Generate the figures (`tools/ovito`) from the relaxed final structure. For VASP
   relaxations, the report figure source is `CONTCAR`, not the input `POSCAR`, unless
   `POSCAR` is explicitly documented as a copy of the final `CONTCAR`. For each model,
   render **orthographic top + side** views and assemble them side by side as one
   `(a)`/`(b)` panel: `(a)` top on the left, `(b)` side on the right. Where a
   charge/valence claim is made, color the atoms by Bader charge with a colorbar
   (`--color-by`) and assemble that view with the same-view plain element-colored render
   into one `(a)`/`(b)` panel. Zoom or crop side-view panels to the
   slab/adsorbate/active-site region so empty vacuum does not dominate the figure. Keep
   the source subimages and panel assembly command as provenance (see
   `tools/ovito/references/structure-rendering.md`). For Matplotlib panels, prefer the
   reusable helpers in `scripts/aicc_figure_style.py` for AICC palettes, layout
   templates, lcurve/parity/PCA/energy/DOS/reaction-profile plot helpers, consistent
   font settings, panel labels, contrast-aware annotations, vector/preview export,
   text-overlap diagnostics, low-contrast text diagnostics, rendered-pixel contrast
   sampling, long-text-in-axes checks, in-raster legend checks, outside legends, and
   figure-level note bands.
5. Write a **results table of relative energies** (E_ads, E_bind, Delta E/Delta G, barriers) — not total energies. State the reference state in the caption.
6. Write the report **manifest** (JSON, below) referencing the paragraphs, tables, figure files, and figure contracts when available.
7. `uv run scripts/build_report.py manifest.json -o report.docx`.
8. Run the full `validation.md` checklist and the final package checklist before handing over. Fix anything the builder flags on stderr.

## Manifest schema (JSON)

```json
{
  "title": "Computational response to peer review",
  "subtitle": "Manuscript NNN — drafted for the authors",
  "sections": [
    {
      "heading": "R2.C8 — interfacial Pt valence state",
      "level": 1,
      "paragraphs": [
        "Quote the comment. State what was computed and the method (one line confirming the manuscript's settings). Give the result with units and provenance, then the resulting manuscript change.",
        "..."
      ],
      "tables": [
        {"caption": "Relative energies (eV) and Bader charges; CO referenced to gas-phase CO.",
         "columns": ["Model", "E_ads(CO) (eV)", "Bader q(Pt) (e)"],
         "rows": [["Pt4 cluster", "-1.97", "+0.05"],
                  ["Pt single-atom +Ov", "-3.04", "-0.21"]]}
      ],
      "figures": [
        {"path": "figs/pt4_top_side_panel.png",
         "caption": "Pt4/anatase(101) model: (a) orthographic top view; (b) zoomed orthographic side view.",
         "contract": "figs/pt4_top_side_panel.figure-contract.yaml",
         "width_in": 6.2},
        {"path": "figs/pt4_charge_panel.png",
         "caption": "Same side-view geometry: (a) element-colored ball-and-stick render; (b) Bader-charge-colored render with symmetric colorbar.",
         "contract": "figs/pt4_charge_panel.figure-contract.yaml",
         "width_in": 6.2}
      ]
    }
  ]
}
```

- `level`: 1–3. Tables get a caption **above**, figures a caption **below**; both auto-numbered.
- Paragraphs are plain text (the builder keeps assembly mechanical — write prose in the package, not markup here).
- Keep figure files beside the manifest (relative paths resolve from the manifest's directory).

## Report skeleton (peer-review response — the flagship case)

1. **Summary / cover** — what was computed, one line per comment outcome.
2. **Per comment** (one section each): quoted comment → method line → result (relative energies + the paired structure/charge figure) → manuscript change. Mark `contradicts`/`inconclusive` outcomes plainly.
3. **SI material** — full tables (relative energies, units, convergence) + figures with complete captions, paste-ready.
4. **Revision changelog** — where the manuscript changed and why.
5. **Calculation directory index** — a final table mapping every Figure/Table to the directory its data was computed in (e.g. `Figure 1 → calc/pt4_ads/`, `Table 2 → calc/co_configs/`). This lets a human trace any number back to its raw inputs/outputs for checking and archival. Always include it; it is the provenance backbone of the report.

For a generic calculation report, drop the per-comment framing and use: objective → method → results (relative energies + figures) → validation → limitations. Generic reports still use figure contracts, but the `scientific_drivers` are research questions, manuscript claims, benchmark cases, method-validation tasks, or exploratory-analysis IDs rather than reviewer comments.

For a stage synthesis, add an opening section named "Current Status" with:

- accepted claims so far;
- validated evidence still awaiting critic/user acceptance;
- `needs-follow-up` tasks with IDs, purpose, and expected next decision;
- waived limitations, with decision provenance.

## Figures: the pairing rule in practice

Never present a Bader charge / bond length / valence claim as a bare number. The structure figure *is* the evidence: atoms colored by the quantity (+ colorbar), the few decisive atoms labeled, top **and** side ortho views so geometry is unambiguous. Combine with a DOS/PDOS panel when the electronic-structure argument needs it (`knowledge/scientific-visualization.md`).

For report-ready structure figures, the unit consumed by the manifest should usually be
the assembled panel image, not the individual top/side or charge/plain subimages:

- model geometry: `(a)` top view on the left + `(b)` zoomed/cropped side view on
  the right in one figure;
- charge/property evidence: `(a)` plain element-colored view + `(b)` same-view
  property-colored view in one figure;
- side views should be zoomed/cropped to the chemically relevant slab/adsorbate region
  unless the full vacuum/cell height is part of the claim.

## Figure layout QA

Before final docx assembly, open every assembled figure at the size it will occupy in
the document. The report is not ready if text overlaps, legends cover data, panel labels
hide evidence, white text sits on a white/light background, dark text sits on a dark
panel, long explanatory text sits inside a data axes, a heatmap/charge-density/contour
legend is placed over the raster image, or structure labels obscure the active site.
Fix layout by enlarging the canvas, changing the panel hierarchy, moving to a shared
legend or legend-only panel, moving notes/formula definitions to `add_note_band()` or
the caption, shortening labels, using contrast-aware annotation helpers, choosing the
AICC layout template that matches the figure archetype, or splitting the figure. Do not
solve crowding by shrinking text below the font-size floor recorded in the figure
contract.

For Matplotlib report figures, treat the `warnings` returned by `save_aicc_figure()` as
blocking for final `.docx` assembly. A stage synthesis may carry warnings as visible
limitations, but a final report needs warnings fixed or an explicit waiver with the
affected figure and reason.

For final images assembled outside Matplotlib, run the raster check on the exact files
referenced by the report manifest:

```bash
uv run tools/report/scripts/check_figure_images.py --final-width-in 6.8 --fail-on-warnings figs/*.png
```

This check is intentionally conservative. A warning does not mean the science is wrong,
but it does mean the figure must be visually reviewed at the inserted width and fixed
or waived before a final report handoff.
