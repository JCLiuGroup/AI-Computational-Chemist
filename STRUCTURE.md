# Repository Structure Convention

How this collection is organized and how to extend it.

## Top-level taxonomy

```text
procedures/   orchestrator skills: review-response, comp-chem-workflow, literature-to-calculation, research-orchestrator
tools/        per-code skills: vasp, cp2k, gaussian, multiwfn, gromacs, lammps, mlp, deepmd, phonopy, vaspkit, catmap, lobster, ovito, structure-prep, hpc-submit, rsess, report
knowledge/    tool-agnostic science + practice (flat reference library; NOT skills)
```

**Three content types, two levels — stop there.** The split is by *kind of content*, not depth:

- **procedure** — *how to drive* multi-step work (orchestrators with state + approval gates). Goes in `procedures/`.
- **tool** — *how to operate* one code (inputs, parsers, error tables). Goes in `tools/<name>/`. Dies if you switch codes.
- **knowledge** — *the science and practice itself*: what to compute, the formalism, how to interpret and design it, "for this kind of question we usually solve it like this." Tool-agnostic — survives switching codes. Goes in `knowledge/` as flat reference docs.

The test for tool-vs-knowledge: **"would this still be true if you switched codes?"** Yes → `knowledge/`; no → `tools/<code>/`.

`procedures/` and `tools/` hold **skills** (frontmatter + `SKILL.md`, routable, installed). `knowledge/` is a **flat reference library** — no `SKILL.md`, not in the routing table, and never exposed as a skill; the collection copy includes it because skills cross-link into it, and agents read it for ideas and adapt freely (never bound to follow it). The top-level `aicc/` directory is runtime infrastructure for the collection CLI, not a fourth content or routing category. Do not add more content categories or deeper nesting; deep taxonomy with routing layers defeats description-based routing. Skill names stay globally unique regardless of folder.

Procedure skills are a SKILL.md plus their own `references/` as needed. Every tool skill follows the canonical layout below.

## Research-orchestrator protocol layout

`procedures/research-orchestrator/` is a procedure skill with an additional responsibility: it defines shared project state. Keep this protocol separate from engine details. It coordinates tasks and records evidence; it does not decide that every calculation must use one code.

```text
procedures/research-orchestrator/
  SKILL.md
  references/               # state, task, artifact, gate, ownership, job, recovery contracts
  scripts/                  # state validators, gates, leases/jobs, claim/report helpers
  examples/
```

The skill's situation table is the maintained index of individual references and
commands. Do not duplicate that inventory here.

Projects using this protocol keep their live state under `.research/`:

```text
.research/
  project.yaml              # project metadata, approvals, assumptions, status
  tasks/
    T001.yaml               # one DAG node per task
  jobs/
    J-<uuid>.json           # authoritative scheduler-attempt history
  artifacts.jsonl           # output records with provenance and claims
  decisions.jsonl           # scientific and workflow decisions
  events.jsonl              # append-only state-change log
  leases/
    T001.json               # active ownership and heartbeat, if claimed
```

Task files route both execution and context. `skill` points to the procedure/tool that should do the work (`comp-chem-workflow`, `structure-prep`, `vasp`, `cp2k`, `gaussian`, `hpc-submit`, `report`, etc.). `knowledge_required` lists root-relative `knowledge/` references that should inform the scientific proposal or interpretation. This keeps tools as software-operation skills and knowledge as reusable scientific context.

Execution tasks, especially HPC submission and monitoring, must have one active owner through the lease protocol. Planning and critique can involve multiple agents, but no task should be blindly submitted or rerun just because another session sees it as incomplete. Use `validate_state.py`, `ready_tasks.py`, `run_required_checks.py`, and lease reconciliation at handoff and recovery boundaries.

The normative protocol is defined by the skill, references, scripts, examples, and
this structure contract.

## Three loading tiers

