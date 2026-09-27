# Knowledge library

Tool-agnostic **science and practice** — the formalism, the equations, how to set a
calculation up and interpret it, and the hard-won "for this kind of question we usually
solve it like this." This is the knowledge that *survives switching codes* (VASP, Quantum
ESPRESSO, CP2K, …); how to *operate* a specific code lives in `tools/<name>/`.

## How this differs from a skill

These are **flat reference documents, not skills**: no frontmatter, no `SKILL.md`, and not
in the skill routing table. `install.sh` copies them into the installed collection, where
skills can cross-link to them; it does not register them as independent skills. They are
**starting points to draw ideas from, not rules** — an agent reads the relevant doc, takes
what fits the problem, and adapts freely. Discovery is by cross-links from procedure/tool
skills (e.g. `tools/vasp/SKILL.md` points the science of surface energy here), plus the
`AGENTS.md` routing note and this index.

## Conventions

- One topic per file; open with a one-line `> Covers: …` header.
- Tool-agnostic: describe the science/method and how to design & read it, not how to drive a
  particular program. Point to `tools/<code>/` for execution.
- Privacy-neutral, like the rest of the repo: no real-engagement, manuscript, or site detail.
- Defaults, not endorsements: published/source settings always override these starting points.

## Topics

- [surface-thermodynamics.md](surface-thermodynamics.md) — surface energies,
  chemical-potential & oxygen-coverage phase diagrams, stability diagrams, vibrational
  free-energy corrections, Wulff construction.
- [reaction-kinetics.md](reaction-kinetics.md) — DFT energies → rate constants, TST/Eyring,
  mechanisms, RDS/TDTS/TDI, BEP, volcano curves, microkinetic-model inputs.
- [catalytic-reaction-pathways.md](catalytic-reaction-pathways.md) — catalytic reaction path diagrams, sequential intermediate construction, co-adsorption candidate choices, transition-state timing, and energy/free-energy profile discipline.
- [electrochemistry.md](electrochemistry.md) — CHE thermodynamics, OER/ORR/HER step diagrams,
  pH and SHE/RHE potential corrections, overpotential definitions, volcano descriptors, and
  constant-potential concepts. VASP/VASPsol execution lives in `tools/vasp/references/electrochemistry.md`.
- [surface-pourbaix.md](surface-pourbaix.md) — thermodynamic surface-state and adsorbate-coverage
  maps versus pH and potential, CHE lower envelopes, SHE/RHE conversion, dissolution channels,
  aqueous activities, water-window overlays, boundary audits, and interpretation limits.
- [periodic-dft-modeling.md](periodic-dft-modeling.md) — periodic cells, PBC/vacuum, k-points
  versus supercells, convergence tests, energy-comparison discipline, smearing, and reporting.
- [periodic-electrostatics.md](periodic-electrostatics.md) — boundary conditions, molecules in
  boxes, slabs/2D/1D systems, charged-cell corrections, vacuum and dipole convergence, work
  functions, band alignment, and implicit-solvent thermodynamic cycles.
- [bonding-analysis.md](bonding-analysis.md) — interpreting COHP/COOP/ICOHP bonding (bonding vs
  antibonding, occupied antibonding, bond weakening); running LOBSTER lives in `tools/lobster`.
- [electronic-structure.md](electronic-structure.md) — reading DOS/PDOS, bands, Bader/charge,
  charge-density difference, spin density, work function, ELF, d-band center; what each observable
  proves and the evidence-chain discipline. Running these tasks lives in the engine skill such as
  `tools/vasp` or `tools/cp2k`.
- [force-fields.md](force-fields.md) — classical force-field families, charges, bonded/nonbonded
  terms, mixing rules, water/ion models, and parameter provenance. Execution lives in engine skills
  such as `tools/gromacs` or `tools/lammps`.
- [molecular-dynamics.md](molecular-dynamics.md) — MD model choice, statistical sampling,
  RDF/VACF/VDOS, MSD/diffusion, equilibration/statistics, and enhanced sampling
  (Blue-moon/slow-growth/metadynamics). Classical MD runs in `tools/gromacs` or `tools/lammps`;
  AIMD lives in `tools/vasp` or `tools/cp2k`.
- [machine-learning-potentials.md](machine-learning-potentials.md) — tool-agnostic MLP concepts:
  local energy models, symmetry/equivariance, dataset design, validation, active learning, and how
  DeePMD, MACE, NequIP, GPUMD/NEP, LASP, GemNet-OC, and EquiformerV2 differ. Program operation lives
  in separate `tools/<program>/` skills.
- [vibrational-phonon-analysis.md](vibrational-phonon-analysis.md) — molecular vibrations,
  phonons, imaginary modes, IR/Raman/VDOS, phonon DOS/bands, and force-constant interpretation.
- [thermochemistry-and-free-energy.md](thermochemistry-and-free-energy.md) — electronic energies,
  ZPE, thermal corrections, entropy, smearing free energies, gas/surface/defect references, and
  free-energy expression discipline.
- [excited-state-and-core-spectroscopy.md](excited-state-and-core-spectroscopy.md) — UV-Vis/TDDFT,
  XAS/core spectra, oscillator strengths, SOC, GW/BSE context, broadening, and experiment comparison.
- [molecular-qc-practical-rules.md](molecular-qc-practical-rules.md) — tool-agnostic method-choice
  rules for finite-molecule QC: method/basis, SCF/state validity, stationary points, solvation/BSSE,
  excited states — avoiding common wrong-but-runnable calculations.
- [hubbard-u-and-magnetism.md](hubbard-u-and-magnetism.md) — choosing a Hubbard U value (common
  database/literature sets, when +U applies) and initial magnetic moments/orderings. Engine-specific
  syntax lives in `tools/vasp`, `tools/cp2k`, or the selected code skill.
- [scientific-visualization.md](scientific-visualization.md) — choosing figure tools and
  quality standards: OVITO for structures, PyVista/VESTA for volumetric fields, Matplotlib for
  numerical plots, and the Multiwfn+VMD path for molecule-centered fields (`tools/multiwfn`).
