# AI Computational Chemist (AICC)

Agent skills for computational chemistry and materials science.

Building blocks for **semi-automatic computational research driven by peer review**. Given an original manuscript and the reviewers' comments asking for computational work, an AI agent uses this collection to triage which comments require calculations, run them consistently with the manuscript's own methods (or — for purely experimental manuscripts with no prior calculations — with a user-approved method designed around the experimental characterization), validate whether each result actually addresses the concern, and draft response-letter and SI material — with human approval at every scientific decision point.

The skills are also usable standalone for general computational chemistry work (DFT, quantum chemistry, MD, machine-learning potentials, phonons, microkinetics, HPC execution). Harness-neutral: works with any agent that can read instruction files — Claude Code, Codex, Cursor, opencode, or a custom agent loop.

## Flagship workflow

```text
manuscript + SI + reviews (+ original calculation archive)
  -> review-response: method fingerprint + comment triage    [human approves the plan]
  -> per-comment calculations (comp-chem-workflow + engine skills)
  -> validation against each reviewer's concern
  -> response package: letter paragraphs, SI tables/figures  [human approves the draft]
```

Two hard rules make it trustworthy: new calculations must match the manuscript's method fingerprint (or disclose the deviation), and results that *contradict* the manuscript are never buried or spun. Semi-automatic mode stops for author review; explicitly requested autonomous mode records the contradiction prominently and continues with a draft.

## Research orchestration layer

For larger projects, `procedures/research-orchestrator/` adds a machine-readable control plane on top of the individual skills. A project becomes a task DAG under `.research/`, with explicit dependencies, claims, required checks, decisions, events, and artifact provenance. This is the layer used for multi-agent planning and critique, resumable handoffs, and final report assembly.

The project state is intentionally separate from the scientific and tool knowledge:

- `.research/project.yaml` records project metadata, assumptions, approvals, and high-level status.
- `.research/tasks/*.yaml` records task nodes: dependencies, success criteria, `skill`, `required_refs`, `knowledge_required`, `required_checks`, and output artifacts.
- `.research/jobs/*.json` records authoritative scheduler-attempt history.
- `.research/artifacts.jsonl`, `decisions.jsonl`, and `events.jsonl` preserve evidence, reasoning decisions, and workflow history.
- `.research/leases/*.json` prevents multiple agents from owning the same expensive execution task.

Routing stays flexible. A task's `skill` field can point to `vasp`, `cp2k`, `gaussian`, `lammps`, `structure-prep`, `hpc-submit`, `report`, or another appropriate skill; VASP is not hard-coded into the orchestration layer. Scientific background is requested separately through `knowledge_required`, so tasks can pull in `knowledge/electrochemistry.md`, `knowledge/electronic-structure.md`, `knowledge/scientific-visualization.md`, or other references without turning them into executable tools.

The helper scripts in `procedures/research-orchestrator/scripts/` enforce the protocol: initialize project state, validate schemas, list ready tasks, claim/release/heartbeat leases, reconcile stale ownership, run required checks, classify claims, accept artifacts, and scaffold report manifests. The key safety rule is that `completed`, `validated`, and `accepted` are different states; final reports should consume accepted claims by default.

Structure modeling has its own review gate inside this orchestration layer. For slabs,
surfaces, defects, adsorbates, molecules on surfaces, and supported clusters, the task
DAG should separate surface-literature review, `structure-prep` generation, and
read-only structure criticism. The critic checks Miller index and termination precedent,
slab a/b size, vacuum, fixed layers, closest contacts, adsorbate-surface distance, and
periodic-image separation before VASP/CP2K/Gaussian/LAMMPS or HPC tasks consume the
structure. For very niche materials or unusual modifications, no direct literature
precedent is acceptable when the search scope is recorded and the model is labeled
exploratory; the gate then focuses on internal geometric and chemical plausibility.

## Layout

