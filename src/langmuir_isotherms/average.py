"""``isotherm-average``: average repeated compressions into one isotherm."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional, Sequence

import matplotlib.pyplot as plt

from .cli import add_plot_arguments, configure_logging, find_trial_files
from .fileio import IsothermFormatError, read_trial, write_mean_file
from .plotting import finalize_axes, save_figure
from .processing import average_isotherms, crop_mask

logger = logging.getLogger("isotherm-average")

TRIAL_COLORS = ["#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#17becf"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="isotherm-average",
        description=(
            "Average several repeated pi-A isotherms (one KSV NIMA .txt file per trial) "
            "into one mean isotherm. Writes <output-name>.txt (full range) and a plot."
        ),
    )
    parser.add_argument("folder", type=Path, help="folder with the raw trial files of ONE system")
    parser.add_argument("-o", "--output-name", default="mean_isotherm", help="base name of output files")
    parser.add_argument("-n", "--n-trials", type=int, default=None,
                        help="expected number of trials; stop with an error if the folder contains a different number")
    parser.add_argument("--pattern", default="*.txt", help="file name pattern (default: *.txt)")
    parser.add_argument("--step", type=float, default=0.1, help="grid step in A^2 (default: 0.1)")
    parser.add_argument("--include-edges", action="store_true",
                        help="use the union of trial ranges instead of only the common range")
    parser.add_argument("--area-column", default="Mma", help="beginning of the area column name (default: Mma)")
    parser.add_argument("--pressure-column", default="P1", help="beginning of the pressure column name (default: P1)")
    parser.add_argument("--decimal", choices=["comma", "point"], default="comma",
                        help="decimal separator in the output .txt (default: comma, convenient for Polish Excel)")
    parser.add_argument("--crop-mean-only", action="store_true",
                        help="apply --crop-x to the mean only; draw single trials in full")
    add_plot_arguments(parser)
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def run(args: argparse.Namespace) -> None:
    files = find_trial_files(args.folder, args.pattern, exclude_names=[args.output_name])
    if not files:
        raise FileNotFoundError(f"No files matching '{args.pattern}' in {args.folder}")
    if args.n_trials is not None and len(files) != args.n_trials:
        names = ", ".join(f.name for f in files)
        raise ValueError(f"Expected {args.n_trials} trial files, found {len(files)}: {names}")

    trials = []
    for path in files:
        trial = read_trial(path, args.area_column, args.pressure_column)
        trials.append(trial)
        logger.info("%s: %d points, A from %.2f to %.2f A^2",
                    path.name, len(trial.area), trial.area.min(), trial.area.max())

    mean = average_isotherms(trials, step=args.step, common_range_only=not args.include_edges)

    txt_path = args.folder / f"{args.output_name}.txt"
    write_mean_file(txt_path, mean.area, mean.mean, mean.std, mean.n_trials,
                    decimal_comma=(args.decimal == "comma"))
    logger.info("Saved data (full range): %s", txt_path)

    fig, ax = plt.subplots(figsize=tuple(args.figsize))
    visible = []
    for i, trial in enumerate(trials):
        mask = crop_mask(trial.area, args.crop_x) if not args.crop_mean_only else slice(None)
        ax.plot(trial.area[mask], trial.pressure[mask], lw=1, alpha=0.7,
                color=TRIAL_COLORS[i % len(TRIAL_COLORS)], label=trial.name)
        visible.append((trial.area[mask], trial.pressure[mask]))
    mask = crop_mask(mean.area, args.crop_x)
    ax.plot(mean.area[mask], mean.mean[mask], color="red", lw=2.2, label="Wypadkowa (średnia)")
    visible.append((mean.area[mask], mean.mean[mask]))

    title = args.title if args.title is not None else f"Izoterma π–A (liczba prób: {len(trials)})"
    finalize_axes(ax, visible, args.xlim, args.ylim, args.invert_x,
                  args.xlabel, args.ylabel, title, grid=not args.no_grid)
    ax.legend(loc=args.legend_loc)
    fig.tight_layout()
    for path in save_figure(fig, args.folder, args.output_name, args.formats, args.dpi):
        logger.info("Saved plot: %s", path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose)
    try:
        run(args)
    except (IsothermFormatError, ValueError, FileNotFoundError) as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
