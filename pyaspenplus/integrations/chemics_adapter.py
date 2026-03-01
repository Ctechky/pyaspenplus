"""Chemics integration — chemical engineering property estimations.

Provides access to gas viscosity, thermal conductivity, molecular weight
calculations, and particle/bed properties via the ``chemics`` library.

Install: ``pip install chemics``
"""

from __future__ import annotations

from typing import Any

try:
    import chemics as cm

    _CHEMICS_AVAILABLE = True
except ImportError:
    _CHEMICS_AVAILABLE = False


def _require_chemics() -> None:
    if not _CHEMICS_AVAILABLE:
        raise ImportError(
            "chemics is required for this feature. "
            "Install with: pip install chemics"
        )


class ChemicsAdapter:
    """Bridge to chemics for gas-property and particle-property calculations.

    Usage::

        ca = ChemicsAdapter()
        mu = ca.gas_viscosity("H2", T=523.15)
        mw = ca.molecular_weight("CH3OH")
        umf = ca.minimum_fluidisation_velocity(dp=1e-4, rho_s=1190, rho_g=25, mu_g=2e-5)
    """

    def __init__(self) -> None:
        _require_chemics()

    # ------------------------------------------------------------------
    # Gas properties
    # ------------------------------------------------------------------

    @staticmethod
    def molecular_weight(formula: str) -> float:
        """Molecular weight [g/mol] from chemical formula."""
        _require_chemics()
        return cm.mw(formula)

    @staticmethod
    def gas_viscosity(formula: str, T: float) -> float:
        """Gas viscosity [µP] at temperature *T* [K] using chemics correlation.

        Falls back gracefully if the component is not in the chemics database.
        """
        _require_chemics()
        return cm.mu_gas(formula, T)

    @staticmethod
    def gas_thermal_conductivity(formula: str, T: float) -> float:
        """Gas thermal conductivity [W/(m·K)] at *T* [K]."""
        _require_chemics()
        return cm.k_gas(formula, T)

    # ------------------------------------------------------------------
    # Particle / bed properties (useful for catalytic reactor design)
    # ------------------------------------------------------------------

    @staticmethod
    def minimum_fluidisation_velocity(
        dp: float,
        rho_s: float,
        rho_g: float,
        mu_g: float,
    ) -> float:
        """Minimum fluidisation velocity [m/s] using the Ergun equation.

        Parameters
        ----------
        dp : float
            Particle diameter [m].
        rho_s : float
            Solid (catalyst) density [kg/m³].
        rho_g : float
            Gas density [kg/m³].
        mu_g : float
            Gas dynamic viscosity [Pa·s].
        """
        _require_chemics()
        return cm.umf(dp, rho_s, rho_g, mu_g)

    @staticmethod
    def terminal_velocity(
        dp: float,
        rho_s: float,
        rho_g: float,
        mu_g: float,
    ) -> float:
        """Terminal velocity [m/s] of a spherical particle."""
        _require_chemics()
        return cm.ut(dp, rho_s, rho_g, mu_g)

    @staticmethod
    def bed_expansion_ratio(
        umf: float,
        us: float,
    ) -> float:
        """Bed expansion ratio fb = (us / umf)^n for fluidised beds."""
        if umf <= 0:
            return float("inf")
        return us / umf

    @staticmethod
    def available() -> bool:
        return _CHEMICS_AVAILABLE
