# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.7", "numpy>=1.23"]
# ///
"""Matplotlib helpers for AICC report figures.

Import this module from plotting scripts to apply stable report-figure defaults,
add consistent panel labels, export preview/vector files, and detect obvious text
overlap before a figure is handed to the report builder.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


_PANEL_LABEL_SIZE = 8.0

PALETTE = {
    "blue_main": "#0F4D92",
    "blue_secondary": "#3775BA",
    "teal": "#42949E",
    "violet": "#9A4D8E",
    "red_strong": "#B64342",
    "green_3": "#8BCF8B",
    "neutral_light": "#CFCECE",
    "neutral_mid": "#767676",
    "neutral_dark": "#4D4D4D",
    "neutral_black": "#272727",
    "delta_up": "#2E9E44",
    "delta_down": "#E53935",
    "soft_blue": "#B4C0E4",
    "soft_teal": "#C9E7E5",
    "soft_red": "#F6CFCB",
    "soft_violet": "#D8CDEF",
}

AICC_ROLE_COLORS = {
    "primary_observable": PALETTE["blue_main"],
    "validation": PALETTE["teal"],
    "reference_or_baseline": PALETTE["neutral_mid"],
    "secondary_context": PALETTE["violet"],
    "success_or_pass": PALETTE["delta_up"],
    "limitation_or_warning": PALETTE["red_strong"],
    "neutral_fill": PALETTE["neutral_light"],
    "train": PALETTE["blue_secondary"],
    "validation_split": PALETTE["teal"],
    "test": PALETTE["violet"],
    "dft": PALETTE["neutral_black"],
    "mlp": PALETTE["blue_main"],
    "dos_total": PALETTE["neutral_black"],
    "dos_projected": PALETTE["blue_main"],
}

DEFAULT_COLORS = [
    PALETTE["blue_main"],
    PALETTE["teal"],
    PALETTE["violet"],
    PALETTE["red_strong"],
    PALETTE["green_3"],
    PALETTE["neutral_mid"],
]


def role_color(role: str, default: str | None = None) -> str:
    """Return the AICC color assigned to a semantic role."""

    if default is None:
        default = PALETTE["neutral_dark"]
    return AICC_ROLE_COLORS.get(role, default)


@dataclass(frozen=True)
class TextOverlap:
    """A visible overlap between two Matplotlib text objects."""

    text_a: str
    text_b: str
    area_px2: float


@dataclass(frozen=True)
class LowContrastText:
    """A text object whose foreground/background contrast is too low."""

    text: str
    ratio: float
    foreground: str
    background: str


@dataclass(frozen=True)
class LongTextInsideAxes:
    """A long explanatory text object placed inside a data axes."""

    text: str
    axes_label: str
    length: int


@dataclass(frozen=True)
class LegendInsideRasterAxes:
    """A legend placed inside an image/heatmap/contour axes."""

    label: str
    axes_label: str


def set_aicc_matplotlib_style(
    *,
    font_family: str = "Arial",
    font_size: float = 7.0,
    axis_label_size: float = 7.0,
    tick_label_size: float = 6.5,
    legend_size: float = 6.5,
    panel_label_size: float = 8.0,
) -> None:
    """Apply conservative publication/report defaults to Matplotlib."""

    import matplotlib as mpl
    from cycler import cycler

    global _PANEL_LABEL_SIZE
    _PANEL_LABEL_SIZE = panel_label_size
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [font_family, "Helvetica", "DejaVu Sans", "Arial"],
            "font.size": font_size,
            "axes.labelsize": axis_label_size,
            "axes.titlesize": axis_label_size,
            "xtick.labelsize": tick_label_size,
            "ytick.labelsize": tick_label_size,
            "legend.fontsize": legend_size,
            "legend.frameon": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "axes.linewidth": 0.7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.prop_cycle": cycler(color=DEFAULT_COLORS),
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 2.5,
            "ytick.major.size": 2.5,
            "figure.dpi": 150,
            "savefig.dpi": 600,
            "savefig.bbox": "tight",
        }
    )


def style_report_ax(ax, *, grid: bool = False, zero_line: bool = False):
    """Apply quiet report-axis defaults to one axis."""

    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    if grid:
        ax.grid(axis="y", color="#E8E8E8", linewidth=0.5, zorder=0)
    else:
        ax.grid(False)
    if zero_line:
        ax.axhline(0, color=role_color("reference_or_baseline"), linewidth=0.8, linestyle="--", zorder=1)
    return ax


def make_aicc_layout(archetype: str, *, figsize: tuple[float, float] | None = None):
    """Create a default AICC figure layout and return `(fig, axes)`.

    The returned `axes` dictionary uses panel letters as keys. The layouts encode
    visual hierarchy: hero panels are wider or taller than validation/context panels.
    """

    import matplotlib.pyplot as plt

    if archetype == "validation-strip":
        fig = plt.figure(figsize=figsize or (7.2, 4.6), constrained_layout=False)
        gs = fig.add_gridspec(
            2,
            4,
            height_ratios=[1.0, 1.25],
            width_ratios=[1.0, 1.0, 1.0, 1.35],
            left=0.07,
            right=0.98,
            top=0.94,
            bottom=0.14,
            hspace=0.42,
            wspace=0.52,
        )
        axes = {
            "a": fig.add_subplot(gs[0, 0]),
            "b": fig.add_subplot(gs[0, 1]),
            "c": fig.add_subplot(gs[0, 2]),
            "d": fig.add_subplot(gs[0, 3]),
            "e": fig.add_subplot(gs[1, 0]),
            "f": fig.add_subplot(gs[1, 1]),
            "g": fig.add_subplot(gs[1, 2]),
            "h": fig.add_subplot(gs[1, 3]),
        }
    elif archetype == "structure-plus-property":
        fig = plt.figure(figsize=figsize or (7.2, 4.6), constrained_layout=True)
        gs = fig.add_gridspec(
            2,
            4,
            width_ratios=[1.15, 1.0, 1.0, 1.35],
            height_ratios=[1.0, 1.0],
            hspace=0.22,
            wspace=0.34,
        )
        axes = {
            "a": fig.add_subplot(gs[:, 0]),
            "b": fig.add_subplot(gs[0, 1]),
            "c": fig.add_subplot(gs[1, 1]),
            "d": fig.add_subplot(gs[:, 2:]),
        }
    elif archetype == "pathway-hero":
        fig = plt.figure(figsize=figsize or (7.2, 4.8), constrained_layout=True)
        gs = fig.add_gridspec(2, 4, height_ratios=[1.45, 0.85], hspace=0.28, wspace=0.28)
        axes = {
            "a": fig.add_subplot(gs[0, :]),
            "b": fig.add_subplot(gs[1, 0]),
            "c": fig.add_subplot(gs[1, 1]),
            "d": fig.add_subplot(gs[1, 2]),
            "e": fig.add_subplot(gs[1, 3]),
        }
    elif archetype == "screening-grid":
        fig = plt.figure(figsize=figsize or (7.2, 5.0), constrained_layout=True)
        gs = fig.add_gridspec(2, 3, width_ratios=[1.45, 1.0, 1.0], hspace=0.28, wspace=0.32)
        axes = {
            "a": fig.add_subplot(gs[:, 0]),
            "b": fig.add_subplot(gs[0, 1]),
            "c": fig.add_subplot(gs[0, 2]),
            "d": fig.add_subplot(gs[1, 1]),
            "e": fig.add_subplot(gs[1, 2]),
        }
    elif archetype == "response-summary":
        fig = plt.figure(figsize=figsize or (7.2, 2.2), constrained_layout=True)
        gs = fig.add_gridspec(1, 4, width_ratios=[1.1, 1.0, 1.2, 1.0], wspace=0.26)
        axes = {letter: fig.add_subplot(gs[0, idx]) for idx, letter in enumerate(["a", "b", "c", "d"])}
    else:
        raise ValueError(
            "unknown AICC layout archetype: "
            f"{archetype!r}; expected validation-strip, structure-plus-property, "
            "pathway-hero, screening-grid, or response-summary"
        )

    for letter, ax in axes.items():
        add_panel_label(ax, letter, x=0.02, y=0.98, background=ax.get_facecolor(), halo=False)
    return fig, axes


def make_legend_panel(ax, handles, labels, *, title: str | None = None, ncol: int = 1):
    """Use an axis as a dedicated legend panel."""

    ax.set_axis_off()
    legend = ax.legend(handles, labels, title=title, ncol=ncol, loc="center", frameon=False)
    legend._aicc_outside_axes = True
    return legend


def legend_panel(ax, handles, labels, *, title: str | None = None, ncol: int = 1):
    """Alias for `make_legend_panel()` for figure-contract wording."""

    return make_legend_panel(ax, handles, labels, title=title, ncol=ncol)


def legend_outside(
    ax,
    *args,
    loc: str = "center left",
    bbox_to_anchor: tuple[float, float] = (1.02, 0.5),
    frameon: bool = False,
    **kwargs,
):
    """Place an axes legend outside the data panel.

    Use this for heatmaps, charge-density maps, contours, and dense plots where an
    in-panel legend can hide evidence or become unreadable over raster backgrounds.
    """

    legend = ax.legend(*args, loc=loc, bbox_to_anchor=bbox_to_anchor, frameon=frameon, **kwargs)
    legend._aicc_outside_axes = True
    background = ax.figure.get_facecolor()
    for text_obj in legend.get_texts():
        _mark_contrast_background(text_obj, background)
    return legend


def add_note_band(
    fig,
    text: str,
    *,
    position: str = "top",
    x: float = 0.5,
    fontsize: float = 6.5,
    color: str | None = None,
    background: str = "#FFFFFF",
    border: str = "#D8DEE4",
    wrap_width: int | None = 120,
):
    """Add a short method/reference/formula note outside data axes.

    This is the preferred destination for long explanatory text, formula definitions,
    reference-state notes, or reviewer-comment context that would otherwise cover data.
    Reserve margin in the layout when the note is more than one line.
    """

    import textwrap

    if position not in {"top", "bottom"}:
        raise ValueError("position must be 'top' or 'bottom'")
    note = text.strip()
    if wrap_width is not None and wrap_width > 0:
        note = "\n".join(textwrap.wrap(note, width=wrap_width, break_long_words=False)) or note
    if color is None:
        color = choose_contrast_text_color(background)
    y = 0.985 if position == "top" else 0.015
    va = "top" if position == "top" else "bottom"
    text_obj = fig.text(
        x,
        y,
        note,
        ha="center",
        va=va,
        fontsize=fontsize,
        color=color,
        bbox={"boxstyle": "round,pad=0.22", "facecolor": background, "edgecolor": border, "linewidth": 0.6},
    )
    text_obj._aicc_note_band = True
    _mark_contrast_background(text_obj, background)
    return text_obj


def _as_float_list(values: Sequence[float]) -> list[float]:
    return [float(value) for value in values]


def _finite_range(values: Sequence[float]) -> tuple[float, float]:
    finite = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not finite:
        return 0.0, 1.0
    return min(finite), max(finite)


def tighten_yaxis(ax, values: Sequence[float], *, include_zero: bool = False, margin_fraction: float = 0.12):
    """Tighten a y axis around the data unless zero is scientifically required."""

    low, high = _finite_range(values)
    if include_zero:
        low = min(low, 0.0)
        high = max(high, 0.0)
    if low == high:
        pad = abs(low) * 0.1 if low else 1.0
    else:
        pad = (high - low) * margin_fraction
    ax.set_ylim(low - pad, high + pad)
    return ax


def plot_lcurve(
    ax,
    steps: Sequence[float],
    train: Sequence[float],
    validation: Sequence[float] | None = None,
    *,
    ylabel: str = "RMSE",
    logy: bool = True,
):
    """Plot a DeePMD/MLP learning curve with quiet validation styling."""

    style_report_ax(ax)
    ax.plot(steps, train, color=role_color("train"), linewidth=1.4, label="train")
    if validation is not None:
        ax.plot(steps, validation, color=role_color("validation_split"), linewidth=1.4, label="validation")
    ax.set_xlabel("Training step")
    ax.set_ylabel(ylabel)
    if logy:
        from matplotlib.ticker import LogLocator, NullFormatter

        validation_values = list(validation) if validation is not None else []
        positives = [value for value in list(train) + validation_values if float(value) > 0]
        if positives:
            ax.set_yscale("log")
            ax.yaxis.set_major_locator(LogLocator(base=10, numticks=4))
            ax.yaxis.set_minor_formatter(NullFormatter())
    ax.tick_params(axis="both", pad=1.5)
    ax.legend(frameon=False, loc="best")
    return ax


def plot_parity(
    ax,
    reference: Sequence[float],
    predicted: Sequence[float],
    *,
    xlabel: str = "DFT",
    ylabel: str = "MLP",
    unit: str | None = None,
    color: str | None = None,
):
    """Plot predicted-vs-reference parity with a one-to-one line."""

    style_report_ax(ax)
    ref = _as_float_list(reference)
    pred = _as_float_list(predicted)
    low, high = _finite_range(ref + pred)
    pad = (high - low) * 0.04 if high != low else 1.0
    low -= pad
    high += pad
    ax.scatter(ref, pred, s=14, color=color or role_color("mlp"), edgecolor="white", linewidth=0.35, alpha=0.85)
    ax.plot([low, high], [low, high], color=role_color("reference_or_baseline"), linewidth=0.9, linestyle="--")
    unit_suffix = f" ({unit})" if unit else ""
    ax.set_xlabel(f"{xlabel}{unit_suffix}")
    ax.set_ylabel(f"{ylabel}{unit_suffix}")
    ax.set_xlim(low, high)
    ax.set_ylim(low, high)
    from matplotlib.ticker import MaxNLocator

    ax.xaxis.set_major_locator(MaxNLocator(nbins=3, prune="both"))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=3, prune="both"))
    ax.tick_params(axis="both", pad=1.5)
    return ax


def plot_pca_embedding(
    ax,
    x: Sequence[float],
    y: Sequence[float],
    groups: Sequence[str] | None = None,
    *,
    xlabel: str = "PC1",
    ylabel: str = "PC2",
):
    """Plot a PCA/embedding panel with stable split/source colors."""

    style_report_ax(ax)
    xs = _as_float_list(x)
    ys = _as_float_list(y)
    if groups is None:
        ax.scatter(xs, ys, s=16, color=role_color("validation"), alpha=0.78, edgecolor="white", linewidth=0.25)
    else:
        group_order = list(dict.fromkeys(groups))
        palette = [role_color("train"), role_color("validation_split"), role_color("test"), role_color("secondary_context")]
        color_by_group = {group: palette[idx % len(palette)] for idx, group in enumerate(group_order)}
        for group in group_order:
            idxs = [idx for idx, value in enumerate(groups) if value == group]
            ax.scatter(
                [xs[idx] for idx in idxs],
                [ys[idx] for idx in idxs],
                s=16,
                label=str(group),
                color=color_by_group[group],
                alpha=0.78,
                edgecolor="white",
                linewidth=0.25,
            )
        ax.legend(frameon=False, loc="best")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    from matplotlib.ticker import MaxNLocator

    ax.xaxis.set_major_locator(MaxNLocator(nbins=3, prune="both"))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=3, prune="both"))
    ax.tick_params(axis="both", pad=1.5)
    return ax


def plot_relative_energy_bar(
    ax,
    labels: Sequence[str],
    energies: Sequence[float],
    *,
    unit: str = "eV",
    reference_line: float = 0.0,
    color: str | None = None,
    sort: bool = False,
    annotate: bool = True,
):
    """Plot relative energies with contrast-aware value annotations."""

    style_report_ax(ax, zero_line=True)
    pairs = list(zip(labels, _as_float_list(energies)))
    if sort:
        pairs = sorted(pairs, key=lambda item: item[1])
    plot_labels = [item[0] for item in pairs]
    plot_values = [item[1] for item in pairs]
    bar_color = color or role_color("primary_observable")
    bars = ax.bar(range(len(plot_values)), plot_values, color=bar_color, edgecolor="#272727", linewidth=0.5)
    ax.axhline(reference_line, color=role_color("reference_or_baseline"), linewidth=0.9, linestyle="--")
    ax.set_xticks(range(len(plot_labels)))
    ax.set_xticklabels(plot_labels, rotation=30, ha="right")
    ax.set_ylabel(f"Relative energy ({unit})")
    tighten_yaxis(ax, plot_values + [reference_line], include_zero=True)
    from matplotlib.ticker import MaxNLocator

    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    ax.tick_params(axis="both", pad=1.5)
    if annotate:
        annotate_bars_contrast(ax, bars, fmt="{:.2f}", inside=False)
    return bars


def plot_dos_pdos(
    ax,
    energy: Sequence[float],
    series: Mapping[str, Sequence[float]],
    *,
    fermi: float = 0.0,
    xlabel: str = "Energy - E_F (eV)",
    ylabel: str = "DOS (a.u.)",
    fill: bool = False,
):
    """Plot DOS/PDOS with restrained line hierarchy."""

    style_report_ax(ax)
    color_cycle = [
        role_color("dos_total"),
        role_color("dos_projected"),
        role_color("secondary_context"),
        role_color("validation"),
        role_color("limitation_or_warning"),
    ]
    shifted_energy = [float(value) - fermi for value in energy]
    for idx, (name, values) in enumerate(series.items()):
        color = color_cycle[idx % len(color_cycle)]
        line_width = 1.5 if idx == 0 else 1.1
        ax.plot(shifted_energy, values, label=name, color=color, linewidth=line_width)
        if fill and idx > 0:
            ax.fill_between(shifted_energy, values, color=color, alpha=0.12, linewidth=0)
    ax.axvline(0, color=role_color("reference_or_baseline"), linewidth=0.9, linestyle="--")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    from matplotlib.ticker import MaxNLocator

    ax.xaxis.set_major_locator(MaxNLocator(nbins=5, prune="both"))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4, prune="both"))
    ax.tick_params(axis="both", pad=1.5)
    ax.legend(frameon=False, loc="best")
    return ax


def plot_reaction_profile(
    ax,
    states: Sequence[str],
    energies: Sequence[float],
    *,
    unit: str = "eV",
    color: str | None = None,
    plateau_width: float = 0.56,
    connector: str = "dashed",
):
    """Plot a reaction/free-energy profile as plateau states plus sequence guides.

    Each intermediate or transition state is drawn as a thick horizontal plateau. Thin
    solid or dashed connectors indicate the reaction sequence only; they do not imply a
    continuous path unless the caller is plotting actual NEB/IRC path-coordinate data.
    """

    style_report_ax(ax, zero_line=True)
    values = _as_float_list(energies)
    xs = list(range(len(states)))
    line_color = color or role_color("primary_observable")
    connector_style = "--" if connector == "dashed" else "-"
    if len(values) > 1 and connector != "none":
        for left_idx in range(len(values) - 1):
            ax.plot(
                [
                    xs[left_idx] + plateau_width / 2,
                    xs[left_idx + 1] - plateau_width / 2,
                ],
                [values[left_idx], values[left_idx + 1]],
                color=role_color("reference_or_baseline"),
                linewidth=0.8,
                linestyle=connector_style,
                zorder=1,
            )
    for x_value, y_value in zip(xs, values):
        ax.hlines(
            y_value,
            x_value - plateau_width / 2,
            x_value + plateau_width / 2,
            color=line_color,
            linewidth=3.0,
            zorder=3,
        )
    ax.set_xticks(xs)
    ax.set_xticklabels(states, rotation=20, ha="right")
    ax.set_ylabel(f"Relative energy ({unit})")
    tighten_yaxis(ax, values, include_zero=True)
    from matplotlib.ticker import MaxNLocator

    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    ax.tick_params(axis="both", pad=1.5)
    for x_value, y_value in zip(xs, values):
        add_contrast_text(
            ax,
            x_value,
            y_value,
            f"{y_value:.2f}",
            background=ax.get_facecolor(),
            ha="center",
            va="bottom",
            fontsize=6.3,
            halo=True,
        )
    return ax


def plot_md_observable(
    ax,
    x: Sequence[float],
    y: Sequence[float],
    *,
    xlabel: str = "Time (ps)",
    ylabel: str = "Observable",
    color: str | None = None,
    label: str | None = None,
):
    """Plot an MD observable as the primary evidence panel."""

    style_report_ax(ax)
    ax.plot(x, y, color=color or role_color("primary_observable"), linewidth=1.6, label=label)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    from matplotlib.ticker import MaxNLocator

    ax.xaxis.set_major_locator(MaxNLocator(nbins=4, prune="both"))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4, prune="both"))
    ax.tick_params(axis="both", pad=1.5)
    if label:
        ax.legend(frameon=False, loc="best")
    return ax


def _rgba(color) -> tuple[float, float, float, float]:
    import matplotlib.colors as mcolors

    return mcolors.to_rgba(color)


def _hex(color) -> str:
    import matplotlib.colors as mcolors

    return mcolors.to_hex(_rgba(color), keep_alpha=False)


def _linear_channel(channel: float) -> float:
    if channel <= 0.03928:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(color) -> float:
    """Return WCAG relative luminance for any Matplotlib color."""

    r, g, b, _ = _rgba(color)
    return 0.2126 * _linear_channel(r) + 0.7152 * _linear_channel(g) + 0.0722 * _linear_channel(b)


def contrast_ratio(foreground, background) -> float:
    """Return WCAG contrast ratio between two Matplotlib colors."""

    lum_fg = relative_luminance(foreground)
    lum_bg = relative_luminance(background)
    lighter = max(lum_fg, lum_bg)
    darker = min(lum_fg, lum_bg)
    return (lighter + 0.05) / (darker + 0.05)


def choose_contrast_text_color(background, *, dark: str = "#272727", light: str = "#FFFFFF") -> str:
    """Choose dark or light text for the given background color."""

    return light if contrast_ratio(light, background) >= contrast_ratio(dark, background) else dark


def _opposite_for_halo(text_color: str) -> str:
    return "#FFFFFF" if contrast_ratio("#FFFFFF", text_color) > contrast_ratio("#272727", text_color) else "#272727"


def _mark_contrast_background(text_obj, background) -> None:
    text_obj._aicc_contrast_background = _rgba(background)


def add_panel_label(
    ax,
    label: str,
    *,
    x: float = -0.14,
    y: float = 1.06,
    size: float | None = None,
    weight: str = "bold",
    color: str | None = None,
    background=None,
    halo: bool = True,
):
    """Add a readable lowercase panel label to an axis."""

    import matplotlib.patheffects as path_effects

    if size is None:
        size = _PANEL_LABEL_SIZE
    if background is None:
        background = ax.get_facecolor() if 0 <= x <= 1 and 0 <= y <= 1 else ax.figure.get_facecolor()
    if color is None:
        color = choose_contrast_text_color(background)
    kwargs = {}
    if halo:
        kwargs["path_effects"] = [
            path_effects.withStroke(linewidth=1.0, foreground=_opposite_for_halo(color), alpha=0.55)
        ]
    text_obj = ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=size,
        fontweight=weight,
        color=color,
        clip_on=False,
        **kwargs,
    )
    _mark_contrast_background(text_obj, background)
    return text_obj


def add_contrast_text(ax, x, y, text: str, *, background, color: str | None = None, halo: bool = False, **kwargs):
    """Add text with foreground chosen for the declared background.

    Use this for in-bar labels, labels inside colored regions, and labels on dark
    structure/image panels. Passing the real background lets the contrast audit avoid
    guessing from the white axes facecolor.
    """

    import matplotlib.patheffects as path_effects

    if color is None:
        color = choose_contrast_text_color(background)
    if halo and "path_effects" not in kwargs:
        kwargs["path_effects"] = [
            path_effects.withStroke(linewidth=1.0, foreground=_opposite_for_halo(color), alpha=0.6)
        ]
    text_obj = ax.text(x, y, text, color=color, **kwargs)
    _mark_contrast_background(text_obj, background)
    return text_obj


def annotate_bars_contrast(ax, bars, *, fmt: str = "{:.2f}", inside: bool = True, fontsize: float | None = None):
    """Annotate bars with text color chosen from each bar's facecolor."""

    if fontsize is None:
        fontsize = 6.5
    texts = []
    for bar in bars:
        value = bar.get_height()
        if inside:
            low, high = ax.get_ylim()
            pad = 0.015 * abs(high - low)
            if value >= 0:
                y = value - pad
                va = "top"
            else:
                y = value + pad
                va = "bottom"
            background = bar.get_facecolor()
            halo = False
        else:
            y = value
            va = "bottom" if value >= 0 else "top"
            background = ax.get_facecolor()
            halo = True
        texts.append(
            add_contrast_text(
                ax,
                bar.get_x() + bar.get_width() / 2,
                y,
                fmt.format(value),
                background=background,
                ha="center",
                va=va,
                fontsize=fontsize,
                halo=halo,
            )
        )
    return texts


