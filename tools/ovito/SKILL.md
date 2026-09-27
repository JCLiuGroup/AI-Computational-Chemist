---
name: ovito
description: Use OVITO or the OVITO Python module for atomistic visualization and analysis of structures and trajectories, including rendering, common-neighbor/PTM structure classification, coordination/RDF, surface meshes, Wigner-Seitz defects, and trajectory-derived figures.
---

# OVITO

Use this skill when the task is visual inspection, publication-style rendering, or atomistic trajectory/structure analysis with OVITO. It pairs naturally with VASP, LAMMPS, MLP, and structure-prep outputs.

## Required inputs

- Structure or trajectory path and format: POSCAR/CONTCAR, XYZ/extxyz, dump, data, XDATCAR, CIF, etc.
- Analysis target: image, animation, coordination/RDF, structure classification, defect count, surface/cluster metric, or selection/export.
- Frame range and timestep/units for trajectories.
- Species/type mapping and periodic boundary convention.
- Rendering target: image size, camera/view, colors, labels, and whether the result is exploratory or publication-ready.

## Where to find what

| Situation | Go to |
|---|---|
| install/check OVITO Python, build a pipeline, render images, analyze trajectories | `references/running.md` |
| choose the right scientific figure path and quality floor before rendering | `knowledge/scientific-visualization.md` |
| render atomistic structures as CPK, ball-and-stick, or quick ASE preview images | `references/structure-rendering.md` |
| validate imported data, modifiers, image outputs, and quantitative summaries | `scripts/ovito_analyze.py`, `scripts/ovito_render.py`, then `references/validation.md` |
| headless import/render fails, modifiers give wrong counts, colors or PBC look wrong | `references/errors.md` |
| official user manual, Python API, modifiers, PyPI/conda install pages | `references/resources.md` |
| example contribution rules | `examples/README.md` |

## Workflow

1. Confirm the source file and units with the engine skill that produced it.
2. Load `running.md` for the matching task family.
3. For quantitative analysis, run `ovito_analyze.py` on a small frame range first; inspect counts and warnings.
4. For figures, run `ovito_render.py` and visually inspect the image before using it in a report.
5. Save the script, source file path, OVITO version, modifier parameters, frame range, and rendered/exported artifacts.

## Hard guardrails

- OVITO modifier outputs depend on cutoffs, structure type, PBC, and particle type mapping; record them.
- Do not infer chemistry from color alone. Preserve explicit element/type legends in notes or figure metadata.
- Do not claim defect counts from a visualization-only pipeline; use a quantitative modifier and exported table/JSON.
- Large trajectories and rendered animations are generated artifacts; do not commit them unless deliberately small examples.
