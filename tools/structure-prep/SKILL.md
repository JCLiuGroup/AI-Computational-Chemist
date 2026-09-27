---
name: structure-prep
description: Prepare and convert atomistic structures before calculations. Use for CIF/POSCAR/CONTCAR/XYZ/PDB/MOL/SDF/SMILES handling, supercells, slabs, surface terminations, defects, substitutions, adsorbate placement, symmetry analysis, conformer generation, and charge/multiplicity determination for molecules.
---

# Structure Preparation

Use pymatgen for periodic crystals/slabs/defects and RDKit for finite molecules and
conformers.

## Required inputs

- Source structure or declared database/literature/manuscript evidence from which to
  build it, plus provenance.
- Requested operation and the scientific choices it introduces: cell/facet,
  termination, site, defect, coverage, conformer, or periodicity.
- For molecules, explicit charge and multiplicity with their origin.

## Route map

| Need | Load or run |
|---|---|
| source, convert, build, or edit structures | `references/running.md` |
| validate and release a candidate | `references/validation.md`; `scripts/audit_structure.py` |
| review slab/surface/defect/adsorbate models | `procedures/research-orchestrator/references/model-structure-review.md` |
| build slabs or enumerate adsorbate sites | `scripts/make_slab.py`; `scripts/place_adsorbate.py` |
| make substitutions, vacancies, or interstitials | `scripts/dope_structure.py` |
| convert formats or generate a molecular conformer | `scripts/convert_structure.py`; `scripts/smiles_to_xyz.py` |
| troubleshoot geometry, symmetry, disorder, or embedding | `references/errors.md` |
| consult upstream tools and databases | `references/resources.md` |

## Workflow

1. Search only the project root/current working directory and user-explicit paths for
   supplied structures. Otherwise declare the source and every reconstruction
   assumption.
2. Enumerate scientifically distinct candidates where termination, site, defect, or
   conformer is unresolved; write derived structures to new paths.
3. Validate after each operation. For surface/defect/adsorbate models, run
   `scripts/audit_structure.py` and the model-structure review gate.
4. Release only accepted candidates to the engine skill. Report paths, formula, atom
   count, provenance, and assumptions.

## Hard guardrails

- Never invent lattice vectors, periodicity, atom identities, coordinates, charge, or
  multiplicity.
- Do not silently randomize scientific model choices; enumerate them or record the
  evidence and rationale for one choice.
- Match slab termination, stoichiometry, symmetry/asymmetry, and charge balance to the
  declared chemical environment; disclose polarity, dipole, and correction risks.
- Treat cell orientation, vacuum, contacts, periodic-image separation, and model cost
  as release-gate checks, using the thresholds and exceptions in
  `references/validation.md`.
- Structure-generation code stops at candidates and audit artifacts. Before engine
  handoff, enforce the boundary with
  `procedures/research-orchestrator/scripts/check_structure_generator_boundary.py
  --forbid-engine-inputs PATH/TO/SCRIPTS`; do not generate final engine/scheduler
  inputs or submit jobs in the same call path.
- Preserve originals. Give database-derived structures their entry ID and every
  derived structure a provenance trail.

## Handoff

Route periodic DFT to `vasp`, molecular QC to `gaussian`, biomolecular/liquid/membrane
MD to `gromacs`, and materials/reactive/MLP MD to `lammps`.