def _text_label(text_obj) -> str:
    value = text_obj.get_text().strip()
    if value:
        return value
    return f"<empty {text_obj.__class__.__name__}>"


def _iter_visible_text(fig, *, ignore_empty: bool = True):
    for text_obj in fig.findobj(match=lambda obj: obj.__class__.__name__ == "Text"):
        if not text_obj.get_visible():
            continue
        if ignore_empty and not text_obj.get_text().strip():
            continue
        yield text_obj


def _legend_texts(fig) -> set:
    texts = set()
    legends = []
    for ax in fig.axes:
        legend = ax.get_legend()
        if legend is not None:
            legends.append(legend)
    legends.extend(getattr(fig, "legends", []))
    for legend in legends:
        texts.update(legend.get_texts())
        title = legend.get_title()
        if title is not None:
            texts.add(title)
    return texts


def _is_axis_structural_text(text_obj, ax) -> bool:
    structural = [
        ax.title,
        getattr(ax, "_left_title", None),
        getattr(ax, "_right_title", None),
        ax.xaxis.label,
        ax.yaxis.label,
        ax.xaxis.get_offset_text(),
        ax.yaxis.get_offset_text(),
    ]
    if any(text_obj is item for item in structural if item is not None):
        return True
    tick_labels = (
        ax.get_xticklabels(minor=False)
        + ax.get_xticklabels(minor=True)
        + ax.get_yticklabels(minor=False)
        + ax.get_yticklabels(minor=True)
    )
    return any(text_obj is item for item in tick_labels)


