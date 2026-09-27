# Running VASP Electrochemistry: CHE Inputs, VASPsol, VASPsol++

> Load this when: using VASP outputs to assemble CHE step diagrams or surface Pourbaix diagrams, preparing VASP calculations for electrochemical intermediates and dissolution states, or setting up VASPsol/VASPsol++ implicit-solvent and constant-potential calculations. The model equations and interpretation live in `knowledge/electrochemistry.md` and `knowledge/surface-pourbaix.md`.

## Use the knowledge layer first

Before touching INCARs, write the electrochemical cycle from `knowledge/electrochemistry.md`:

- reaction and elementary steps;
- potential scale, SHE or RHE;
- pH and temperature;
- gas/liquid references and corrections;
- adsorbate states and coverage;
- whether the model is vacuum CHE, VASPsol, or VASPsol++ constant potential.

Most routine OER/ORR/HER screening should use CHE only. VASPsol/VASPsol++ is for cases where solvent, electrolyte, charge, field, or true potential control matters.

## VASP calculations for CHE step diagrams

Run the same slab model for all adsorbate states:

```text
*      clean surface
*OH    hydroxyl intermediate
*O     oxo intermediate
*OOH   hydroperoxyl intermediate
*H     hydrogen intermediate for HER
```

Rules:

- identical functional, PAW set, ENCUT, k-point density, smearing, spin/U policy, dispersion, dipole/solvation settings, slab cell, vacuum, fixed layers, and convergence thresholds;
- relax each state consistently, then run a final static calculation for the reported energy;
- keep adsorbate coverage/site definition constant unless deliberately comparing different mechanisms;
- add adsorbate vibrational corrections when reporting free energies rather than electronic energies;
- do not use unconverged relaxations, smoke-test energies, or mixed solvent/vacuum states in one CHE expression.

Gas/liquid references should be computed or imported with the same DFT convention and documented thermochemical corrections. For OER/ORR, back-calculate O2 from H2O/H2 and 4.92 eV unless intentionally using a different thermodynamic cycle.

In the tables below, `DeltaG correction` is the free-energy correction added to the VASP electronic energy. For isolated molecules such as H2, H2O, O2, CO, or CO2, first run a molecular frequency calculation, then use VASPKIT task 502 to obtain temperature- and pressure-dependent thermodynamic corrections. For surface adsorbates such as `*OH`, `*O`, `*OOH`, or `*H`, run a slab frequency calculation with the slab atoms fixed and only the adsorbate/reacting atoms mobile, then use VASPKIT task 501 for the adsorbate vibrational free-energy correction. See `knowledge/thermochemistry-and-free-energy.md` for the thermodynamic bookkeeping and `tools/vaspkit/references/thermochemistry.md` for the VASPKIT 501/502 workflow.

Do not apply gas-phase translational/rotational entropy to a bound adsorbate. Treat adsorbate translations/rotations as frustrated vibrations unless a deliberately different model is documented.

## VASP calculation set for a surface Pourbaix diagram

Read `knowledge/surface-pourbaix.md` and balance every candidate state before launching calculations. A minimal calculation set normally contains:

```text
clean slab                    common surface reference
each adsorbate/coverage       several plausible sites and arrangements
each reconstructed surface   if reconstruction is chemically credible
each residual slab            after removing a dissolving surface atom
elemental bulk metal          converged energy per atom
H2 and H2O references         one documented thermochemical convention
frequency calculations        adsorbate/local modes used in corrections
```

Use the same surface cell and normalize all reported intercepts to the same cell, face, or number of active sites. Keep the functional, PAW datasets, ENCUT, k-point density, spin/U policy, dispersion, solvation, dipole treatment, fixed layers, and convergence thresholds consistent across every term in an energy expression. A residual slab after dissolution must be relaxed as its own state; subtracting an atomic energy from the intact slab is not a vacancy calculation.

For each nominal coverage, optimize multiple arrangements when the surface permits them. Preserve the VASP directory and a ledger containing:

- state name, composition relative to the clean slab, adsorption site, and coverage;
- final electronic energy and convergence evidence;
- ZPE, thermal, entropy, solvation, and standard-state corrections as separate fields;
- final standard intercept `g0_eV` on the declared normalization basis;
- source and conditions for each aqueous-ion standard reduction potential and activity.

For bare dissolution `M^(z+) + z e- -> M(bulk)`, form the ion reference with

```text
G_ion^0 = G_bulk_per_atom + z * U0
L0      = G_residual_slab + G_ion^0 - G_supported_slab
```

when energies are in eV and `U0` is in V versus SHE. Do not change the plus sign based on whether the numerical value of `U0` is positive or negative. More complicated hydrolysis or complexation reactions require explicitly balanced reservoirs and are outside the bare-ion shortcut.

Assemble the corrected intercepts in CSV and run the deterministic helper:

```bash
uv run tools/vasp/scripts/surface_pourbaix.py states.csv \
  --reference SHE --ph-range 0 14 --potential-range -2.5 2.0 \
  --water-window --audit 0,0 --audit 7,-0.5 \
  --output-prefix pourbaix
```

