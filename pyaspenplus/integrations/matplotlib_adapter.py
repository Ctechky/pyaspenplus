"""Matplotlib/Seaborn integration — visualization utilities.

Provides ready-made plotting functions for pyaspenplus results:
stream profiles, block comparisons, optimization convergence, etc.

Install: ``pip install matplotlib seaborn``
"""

from __future__ import annotations

from typing import Any

try:
    import matplotlib
    import matplotlib.pyplot as plt

    _MPL_AVAILABLE = True
except ImportError:
    _MPL_AVAILABLE = False

try:
    import seaborn as sns

    _SEABORN_AVAILABLE = True
except ImportError:
    _SEABORN_AVAILABLE = False


def _require_matplotlib() -> None:
    if not _MPL_AVAILABLE:
        raise ImportError(
            "matplotlib is required for plotting. "
            "Install with: pip install matplotlib"
        )


class PlotAdapter:
    """Convenience plotting functions for pyaspenplus data.

    All methods return ``(fig, ax)`` tuples for further customisation.
    """

    def __init__(self, style: str = "seaborn-v0_8-whitegrid") -> None:
        _require_matplotlib()
        try:
            plt.style.use(style)
        except OSError:
            plt.style.use("ggplot")
        if _SEABORN_AVAILABLE:
            sns.set_palette("deep")

    # ------------------------------------------------------------------
    # Stream / profile plots
    # ------------------------------------------------------------------

    @staticmethod
    def plot_stream_temperatures(
        stream_names: list[str],
        temperatures: list[float],
        *,
        title: str = "Stream Temperatures",
        ylabel: str = "Temperature (K)",
    ) -> tuple:
        """Bar chart of stream temperatures."""
        _require_matplotlib()
        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.bar(stream_names, temperatures, edgecolor="black", alpha=0.85)
        ax.set_ylabel(ylabel, fontweight="bold")
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.tick_params(axis="x", rotation=45)

        for bar, t in zip(bars, temperatures):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(temperatures) * 0.01,
                f"{t:.1f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

        fig.tight_layout()
        return fig, ax

    @staticmethod
    def plot_composition_profile(
        z: Any,
        compositions: dict[str, Any],
        *,
        title: str = "Composition Profile",
        xlabel: str = "Reactor Length (m)",
        ylabel: str = "Mole Fraction",
    ) -> tuple:
        """Line plot of species mole fractions along a reactor / column.

        Parameters
        ----------
        z : array-like
            Position axis.
        compositions : dict
            ``{species_name: array_of_mole_fractions}``.
        """
        _require_matplotlib()
        fig, ax = plt.subplots(figsize=(10, 6))
        for species, y in compositions.items():
            ax.plot(z, y, linewidth=2, label=species)
        ax.set_xlabel(xlabel, fontsize=12, fontweight="bold")
        ax.set_ylabel(ylabel, fontsize=12, fontweight="bold")
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.legend(frameon=True)
        ax.grid(True, linestyle="--", alpha=0.4)
        fig.tight_layout()
        return fig, ax

    @staticmethod
    def plot_optimization_convergence(
        history: list[dict[str, Any]],
        *,
        objective_key: str = "objective",
        title: str = "Optimization Convergence",
    ) -> tuple:
        """Plot objective value vs evaluation number."""
        _require_matplotlib()
        import numpy as np

        obj_vals = [h[objective_key] for h in history if objective_key in h]
        evals = list(range(1, len(obj_vals) + 1))

        best_so_far = np.minimum.accumulate(obj_vals)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.scatter(evals, obj_vals, alpha=0.4, s=20, label="Evaluations")
        ax.plot(evals, best_so_far, color="red", linewidth=2, label="Best so far")
        ax.set_xlabel("Evaluation #", fontsize=12, fontweight="bold")
        ax.set_ylabel("Objective Value", fontsize=12, fontweight="bold")
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.4)
        fig.tight_layout()
        return fig, ax

    @staticmethod
    def plot_cost_breakdown(
        labels: list[str],
        values: list[float],
        *,
        title: str = "Cost Breakdown",
        currency: str = "$",
    ) -> tuple:
        """Pie chart for cost breakdown."""
        _require_matplotlib()
        fig, ax = plt.subplots(figsize=(8, 8))
        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            pctdistance=0.85,
        )
        for autotext in autotexts:
            autotext.set_fontsize(10)
        ax.set_title(title, fontsize=14, fontweight="bold")
        fig.tight_layout()
        return fig, ax

    @staticmethod
    def plot_block_comparison(
        block_names: list[str],
        metric_values: list[float],
        *,
        metric_name: str = "Duty (kW)",
        title: str = "Block Comparison",
    ) -> tuple:
        """Horizontal bar chart comparing a metric across blocks."""
        _require_matplotlib()
        fig, ax = plt.subplots(figsize=(10, max(4, len(block_names) * 0.5)))
        colors = plt.cm.viridis([i / max(len(block_names), 1) for i in range(len(block_names))])
        ax.barh(block_names, metric_values, color=colors, edgecolor="black", alpha=0.85)
        ax.set_xlabel(metric_name, fontsize=12, fontweight="bold")
        ax.set_title(title, fontsize=14, fontweight="bold")
        fig.tight_layout()
        return fig, ax

    @staticmethod
    def plot_sensitivity(
        param_values: Any,
        objective_values: Any,
        *,
        param_name: str = "Parameter",
        objective_name: str = "Objective",
        title: str = "Sensitivity Analysis",
    ) -> tuple:
        """Scatter/line plot of objective vs a single parameter."""
        _require_matplotlib()
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(param_values, objective_values, "o-", linewidth=2, markersize=6)
        ax.set_xlabel(param_name, fontsize=12, fontweight="bold")
        ax.set_ylabel(objective_name, fontsize=12, fontweight="bold")
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.grid(True, linestyle="--", alpha=0.4)
        fig.tight_layout()
        return fig, ax

    @staticmethod
    def available() -> bool:
        return _MPL_AVAILABLE