def _axes_label(fig, ax) -> str:
    title = ax.get_title().strip()
    if title:
        return title
    label = ax.get_label()
    if label and not label.startswith("_"):
        return label
    try:
        return f"axes {fig.axes.index(ax) + 1}"
    except ValueError:
        return "axes"


def _bbox_overlap_area(bbox_a, bbox_b) -> float:
    x0 = max(bbox_a.x0, bbox_b.x0)
    y0 = max(bbox_a.y0, bbox_b.y0)
    x1 = min(bbox_a.x1, bbox_b.x1)
    y1 = min(bbox_a.y1, bbox_b.y1)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return float((x1 - x0) * (y1 - y0))


def _bbox_center_inside(inner_bbox, outer_bbox) -> bool:
    center_x = (inner_bbox.x0 + inner_bbox.x1) / 2
    center_y = (inner_bbox.y0 + inner_bbox.y1) / 2
    return bool(outer_bbox.contains(center_x, center_y))


def _axes_has_raster(ax) -> bool:
    if getattr(ax, "images", None):
        if len(ax.images) > 0:
            return True
    raster_collection_names = {"QuadMesh", "PolyQuadMesh"}
    for collection in getattr(ax, "collections", []):
        name = collection.__class__.__name__
        if name in raster_collection_names:
            return True
        if getattr(collection, "get_array", lambda: None)() is not None and name in {"PathCollection", "PolyCollection"}:
            return True
    return False


