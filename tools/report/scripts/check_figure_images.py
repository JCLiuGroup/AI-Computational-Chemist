# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.23", "pillow>=10"]
# ///
"""Raster-level sanity checks for already-assembled AICC report figures.

This complements ``aicc_figure_style.save_aicc_figure()``.  Matplotlib checks catch
text objects before export, while this script checks final PNG/JPEG/TIFF composites
made from OVITO renders, PIL/ImageMagick, screenshots, or other raster sources.
It cannot prove a figure is publication-ready; it highlights common report blockers
that need visual review at the final inserted width.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass
class RasterFigureCheck:
    path: str
    width_px: int
    height_px: int
    aspect_ratio: float
    final_width_in: float
    final_height_in: float
    border_median_hex: str
    border_document_delta: int
    near_white_fraction: float
    content_bbox_coverage: float
    warnings: list[str]


def check_image(path: Path, *, final_width_in: float = 6.8) -> RasterFigureCheck:
    image = Image.open(path).convert("RGB")
    arr = np.asarray(image)
    height, width = arr.shape[:2]
    aspect = width / height if height else 0.0
    final_height_in = final_width_in / aspect if aspect else 0.0

    near_white = (
        (arr[:, :, 0] >= 245)
        & (arr[:, :, 1] >= 245)
        & (arr[:, :, 2] >= 245)
    )
    near_white_fraction = float(near_white.mean())

    # Bounding box of the non-white "ink". A normal plot — even a sparse line
    # or bar chart that is mostly white — spreads ink (axes, ticks, labels)
    # across nearly the whole canvas, so its content bbox covers most of the
    # area. A screenshot/collage floating in a big blank canvas has its ink
    # confined to a small sub-region. Coverage, not raw white fraction,
    # separates the two.
    ink = ~near_white
    ink_rows = np.any(ink, axis=1)
    ink_cols = np.any(ink, axis=0)
    if ink_rows.any() and ink_cols.any():
        r0, r1 = int(np.argmax(ink_rows)), int(height - np.argmax(ink_rows[::-1]))
        c0, c1 = int(np.argmax(ink_cols)), int(width - np.argmax(ink_cols[::-1]))
        content_bbox_coverage = ((r1 - r0) * (c1 - c0)) / float(width * height) if width and height else 0.0
    else:
        content_bbox_coverage = 0.0

    border_px = max(8, min(width, height) // 80)
    border_mask = np.zeros((height, width), dtype=bool)
    border_mask[:border_px, :] = True
    border_mask[-border_px:, :] = True
    border_mask[:, :border_px] = True
    border_mask[:, -border_px:] = True
    border_pixels = arr[border_mask]
    border_median = np.median(border_pixels, axis=0).astype(int)
    document_white_delta = int(np.max(np.abs(border_median - np.array([255, 255, 255]))))
    border_median_hex = "#{:02x}{:02x}{:02x}".format(*border_median.tolist())

    warnings: list[str] = []
    if width < 1500 or height < 900:
        warnings.append(
            "low_pixel_budget: final report figures should usually be at least "
            "1500 px wide and 900 px tall before insertion"
        )
    if aspect > 2.45:
        warnings.append(
            "very_wide_short_canvas: check that panels remain readable after "
            "insertion; split or redesign if the figure becomes a thin strip"
        )
    if near_white_fraction > 0.92 and content_bbox_coverage < 0.55:
        warnings.append(
            "content_floats_in_blank_canvas: the drawn content spans only "
            f"{content_bbox_coverage:.0%} of the canvas while {near_white_fraction:.0%} "
            "is near-white — a screenshot/PIL collage floating in a large blank "
            "area should be cropped to the content or redesigned. (A normal sparse "
            "plot spreads axes/labels across the canvas and does not trip this.)"
        )
    if final_height_in < 2.6:
        warnings.append(
            "small_final_height: at the requested width this figure is shorter "
            "than 2.6 in; multi-panel labels and structure details may be unreadable"
        )
    if document_white_delta > 8:
        warnings.append(
            "non_white_outer_canvas: figure border/background median is "
            f"{border_median_hex}, which will appear as a visible block on a white "
            "docx page; use a white (#ffffff) outer canvas or crop to the data panel"
        )

    return RasterFigureCheck(
        path=str(path),
        width_px=width,
        height_px=height,
        aspect_ratio=round(aspect, 3),
        final_width_in=round(final_width_in, 3),
        final_height_in=round(final_height_in, 3),
        border_median_hex=border_median_hex,
        border_document_delta=document_white_delta,
        near_white_fraction=round(near_white_fraction, 4),
        content_bbox_coverage=round(content_bbox_coverage, 4),
        warnings=warnings,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--final-width-in", type=float, default=6.8)
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Exit with status 1 if any image emits a warning.",
    )
    args = parser.parse_args()

    checks = [check_image(path, final_width_in=args.final_width_in) for path in args.images]
    print(json.dumps([asdict(check) for check in checks], indent=2))
    has_warning = any(check.warnings for check in checks)
    return 1 if args.fail_on_warnings and has_warning else 0


if __name__ == "__main__":
    raise SystemExit(main())
