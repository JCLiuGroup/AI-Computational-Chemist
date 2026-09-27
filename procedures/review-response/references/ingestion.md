# PDF ingestion for review-response

> Load this when: extracting text from manuscript/SI/reviewer-report PDFs at
> Phase 0 — especially locating the computational methods section (mode A vs B)
> and finding computation-related comments in long review files.

The collection ships no extractor — use the system tool (poppler `pdftotext`;
any text extractor works, the Phase 0 ingestion contract in `SKILL.md` is what
matters). Two probes cover the routine cases:

```bash
# methods-section probe (decides manuscript-derived vs designed fingerprint):
pdftotext -layout manuscript.pdf - | grep -niE 'DFT|VASP|functional|basis|cutoff|k-point'

# per-page comment scan that keeps page numbers (read only the pages that hit):
pages=$(pdfinfo reviews.pdf | awk '/^Pages:/{print $2}')
for p in $(seq 1 "$pages"); do
  pdftotext -layout -f "$p" -l "$p" reviews.pdf - | grep -qiE 'DFT|simulat|theor|calculat' && echo "page $p: computational hit"
done
```

Practice:

- Run the methods-section probe **before** classifying the manuscript as
  computational vs experimental — a computational paper has a methods section
  (extract from it; that always beats a designed fingerprint), a purely
  experimental paper does not (design one).
- Record the page number with each comment quote; the ingestion object carries
  `{id, reviewer, page, verbatim_quote}` and downstream phases key off it.
- Long or scanned documents: extraction quality varies; if text extraction
  fails or garbles, say so in the ingestion object rather than silently
  working from a partial read.