def _normalized_text_length(text: str) -> int:
    return len(" ".join(text.split()))


def _looks_like_explanatory_text(text_obj, *, max_chars: int) -> bool:
    text = " ".join(text_obj.get_text().split())
    text_lower = text.lower()
    length = len(text)
    if length > max_chars:
        return True
    bbox_patch = text_obj.get_bbox_patch()
    if bbox_patch is not None and bbox_patch.get_visible() and length > min(max_chars, 12):
        return True
    formula_tokens = ("=", "delta", "rho", "\u0394", "\u2211", "reference", "method")
    return length > 12 and any(token in text_lower for token in formula_tokens)


def find_long_text_inside_axes(
    fig,
    *,
    max_chars: int = 20,
    ignore_empty: bool = True,
) -> list[LongTextInsideAxes]:
    """Return long explanatory text boxes placed inside data axes.

    Long notes, formula definitions, reference-state details, and method explanations
    should live in captions, figure-level note bands, or dedicated note/legend panels.
    """

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    legend_texts = _legend_texts(fig)
    findings: list[LongTextInsideAxes] = []
    for text_obj in _iter_visible_text(fig, ignore_empty=ignore_empty):
        if text_obj in legend_texts:
            continue
        if getattr(text_obj, "_aicc_allow_long_inside_axes", False):
            continue
        if getattr(text_obj, "_aicc_note_band", False):
            continue
        ax = getattr(text_obj, "axes", None)
        if ax is None or not ax.get_visible():
            continue
        if _is_axis_structural_text(text_obj, ax):
            continue
        if not _looks_like_explanatory_text(text_obj, max_chars=max_chars):
            continue
        text_bbox = text_obj.get_window_extent(renderer=renderer)
        axes_bbox = ax.get_window_extent(renderer=renderer)
        if text_bbox.width <= 0 or text_bbox.height <= 0:
            continue
        if _bbox_center_inside(text_bbox, axes_bbox) or _bbox_overlap_area(text_bbox, axes_bbox) > 0.35 * (
            text_bbox.width * text_bbox.height
        ):
            findings.append(
                LongTextInsideAxes(
                    text=_text_label(text_obj),
                    axes_label=_axes_label(fig, ax),
                    length=_normalized_text_length(text_obj.get_text()),
                )
            )
    return findings


