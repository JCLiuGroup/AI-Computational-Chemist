> Covers: thermodynamic surface Pourbaix diagrams from consistently referenced free energies, including CHE surface states, dissolution channels, SHE/RHE conversion, water-window overlays, lower-envelope construction, and scientific audit.

# Surface Pourbaix diagrams

A surface Pourbaix diagram assigns the lowest-grand-potential member of a declared set of surface and dissolved states at each pH and electrode potential. It is a thermodynamic model of that candidate set, not a kinetic map and not a complete aqueous-speciation Pourbaix calculation. Missing adsorbate configurations, reconstructions, bulk phases, hydrolyzed ions, or complexes can change the apparent stable region.

## Declare the model before calculating

Record:

- temperature, pressure, gas standard states, water convention, and aqueous activities;
- potential scale (SHE or RHE) and the sign convention for electron chemical potential;
- surface cell and normalization (per cell, per face, per active site, or per metal atom);
- all allowed adsorbates, coverages, protonation states, vacancies, reconstructions, and dissolution products;
- whether solvation, electric-field, double-layer, configurational-entropy, or constant-potential effects are included.

Compare only states normalized to the same surface composition basis. A label such as `2OH` is not a unique phase: optimize several plausible arrangements at each coverage, retain their provenance, and either use the lowest free energy or include configurational statistics explicitly.

## Free-energy ledger

Keep electronic energies and corrections in separate columns:

\[
G_i(T)=E_{\mathrm{DFT},i}+E_{\mathrm{ZPE},i}+\Delta H_i(T)-TS_i(T)
+\Delta G_{i,\mathrm{solv}}+\Delta G_{i,\mathrm{other}}.
\]

Use one internally consistent electronic-structure setup for the clean surface, all adsorbed states, every residual surface after dissolution, elemental bulk references, and molecular reservoirs. State which atoms and modes enter adsorbate vibrational corrections. Do not apply gas-phase translational and rotational entropy to a bound adsorbate without a declared model.

For water, use a documented liquid-water convention. Examples include gas-phase molecular thermochemistry followed by a condensation/standard-state correction, a validated method-specific liquid-water correction, or a consistent experimental thermochemical cycle. An isolated-water electronic energy is not silently interchangeable with \(G_{H_2O(l)}\).

General free-energy bookkeeping is in `knowledge/thermochemistry-and-free-energy.md`; slab and coverage thermodynamics are in `knowledge/surface-thermodynamics.md`.

## Computational hydrogen electrode

For

\[
H^+ + e^- \rightleftharpoons \tfrac12 H_2,
\]

the computational hydrogen electrode (CHE) gives

\[
\mu_{H^++e^-}(U_{\mathrm{SHE}},\mathrm{pH})
=\tfrac12G_{H_2}-eU_{\mathrm{SHE}}-k_BT\ln(10)\,\mathrm{pH}.
\]

Define

\[
s_T=\frac{k_BT\ln(10)}{e}; \qquad s_{298.15\,\mathrm K}=0.05916\ \mathrm{V\,pH^{-1}}.
\]

The potential scales obey

\[
U_{\mathrm{RHE}}=U_{\mathrm{SHE}}+s_T\,\mathrm{pH}.
\]

Consequently \(\mu_{H^++e^-}=\tfrac12G_{H_2}-eU_{\mathrm{RHE}}\). Do not add a separate pH term when a CHE expression is already written versus RHE.

## Oxygenated and hydrogenated surface states

Represent a state as \(*O_mH_n\), where \(m\) and \(n\) count atoms added to the clean reference, and define

\[
q=2m-n.
\]

Using

\[
*+mH_2O(l)\rightarrow *O_mH_n+q(H^++e^-),
\]

the standard formation free energy at \(U_{\mathrm{SHE}}=0\) and pH 0 is

\[
\Delta G_{m,n}^{0}
=G_{*O_mH_n}+\frac q2G_{H_2}-G_*-mG_{H_2O(l)}.
\]

The surface grand potential is

\[
\boxed{\Omega_{m,n}(U_{\mathrm{SHE}},\mathrm{pH})
=\Delta G_{m,n}^{0}-q\left[eU_{\mathrm{SHE}}+k_BT\ln(10)\,\mathrm{pH}\right].}
\]

When free energies are in eV and potential is in V, \(eU\) is numerically \(U\) eV per transferred electron. The expression also covers hydrogen-only states: \(m=0,n>0\) gives \(q<0\).

For states \(i\) and \(j\), with \(q_i\ne q_j\),

