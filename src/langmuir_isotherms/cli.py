"""Helpers shared by the command-line tools."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List, Optional, Sequence

from .fileio import looks_like_trial
from .processing import Bounds

LOGGER_FORMAT = "%(levelname)s: %(message)s"


def configure_logging(verbose: bool = False) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format=LOGGER_FORMAT)


def limit(value: str) -> Optional[float]:
    """Parse an axis/crop limit: a number or ``none`` (= unbounded)."""
    if value.strip().lower() in {"none", "null", "-"}:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"'{value}' is neither a number nor 'none'") from exc


def bounds_arg(parser: argparse.ArgumentParser, flag: str, help_text: str) -> None:
    parser.add_argument(
        flag, nargs=2, type=limit, metavar=("MIN", "MAX"), default=(None, None), help=help_text
    )


def find_files(
    folder: Path,
    pattern: str,
    exclude_prefixes: Sequence[str] = (),
    exclude_names: Sequence[str] = (),
) -> List[Path]:
    """Sorted list of files in ``folder`` matching ``pattern``, minus exclusions."""
    folder = Path(folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"Folder not found: {folder}")
    files = []
    for path in sorted(folder.glob(pattern)):
        if path.stem in exclude_names or path.name in exclude_names:
            continue
        if any(path.name.startswith(prefix) for prefix in exclude_prefixes):
            continue
        files.append(path)
    return files


def add_plot_arguments(parser: argparse.ArgumentParser) -> None:
    """Options affecting only the appearance of plots (never the numbers saved)."""
    group = parser.add_argument_group("plot options (visual only, data files are not changed)")
    bounds_arg(group, "--xlim", "x-axis range, e.g. --xlim 25 85 or --xlim 25 none")
    bounds_arg(group, "--ylim", "y-axis range, e.g. --ylim 0 55 (default: fit to visible curves)")
    bounds_arg(group, "--crop-x", "draw curves only for MIN <= A <= MAX, e.g. --crop-x 33 none")
    group.add_argument("--invert-x", action="store_true", help="large areas on the left (compression order)")
    group.add_argument("--xlabel", default="Powierzchnia na cząsteczkę [Å$^2$]")
    group.add_argument("--ylabel", default="Ciśnienie powierzchniowe $\\pi$ [mN/m]")
    group.add_argument("--title", default=None, help="plot title (default: none)")
    group.add_argument("--figsize", nargs=2, type=float, default=(8.0, 5.5), metavar=("W", "H"))
    group.add_argument("--dpi", type=int, default=300)
    group.add_argument("--formats", nargs="+", default=["png"], help="e.g. --formats png pdf")
    group.add_argument("--no-grid", action="store_true")
    group.add_argument("--legend-loc", default="best")


def find_trial_files(folder: Path, pattern: str, exclude_names: Sequence[str] = ()) -> List[Path]:
    """Like :func:`find_files`, but keep only raw KSV NIMA exports.

    Result files that happen to lie in the same folder (mean isotherms, reports)
    are skipped automatically because they have no ``t[s]`` table header.
    """
    logger = logging.getLogger(__name__)
    trials = []
    for path in find_files(folder, pattern, exclude_names=exclude_names):
        if looks_like_trial(path):
            trials.append(path)
        else:
            logger.info("Skipping %s (not a raw KSV NIMA export)", path.name)
    return trials