def find_legend_inside_raster_axes(fig) -> list[LegendInsideRasterAxes]:
    """Return legends placed over image/heatmap/contour axes."""

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    findings: list[LegendInsideRasterAxes] = []
    for ax in fig.axes:
        if not ax.get_visible() or not _axes_has_raster(ax):
            continue
        legend = ax.get_legend()
        if legend is None:
            continue
        if getattr(legend, "_aicc_outside_axes", False) or getattr(legend, "_aicc_allow_inside_raster_axes", False):
            continue
        legend_bbox = legend.get_window_extent(renderer=renderer)
        axes_bbox = ax.get_window_extent(renderer=renderer)
        if _bbox_overlap_area(legend_bbox, axes_bbox) <= 0:
            continue
        legend_title = legend.get_title().get_text().strip()
        labels = [text_obj.get_text().strip() for text_obj in legend.get_texts() if text_obj.get_text().strip()]
        label = legend_title or ", ".join(labels[:3]) or "legend"
        findings.append(LegendInsideRasterAxes(label=label, axes_label=_axes_label(fig, ax)))
    return findings


def _sample_background_under_text(fig, text_obj, renderer, *, pad_px: int = 2):
    try:
        import numpy as np
    except Exception:
        return None

    try:
        buffer = np.asarray(fig.canvas.buffer_rgba())
    except Exception:
        return None
    if buffer.ndim != 3 or buffer.shape[2] < 3:
        return None
    height, width = buffer.shape[:2]
    try:
        bbox = text_obj.get_window_extent(renderer=renderer)
    except Exception:
        return None
    if bbox.width <= 0 or bbox.height <= 0:
        return None

    x0 = max(0, int(math.floor(bbox.x0 - pad_px)))
    x1 = min(width, int(math.ceil(bbox.x1 + pad_px)))
    y0_display = max(0, bbox.y0 - pad_px)
    y1_display = min(height, bbox.y1 + pad_px)
    row0 = max(0, int(math.floor(height - y1_display)))
    row1 = min(height, int(math.ceil(height - y0_display)))
    if x1 <= x0 or row1 <= row0:
        return None

    patch = buffer[row0:row1, x0:x1, :3]
    if patch.size == 0:
        return None
    median_rgb = np.median(patch.reshape(-1, 3), axis=0) / 255.0
    return (float(median_rgb[0]), float(median_rgb[1]), float(median_rgb[2]), 1.0)


