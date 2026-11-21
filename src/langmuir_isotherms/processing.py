"""Numerical routines: averaging of isotherms and extraction of parameters."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

import numpy as np

from .fileio import Isotherm

Bounds = Tuple[Optional[float], Optional[float]]


@dataclass(frozen=True)
class MeanIsotherm:
    """Mean of several isotherms on a common area grid."""

    area: np.ndarray
    mean: np.ndarray
    std: np.ndarray       # sample standard deviation (ddof=1); NaN where fewer than 2 trials
    n_trials: np.ndarray  # number of trials contributing at each grid point


def crop_mask(x: np.ndarray, bounds: Bounds) -> np.ndarray:
    """Boolean mask of points with ``bounds[0] <= x <= bounds[1]`` (``None`` = unbounded)."""
    low, high = bounds
    mask = np.ones_like(x, dtype=bool)
    if low is not None:
        mask &= x >= low
    if high is not None:
        mask &= x <= high
    return mask


def average_isotherms(
    isotherms: Sequence[Isotherm],
    step: float = 0.1,
    common_range_only: bool = True,
) -> MeanIsotherm:
    """Average isotherms after linear interpolation onto a common area grid.

    Parameters
    ----------
    isotherms:
        Trials to average (at least one).
    step:
        Grid spacing in A^2.
    common_range_only:
        If True, only areas covered by *all* trials are used. If False, the grid
        spans the union of the ranges and edge points are averaged over the trials
        that reach them. No extrapolation is ever performed.
    """
    if not isotherms:
        raise ValueError("No isotherms to average")
    if step <= 0:
        raise ValueError("step must be positive")

    lows = [iso.area.min() for iso in isotherms]
    highs = [iso.area.max() for iso in isotherms]
    low, high = (max(lows), min(highs)) if common_range_only else (min(lows), max(highs))
    if low >= high:
        raise ValueError("The trials have no common area range")

    first, last = math.ceil(low / step), math.floor(high / step)
    grid = np.round(np.arange(first, last + 1) * step, 10)

    stack = np.vstack(
        [np.interp(grid, iso.area, iso.pressure, left=np.nan, right=np.nan) for iso in isotherms]
    )
    counts = np.sum(~np.isnan(stack), axis=0)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        mean = np.nanmean(stack, axis=0)
        std = np.nanstd(stack, axis=0, ddof=1) if len(isotherms) > 1 else np.full_like(mean, np.nan)
    std = np.where(counts > 1, std, np.nan)

    return MeanIsotherm(area=grid, mean=mean, std=std, n_trials=counts)


def area_at_pressure(isotherm: Isotherm, target_pressure: float) -> float:
    """Area per molecule at a given surface pressure.

    The isotherm is re-sorted by pressure, points with identical pressure are
    averaged and the area is obtained by linear interpolation A(Pi). Returns
    NaN when the pressure was not reached (no extrapolation).

    Note: for noisy, non-monotonic data the result is the interpolation of the
    sorted points, not the first crossing of the target pressure.
    """
    pressure, area = isotherm.pressure, isotherm.area
    if target_pressure < np.min(pressure) or target_pressure > np.max(pressure):
        return float("nan")

    order = np.argsort(pressure)
    p_sorted, a_sorted = pressure[order], area[order]
    unique_p, inverse = np.unique(p_sorted, return_inverse=True)
    if len(unique_p) < 2:
        return float("nan")
    mean_a = np.bincount(inverse, weights=a_sorted) / np.bincount(inverse)
    return float(np.interp(target_pressure, unique_p, mean_a))


def summary_stats(values: Sequence[float]) -> Tuple[float, float, int]:
    """Return ``(mean, sample SD, n)`` ignoring non-finite values.

    The SD uses ``ddof=1`` and is NaN when n < 2.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = len(arr)
    if n == 0:
        return float("nan"), float("nan"), 0
    sd = float(np.std(arr, ddof=1)) if n >= 2 else float("nan")
    return float(np.mean(arr)), sd, n
