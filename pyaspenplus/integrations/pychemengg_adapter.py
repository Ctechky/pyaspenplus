"""PyChemEngg integration — material/energy balances and heat transfer.

Bridges pyaspenplus stream and block data with PyChemEngg for quick
engineering calculations (heat exchanger sizing, energy balances).

Install: ``pip install pychemengg``
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import pychemengg.heattransfer as ht

    _PYCHEMENGG_AVAILABLE = True
except ImportError:
    _PYCHEMENGG_AVAILABLE = False


def _require_pychemengg() -> None:
    if not _PYCHEMENGG_AVAILABLE:
        raise ImportError(
            "pychemengg is required for this feature. "
            "Install with: pip install pychemengg"
        )


@dataclass
class EnergyBalanceResult:
    """Result of a stream energy-balance calculation."""

    Q_required: float = 0.0  # W
    T_out: float | None = None  # K
    delta_H: float = 0.0  # J/mol
    description: str = ""


class PyChemEnggAdapter:
    """Utility calculations via PyChemEngg.

    Provides helpers for heat-exchanger duty estimation and simple
    material/energy balance checks on pyaspenplus stream data.
    """

    def __init__(self) -> None:
        _require_pychemengg()

    # ------------------------------------------------------------------
    # Energy balance helpers
    # ------------------------------------------------------------------

    @staticmethod
    def heat_duty(
        mass_flow: float,
        cp: float,
        T_in: float,
        T_out: float,
    ) -> float:
        """Simple sensible-heat duty Q = m * cp * (T_out - T_in) [W].

        Parameters
        ----------
        mass_flow : float
            Mass flow rate [kg/s].
        cp : float
            Specific heat capacity [J/(kg·K)].
        T_in, T_out : float
            Inlet / outlet temperatures [K].
        """
        return mass_flow * cp * (T_out - T_in)

    @staticmethod
    def lmtd(
        T_hot_in: float,
        T_hot_out: float,
        T_cold_in: float,
        T_cold_out: float,
    ) -> float:
        """Log-mean temperature difference for a counter-current HX [K]."""
        import math

        dT1 = T_hot_in - T_cold_out
        dT2 = T_hot_out - T_cold_in

        if abs(dT1 - dT2) < 1e-6:
            return dT1
        if dT1 <= 0 or dT2 <= 0:
            raise ValueError("Temperature cross detected — LMTD is undefined.")
        return (dT1 - dT2) / math.log(dT1 / dT2)

    @staticmethod
    def hx_area(Q: float, U: float, lmtd_val: float) -> float:
        """Required HX area [m²]:  A = Q / (U * LMTD).

        Parameters
        ----------
        Q : float
            Heat duty [W].
        U : float
            Overall heat transfer coefficient [W/(m²·K)].
        lmtd_val : float
            Log-mean temperature difference [K].
        """
        if U * lmtd_val == 0:
            return float("inf")
        return abs(Q) / (U * lmtd_val)

    # ------------------------------------------------------------------
    # Material-balance check
    # ------------------------------------------------------------------

    @staticmethod
    def mass_balance_check(
        inlet_flows: dict[str, float],
        outlet_flows: dict[str, float],
    ) -> dict[str, float]:
        """Return component-wise mass imbalances (outlet − inlet).

        A balanced system should return values near zero.
        """
        all_comps = set(inlet_flows) | set(outlet_flows)
        return {
            c: outlet_flows.get(c, 0.0) - inlet_flows.get(c, 0.0)
            for c in sorted(all_comps)
        }

    @staticmethod
    def energy_balance_check(
        inlet_enthalpy: float,
        outlet_enthalpy: float,
        heat_added: float = 0.0,
        work_done: float = 0.0,
    ) -> float:
        """Return energy imbalance: Q + H_in - H_out - W (should be ~0)."""
        return heat_added + inlet_enthalpy - outlet_enthalpy - work_done

    @staticmethod
    def available() -> bool:
        return _PYCHEMENGG_AVAILABLE