def find_sampled_low_contrast_text(
    fig,
    *,
    min_ratio: float = 4.5,
    ignore_empty: bool = True,
) -> list[LowContrastText]:
    """Return low-contrast text by sampling rendered pixels behind the text bbox."""

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    findings: list[LowContrastText] = []
    for text_obj in _iter_visible_text(fig, ignore_empty=ignore_empty):
        if getattr(text_obj, "_aicc_contrast_background", None) is not None:
            continue
        if text_obj.get_path_effects():
            continue
        bbox_patch = text_obj.get_bbox_patch()
        if bbox_patch is not None and bbox_patch.get_visible() and bbox_patch.get_facecolor()[-1] > 0.75:
            continue
        foreground = _rgba(text_obj.get_color())
        if foreground[-1] == 0:
            continue
        background = _sample_background_under_text(fig, text_obj, renderer)
        if background is None:
            continue
        ratio = contrast_ratio(foreground, background)
        if ratio < min_ratio:
            findings.append(
                LowContrastText(
                    text=_text_label(text_obj),
                    ratio=ratio,
                    foreground=_hex(foreground),
                    background=_hex(background),
                )
            )
    return findings


def find_text_overlaps(
    fig,
    *,
    tolerance_px: float = 1.0,
    min_area_px2: float = 4.0,
    ignore_empty: bool = True,
) -> list[TextOverlap]:
    """Return visible text-object overlaps in display coordinates.

    This is a conservative diagnostic for common failures such as crowded tick labels,
    legends covering labels, or panel labels colliding with axis titles. It cannot see
    labels baked into raster/OVITO images.
    """

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = []
    for text_obj in fig.findobj(match=lambda obj: obj.__class__.__name__ == "Text"):
        if not text_obj.get_visible():
            continue
        if ignore_empty and not text_obj.get_text().strip():
            continue
        bbox = text_obj.get_window_extent(renderer=renderer).expanded(
            1.0 + tolerance_px / 100.0,
            1.0 + tolerance_px / 100.0,
        )
        if bbox.width <= 0 or bbox.height <= 0:
            continue
        texts.append((text_obj, bbox))

    overlaps: list[TextOverlap] = []
    for idx, (text_a, bbox_a) in enumerate(texts):
        for text_b, bbox_b in texts[idx + 1 :]:
            x0 = max(bbox_a.x0, bbox_b.x0)
            y0 = max(bbox_a.y0, bbox_b.y0)
            x1 = min(bbox_a.x1, bbox_b.x1)
            y1 = min(bbox_a.y1, bbox_b.y1)
            if x1 <= x0 or y1 <= y0:
                continue
            area = (x1 - x0) * (y1 - y0)
            if area >= min_area_px2:
                overlaps.append(TextOverlap(_text_label(text_a), _text_label(text_b), area))
    return overlaps


