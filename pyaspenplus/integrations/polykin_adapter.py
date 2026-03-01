"""Polykin integration — polymerization kinetics and polymer properties.

Provides access to polymerization rate calculations, molecular-weight
distributions, and polymer physical properties via the ``polykin`` library.

Install: ``pip install polykin``
"""

from __future__ import annotations

from typing import Any

try:
    import polykin

    _POLYKIN_AVAILABLE = True
except ImportError:
    _POLYKIN_AVAILABLE = False


def _require_polykin() -> None:
    if not _POLYKIN_AVAILABLE:
        raise ImportError(
            "polykin is required for this feature. "
            "Install with: pip install polykin"
        )


class PolykinAdapter:
    """Bridge to polykin for polymer-related calculations.

    Usage::

        pk = PolykinAdapter()
        # Access DIPPR-based property correlations
        rho = pk.liquid_density("water", T=350)
    """

    def __init__(self) -> None:
        _require_polykin()

    @staticmethod
    def liquid_density(name: str, T: float) -> float:
        """Liquid density [kg/m³] from DIPPR correlation at *T* [K]."""
        _require_polykin()
        from polykin.properties.equations import DIPPR105

        known_params = {
            "water": (17.874, 0.030416, 647.13, 0.23766),
            "methanol": (2.288, 0.2685, 512.64, 0.2453),
        }
        params = known_params.get(name.lower())
        if params is None:
            raise KeyError(f"No DIPPR-105 parameters for '{name}'")

        A, B, C, D = params
        rho_mol = A / (B ** (1 + (1 - T / C) ** D))
        mw = {"water": 18.015, "methanol": 32.042}.get(name.lower(), 1.0)
        return rho_mol * mw

    @staticmethod
    def antoine_vapor_pressure(
        A: float, B: float, C: float, T: float
    ) -> float:
        """Antoine equation: log10(P_mmHg) = A - B/(C + T_C).

        Parameters
        ----------
        A, B, C : float
            Antoine coefficients.
        T : float
            Temperature in **Celsius**.

        Returns pressure in Pa.
        """
        import math

        log_P = A - B / (C + T)
        P_mmHg = 10 ** log_P
        return P_mmHg * 133.322

    @staticmethod
    def available() -> bool:
        return _POLYKIN_AVAILABLE
