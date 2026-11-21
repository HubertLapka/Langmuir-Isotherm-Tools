"""Generate synthetic KSV NIMA-like trial files for trying out the pipeline.

Creates, in the given output folder, two systems (``control`` and ``genistein``)
with three compressions each. The data are artificial and have no physical meaning.

Usage:
    python examples/make_synthetic_data.py data_demo
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


def write_trial(path: Path, area: np.ndarray, pressure: np.ndarray) -> None:
    """Write one file in a KSV NIMA-like layout (tab separated, decimal comma, latin-1)."""
    lines = [
        "Synthetic demo file (not real data)",
        "Subphase: demo",
        "",
        "t[s]\tMma[A2]\tP1[mN/m]\tP2[mN/m]",
    ]
    for t, (a, p) in enumerate(zip(area, pressure)):
        lines.append(f"{t}\t{a:.3f}\t{p:.4f}\t{p:.4f}".replace(".", ","))
    path.write_text("\n".join(lines) + "\n", encoding="latin-1")


def synthetic_isotherm(rng: np.random.Generator, onset: float, collapse: float) -> tuple:
    area = np.linspace(110.0, 35.0, 600)
    pressure = collapse / (1.0 + np.exp((area - onset) / 6.0))
    pressure += rng.normal(0.0, 0.08, area.size)
    return area, np.clip(pressure, 0.0, None)


def main(out_dir: str = "data_demo") -> None:
    rng = np.random.default_rng(42)
    systems = {"control": (62.0, 48.0), "genistein": (68.0, 50.0)}
    for system, (onset, collapse) in systems.items():
        folder = Path(out_dir) / system
        folder.mkdir(parents=True, exist_ok=True)
        for k in range(1, 4):
            area, pressure = synthetic_isotherm(rng, onset + rng.normal(0, 0.8), collapse + rng.normal(0, 0.5))
            write_trial(folder / f"trial_{k}.txt", area, pressure)
        print(f"Created 3 trials in {folder}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