```text
AGENTS.md                      global guardrails + routing (load into every session)
STRUCTURE.md                   the organization convention (read before adding content)
aicc/                          optional standalone CLI extension
procedures/                    orchestrators - how work is driven (agent skills)
  review-response/             flagship: manuscript + reviews -> validated response package
  comp-chem-workflow/          scientific lifecycle and cross-engine validation controller
  literature-to-calculation/   third-party paper / SI / report -> concrete calculation target
  research-orchestrator/       durable state: task DAG, gates, artifacts, leases/jobs, ready/blocked
knowledge/                     tool-agnostic science + practice (flat reference library; not skills)
  machine-learning-potentials.md MLP concepts and cross-code comparison
  electrochemistry.md          CHE step diagrams, SHE/RHE/pH corrections, constant-potential concepts
  surface-pourbaix.md          surface-state thermodynamics, dissolution, SHE/RHE and phase-map audits
tools/                         per-code skills - how each tool is operated
  structure-prep/              periodic (pymatgen) + molecular (RDKit) structure preparation
  vasp/                        static, relax, electronic, reaction/NEB, CHE/VASPsol/VASPsol++ electrochemistry
  cp2k/                        Quickstep GPW/GAPW, opt/cell-opt, MD, electronic analysis
  gaussian/                    molecular QC: SP, opt, freq, TS, IRC, solvation
  multiwfn/                    molecular wavefunction analysis, charges, orbitals/NTOs, spectra
  gromacs/                     biomolecular, liquid, membrane, ligand, MARTINI, and GROMACS analysis workflows
  lammps/                      classical / reactive / MLP-driven MD
  mlp/                         MLP concepts and cross-program routing: MACE, NequIP, GPUMD, LASP, GemNet-OC, EquiformerV2
  deepmd/                      DeePMD-kit datasets, training, inference, validation, DP-GEN-style workflows
  phonopy/                     finite-displacement phonon workflows
  vaspkit/                     VASP helper input generation and post-processing
  catmap/                      microkinetic modeling, TOF maps, volcano plots
  lobster/                     LOBSTER COHP/COOP bonding analysis from VASP wavefunctions
  ovito/                       atomistic visualization and trajectory analysis
  hpc-submit/                  local / SSH / Slurm / PBS execution
  rsess/                       persistent remote shell sessions (tmux on the remote)
  report/                      assemble the near-submission .docx report / response package
benchmark/                     published benchmark archive (cases, rubric, evaluations)
LICENSE                        license terms
CITATION.cff                   citation metadata
```

