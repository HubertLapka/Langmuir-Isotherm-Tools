"""Reading and writing of isotherm text files.

Two kinds of files are handled:

* **trial files** - raw exports from KSV NIMA (one compression = one file);
* **mean files** - the output of ``isotherm-average`` (tab separated, four columns).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)

HEADER_MARKER = "t[s]"
MEAN_FILE_HEADER = "A_A2\tPi_mean_mN_per_m\tPi_std_mN_per_m\tn_trials"


class IsothermFormatError(ValueError):
    """Raised when an input file does not have the expected structure."""


@dataclass(frozen=True)
class Isotherm:
    """A single isotherm: pressure as a function of area per molecule.

    Attributes
    ----------
    name:
        File name without extension.
    area:
        Area per molecule in A^2, sorted in ascending order, without duplicates.
    pressure:
        Surface pressure in mN/m, same length as ``area``.
    std:
        Optional standard deviation of ``pressure`` (only for mean files).
    """

    name: str
    area: np.ndarray
    pressure: np.ndarray
    std: Optional[np.ndarray] = None


def _to_float(text: str) -> float:
    """Convert a string with either a decimal comma or a decimal point."""
    return float(text.strip().replace(",", "."))


def _collapse_duplicates(x: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Sort by ``x`` and average ``y`` over repeated ``x`` values."""
    order = np.argsort(x, kind="stable")
    x, y = x[order], y[order]
    unique_x, inverse = np.unique(x, return_inverse=True)
    mean_y = np.bincount(inverse, weights=y) / np.bincount(inverse)
    return unique_x, mean_y


def _read_text_lines(path: Path, encodings: Sequence[str]) -> list:
    last_error: Optional[Exception] = None
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding).splitlines()
        except UnicodeDecodeError as exc:  # try the next encoding
            last_error = exc
    raise IsothermFormatError(f"Cannot decode {path}: {last_error}")


def looks_like_trial(path: Path, encoding: str = "latin-1") -> bool:
    """True if the file contains a KSV NIMA table header (a line starting with ``t[s]``).

    Used to skip result files (means, reports) that may share the folder with raw trials.
    """
    try:
        lines = Path(path).read_text(encoding=encoding).splitlines()
    except (OSError, UnicodeDecodeError):
        return False
    return any(line.strip().startswith(HEADER_MARKER) for line in lines)


def read_trial(
    path: Path,
    area_column: str = "Mma",
    pressure_column: str = "P1",
    encoding: str = "latin-1",
) -> Isotherm:
    """Read one raw KSV NIMA export.

    The file must contain a header line starting with ``t[s]``; the columns
    are located by the *beginning* of their names (``Mma`` and ``P1`` by default).
    Non-numeric rows are ignored; repeated area values are averaged.
    """
    path = Path(path)
    lines = _read_text_lines(path, (encoding,))

    header_index = next(
        (i for i, line in enumerate(lines) if line.strip().startswith(HEADER_MARKER)), None
    )
    if header_index is None:
        raise IsothermFormatError(f"{path.name}: header line starting with '{HEADER_MARKER}' not found")

    headers = [h.strip() for h in lines[header_index].split("\t")]

    def column_index(prefix: str) -> int:
        for i, header in enumerate(headers):
            if header.startswith(prefix):
                return i
        raise IsothermFormatError(
            f"{path.name}: no column starting with '{prefix}'. Available columns: {headers}"
        )

    ix, iy = column_index(area_column), column_index(pressure_column)

    area, pressure = [], []
    for line in lines[header_index + 1:]:
        fields = line.split("\t")
        try:
            a, p = _to_float(fields[ix]), _to_float(fields[iy])
        except (ValueError, IndexError):
            continue
        if np.isfinite(a) and np.isfinite(p):
            area.append(a)
            pressure.append(p)

    if len(area) < 2:
        raise IsothermFormatError(f"{path.name}: fewer than two valid data points")

    x, y = _collapse_duplicates(np.asarray(area, float), np.asarray(pressure, float))
    return Isotherm(name=path.stem, area=x, pressure=y)


def read_mean_file(path: Path) -> Isotherm:
    """Read a file produced by :func:`write_mean_file`.

    Only the first two columns are required; the third (standard deviation)
    is optional and may be empty. Header lines are skipped automatically,
    so files written by older versions of the scripts are accepted too.
    """
    path = Path(path)
    lines = _read_text_lines(path, ("utf-8", "latin-1"))

    area, pressure, std = [], [], []
    for line in lines:
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        try:
            a, p = _to_float(fields[0]), _to_float(fields[1])
        except ValueError:
            continue  # header or damaged line
        try:
            s = _to_float(fields[2]) if len(fields) > 2 and fields[2].strip() else np.nan
        except ValueError:
            s = np.nan
        area.append(a)
        pressure.append(p)
        std.append(s)

    if not area:
        raise IsothermFormatError(f"{path.name}: no numeric data rows found")

    order = np.argsort(area, kind="stable")
    return Isotherm(
        name=path.stem,
        area=np.asarray(area)[order],
        pressure=np.asarray(pressure)[order],
        std=np.asarray(std)[order],
    )


def write_mean_file(
    path: Path,
    area: np.ndarray,
    mean: np.ndarray,
    std: np.ndarray,
    n_trials: np.ndarray,
    decimal_comma: bool = True,
) -> None:
    """Write a mean isotherm, ordered from the largest to the smallest area."""
    order = np.argsort(-area)
    rows = [MEAN_FILE_HEADER]
    for a, p, s, n in zip(area[order], mean[order], std[order], n_trials[order]):
        std_text = "" if np.isnan(s) else f"{s:.4f}"
        row = f"{a:.2f}\t{p:.4f}\t{std_text}\t{int(n)}"
        rows.append(row.replace(".", ",") if decimal_comma else row)
    Path(path).write_text("\n".join(rows) + "\n", encoding="utf-8")
