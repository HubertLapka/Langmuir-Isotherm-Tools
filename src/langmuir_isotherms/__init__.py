"""Tools for working with Langmuir pi-A isotherms exported from KSV NIMA."""

from .fileio import (
    Isotherm,
    IsothermFormatError,
    looks_like_trial,
    read_mean_file,
    read_trial,
    write_mean_file,
)
from .processing import MeanIsotherm, area_at_pressure, average_isotherms, summary_stats

__version__ = "0.1.0"

__all__ = [
    "Isotherm",
    "IsothermFormatError",
    "MeanIsotherm",
    "area_at_pressure",
    "average_isotherms",
    "looks_like_trial",
    "read_mean_file",
    "read_trial",
    "summary_stats",
    "write_mean_file",
]
