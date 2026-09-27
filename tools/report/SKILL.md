---
name: report
description: "Assemble stage-synthesis or final .docx reports from computed results. Use for interim review packets after a calculation wave, or as the final deliverable of peer-review responses, calculation reports, and reproductions when accepted claims must be handed to humans with figures, captioned relative-energy tables, and structure figures paired with their data. Encodes report maturity gates: stage reports disclose pending follow-up; final reports consume accepted claims by default."
---

# Report Builder

Build one of two post-result deliverables: a **stage synthesis** from validated but
unaccepted evidence, or a **final `.docx`** from accepted claims and explicit waivers.
Do not put report tasks on the first engine/HPC submission critical path.

## Required inputs

- Report mode and the evidence/claim package, including status, provenance, units,
  limitations, waivers, and open follow-up items.
- Source tables and figures; for new or revised figures, their source data and
  scientific driver.
- The accepted report gate for final mode.

## Route map

| Need | Load or run |
|---|---|
| select only the references needed for this report | `manifest.yaml` |
| choose mode, write the manifest, and assemble the document | `references/running.md`; `scripts/build_report.py`; `examples/manifest.json` |
| check scientific and human-readability readiness | `references/validation.md` |
| contract a figure and choose its panel responsibilities | `references/figure-contract.md`; `references/figure-archetype-atlas.md` |
| compose, size, and QA publication figures | `references/computational-chemistry-figure-style.md`; `references/figure-layout-qa.md`; `scripts/aicc_figure_style.py`; `scripts/check_figure_images.py` |
| run final `.docx` package QA | `references/final-package-checklist.md` |
| render atomistic models and choose scientifically appropriate evidence | `tools/ovito/references/structure-rendering.md`; `knowledge/scientific-visualization.md` |

## Workflow

1. Choose stage synthesis unless claims are accepted, waivers and limitations are
   explicit, follow-up state is resolved, and the report gate permits final mode.
2. Load `manifest.yaml` routes, run the pre-report checks in `references/validation.md`,
   and resolve or visibly waive missing low-cost analyses.
3. Contract any new figures before plotting, build the report manifest, and run
   `uv run scripts/build_report.py`.
4. Validate the rendered document; in final mode also complete
   `references/final-package-checklist.md`. Report contents, mode, and advisories.

## Hard guardrails

- Never promote validated or exploratory evidence to accepted/conclusive language.
  Stage reports must remain visibly interim.
- Report relative energies with units and reference states; do not expose bare total
  energies as scientific conclusions.
- Pair quantitative structural/electronic claims with suitable visual evidence. Use
  relaxed final structures and the model-view rules in `references/running.md`.
- Give every report-ready figure a scientific driver, source-data provenance, panel
  purpose, and final-size QA; automated checks do not replace visual inspection.
- Keep captions paste-ready with method, units, convergence status, and provenance.
- Produce an author-editable draft only. Humans accept claims, finalize tone, and send
  the package.