1. **Frontmatter `description`** — always in the agent's context; the routing key. One sentence of "use when".
2. **SKILL.md** — loaded when the skill triggers. A table of contents: when to use, required inputs, the task decision, a *situation-indexed* map of the content, and hard guardrails. No deep content — keep it a map, not the territory.
3. **references/ + examples/ + scripts/** — loaded selectively, one file at a time. This is where all knowledge lives.

## Canonical per-tool layout

```text
tools/<name>/
  SKILL.md                # TOC; see tier 2
  references/
    running.md            # how to run: templates, defaults, task rules
    validation.md         # preflight + post-run checks, convergence criteria, provenance
    errors.md             # symptom -> cause -> fix tables, escalation ladders
    resources.md          # annotated external links (manuals, forums, databases)
    <topic>.md            # extra topics as they accumulate (e.g. u-values-magmom.md)
  examples/
    README.md             # example rules + per-example README template
    <case-name>/          # complete inputs + README.md + expected-output.md
  scripts/                # deterministic CLI helpers (preflight checks, parsers)
```

The three subfolders are three affordances: **references/** you *read*, **examples/** you *copy and adapt*, **scripts/** you *execute*. Keep the boundary clean.

Structure-prep is the model release boundary for atomistic geometry. For slab, surface,
defect, adsorbate, or cluster models, pair `tools/structure-prep` generation with the
research-orchestrator `model-structure-review` gate: literature precedent first, then
read-only numerical geometry audit, then accepted structures for engine skills.

## File conventions

- **Canonical names are identical across skills** (`running`, `validation`, `errors`, `resources`) — learn the pattern once, know every skill.
- Every reference file opens with a `> Load this when: ...` scope line, so a file found by `ls` still explains itself.
- One topic per file. Split only when a file genuinely spans multiple tasks — then split by task (`running-neb.md`, ...) and demote the original to a mini-index pointing onward. Length alone is not a trigger: a long file on one coherent topic is fine.
- **Index discipline**: adding a file isn't done until the SKILL.md situation table has a row for it. A stale TOC is how progressive disclosure dies.
- **Cross-references are project-root-relative.** A pointer that leaves the current skill — to `knowledge/…`, another `tools/<skill>/…`, or a `procedures/<proc>/…` — is written from the repo root (`knowledge/electronic-structure.md`, `tools/vasp/references/dos-band.md`), never with `../`-counting. This matches AGENTS.md, reads the same from any depth, and removes a whole class of wrong-depth bugs. Paths *within* a skill stay skill-relative (`references/running.md`, `scripts/make_slab.py`).
- Scripts: stdlib-only where possible, clear error if a dependency is missing, non-zero exit on failure so they compose into gates.
- **Third-party deps go inline (PEP 723), run with `uv run`.** A script needing pymatgen/rdkit/ovito/… declares them in a `# /// script … dependencies = [...] # ///` header and is invoked `uv run script.py …`; uv resolves a pinned, isolated, cached env so the script just works without a global install or a host-env match. Pure-stdlib scripts (parsers, preflight checks) need no header and run under plain `python` or `uv run` alike. Keep the missing-dependency guard anyway, pointing at `uv run`.
- **Scripts target modern Python** (current stable; no compatibility downgrades for old cluster interpreters). On remotes, obtain a modern interpreter via the cluster guide's Python recipe (conda/uv/module) — the environment comes to the scripts, not the other way around.

## Examples

- Verified only: actually run, with software version/date/machine in the example's README.
- `expected-output.md` = parsed summary + trimmed excerpts, never bulky raw output.
- Each example README answers: what it demonstrates, expected result, runtime, what to adapt.
- **Examples are site-neutral**: job scripts in examples are templates with site placeholders (`<PARTITION>`, `<LOAD_CODE>`, `<MPI_LAUNCH>`); hostnames, partitions, module names, accounts, and user paths never appear in committed examples.

## Licensing and large files

- Never commit: POTCAR or licensed force-field/basis files (record identity: TITEL lines, name/version/source), copyrighted manuals (link + paraphrase into the topical reference instead), bulky binaries (WAVECAR, CHGCAR, .chk, trajectories).
- `.gitignore` enforces the common cases; `git add -f` consciously if a small exception is justified.
- Local manual copies, if needed, go in a gitignored `manuals/` — available locally, never versioned.

## Reference values

Templates, U values, thresholds, and defaults in `references/` are community starting points meant to be **edited into group conventions** — that is the intended use. A reproduction target's published settings always override them.
