"""``isotherm-stats``: characteristic parameters of one system from repeated trials."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

from .cli import configure_logging, find_trial_files
from .fileio import IsothermFormatError, read_trial
from .processing import area_at_pressure, summary_stats

logger = logging.getLogger("isotherm-stats")


def format_value(mean: float, sd: float) -> str:
    if not np.isfinite(mean):
        return "n/a"
    if not np.isfinite(sd):
        return f"{mean:.2f} +/- n.d."
    return f"{mean:.2f} +/- {sd:.2f}"


def pressure_key(pressure: float) -> str:
    return f"A{pressure:g}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="isotherm-stats",
        description=(
            "For each trial of one system compute the area per molecule at chosen surface "
            "pressures (linear interpolation, no extrapolation) and the maximum recorded "
            "pressure; report mean +/- sample SD over trials."
        ),
    )
    parser.add_argument("folder", type=Path, help="folder with the raw trial files of ONE system")
    parser.add_argument("--label", default=None, help="system name in the report (default: folder name)")
    parser.add_argument("-n", "--n-trials", type=int, default=None,
                        help="expected number of trials; error if the folder contains a different number")
    parser.add_argument("--pressures", nargs="+", type=float, default=[30.0, 32.5, 35.0], metavar="PI",
                        help="surface pressures in mN/m (default: 30 32.5 35)")
    parser.add_argument("--pattern", default="*.txt", help="file name pattern (default: *.txt)")
    parser.add_argument("--area-column", default="Mma")
    parser.add_argument("--pressure-column", default="P1")
    parser.add_argument("-o", "--output", default="parameters_summary.txt", help="report file name")
    parser.add_argument("--csv", default=None, help="optional CSV with per-trial values")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def run(args: argparse.Namespace) -> None:
    files = find_trial_files(args.folder, args.pattern, exclude_names=[args.output, args.csv or ""])
    if not files:
        raise FileNotFoundError(f"No files matching '{args.pattern}' in {args.folder}")
    if args.n_trials is not None and len(files) != args.n_trials:
        names = ", ".join(f.name for f in files)
        raise ValueError(f"Expected {args.n_trials} trial files, found {len(files)}: {names}")

    label = args.label or args.folder.resolve().name
    keys = [pressure_key(p) for p in args.pressures] + ["pi_max"]

    results: List[Dict[str, float]] = []
    names: List[str] = []
    for path in files:
        trial = read_trial(path, args.area_column, args.pressure_column)
        row = {pressure_key(p): area_at_pressure(trial, p) for p in args.pressures}
        row["pi_max"] = float(np.max(trial.pressure))
        results.append(row)
        names.append(path.name)
        logger.info("%s: %s", path.name, ", ".join(f"{k}={row[k]:.3f}" for k in keys))

    stats = {k: summary_stats([r[k] for r in results]) for k in keys}

    units = {k: "A^2" for k in keys}
    units["pi_max"] = "mN/m"
    lines = [
        "SUMMARY OF pi-A ISOTHERM PARAMETERS",
        "===================================",
        "",
        f"System: {label}",
        f"Number of trials: {len(results)}",
        "",
        "A_x is the area per molecule at surface pressure x [mN/m], obtained by linear",
        "interpolation of A(Pi) for each trial separately. No extrapolation outside the",
        "pressure range recorded in a trial (such trials give n/a). Mean +/- sample SD (n-1).",
        "",
        "pi_max is the MAXIMUM RECORDED pressure. It is not necessarily the collapse",
        "pressure; verify it on the isotherm.",
        "",
        "SUMMARY TABLE",
        "-------------",
        "System\t" + "\t".join(f"{k} [{units[k]}]" for k in keys),
        label + "\t" + "\t".join(format_value(*stats[k][:2]) for k in keys),
        "",
        "PER-TRIAL VALUES",
        "----------------",
        "File\t" + "\t".join(keys),
    ]
    for name, row in zip(names, results):
        lines.append(name + "\t" + "\t".join(f"{row[k]:.4f}" for k in keys))
    lines += ["", "NUMBER OF VALID RESULTS", "-----------------------"]
    lines += [f"{k}: n = {stats[k][2]}" for k in keys]

    out_path = args.folder / args.output
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Report saved: %s", out_path)

    if args.csv:
        csv_path = args.folder / args.csv
        rows = ["file," + ",".join(keys)]
        rows += [name + "," + ",".join(f"{row[k]:.6f}" for k in keys) for name, row in zip(names, results)]
        csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        logger.info("CSV saved: %s", csv_path)


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
