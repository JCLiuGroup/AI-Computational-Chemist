# Running Structure Preparation: pymatgen and RDKit Workflows

> Load this when: building, converting, or manipulating structures — slabs, supercells, defects, adsorbates, conformers, format conversion.

## Periodic structures (pymatgen)

1. Read and validate (see validation.md), 2. operate, 3. write outputs and report species ordering (critical for POTCAR consistency).

## Initial-Structure Discovery Scope

Before self-building, check only the project-local input scope:

- the current project root or current working directory;
- obvious project subdirectories such as `inputs/`, `input/`, `structures/`, `models/`,
  `work/structures/`, and `work/models/`;
- files or directories explicitly named by the user, a task input, or `.research`
  artifact/path metadata.

Use bounded listing/search commands from that scope, for example `rg --files` or
`find . -maxdepth 3` with structure suffixes such as `POSCAR`, `CONTCAR`, `*.vasp`,
`*.cif`, `*.xyz`, `*.pdb`, `*.mol`, and `*.sdf`. Do not search `$HOME`, `/home`,
`/opt`, `/`, shared software trees, scratch roots, or unrelated archives for hidden
structures. If no usable structure is found in the bounded project-local scope, record
`initial-structure-decision: not_supplied` and build the model from declared database,
literature, manuscript, or builder assumptions.

Key APIs and conventions:

