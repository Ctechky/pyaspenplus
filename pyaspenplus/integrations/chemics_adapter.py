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
        return cm.molecular_weight(formula)

    @staticmethod
    def gas_viscosity(formula: str, T: float) -> float:
        """Gas viscosity [uP] at temperature *T* [K] using chemics Gas class."""
        _require_chemics()
        g = cm.Gas(formula, T)
        return g.viscosity()

    @staticmethod
    def gas_thermal_conductivity(formula: str, T: float) -> float:
        """Gas thermal conductivity [W/(m*K)] at *T* [K]."""
        _require_chemics()
        g = cm.Gas(formula, T)
        return g.thermal_conductivity()

    # ------------------------------------------------------------------
    # Particle / bed properties (useful for catalytic reactor design)
    # ------------------------------------------------------------------

    @staticmethod
    def archimedes_number(
        dp: float,
        rho_s: float,
        rho_g: float,
        mu_g: float,
    ) -> float:
        """Archimedes number for a particle in a fluid.

        Parameters
        ----------
        dp : float
            Particle diameter [m].
        rho_s : float
            Solid density [kg/m^3].
        rho_g : float
            Gas density [kg/m^3].
        mu_g : float
            Gas dynamic viscosity [Pa*s].
        """
        _require_chemics()
        return cm.archimedes(dp, rho_g, mu_g, rho_s)

    @staticmethod
    def minimum_fluidisation_velocity(
        dp: float,
        rho_s: float,
        rho_g: float,
        mu_g: float,
    ) -> float:
        """Minimum fluidisation velocity [m/s] using Wen-Yu correlation.

        Ar = d_p^3 * rho_g * (rho_s - rho_g) * g / mu_g^2
        Re_mf = (33.7^2 + 0.0408*Ar)^0.5 - 33.7
        u_mf = Re_mf * mu_g / (dp * rho_g)
        """
        import math
        g = 9.81
        Ar = dp**3 * rho_g * (rho_s - rho_g) * g / mu_g**2
        Re_mf = math.sqrt(33.7**2 + 0.0408 * Ar) - 33.7
        return Re_mf * mu_g / (dp * rho_g)

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