The script writes an SVG, a pointwise phase-grid CSV, analytic equations for the boundaries observed on the grid, inactive-state warnings, and selected-point energy audits. For a dissolved row, either provide a preassembled `g0_eV=L0`, or leave it blank and provide `residual_g_eV`, `supported_g_eV`, `bulk_g_eV`, `standard_potential_V`, and `z`; the latter route makes the ion-reference sign auditable. The helper covers CHE `*O_mH_n` states and bare-ion dissolution. It does not balance reactions, generate missing surface configurations, or perform full aqueous speciation.

## `oer.xlsx`-style assembly

A representative OER assembly uses these references at 298.15 K:

| Species | Pressure | E_DFT (eV) | DeltaG correction (eV) | G (eV) |
|---|---:|---:|---:|---:|
| H2(g) | 1 bar | -6.76 | -0.045 | -6.80 |
| H2O(l), via 0.035 bar vapor | 0.035 bar | -14.22 | -0.001 | -14.22 |
| O2(g), back-calculated | 1 bar | not used | not used | -9.92 |

Example surface/intermediate values:

| State | Electronic E (eV) | Correction (eV) | G_state (eV) | Relative level U=0 (eV) | Level at U=1.23 V (eV) |
|---|---:|---:|---:|---:|---:|
| `* + 2H2O` | -279.084060 | 0.000000 | -279.084060 | 0.000 | 0.000 |
| `*OH + H2O + 1/2H2` | -289.200020 | 0.272014 | -288.928006 | 0.976 | -0.254 |
| `*O + H2O + H2` | -283.839750 | 0.027952 | -283.811798 | 2.692 | 0.232 |
| `*OOH + 3/2H2` | -293.671500 | 0.340296 | -293.331204 | 3.993 | 0.303 |
| `* + O2 + 2H2` | -279.084060 | 0.000000 | -279.084060 | 4.920 | 0.000 |

The resulting U=0 OER steps are:

```text
DG1 = 0.976 eV
DG2 = 1.716 eV
DG3 = 1.301 eV
DG4 = 0.927 eV
eta_OER = max(DGi) - 1.23 = 0.486 V
```

The limiting step is `*OH -> *O + H+ + e-`.

## Traditional VASPsol

Original VASPsol adds implicit solvent/electrolyte corrections to fixed-electron VASP calculations. It requires a VASP build with VASPsol routines.

Recommended workflow:

1. Run the corresponding vacuum calculation first and save `WAVECAR`.
2. Start the solvation calculation from the vacuum wavefunction with `ISTART = 1`.
3. Use `PREC = Accurate` and test `ENCUT`/FFT convergence; cavity/cavitation terms are grid-sensitive.
4. Keep identical solvation settings across all states in one energy expression.

Minimal water-like implicit solvent:

```ini
LSOL   = .TRUE.
EB_K   = 78.4
PREC   = Accurate
ISTART = 1
```

Optional electrolyte model in original VASPsol:

```ini
LSOL       = .TRUE.
LAMBDA_D_K = <Debye length in Angstrom>   # <=0 disables ionic screening
```

Caveats:

- `TAU` changes the effective surface-tension/cavitation contribution and therefore the model.
- For charged/electrolyte calculations, VASP's average electrostatic potential is not automatically the bulk-electrolyte zero. Original VASPsol prints `FERMI_SHIFT`; potential alignment and `Q*V` energy corrections may be needed for charged systems.
- Do not mix vacuum and VASPsol terms in a CHE expression without a written solvation cycle.

## VASPsol NELECT-scan potential workflow

Original VASPsol does not directly hold the electrode at a target potential. A common JACS/JCTC-style workaround is to run a family of fixed-`NELECT` calculations, convert each point to an electrode potential, correct the energy, and fit `E(U)` to a parabola. Use this when reproducing workflows where charge is tuned manually and the implicit electrolyte supplies the compensating charge.

Directory pattern:

```text
pzc/     neutral or reference electron count
m0.5/    NELECT = NELECT_PZC - 0.5
0.5/     NELECT = NELECT_PZC + 0.5
```

Representative INCAR settings:

```ini
LSOL       = T
EB_K       = 78.4
LAMBDA_D_K = 3.04
NELECT     = <NELECT_PZC + dq>
```

Use the same structure, spin setup, solvation tags, smearing, k-points, convergence criteria, and VASP binary for every charge point in one fit. A clean scan should bracket the target potential instead of extrapolating far beyond the computed range.

Extract the final values from each directory:

```bash
grep "E-fermi" OUTCAR | tail -1
grep "FERMI_SHIFT" vasp.out | tail -1
grep "free  energy   TOTEN" OUTCAR | tail -1
grep "F=" vasp.out | tail -1
grep "NELECT" OUTCAR | tail -1
```

Spreadsheet columns for the corrected-energy fit:

```text
q        = NELECT - NELECT_PZC
U_vs_SHE = -(Efermi + FERMI_SHIFT) - 4.44
E_corr   = E_VASP + q*FERMI_SHIFT - q*(Efermi + FERMI_SHIFT)
```

The last formula is the energy in the column used for quadratic fitting. Keep it in this explicit form so the sheet records both `Efermi` and `FERMI_SHIFT`; do not silently change signs when moving between scripts. Use either `TOTEN`, `F`, or `E0` consistently for `E_VASP` and state which one was used.

Fit the corrected energy against potential:

```text
E_corr(U) = a*U^2 + b*U + c
```

or rewrite it as:

```text
E_corr(U) = 0.5*C*(U - U_PZC)^2 + E_PZC
```

For adsorption or reaction energies at constant potential, fit the clean surface and adsorbate state separately, evaluate both fitted curves at the same target `U`, and subtract the fitted energies. This is the role of the fitted adsorption-energy (`Dads`) columns.

Example row pattern from a fixed-charge scan, using `NELECT_PZC = 145.0` and `FERMI_SHIFT` near `0.2149 eV`:

| Directory | q (e) | Efermi (eV) | U vs SHE (V) | E_VASP (eV) | E_corr (eV) |
|---|---:|---:|---:|---:|---:|
| `m1.0` | -1.0 | -5.8052 | 1.1503 | -284.538175 | -290.343375 |
| `m0.5` | -0.5 | -5.1697 | 0.5148 | -286.943651 | -289.528501 |
| `pzc` | 0.0 | -4.7691 | 0.1142 | -289.421874 | -289.421874 |
| `0.5` | 0.5 | -4.2750 | -0.3799 | -291.531195 | -289.393695 |
| `1.0` | 1.0 | -3.5703 | -1.0846 | -293.408965 | -289.838665 |

Validation checks for NELECT scans:

- `U(q)` should be monotonic over the fitted region unless there is a physical transition.
- The same magnetic/electronic state should be tracked; record magnetic moments because spin flips can create multiple parabolas.
- Fit only comparable geometries and adsorption configurations.
- Use enough charge points on both sides of the target potential.
- Keep the SHE reference explicit: the JACS-style workflow above uses `4.44 eV`, while VASPsol++ examples may use a different calibrated absolute SHE value.

## VASPsol++ constant-potential setup

VASPsol++ extends VASPsol with a nonlinear/nonlocal implicit electrolyte model and can run constant-potential calculations by varying electron number. It requires a patched VASP/VASPsol++ build.

Model switch:

```ini
LSOL = .TRUE.
ISOL = 1        # original linear/local VASPsol model
ISOL = 2        # VASPsol++ nonlinear/nonlocal model
```

Aqueous electrolyte starting point for `ISOL = 2`:

```ini
LSOL      = .TRUE.
ISOL      = 2
C_MOLAR   = 1.0       # electrolyte concentration, mol/L
R_ION     = 4.0       # ion radius, Angstrom; set deliberately
SOLTEMP   = 298
```

Constant-potential mode is available only for `ISOL = 2` with ionic screening present (`C_MOLAR > 0`). It is triggered by a negative electron chemical potential relative to vacuum:

```ini
EFERMI_ref      = -4.57    # example only; calibrate for your functional/model
EFERMI_tol      = 1E-5
capacitance_init = 1.0
```

Potential conversion:

```text
EFERMI_ref = epsilon_F,SHE - U_SHE
```

The absolute `epsilon_F,SHE` is not universal. It depends on functional and solvation parameters and should be calibrated for the chosen setup. The VASPsol++ README reports `epsilon_F,SHE = -4.57 eV` for its default aqueous-electrolyte/BEEF-vdW setup and notes this is setup-specific.

Output conventions:

- fixed-electron VASPsol++ free energies include solvation corrections when all states use the same model;
- constant-potential calculations print the grand potential, not a fixed-electron Helmholtz free energy;
- `E0` also carries the solvation/constant-potential corrections and is usually the cleaner electronic-energy-like quantity when removing smearing entropy;
- `LVHAR = .TRUE.` or `LVTOT = .TRUE.` writes potential/cavity/charge-density files such as `PHI`, `PHI_SOLV`, `VSOLV`, `RHOB`, `RHOION`, plus additional `ISOL=2` cavity fields.

## Validation checklist

- Confirm all VASP calculations converged with the same method fingerprint.
- State whether reported energies are vacuum CHE, VASPsol fixed-electron energies, VASPsol NELECT-scan corrected energies, or VASPsol++ grand potentials.
- Record the VASP binary/build and solvation patch/version.
- Record all solvation tags: `LSOL`, `ISOL`, `EB_K`, `LAMBDA_D_K` or `C_MOLAR`, cavity/ion radii, `EFERMI_ref`, and any `FERMI_SHIFT` handling.
- For NELECT scans, archive the charge table, `U_vs_SHE` formula, corrected-energy formula, quadratic coefficients, fitted range, and target-potential evaluation.
- For CHE diagrams, report every step energy, limiting step, limiting potential, overpotential, pH, and SHE/RHE scale.
