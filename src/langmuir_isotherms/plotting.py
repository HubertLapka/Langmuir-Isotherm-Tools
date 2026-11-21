"""Matplotlib helpers (headless backend)."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .processing import Bounds  # noqa: E402


def finalize_axes(
    ax: "plt.Axes",
    visible: Sequence[Tuple[np.ndarray, np.ndarray]],
    xlim: Bounds,
    ylim: Bounds,
    invert_x: bool,
    xlabel: str,
    ylabel: str,
    title: Optional[str],
    grid: bool,
) -> None:
    """Apply axis limits (auto-fitting y to the visible part), labels and grid."""
    ax.set_xlim(left=xlim[0], right=xlim[1])
    if invert_x:
        ax.invert_xaxis()

    if ylim != (None, None):
        ax.set_ylim(bottom=ylim[0], top=ylim[1])
    else:
        x_low, x_high = sorted(ax.get_xlim())
        chunks: List[np.ndarray] = []
        for x, y in visible:
            selected = y[(x >= x_low) & (x <= x_high)]
            selected = selected[np.isfinite(selected)]
            if selected.size:
                chunks.append(selected)
        if chunks:
            values = np.concatenate(chunks)
            low, high = values.min(), values.max()
            pad = 0.05 * (high - low if high > low else 1.0)
            ax.set_ylim(low - pad, high + pad)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    if grid:
        ax.grid(alpha=0.3)


def save_figure(fig: "plt.Figure", folder, name: str, formats: Sequence[str], dpi: int) -> List[str]:
    """Save ``fig`` in each requested format and return the written paths."""
    written = []
    for fmt in formats:
        path = folder / f"{name}.{fmt.lstrip('.')}"
        fig.savefig(path, dpi=dpi)
        written.append(str(path))
    return written
