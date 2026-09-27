#!/usr/bin/env python3
"""Construct and audit a thermodynamic surface Pourbaix lower envelope.

The input CSV represents CHE surface states (*O_mH_n) and optional bare-ion
dissolution states.  This helper deliberately uses only the Python standard
library so the thermodynamic bookkeeping remains easy to inspect.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path


KB_EV = 8.617333262145e-5
LN10 = math.log(10.0)
PALETTE = (
    "#dcefd1",
    "#e8b6bd",
    "#f2c46d",
    "#a69bd3",
    "#c9d9f0",
    "#f4f0dc",
    "#b8dfd8",
    "#e3c6ee",
    "#f4d2ad",
    "#cad0d8",
)


@dataclass(frozen=True)
class State:
    name: str
    kind: str
    g0: float
    m_o: int | None
    n_h: int | None
    z: int | None
    activity: float
    color: str
    derivation: str

    @property
    def q(self) -> int:
        if self.kind != "surface" or self.m_o is None or self.n_h is None:
            raise ValueError(f"state {self.name!r} has no CHE q coefficient")
        return 2 * self.m_o - self.n_h

    def coefficients(self, temperature: float, reference: str) -> tuple[float, float, float]:
        """Return intercept, U coefficient, and pH coefficient in eV."""
        slope = KB_EV * temperature * LN10
        if self.kind == "surface":
            q = self.q
            if reference == "SHE":
                return self.g0, -float(q), -float(q) * slope
            return self.g0, -float(q), 0.0

        assert self.z is not None
        intercept = self.g0 + KB_EV * temperature * math.log(self.activity)
        if reference == "SHE":
            return intercept, -float(self.z), 0.0
        return intercept, -float(self.z), float(self.z) * slope

    def omega(self, potential: float, ph: float, temperature: float, reference: str) -> float:
        intercept, u_coeff, ph_coeff = self.coefficients(temperature, reference)
        return intercept + u_coeff * potential + ph_coeff * ph


def parse_float(row: dict[str, str], key: str, *, required: bool = False) -> float | None:
    value = (row.get(key) or "").strip()
    if not value:
        if required:
            raise ValueError(f"missing {key}")
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"invalid {key}={value!r}") from exc


def parse_int(row: dict[str, str], key: str, *, required: bool = False) -> int | None:
    value = parse_float(row, key, required=required)
    if value is None:
        return None
    integer = int(value)
    if value != integer:
        raise ValueError(f"{key} must be an integer, got {value}")
    return integer


def read_states(path: Path) -> list[State]:
    states: list[State] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required_headers = {"state", "kind"}
        missing = required_headers - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")

        for line_number, row in enumerate(reader, start=2):
            try:
                name = (row.get("state") or "").strip()
                if not name:
                    raise ValueError("missing state")
                kind = (row.get("kind") or "").strip().lower()
                if kind not in {"surface", "dissolved"}:
                    raise ValueError("kind must be 'surface' or 'dissolved'")
                color = (row.get("color") or "").strip() or PALETTE[len(states) % len(PALETTE)]
                if not color.startswith("#") or len(color) not in {4, 7}:
                    raise ValueError("color must be an SVG hex color such as #dcefd1")

                if kind == "surface":
                    g0 = parse_float(row, "g0_eV", required=True)
                    assert g0 is not None
                    m_o = parse_int(row, "m_O", required=True)
                    n_h = parse_int(row, "n_H", required=True)
                    assert m_o is not None and n_h is not None
                    if m_o < 0 or n_h < 0:
                        raise ValueError("m_O and n_H must be non-negative")
                    states.append(State(name, kind, g0, m_o, n_h, None, 1.0, color, "provided g0_eV"))
                    continue

                z = parse_int(row, "z", required=True)
                assert z is not None
                if z <= 0:
                    raise ValueError("z must be positive")
                activity = parse_float(row, "activity") or 1.0
                if activity <= 0:
                    raise ValueError("activity must be positive")
                g0 = parse_float(row, "g0_eV")
                if g0 is not None:
                    derivation = "provided L0 as g0_eV"
                else:
                    residual = parse_float(row, "residual_g_eV", required=True)
                    supported = parse_float(row, "supported_g_eV", required=True)
                    bulk = parse_float(row, "bulk_g_eV", required=True)
                    u0 = parse_float(row, "standard_potential_V", required=True)
                    assert residual is not None and supported is not None and bulk is not None and u0 is not None
                    ion = bulk + z * u0
                    g0 = residual + ion - supported
                    derivation = (
                        f"Gion={bulk:.8f}+{z}*({u0:.8f})={ion:.8f}; "
                        f"L0={residual:.8f}+Gion-({supported:.8f})={g0:.8f} eV"
                    )
                states.append(State(name, kind, g0, None, None, z, activity, color, derivation))
            except ValueError as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc

    if not states:
        raise ValueError("CSV contains no states")
    names = [state.name for state in states]
    if len(names) != len(set(names)):
        raise ValueError("state names must be unique")
    if not any(state.kind == "surface" for state in states):
        raise ValueError("at least one surface state is required")
    return states


def linspace(low: float, high: float, points: int) -> list[float]:
    if points < 2:
        raise ValueError("grid dimensions must be at least 2")
    return [low + index * (high - low) / (points - 1) for index in range(points)]


def stable_index(states: list[State], potential: float, ph: float, temperature: float, reference: str) -> tuple[int, float]:
    values = [state.omega(potential, ph, temperature, reference) for state in states]
    index = min(range(len(states)), key=lambda item: (values[item], item))
    return index, values[index]


def build_grid(
    states: list[State],
    ph_values: list[float],
    potential_values: list[float],
    temperature: float,
    reference: str,
) -> tuple[list[list[int]], list[list[float]]]:
    indices: list[list[int]] = []
    energies: list[list[float]] = []
    for potential in potential_values:
        index_row: list[int] = []
        energy_row: list[float] = []
        for ph in ph_values:
            index, energy = stable_index(states, potential, ph, temperature, reference)
            index_row.append(index)
            energy_row.append(energy)
        indices.append(index_row)
        energies.append(energy_row)
    return indices, energies


def observed_pairs(grid: list[list[int]]) -> set[tuple[int, int]]:
    pairs: set[tuple[int, int]] = set()
    rows = len(grid)
    columns = len(grid[0])
    for row in range(rows):
        for column in range(columns):
            here = grid[row][column]
            if row + 1 < rows and grid[row + 1][column] != here:
                pairs.add(tuple(sorted((here, grid[row + 1][column]))))
            if column + 1 < columns and grid[row][column + 1] != here:
                pairs.add(tuple(sorted((here, grid[row][column + 1]))))
    return pairs


def boundary_equation(first: State, second: State, temperature: float, reference: str) -> str:
    b1, u1, p1 = first.coefficients(temperature, reference)
    b2, u2, p2 = second.coefficients(temperature, reference)
    du = u1 - u2
    dp = p1 - p2
    db = b1 - b2
    if abs(du) > 1e-14:
        intercept = -db / du
        slope = -dp / du
        return f"U_{reference} = {intercept:.8f} {slope:+.8f}*pH"
    if abs(dp) > 1e-14:
        ph = -db / dp
        return f"pH = {ph:.8f} (potential-independent)"
    if abs(db) < 1e-12:
        return "degenerate: identical grand-potential planes"
    return "parallel: no boundary"


def write_grid_csv(
    path: Path,
    states: list[State],
    ph_values: list[float],
    potential_values: list[float],
    grid: list[list[int]],
    energies: list[list[float]],
    reference: str,
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["pH", f"U_{reference}_V", "stable_state", "omega_eV"])
        for row, potential in enumerate(potential_values):
            for column, ph in enumerate(ph_values):
                writer.writerow(
                    [f"{ph:.8f}", f"{potential:.8f}", states[grid[row][column]].name, f"{energies[row][column]:.10f}"]
                )


def svg_text(x: float, y: float, value: str, size: int = 14, anchor: str = "middle", weight: str = "normal") -> str:
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" '
        f'font-family="Arial, sans-serif" font-size="{size}" font-weight="{weight}" '
        f'fill="#222">{escape(value)}</text>'
    )


def write_svg(
    path: Path,
    states: list[State],
    ph_values: list[float],
    potential_values: list[float],
    grid: list[list[int]],
    reference: str,
    temperature: float,
    water_window: bool,
) -> None:
    width, height = 900, 650
    x0, y0, plot_w, plot_h = 105.0, 70.0, 620.0, 500.0
    ph_min, ph_max = ph_values[0], ph_values[-1]
    u_min, u_max = potential_values[0], potential_values[-1]
    columns, rows = len(ph_values), len(potential_values)
    dx, dy = plot_w / columns, plot_h / rows
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<defs><clipPath id="plot"><rect x="105" y="70" width="620" height="500"/></clipPath></defs>',
        svg_text(width / 2, 32, "Surface Pourbaix lower envelope", 22, weight="bold"),
    ]

    for column in range(columns):
        last = None
        run_start = 0
        # SVG runs top-to-bottom, so traverse the potential grid in reverse.
        top_down = [grid[rows - 1 - row][column] for row in range(rows)]
        for row, state_index in enumerate(top_down + [-1]):
            if last is None:
                last = state_index
                run_start = row
            elif state_index != last:
                out.append(
                    f'<rect x="{x0 + column * dx:.3f}" y="{y0 + run_start * dy:.3f}" '
                    f'width="{dx + 0.2:.3f}" height="{(row - run_start) * dy + 0.2:.3f}" '
                    f'fill="{states[last].color}" shape-rendering="crispEdges"/>'
                )
                last = state_index
                run_start = row

    def map_x(ph: float) -> float:
        return x0 + (ph - ph_min) / (ph_max - ph_min) * plot_w

    def map_y(potential: float) -> float:
        return y0 + (u_max - potential) / (u_max - u_min) * plot_h

    if water_window:
        nernst = KB_EV * temperature * LN10
        if reference == "SHE":
            her = (-nernst * ph_min, -nernst * ph_max)
            oer = (1.229 - nernst * ph_min, 1.229 - nernst * ph_max)
        else:
            her = (0.0, 0.0)
            oer = (1.229, 1.229)
        out.append('<g clip-path="url(#plot)" fill="none" stroke="#222" stroke-width="1.5" stroke-dasharray="7 5">')
        for first, second in (her, oer):
            out.append(f'<line x1="{map_x(ph_min):.2f}" y1="{map_y(first):.2f}" x2="{map_x(ph_max):.2f}" y2="{map_y(second):.2f}"/>')
        out.append("</g>")

    out.append(f'<rect x="{x0}" y="{y0}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#222" stroke-width="1.5"/>')
    for index in range(8):
        ph = ph_min + index * (ph_max - ph_min) / 7
        x = map_x(ph)
        out.append(f'<line x1="{x:.2f}" y1="{y0 + plot_h:.2f}" x2="{x:.2f}" y2="{y0 + plot_h + 5:.2f}" stroke="#222"/>')
        out.append(svg_text(x, y0 + plot_h + 22, f"{ph:g}", 12))
    for index in range(7):
        potential = u_min + index * (u_max - u_min) / 6
        y = map_y(potential)
        out.append(f'<line x1="{x0 - 5:.2f}" y1="{y:.2f}" x2="{x0:.2f}" y2="{y:.2f}" stroke="#222"/>')
        out.append(svg_text(x0 - 9, y + 4, f"{potential:.2f}", 12, "end"))
    out.append(svg_text(x0 + plot_w / 2, y0 + plot_h + 48, "pH", 15))
    out.append(
        f'<text x="42" y="{y0 + plot_h / 2:.2f}" text-anchor="middle" font-family="Arial, sans-serif" '
        f'font-size="15" fill="#222" transform="rotate(-90 42 {y0 + plot_h / 2:.2f})">U vs {reference} (V)</text>'
    )

    active = sorted(set(item for row in grid for item in row))
    legend_x, legend_y = 755.0, 90.0
    out.append(svg_text(legend_x, legend_y - 18, "Stable phases", 15, "start", "bold"))
    for offset, index in enumerate(active):
        y = legend_y + offset * 27
        out.append(f'<rect x="{legend_x}" y="{y}" width="18" height="14" fill="{states[index].color}" stroke="#666"/>')
        out.append(svg_text(legend_x + 26, y + 12, states[index].name, 12, "start"))
    if water_window:
        y = legend_y + len(active) * 27 + 12
        out.append(f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 20}" y2="{y}" stroke="#222" stroke-width="1.5" stroke-dasharray="7 5"/>')
        out.append(svg_text(legend_x + 26, y + 4, "water limits", 12, "start"))
    out.append("</svg>")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def parse_pair(value: str, option: str) -> tuple[float, float]:
    try:
        first, second = value.split(",", maxsplit=1)
        return float(first), float(second)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{option} requires two comma-separated numbers") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--output-prefix", type=Path, default=Path("surface-pourbaix"))
    parser.add_argument("--temperature", type=float, default=298.15)
    parser.add_argument("--reference", choices=("SHE", "RHE"), default="SHE")
    parser.add_argument("--ph-range", default="0,14", help="minimum,maximum")
    parser.add_argument("--potential-range", default="-2.5,2.0", help="minimum,maximum in V")
    parser.add_argument("--ph-points", type=int, default=281)
    parser.add_argument("--potential-points", type=int, default=181)
    parser.add_argument("--audit", action="append", default=[], metavar="PH,U", help="print all state energies at this point; repeatable")
    parser.add_argument("--water-window", action="store_true", help="overlay equilibrium HER/OER lines")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.temperature <= 0:
            raise ValueError("temperature must be positive")
        ph_min, ph_max = parse_pair(args.ph_range, "--ph-range")
        u_min, u_max = parse_pair(args.potential_range, "--potential-range")
        if ph_min >= ph_max or u_min >= u_max:
            raise ValueError("range minima must be smaller than maxima")
        audits = [parse_pair(item, "--audit") for item in args.audit]
        states = read_states(args.input_csv)
        ph_values = linspace(ph_min, ph_max, args.ph_points)
        potential_values = linspace(u_min, u_max, args.potential_points)
        grid, energies = build_grid(states, ph_values, potential_values, args.temperature, args.reference)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    prefix = args.output_prefix
    prefix.parent.mkdir(parents=True, exist_ok=True)
    svg_path = prefix.with_suffix(".svg")
    grid_path = prefix.with_name(prefix.name + "-grid").with_suffix(".csv")
    write_svg(svg_path, states, ph_values, potential_values, grid, args.reference, args.temperature, args.water_window)
    write_grid_csv(grid_path, states, ph_values, potential_values, grid, energies, args.reference)

    slope = KB_EV * args.temperature * LN10
    print(f"Temperature: {args.temperature:.2f} K; Nernst slope: {slope:.8f} V/pH; reference: {args.reference}")
    print("States:")
    for state in states:
        descriptor = f"q={state.q}" if state.kind == "surface" else f"z={state.z}, activity={state.activity:g}"
        print(f"  {state.name}: kind={state.kind}, g0={state.g0:.8f} eV, {descriptor}; {state.derivation}")

    counts = [0] * len(states)
    for row in grid:
        for index in row:
            counts[index] += 1
    print("Observed lower-envelope boundaries:")
    pairs = sorted(observed_pairs(grid))
    if not pairs:
        print("  none within requested window")
    for first, second in pairs:
        print(f"  {states[first].name} | {states[second].name}: {boundary_equation(states[first], states[second], args.temperature, args.reference)}")
    inactive = [state.name for state, count in zip(states, counts) if count == 0]
    print("Inactive states: " + (", ".join(inactive) if inactive else "none"))

    for ph, potential in audits:
        ranked = sorted(
            ((state.omega(potential, ph, args.temperature, args.reference), state.name) for state in states),
            key=lambda item: (item[0], item[1]),
        )
        print(f"Audit pH={ph:g}, U_{args.reference}={potential:g} V:")
        for energy, name in ranked:
            print(f"  {name}: {energy:.8f} eV")
    print(f"Wrote {svg_path}")
    print(f"Wrote {grid_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
