# Generic surface Pourbaix audit

Demonstrates: a synthetic post-processing fixture with generic oxygenated surface states and one bare `M2+` dissolution channel. It exercises CHE stoichiometry, the signed standard-potential convention, lower-envelope selection, inactive-state reporting, and pointwise audits without encoding a particular material, publication, or research project.

Expected result: the synthetic dissolved-ion reference is constructed with `G(M2+) = G(M_bulk) + 2 U0`, giving `G(M2+) = -5.50000000 eV` and `L0 = -0.50000000 eV`. See `expected-output.md` for the observed boundaries in the requested plotting window.

Runtime: less than 1 s on one CPU core.

Verified: Python 3 standard-library implementation, 2026-08-31, local Linux x86_64 workstation. This is a deterministic software regression fixture, not a DFT calculation or a physically parameterized material model.

Run from the repository root:

```bash
uv run tools/vasp/scripts/surface_pourbaix.py \
  tools/vasp/examples/surface-pourbaix-audit/states.csv \
  --reference SHE --ph-range 0,14 --potential-range=-2.5,2.0 \
  --ph-points 57 --potential-points 91 --water-window \
  --audit 0,0 --audit 7,-0.5 \
  --output-prefix /tmp/surface-pourbaix-audit
```

The command writes `/tmp/surface-pourbaix-audit.svg` and `/tmp/surface-pourbaix-audit-grid.csv`.

Adapt by replacing every synthetic intercept and dissolution-ledger value with values from one consistently normalized calculation set. Add all physically credible configurations and aqueous channels rather than treating this deliberately small fixture as a production phase inventory.
