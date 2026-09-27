# Expected output

This file records the checked invariants and trimmed console output from the command in `README.md`. Grid counts are intentionally omitted because they depend on the requested resolution.

```text
Temperature: 298.15 K; Nernst slope: 0.05915935 V/pH; reference: SHE
States:
  clean: kind=surface, g0=0.00000000 eV, q=0; provided g0_eV
  OH: kind=surface, g0=-0.70000000 eV, q=1; provided g0_eV
  O: kind=surface, g0=0.30000000 eV, q=2; provided g0_eV
  2OH: kind=surface, g0=-0.10000000 eV, q=2; provided g0_eV
  3OH: kind=surface, g0=0.80000000 eV, q=3; provided g0_eV
  M_dissolved: kind=dissolved, g0=-0.50000000 eV, z=2, activity=1; Gion=-5.00000000+2*(-0.25000000)=-5.50000000; L0=-100.00000000+Gion-(-105.00000000)=-0.50000000 eV
```

The run must also:

- report the analytic equations for every phase pair observed across adjacent grid points;
- list `O` as inactive because it is parallel to and higher than `2OH`;
- rank all candidate grand potentials at pH 0, 0 V and pH 7, -0.5 V;
- write a non-empty SVG and a grid CSV with `57 * 91 = 5187` data rows plus one header row.

The dashed water-window lines are contextual overlays and do not alter the selected lower envelope.
