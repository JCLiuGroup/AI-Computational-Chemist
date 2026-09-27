# Response Package

> Load this in Phase 5 when drafting a peer-review response package. The package is a
> writing layer around accepted or explicitly limited computational evidence; it must
> not promote exploratory results into final claims.

## Outputs

Produce these files when the requested deliverable is a reviewer response:

```text
response-letter.md or response-letter.docx
cover-letter.md or cover-letter.docx
revision-changelog.md
report.docx or SI-ready calculation report from tools/report
```

The calculation report remains governed by `tools/report`. This file governs the
letter structure and author-facing decisions.

## Comment identity

Use stable IDs from ingestion and triage:

```text
R1.C1, R1.C2, R2.C1, ...
```

Keep the same ID in:

- triage entries;
- `.research/tasks/*.yaml`;
- scientific-claim artifacts;
- figure contracts (`scientific_drivers.driver_type: reviewer_comment`);
- response-letter sections;
- revision changelog entries.

## Response-letter block

```markdown
### Comment R2.C1
> <verbatim reviewer comment>

**Response.**
We thank the reviewer for this suggestion. To address this point, we performed
<calculation/analysis> using <one-line method fingerprint>. The result shows
<result with units and provenance>. This <addresses / partially addresses / does
not support> the specific concern because <criterion>.

**Changes made.**
- Main text: <page/section/paragraph or AUTHOR_INPUT_NEEDED>
- Supplementary Information: <section, figure, table or not applicable>
- Calculation provenance: <artifact ID or path>

**Status.**
addressed | partially addressed | inconclusive | contradicts | author decision required
```

Rules:

- One response block per comment, in reviewer order.
- Quote the comment exactly; do not paraphrase the concern in place of the quote.
- Every number has units and provenance.
- If a method deviates from the manuscript fingerprint, state the deviation and why.
- Limitations are stated in the response text, not hidden in internal notes.
- `contradicts` results are not written as reassuring replies; route them to the
  authors with options first.

## Cover letter

Keep the cover letter high level. It should summarize major revisions, not duplicate
every point-by-point response.

```markdown
Dear Editor,

We thank you and the reviewers for the constructive evaluation of our manuscript.
In the revised version, we have addressed the main computational and mechanistic
concerns by adding:

1. <major revision 1>
2. <major revision 2>
3. <major revision 3>

All new computational analyses are described in the revised Supplementary
Information with methods, convergence information, limitations, and data
provenance.

Sincerely,
<authors>
```

## AUTHOR_INPUT_NEEDED blocks

Use this marker only when a human author or operator must decide something that the
agent cannot honestly choose:

- a result contradicts or weakens a manuscript claim;
- the response strategy has multiple scientifically plausible options;
- extra expensive computation is optional but could materially change the answer;
- manuscript wording must be softened, removed, or approved by authors;
- journal/editorial metadata is missing.

Template:

```markdown
AUTHOR_INPUT_NEEDED[R2.C3-strategy]
Decision needed: <specific decision>
Options:
A. <option and consequence>
B. <option and consequence>
C. <option and consequence>
Recommended: <one option, with reason>
Blocking: <which package section or claim cannot be finalized>
```

Do not use `AUTHOR_INPUT_NEEDED` for routine command choices, file paths, or minor
formatting unless the missing information blocks the response strategy.

## Revision changelog

```markdown
| Comment ID | Manuscript/SI location | Change | Evidence |
|---|---|---|---|
| R2.C1 | SI Section S4, Fig. S6 | Added adsorption-energy comparison | claim: idmp-anchor-ordering; figure: Fig. S6 |
```
