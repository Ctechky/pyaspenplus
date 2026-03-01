"""Pre-configured methanol synthesis model setup.

Provides a convenience class that wraps :class:`MethanolKinetics` with
typical feed conditions for CO2 hydrogenation to methanol at industrial
conditions (50–100 bar, 200–280 °C, Cu/ZnO/Al2O3 catalyst).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from pyaspenplus.examples.methanol.kinetics import MethanolKinetics


@dataclass
class MethanolSynthesis:
    """High-level methanol-synthesis model for quick evaluations.

    Includes default feed conditions and a simple adiabatic plug-flow
    reactor integration for standalone (non-Aspen) kinetic studies.

    Usage::

        model = MethanolSynthesis()
        profile = model.solve_pfr(length=0.15, n_points=100)
        print(profile["y_CH3OH"][-1])  # exit methanol mole fraction
    """

    # Default operating conditions
    temperature: float = 523.15  # K (250 °C)
    pressure: float = 75e5  # Pa (75 bar)
    feed_composition: dict[str, float] = field(default_factory=lambda: {
        "CO2": 0.0334,
        "H2": 0.8217,
        "CO": 0.0112,
        "CH3OH": 0.0,
        "H2O": 0.0,
        "N2": 0.1337,
    })
    total_molar_flow: float = 0.0144  # mol/s
    reactor_diameter: float = 0.016  # m (lab-scale tube)
    catalyst_void_fraction: float = 0.4

    kinetics: MethanolKinetics = field(default_factory=MethanolKinetics)

    # ------------------------------------------------------------------
    # Quick evaluation
    # ------------------------------------------------------------------

    def reaction_rates(
        self,
        T: float | None = None,
        P: float | None = None,
        y: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """Evaluate reaction rates at given (or default) conditions."""
        return self.kinetics.reaction_rates(
            T or self.temperature,
            P or self.pressure,
            y or self.feed_composition,
        )

    # ------------------------------------------------------------------
    # Simple isothermal PFR solver
    # ------------------------------------------------------------------

    def solve_pfr(
        self,
        length: float = 0.15,
        n_points: int = 200,
        *,
        isothermal: bool = True,
    ) -> dict[str, np.ndarray]:
        """Integrate a 1-D isothermal PFR and return axial profiles.

        Returns
        -------
        dict
            Keys: ``"z"`` (length), ``"y_<species>"`` for each species,
            ``"F_<species>"`` for molar flows [mol/s].
        """
        import math
        from scipy.integrate import solve_ivp

        species = ["CO2", "H2", "CO", "CH3OH", "H2O"]
        n_sp = len(species)

        A_cs = math.pi / 4 * self.reactor_diameter ** 2
        F_total_in = self.total_molar_flow
        F_in = np.array([self.feed_composition.get(sp, 0.0) * F_total_in for sp in species])

        T = self.temperature
        P = self.pressure

        def rhs(z: float, F: np.ndarray) -> np.ndarray:
            F_total = max(F.sum(), 1e-30)
            y = {sp: max(F[i] / F_total, 0.0) for i, sp in enumerate(species)}
            rates = self.kinetics.species_rates(T, P, y)
            dFdz = np.array([rates.get(sp, 0.0) * A_cs * (1 - self.catalyst_void_fraction)
                             for sp in species])
            return dFdz

        z_span = (0.0, length)
        z_eval = np.linspace(0, length, n_points)

        sol = solve_ivp(rhs, z_span, F_in, t_eval=z_eval, method="RK45",
                        rtol=1e-8, atol=1e-12)

        result: dict[str, np.ndarray] = {"z": sol.t}
        F_total = sol.y.sum(axis=0)
        F_total = np.where(F_total > 0, F_total, 1e-30)

        for i, sp in enumerate(species):
            result[f"F_{sp}"] = sol.y[i]
            result[f"y_{sp}"] = sol.y[i] / F_total

        return result