- **Symmetry**: `SpacegroupAnalyzer(structure, symprec=1e-3)` — report the space group *with* the symprec used; choose primitive vs conventional cell deliberately and say which.
- **Slabs**: `pymatgen.core.surface.SlabGenerator(bulk, miller_index, min_slab_size, min_vacuum_size, center_slab=True, primitive=False, max_normal_search=max(abs(h), abs(k), abs(l), 1), reorient_lattice=True)`. Prefer a conventional input cell for surface cuts; do not let pymatgen reduce to a primitive cell unless there is a recorded reason. `max_normal_search` asks pymatgen to choose the most normal available `c` vector during slab construction; keep it modest because the resulting cell may not be the smallest simulation cell. Enumerate terminations with `get_slabs()`; when more than one is plausible, that's a scientific choice — ask or follow the source paper, never pick silently. Vacuum >= 12 A neutral, around 15 A with adsorbates/dipoles unless a convergence or electrostatic rationale requires more; avoid excessive vacuum because it enlarges the FFT/grid volume without adding surface physics.
- **Keep the slab `c` vector normal to the surface plane when possible**: after any slab cut, conversion, rotation, centering, or vacuum edit, check that `c` is perpendicular to both `a` and `b` (`alpha` and `beta` near 90 deg). A tilted `c` makes c-axis vacuum and layer-order checks easy to misread and can indicate that pymatgen generated or preserved an oblique cell for the requested Miller cut. Do not fix this by first hard-rotating or orthogonalizing the finished slab. Re-check whether the input was conventional, whether `SlabGenerator` used `primitive=False` and a suitable `max_normal_search`, and whether the Miller index/surface normal is the intended one. Use `Slab.get_orthogonal_c_slab()` only as an explicit fallback when a downstream interface/post-processing workflow truly requires orthogonal `c`; record the reason and rerun the geometry audit because pymatgen notes that it can break slab symmetries.
- **Symmetric slabs are a preference, not an absolute rule**: top/bottom symmetry reduces dipoles and simplifies surface-energy comparisons when it preserves the intended chemistry and cost. If enforcing symmetry would require the wrong termination, duplicate adsorbates on both sides, distort the intended stoichiometry, or make the model too large, use an asymmetric slab instead. Record the top and bottom terminations, whether the slab is polar or carries a net dipole risk, which layers are fixed, the vacuum choice, and whether the downstream engine should use a dipole/electrostatic correction.
- **Stoichiometry follows the oxidation chemistry**: for effectively fixed-valence or non-redox-active components under the modeled condition (for example Al/Mg/Zr/Hf-type cations in their usual oxide environments), the slab or supported model should remain charge-balanced and close to the expected stoichiometry unless an explicit compensating defect, adsorbate, reconstruction, or literature precedent is part of the model. For redox-active or variable-valence components, exact bulk stoichiometry is not always required; oxygen/metal-rich terminations, vacancies, hydroxylation, or other non-stoichiometric models can be defensible when they match the declared synthesis, gas, solvent, electrochemical, oxygen-chemical-potential, or reservoir condition. State the chemical environment and oxidation-state rationale before engine handoff.
- **Lateral cell size for a supported cluster/molecule/dopant**: a 1×1 surface cell is often too small once you load a metal cluster, an adsorbed molecule, or a dopant — the species can interact with its own periodic image. Build a lateral supercell sized so the loaded species *fits with room around it*: aim for a **minimum image separation of ≥ ~5 Å between adsorbate copies** (edge-to-edge) for routine screening, use larger separations when long-range lateral interactions or coverage-sensitive energetics matter, and verify with PBC on (`structure.get_all_neighbors`) that the adsorbate does not see an unintended neighbor. Separations below ~5 Å are not automatically invalid, but they require an explicit finite-size/coverage and computational-cost justification. Pick the in-plane multiplicity from the footprint of what you're loading, not from the bare-slab default. (Reported coverage/energetics depend on this — too small a cell silently inflates lateral interactions.)
- **Computational economy is part of the model review**: larger is not automatically better. Atom counts above roughly 200 should trigger an economy review, and models above roughly 300 atoms or lattice lengths above roughly 30 Å need a clear scientific reason or a cheaper alternative. Balance finite-size error, coverage realism, wall time, and the number of candidate structures before release.
- **Pick terminations by coordination signature, never by list index**: for each `get_slabs()` shift, check the topmost atoms' coordination numbers against the known stable termination (e.g. anatase(101): 2-coordinate O over 5-coordinate Ti). The first non-polar stoichiometric slab in the list is often a wrong cut that only reveals itself after a wasted relaxation.
- **`get_slabs()` enumerates symmetric/stoichiometric cuts only — it is not the full set of physical terminations.** Polar or *non-stoichiometric* terminations (e.g. an ABX₃ perovskite's BX₂ surface, a metal- or O-terminated binary oxide, a hydroxylated or reconstructed face) are frequently **not** returned. Build those by hand: cut a stoichiometric slab, then delete/add the surface layer to the intended termination and re-apply vacuum, and verify the resulting top-layer coordination. Don't treat the `get_slabs()` list as exhaustive when the decisive surface is non-stoichiometric.
- **"N-layer slab" in papers is ambiguous** (trilayers vs atomic planes vs d-spacings). Verify by counting metal z-planes and comparing slab thickness to N x d(hkl); don't trust `min_slab_size` to reproduce a paper's model without checking.
- **Selective dynamics**: fix the bottom ~half of slab layers; `scripts/make_slab.py` does it by fractional-coordinate cutoff, prints each termination's **coordination signature + z-layer count** (so you pick by signature per the rule above, not by list index), and refuses to choose among multiple terminations on its own.
- **Adsorbates**: use **`scripts/place_adsorbate.py`** — a runnable wrapper for `pymatgen.analysis.adsorption.AdsorbateSiteFinder` that enumerates the symmetry-distinct ontop/bridge/hollow sites (incl. ontop of a single-atom site on a *relaxed* slab), writes one POSCAR per site with selective dynamics, and reports the nearest adsorbate–surface distance. **Don't hand-roll docking; test multiple sites/orientations — don't assume the first or lowest-coordination site.** A metal atom that ends up singly-coordinated (e.g. Pt bound to one O) may not be the real minimum; a higher metal–O coordination can lower the energy and shift the inferred oxidation state. Relax the candidate sites, check the resulting coordination number, and report which were compared (the multi-start site search).
- **Nearest-contact thresholds are element-pair specific**: after placement,
  compare nearest contacts to Pyykkö/Atsumi single-bond covalent-radius sums
  rather than a fixed number. The radius sum is a reference scale; the default
  audit hard threshold allows about 5% compression:
  `d_ij >= 0.95 * (r_cov(i) + r_cov(j))` (`--contact-radius-scale 0.95`).
  For example, O(0.63 Å) + Pt(1.23 Å) gives a Pt-O radius sum of 1.86 Å and a
  default allowed minimum of 1.77 Å. Contacts between 0.95 and 1.00 times the
  radius sum can pass but are recorded as compressed contacts. If a deliberately
  short multiple bond, TS guess, or constrained starting contact is kept, record
  that rationale.
- **Defects/substitutions**: enumerate symmetry-distinct sites; choose by stated criterion or ask — never randomize for production.
- **Sourcing structures from experiments**: XRD-matched phases resolve to database entries (Materials Project API, COD, ICSD if licensed); record the entry ID as provenance.

Scripts:

```bash
# Run with `uv run` — these scripts carry inline PEP 723 deps (pymatgen), so uv
# resolves an isolated, cached env; no global pymatgen install required.
uv run scripts/make_slab.py BULK h k l --min-slab 10 --min-vacuum 15 --fix-below 0.5 [--termination N]
#   lists terminations with coordination signature + z-layers; choose --termination by signature.
#   uses SlabGenerator(..., primitive=False, max_normal_search=auto, reorient_lattice=True).
#   warns if c is not approximately perpendicular to a/b; re-check conventional-cell input
#   and the Miller cut before any post-hoc hard rotation/orthogonalization. Use
#   --orthogonal-c-reason TEXT only when forced orthogonal c is explicitly justified.
#   e.g. anatase(101): pick the cut whose top is 2-coordinate O over 5-coordinate Ti (`O(2c)`, `Ti(5c)`).
uv run scripts/place_adsorbate.py SLAB ADSORBATE [--height 2.0] [--sites all|ontop|bridge|hollow] [--fix-below 0.45]
#   ADSORBATE = element symbol (H/O/N/...) or an .xyz file. Writes ads00/ ads01/ ... one POSCAR per
#   distinct site (selective dynamics set) + the nearest adsorbate-surface distance. Relax all, compare.
uv run scripts/audit_structure.py ads00/POSCAR --adsorbate-count 1 --json ads00/structure-audit.json
#   deterministic release-gate summary: a/b/c, slab thickness, vacuum estimate, selective dynamics,
#   c-axis orthogonality to a/b, closest PBC pairs with covalent-radius thresholds/margins,
#   adsorbate-surface distance, and adsorbate-image distance. For molecule/cluster adsorbates
#   use --adsorbate-count N or --adsorbate-indices 73-84.
uv run scripts/convert_structure.py IN OUT [--primitive|--conventional]
# one explicit edit per call (chain for several): substitution / vacancy / interstitial.
# "top" = largest Cartesian z. The site is a scientific choice — this only performs the edit.
uv run scripts/dope_structure.py STRUCT --substitute-top Fe:Pt        # topmost Fe -> Pt single atom
uv run scripts/dope_structure.py STRUCT --vacancy-top O               # surface O vacancy
uv run scripts/dope_structure.py STRUCT --interstitial Na:0.5,0.5,0.45 # subsurface Na dopant (frac coords)
uv run scripts/dope_structure.py STRUCT --substitute 17:Pt            # replace atom #17 (1-based) with Pt
```

## Molecules (RDKit)

1. Parse SMILES/SDF/MOL/XYZ; check valence, formal charge, fragments, stereochemistry. Keep salts/fragments unless told otherwise — never drop silently.
2. Embed 3D: `AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())`, then MMFF94 (fallback UFF) cleanup.
3. Conformers for flexible molecules: `EmbedMultipleConfs` with `numConfs` 20–200 scaled by rotatable bonds; MMFF-rank; report the energy spread. One conformer is a guess, not sampling — say so.
4. Charge/multiplicity for downstream QC: formal charge from the graph; multiplicity = unpaired electrons + 1. Open-shell species, radicals, TM complexes: do not guess — ask or derive from the source.

```bash
uv run scripts/smiles_to_xyz.py "SMILES" out.xyz [--confs N]   # 3D + charge/multiplicity report (inline rdkit dep)
```
