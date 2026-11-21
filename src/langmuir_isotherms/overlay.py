"""``isotherm-overlay``: draw several mean isotherms on one plot (no averaging)."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, Optional, Sequence

import matplotlib.pyplot as plt
import numpy as np

from .cli import add_plot_arguments, configure_logging, find_files, limit
from .fileio import IsothermFormatError, read_mean_file
from .plotting import finalize_axes, save_figure
from .processing import crop_mask

logger = logging.getLogger("isotherm-overlay")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="isotherm-overlay",
        description=(
            "Overlay mean isotherms (output of isotherm-average) on one common plot. "
            "Nothing is averaged and no input file is modified."
        ),
    )
    parser.add_argument("folder", type=Path, help="folder with the mean-isotherm .txt files")
    parser.add_argument("-o", "--output-name", default="isotherms_overlay", help="base name of the plot file")
    parser.add_argument("--pattern", default="mean_*.txt",
                        help="file name pattern (default: mean_*.txt); older files: 'izoterma_wypadkowa*.txt'")
    parser.add_argument("--exclude", nargs="*", default=[], metavar="NAME",
                        help="file names (with or without .txt) to skip")
    parser.add_argument("--label", nargs=2, action="append", default=[], metavar=("FILE", "LABEL"),
                        help="legend label for a file (file name without .txt); repeatable")
    parser.add_argument("--crop-file", nargs=3, action="append", default=[], metavar=("FILE", "MIN", "MAX"),
                        help="override --crop-x for one file, e.g. --crop-file mean_cancer 40 none; repeatable")
    parser.add_argument("--show-std", action="store_true", help="shade +/- standard deviation around each curve")
    parser.add_argument("--linewidth", type=float, default=2.0)
    parser.add_argument("--colors", nargs="+", default=None, help="e.g. --colors '#d62728' '#1f77b4'")
    parser.add_argument("--linestyles", nargs="+", default=None, help="e.g. --linestyles - -- :")
    add_plot_arguments(parser)
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def default_label(name: str) -> str:
    for prefix in ("mean_", "izoterma_wypadkowa_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name.replace("_pi-A", "")


def run(args: argparse.Namespace) -> None:
    files = find_files(args.folder, args.pattern,
                       exclude_prefixes=[args.output_name], exclude_names=args.exclude)
    if not files:
        raise FileNotFoundError(f"No files matching '{args.pattern}' in {args.folder}")

    labels: Dict[str, str] = {name: text for name, text in args.label}
    crops = {name: (limit(lo), limit(hi)) for name, lo, hi in args.crop_file}
    colors = args.colors or plt.rcParams["axes.prop_cycle"].by_key()["color"]

    fig, ax = plt.subplots(figsize=tuple(args.figsize))
    visible = []
    for i, path in enumerate(files):
        iso = read_mean_file(path)
        mask = crop_mask(iso.area, crops.get(iso.name, args.crop_x))
        x, y = iso.area[mask], iso.pressure[mask]
        if x.size == 0:
            logger.warning("%s: nothing left after cropping, skipped", iso.name)
            continue
        color = colors[i % len(colors)]
        style = args.linestyles[i % len(args.linestyles)] if args.linestyles else "-"
        ax.plot(x, y, lw=args.linewidth, color=color, ls=style,
                label=labels.get(iso.name, default_label(iso.name)))
        if args.show_std and iso.std is not None and not np.all(np.isnan(iso.std)):
            s = np.nan_to_num(iso.std[mask])
            ax.fill_between(x, y - s, y + s, color=color, alpha=0.18, lw=0)
        visible.append((x, y))
        logger.info("%s: %d points, A from %.2f to %.2f A^2, max Pi %.2f mN/m",
                    iso.name, x.size, x.min(), x.max(), y.max())

    if not visible:
        raise ValueError("Nothing to plot (check --crop-x and --pattern)")

    finalize_axes(ax, visible, args.xlim, args.ylim, args.invert_x,
                  args.xlabel, args.ylabel, args.title, grid=not args.no_grid)
    ax.legend(loc=args.legend_loc)
    fig.tight_layout()
    for path in save_figure(fig, args.folder, args.output_name, args.formats, args.dpi):
        logger.info("Saved plot: %s", path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose)
    try:
        run(args)
    except (IsothermFormatError, ValueError, FileNotFoundError, argparse.ArgumentTypeError) as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
