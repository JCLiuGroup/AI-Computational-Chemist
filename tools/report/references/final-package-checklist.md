# Final Package Checklist

> Load this after a `.docx` or final report package is assembled and before handoff to
> the user. This checklist verifies the delivered file and its provenance. Scientific
> readiness remains governed by `validation.md`.

## Document integrity

- [ ] The `.docx` archive opens and passes a ZIP integrity check (`unzip -t file.docx`).
- [ ] The number of embedded images matches the expected figure count.
- [ ] The number of figure captions matches the expected figure count.
- [ ] No expected figure is blank, duplicated, or missing from the document XML.
- [ ] No unresolved placeholders remain: `TODO`, `XXX`, `[DECIDE]`,
  `AUTHOR_INPUT_NEEDED`, `<fill>`, or similar draft markers.
- [ ] The document uses the requested font/alignment/page format when a format was
  specified by the user or target journal.

## Claim and evidence mapping

- [ ] Each formal conclusion consumes an accepted claim, an explicit waiver, or a
  visible `inconclusive` / `contradicts` limitation.
- [ ] Each figure has a figure contract or an equivalent manifest section naming its
  scientific driver, core conclusion, panel map, source data, layout/aesthetic
  contract, and risk notes.
- [ ] Reviewer-response figures link to reviewer comment IDs when applicable; generic
  research-report figures link to research questions, manuscript claims, benchmark
  cases, method-validation tasks, or exploratory-analysis IDs instead.
- [ ] Every reported number has units and a source path or artifact ID.
- [ ] The calculation-directory index maps each figure/table to the raw input/output
  directory or data file used to make it.

## Figure and table handoff

- [ ] Every panel mentioned in a caption is present in the figure.
- [ ] Every panel present in a figure is explained in the caption or nearby text.
- [ ] Figures have been checked at final inserted size; text is readable, tick labels do
  not collide, legends/colorbars do not cover data, and panel labels do not obscure
  evidence.
- [ ] Matplotlib figure QA warnings are cleared or explicitly waived. A final report does
  not carry unresolved warnings for overlap, low contrast, sampled raster contrast, long
  explanatory text inside axes, or legends inside heatmap/charge-density/contour panels.
- [ ] Raster/post-assembly figure warnings from `check_figure_images.py` are cleared or
  explicitly waived for figures assembled from OVITO renders, screenshots, PIL,
  ImageMagick, slide exports, or other non-Matplotlib composites.
- [ ] Multi-panel figures show a clear visual hierarchy rather than an equal-sized
  dashboard when one panel carries the conclusion; repeated legends are shared or moved
  out of data panels.
- [ ] Colors are consistent with semantic roles across panels and do not change meaning
  within the same figure.
- [ ] Figure text has sufficient contrast at final size. White text appears only on
  dark panels or dark filled regions; any text over structure/raster images uses a
  visible label box, stroke/halo, or documented high-contrast placement.
- [ ] The outer canvas of each inserted figure visually matches the document
  background. For Word/docx reports, the figure border should normally be white rather
  than `neutral-white` gray.
- [ ] Structure labels, atom labels, arrows, and annotations do not cover the active
  site, decisive bond, adsorbate, or property colorbar.
- [ ] Captions state method/provenance at reader-facing detail and do not overclaim.
- [ ] Relative energies state reference states; bare total energies do not appear as
  scientific evidence.
- [ ] Structure figures use final accepted structures unless a limitation states why not.
- [ ] Charge, DOS/PDOS, Bader, spin, ELF, work-function, or other electronic-structure
  claims are paired with the relevant model/structure context.

## Handoff statement

The final response to the user should state:

- report mode: `stage-synthesis` or `final`;
- files produced or checked;
- figure/table counts;
- validation commands run;
- unresolved author decisions or limitations, if any.