\[
U_{\mathrm{SHE}}
=\frac{\Delta G_i^0-\Delta G_j^0}{q_i-q_j}-s_T\,\mathrm{pH}.
\]

States with the same \(q\) have identical pH/potential slopes; only the one with the lowest intercept can reach the lower envelope.

## Dissolution and aqueous activity

For the standard reduction reaction

\[
M^{z+}(aq)+ze^-\rightleftharpoons M(\mathrm{bulk}),
\]

use a standard reduction potential \(U^0\) on the same SHE scale. With \(\mu_e=-eU\), equilibrium at \(U^0\) gives

\[
\boxed{G_{M^{z+}}^0=G_{M,\mathrm{bulk}}+zeU^0.}
\]

The plus sign is an important audit invariant. A formula containing a minus sign but also inserting a signed negative reduction potential is not a consistent general convention.

At activity \(a_{M^{z+}}\),

\[
G_{M^{z+}}=G_{M^{z+}}^0+k_BT\ln a_{M^{z+}}.
\]

For bare dissolution of a supported atom,

\[
M/*\rightarrow *_{\mathrm{vac}}+M^{z+}(aq)+ze^-,
\]

define

\[
L^0=G_{*_{\mathrm{vac}}}+G_{M^{z+}}^0-G_{M/*},
\]

and

\[
\boxed{\Omega_{\mathrm{diss}}(U_{\mathrm{SHE}})
=L^0+k_BT\ln a_{M^{z+}}-zeU_{\mathrm{SHE}}.}
\]

This is a special case with no proton in the dissolution reaction. Hydrolysis, oxide formation, ligand complexation, or proton-coupled dissolution requires a separately balanced reaction and the chemical potential/activity of every additional species. Do not represent a complex aqueous phase diagram with a single bare-ion line unless that approximation is explicitly intended.

For bare dissolution against a surface state \(*O_mH_n\), let \(L_a=L^0+k_BT\ln a\). If \(z\ne q\), their boundary is

\[
U_{\mathrm{SHE}}
=\frac{L_a-\Delta G_{m,n}^0}{z-q}
+\frac{q}{z-q}s_T\,\mathrm{pH}.
\]

If \(z=q\), potential cancels and the boundary, when it exists, is vertical in pH. For multicomponent surfaces, calculate each allowed dissolution channel with its own relaxed residual surface and aqueous product.

## Water stability window

At 298.15 K under the usual unit-activity/unit-fugacity conventions, the equilibrium water limits versus SHE are approximately

\[
U_{\mathrm{HER}}=-0.05916\,\mathrm{pH},\qquad
U_{\mathrm{OER}}=1.229-0.05916\,\mathrm{pH}.
\]

Versus RHE they are 0 and 1.229 V. Plot these as contextual overlays, not as phase-selection constraints: kinetics, overpotential, metastability, and gas activities determine whether a real interface persists outside the equilibrium window.

## Lower-envelope construction and audit

1. Assemble a machine-readable table of state, kind, stoichiometry, standard intercept, normalization, activity, corrections, and provenance.
2. Evaluate every candidate grand potential on the requested pH/potential grid.
3. Assign the lowest value at each point; retain unrounded values for comparisons.
4. Independently derive pairwise analytic boundaries and verify grid transitions against equality of adjacent states.
5. Print all competing energies at selected audit points.
6. Report candidates that never reach the lower envelope; do not silently delete them.
7. Repeat near important boundaries with plausible energy perturbations or confidence intervals. A crisp color boundary is not evidence of sub-0.01 eV certainty.

The helper `tools/vasp/scripts/surface_pourbaix.py` performs this lower-envelope and sign-audit step for CHE surface states plus bare-ion dissolution channels. It does not replace reaction balancing or aqueous-speciation software.

## Interpretation limits

- Stable means lowest grand potential among the declared candidates, not necessarily experimentally observable.
- Dissolution barriers, adsorption barriers, reconstruction kinetics, mass transport, hysteresis, and finite-current effects are absent.
- CHE does not by itself include field-dependent adsorption, double-layer charging, or state-specific capacitance. Constant-potential calculations can improve those terms but must not be mixed with CHE corrections without a written thermodynamic cycle.
- Candidate completeness usually matters more than plotting resolution. Test alternative sites, coverages, magnetic states, residual surfaces, ions, and complexes appropriate to the chemistry.
- Report the energy ledger, equations, potential scale, activities, inactive states, selected-point audits, and limitations with the final diagram.
