from pathlib import Path

import numpy as np


def write_trial(path: Path, area, pressure, decimal_comma: bool = True, encoding: str = "latin-1") -> None:
    lines = ["Some header text", "", "t[s]\tMma[A2]\tP1[mN/m]\tP2[mN/m]"]
    for t, (a, p) in enumerate(zip(area, pressure)):
        row = f"{t}\t{a:.3f}\t{p:.4f}\t{p:.4f}"
        lines.append(row.replace(".", ",") if decimal_comma else row)
    Path(path).write_text("\n".join(lines) + "\n", encoding=encoding)


def linear_isotherm(a_max=100.0, a_min=40.0, slope=0.5, n=300):
    """Pi = slope * (a_max - A): perfectly linear, so interpolation results are exact."""
    area = np.linspace(a_max, a_min, n)
    return area, slope * (a_max - area)