def _text_background(text_obj, fig):
    custom = getattr(text_obj, "_aicc_contrast_background", None)
    if custom is not None:
        return custom

    bbox_patch = text_obj.get_bbox_patch()
    if bbox_patch is not None and bbox_patch.get_visible():
        patch_face = bbox_patch.get_facecolor()
        if patch_face[-1] > 0:
            return patch_face

    axes = getattr(text_obj, "axes", None)
    if axes is None:
        return fig.get_facecolor()

    try:
        renderer = fig.canvas.get_renderer()
        text_bbox = text_obj.get_window_extent(renderer=renderer)
        center_x = (text_bbox.x0 + text_bbox.x1) / 2
        center_y = (text_bbox.y0 + text_bbox.y1) / 2
        if axes.get_window_extent(renderer=renderer).contains(center_x, center_y):
            return axes.get_facecolor()
    except Exception:
        return axes.get_facecolor()
    return fig.get_facecolor()


def find_low_contrast_text(
    fig,
    *,
    min_ratio: float = 4.5,
    ignore_empty: bool = True,
) -> list[LowContrastText]:
    """Return visible text likely to be unreadable against its local background."""

    fig.canvas.draw()
    findings: list[LowContrastText] = []
    for text_obj in fig.findobj(match=lambda obj: obj.__class__.__name__ == "Text"):
        if not text_obj.get_visible():
            continue
        if ignore_empty and not text_obj.get_text().strip():
            continue
        foreground = _rgba(text_obj.get_color())
        if foreground[-1] == 0:
            continue
        background = _text_background(text_obj, fig)
        ratio = contrast_ratio(foreground, background)
        if ratio < min_ratio:
            findings.append(
                LowContrastText(
                    text=_text_label(text_obj),
                    ratio=ratio,
                    foreground=_hex(foreground),
                    background=_hex(background),
                )
            )
    return findings


def format_overlap_warnings(overlaps: Iterable[TextOverlap]) -> list[str]:
    """Format text-overlap diagnostics for logs or stderr."""

    return [
        f"text overlap: {item.text_a!r} vs {item.text_b!r} ({item.area_px2:.1f} px^2)"
        for item in overlaps
    ]


def format_contrast_warnings(findings: Iterable[LowContrastText]) -> list[str]:
    """Format low-contrast diagnostics for logs or stderr."""

    return [
        "low text contrast: "
        f"{item.text!r} foreground {item.foreground} on {item.background} "
        f"(ratio {item.ratio:.2f}, require >=4.5)"
        for item in findings
    ]


def format_long_text_warnings(findings: Iterable[LongTextInsideAxes]) -> list[str]:
    """Format long-text-inside-axes diagnostics for logs or stderr."""

    return [
        "long explanatory text inside data axes: "
        f"{item.text!r} in {item.axes_label} ({item.length} chars); "
        "move it to the caption, add_note_band(), or a note/legend panel"
        for item in findings
    ]


def format_raster_legend_warnings(findings: Iterable[LegendInsideRasterAxes]) -> list[str]:
    """Format in-raster-legend diagnostics for logs or stderr."""

    return [
        "legend inside raster/data-image axes: "
        f"{item.label!r} in {item.axes_label}; use legend_outside() or a legend panel"
        for item in findings
    ]


def save_aicc_figure(
    fig,
    output_base: str | Path,
    *,
    width_in: float | None = None,
    formats: tuple[str, ...] = ("png", "pdf", "svg"),
    dpi: int = 600,
    check_overlaps: bool = True,
    check_contrast: bool = True,
    check_sampled_contrast: bool = True,
    check_long_text: bool = True,
    check_raster_legends: bool = True,
) -> list[str]:
    """Save preview/vector exports and return blocking layout warnings."""

    if width_in is not None:
        current_width, current_height = fig.get_size_inches()
        if current_width > 0:
            fig.set_size_inches(width_in, current_height * width_in / current_width)
    fig.canvas.draw()

    warnings: list[str] = []
    if check_overlaps:
        warnings.extend(format_overlap_warnings(find_text_overlaps(fig)))
    if check_contrast:
        warnings.extend(format_contrast_warnings(find_low_contrast_text(fig)))
    if check_sampled_contrast:
        warnings.extend(
            "sampled " + warning
            for warning in format_contrast_warnings(find_sampled_low_contrast_text(fig))
        )
    if check_long_text:
        warnings.extend(format_long_text_warnings(find_long_text_inside_axes(fig)))
    if check_raster_legends:
        warnings.extend(format_raster_legend_warnings(find_legend_inside_raster_axes(fig)))

    base = Path(output_base)
    base.parent.mkdir(parents=True, exist_ok=True)
    for fmt in formats:
        fig.savefig(base.with_suffix(f".{fmt}"), dpi=dpi, bbox_inches="tight")
    return warnings


def _demo(output: Path | None) -> int:
    return _demo_basic(output)


def _emit_warnings(warnings: list[str]) -> int:
    for warning in warnings:
        print(warning)
    return 1 if warnings else 0


def _demo_basic(output: Path | None) -> int:
    import matplotlib.pyplot as plt

    set_aicc_matplotlib_style()
    fig, ax = plt.subplots(figsize=(3.4, 2.2), constrained_layout=True)
    ax.plot([0, 1, 2, 3], [0.1, 0.4, 0.35, 0.8], marker="o", label="validation")
    ax.set_xlim(-0.05, 3.05)
    ax.set_xticks([0, 1, 2, 3])
    ax.set_ylim(0.0, 0.9)
    ax.set_xlabel("Training step")
    ax.set_ylabel("RMSE (eV/A)")
    ax.legend(frameon=False, loc="upper left")
    add_panel_label(ax, "a")
    if output is None:
        output = Path("aicc_figure_style_demo")
    warnings = save_aicc_figure(fig, output, formats=("png",), check_overlaps=True)
    return _emit_warnings(warnings)