The three top-level content kinds are distinct: **procedures/** drive multi-step work, **tools/** operate a specific code, **knowledge/** is tool-agnostic science and practice the others draw on (read it for ideas, adapt freely — it is not a skill). Program families can have both layers: for example `knowledge/machine-learning-potentials.md` explains MLP concepts across DeePMD, MACE, NequIP, GPUMD, LASP, GemNet-OC, and EquiformerV2, while `tools/deepmd/` contains DeePMD-kit-specific commands and validation; `knowledge/force-fields.md` and `knowledge/molecular-dynamics.md` explain classical MD model choice, sampling, and trajectory interpretation, while `tools/gromacs/` and `tools/lammps/` contain engine-specific setup and validation; `knowledge/electrochemistry.md` explains CHE/constant-potential concepts, while `tools/vasp/references/electrochemistry.md` contains VASP/VASPsol execution details. Every procedure/tool skill follows the same structure (see `STRUCTURE.md`): `SKILL.md` is a short table of contents; detail lives in `references/` (`running.md`, `validation.md`, `errors.md`, `resources.md`, plus topic files), example contribution rules and any verified cases live in `examples/`, and deterministic helpers live in `scripts/` (preflight checks and output parsers that exit non-zero on failure). Each skill owns its full life cycle — setup, preflight, error recovery, and output parsing; the cross-engine validation ladder lives in `comp-chem-workflow`.

## Installation

Use the installer for normal setup:

```bash
./install.sh --target ~/.codex/skills
./install.sh --target ~/.claude/skills --harness claude --project /path/to/work
```

The installer also provides an optional, lightweight `aicc` CLI under
`~/.local/bin`. It is a convenience layer for project status, task/lease operations,
recorded jobs, skill management, and installation diagnostics; the skills remain usable
without it.

```bash
aicc --help
aicc status PROJECT
aicc job --help
aicc skill --help
aicc doctor
```

Use each command's `--help` for its current interface. The CLI does not install or
replace scientific engines, scheduler software, potentials, basis sets, or licensed
data.

**Runtime for helper scripts** — install [`uv`](https://docs.astral.sh/uv/). The Python helpers in `scripts/` that need third-party packages (pymatgen, rdkit, ovito) declare those deps inline (PEP 723) and are run with `uv run script.py …`: uv resolves a **per-script** isolated, cached environment, so tools with conflicting requirements never clash and there is no host-environment to match. Pure-stdlib helpers (output parsers, preflight checks) need nothing beyond Python.

uv fetches deps from the index only on a **cache miss**; once an env is built it is reused with no network. On **unstable-internet or air-gapped sites**, warm the cache once where there is connectivity, then run with `uv run --offline …` (or `UV_OFFLINE=1`) — nothing is fetched at run time, so a flaky link or an offline node can't stall a job. On **HPC**, point `UV_CACHE_DIR` at a shared filesystem and warm it on the login node; compute nodes then reuse the same per-tool envs offline.

**`uv run` is the preferred path**; PyPI has fast regional mirrors too, so point uv at one with `UV_DEFAULT_INDEX` where the default index is slow. **conda/mamba is the fallback** — the scripts run against any interpreter that has the deps, so a prepared conda/mamba env works (then just `python script.py`); reach for it when a package installs more reliably from conda-forge (notably **ovito**, which is conda-blessed via its own channel) or when uv/PyPI is blocked. Region-specific mirror URLs (PyPI or conda-forge) are site config — record them in your `~/.cluster-agents.md`, never in this repo.

Manual install for **Claude Code** - symlink the skill directories and the instruction file:

```bash
ln -s "$(pwd)"/procedures/* "$(pwd)"/tools/* ~/.claude/skills/   # or .claude/skills/ inside a project
ln -s "$(pwd)"/AGENTS.md CLAUDE.md                               # in the project where you work
```

(`knowledge/` is a flat reference library, not skills — don't symlink it as a skill; the skills point into it.)

Manual install for **Codex / AGENTS.md-native harnesses** - `AGENTS.md` is read automatically from the working directory; symlink or copy the `procedures/` and `tools/` directories into the harness's skill location.

**Any other agent** — load `AGENTS.md` as a system/project instruction and make `procedures/*/SKILL.md` and `tools/*/SKILL.md` discoverable (the frontmatter `description` is the routing key).

**Site setup (required before running calculations)** — every environment is different, so the collection never assumes yours. The agent learns a cluster in three tiers (full rules in `AGENTS.md` "Site environment"): (1) a tiny **local bootstrap** — just how to connect and transfer files — that you provide once (a small file, your agent's memory, or taught interactively); (2) the **login banner/MOTD** it reads on connecting; (3) an operating guide **`~/.cluster-agents.md` in your home directory on the cluster** — partitions, modules, code paths, job templates, quotas — authored once on the machine so every later session and teammate inherits it. Fill `~/.cluster-agents.md` from `tools/hpc-submit/references/cluster-guide-template.md`, or let the agent draft it after probing the cluster. Connection facts stay on your machine; nothing site-specific ever enters this repo.

## Design principles

1. **Skills carry knowledge the model can't infer**: concrete templates, default policies, error-recovery tables, and validation scripts — not generic checklists.
2. **Routing happens through descriptions**, not router trees. Each skill's frontmatter says when to use it; `comp-chem-workflow` coordinates multi-stage work.
3. **Deterministic over improvised**: input validation and output parsing are scripts, so they behave the same on every run.
4. **Safety rails are centralized** in `AGENTS.md`: provenance, no invented parameters, approval breakpoints before expensive or destructive actions.
5. **Durable orchestration state is explicit**: `.research/` records task DAGs, artifacts, decisions, events, leases, and acceptance gates so a project can be resumed or handed off without relying on chat history.

## A note on reference values

INCAR templates, Hubbard U values, convergence thresholds, and force-field defaults in `references/` are widely used literature/community starting points. They are **defaults, not endorsements** — when reproducing a paper or following group conventions, the source's settings always win. Edit the reference files to encode your own group's conventions; that is the intended use.

## Peer-review-replication benchmark

`benchmark/` contains the complete evaluation reported in the AICC paper: five published Nature Communications papers whose review files contain explicit computational requests, redacted so the referees' questions remain answerable but the authors' computational answers are removed. Agents equipped with this skill collection answered the original referees' requests autonomously; a fixed six-dimension rubric with seven mandatory red flags then scored the agent reports head-to-head against the original authors' own calculations, executed end-to-end by two independent LLM evaluator models. The case fixtures, agent reports, task prompt, rubric, orchestration protocol, design rationale and both evaluators' complete rating files are all included — see `benchmark/README.md`.

## License

This repository is licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) (see `LICENSE`). The redacted benchmark fixtures under `benchmark/cases/` are derivatives of open-access Nature Communications articles published under CC BY 4.0; original attribution is given by DOI in `benchmark/README.md`.

## Citation

If you use this collection or the benchmark, please cite the repository (see `CITATION.cff`) and the accompanying paper:

> R. Wang, J. Cai & J.-C. Liu. *A harness-neutral skill framework for agentic computational chemistry evaluated on peer-review-derived tasks.* Manuscript in preparation (2026).