def _demo_mlp(output: Path | None) -> int:
    set_aicc_matplotlib_style()
    fig, axes = make_aicc_layout("validation-strip")
    steps = [1, 2, 5, 10, 20, 50, 100]
    plot_lcurve(axes["a"], steps, [0.9, 0.5, 0.25, 0.14, 0.08, 0.05, 0.035], [1.0, 0.56, 0.29, 0.17, 0.1, 0.065, 0.045], ylabel="Energy RMSE (meV/atom)")
    plot_lcurve(axes["b"], steps, [0.45, 0.25, 0.13, 0.08, 0.055, 0.04, 0.032], [0.50, 0.30, 0.16, 0.10, 0.075, 0.055, 0.043], ylabel="Force RMSE (eV/A)")
    ref_e = [-0.30, -0.15, 0.0, 0.2, 0.38, 0.52, 0.7]
    pred_e = [-0.28, -0.18, 0.03, 0.18, 0.42, 0.49, 0.74]
    plot_parity(axes["c"], ref_e, pred_e, xlabel="DFT energy", ylabel="MLP energy", unit="eV")
    plot_parity(axes["d"], [-1.0, -0.6, -0.2, 0.1, 0.5, 0.9], [-0.95, -0.66, -0.24, 0.12, 0.44, 0.86], xlabel="DFT force", ylabel="MLP force", unit="eV/A")
    plot_pca_embedding(
        axes["e"],
        [-2.0, -1.4, -0.8, -0.2, 0.5, 1.2, 1.8, 2.2],
        [0.2, 0.7, 0.1, -0.4, -0.2, 0.35, 0.8, 0.1],
        ["train", "train", "train", "val", "val", "test", "test", "target"],
    )
    axes["f"].set_axis_off()
    axes["f"].text(0.5, 0.55, "Structure\ncontext", ha="center", va="center", fontsize=7, color=role_color("neutral_dark"))
    plot_relative_energy_bar(axes["g"], ["dilute", "cluster"], [0.0, 0.18], annotate=True)
    plot_md_observable(axes["h"], [0, 20, 40, 60, 80, 100], [1.0, 0.52, 0.28, 0.15, 0.08, 0.04], ylabel="Contact survival")
    if output is None:
        output = Path("aicc_mlp_qa_demo")
    return _emit_warnings(save_aicc_figure(fig, output, formats=("png",), width_in=7.2))


def _demo_energy(output: Path | None) -> int:
    import matplotlib.pyplot as plt

    set_aicc_matplotlib_style()
    fig, ax = plt.subplots(figsize=(3.8, 2.5), constrained_layout=True)
    add_panel_label(ax, "a")
    plot_relative_energy_bar(ax, ["model A", "model B", "model C"], [0.0, -0.23, 0.31], sort=False)
    if output is None:
        output = Path("aicc_energy_demo")
    return _emit_warnings(save_aicc_figure(fig, output, formats=("png",), width_in=3.8))


def _demo_electronic(output: Path | None) -> int:
    set_aicc_matplotlib_style()
    fig, axes = make_aicc_layout("structure-plus-property")
    axes["a"].set_axis_off()
    axes["a"].text(0.5, 0.55, "Model\nstructure", ha="center", va="center", fontsize=7, color=role_color("neutral_dark"))
    plot_relative_energy_bar(axes["b"], ["clean", "ads"], [0.0, -0.74], annotate=True)
    plot_pca_embedding(axes["c"], [-0.8, -0.2, 0.25, 0.75], [0.1, 0.5, -0.25, 0.2], ["site 1", "site 1", "site 2", "site 2"], xlabel="descriptor 1", ylabel="descriptor 2")
    energy = [-3, -2, -1, 0, 1, 2, 3]
    plot_dos_pdos(
        axes["d"],
        energy,
        {
            "total": [0.2, 0.6, 1.1, 0.4, 0.3, 0.55, 0.2],
            "Pt-d": [0.1, 0.45, 0.8, 0.2, 0.12, 0.35, 0.1],
            "O-p": [0.05, 0.15, 0.35, 0.24, 0.18, 0.10, 0.04],
        },
        fill=True,
    )
    if output is None:
        output = Path("aicc_electronic_demo")
    return _emit_warnings(save_aicc_figure(fig, output, formats=("png",), width_in=7.2))


def _demo_pathway(output: Path | None) -> int:
    set_aicc_matplotlib_style()
    fig, axes = make_aicc_layout("pathway-hero")
    plot_reaction_profile(axes["a"], ["IS", "TS1", "MS", "TS2", "FS"], [0.0, 0.82, 0.31, 0.65, -0.22])
    for letter, label in zip(["b", "c", "d", "e"], ["IS", "TS1", "MS", "FS"]):
        axes[letter].set_axis_off()
        axes[letter].text(0.5, 0.55, label, ha="center", va="center", fontsize=7, color=role_color("neutral_dark"))
    if output is None:
        output = Path("aicc_pathway_demo")
    return _emit_warnings(save_aicc_figure(fig, output, formats=("png",), width_in=7.2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo-kind",
        choices=("basic", "mlp", "energy", "electronic", "pathway"),
        default="basic",
        help="Select which built-in synthetic demo to render.",
    )
    parser.add_argument(
        "--demo-out",
        type=Path,
        default=None,
        help="Write a small demo PNG to this basename/path and run the overlap check.",
    )
    args = parser.parse_args()
    demos = {
        "basic": _demo_basic,
        "mlp": _demo_mlp,
        "energy": _demo_energy,
        "electronic": _demo_electronic,
        "pathway": _demo_pathway,
    }
    return demos[args.demo_kind](args.demo_out)


if __name__ == "__main__":
    raise SystemExit(main())
