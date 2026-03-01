"""Bussche & Froment (1996) kinetics for methanol synthesis on Cu/ZnO/Al2O3.

Reactions
---------
1. CO2 hydrogenation:  CO2 + 3 H2  ->  CH3OH + H2O
2. Reverse water-gas shift:  CO2 + H2  ->  CO + H2O

Rate expressions follow the Langmuir-Hinshelwood-Hougen-Watson (LHHW) form
from Vanden Bussche & Froment, *J. Catal.* **161**, 1–10 (1996).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

R_GAS = 8.314  # J/(mol·K)


@dataclass
class MethanolKinetics:
    """Evaluate Bussche & Froment reaction rates.

    All parameters use SI units internally (Pa, K, mol, m³, s).

    Usage::

        kin = MethanolKinetics()
        rates = kin.reaction_rates(T=523.15, P=75e5,
                                   y={"CO2": 0.03, "H2": 0.82,
                                      "CO": 0.01, "CH3OH": 0.005,
                                      "H2O": 0.005})
    """

    # Kinetic parameters (default: Bussche & Froment 1996, Table 3)
    # Rate constant: k = A * exp(-Ea / (R*T))
    k1_A: float = 1.07  # mol/(kg_cat·s·bar^0.5)
    k1_Ea: float = 36_696.0  # J/mol (methanol synthesis)

    k2_A: float = 1.22e10  # mol/(kg_cat·s·bar)
    k2_Ea: float = 94_765.0  # J/mol (RWGS)

    # Adsorption equilibrium constants: K = A * exp(B / (R*T))
    Ka_H2O_H2_A: float = 3453.38
    Ka_H2O_H2_B: float = 0.0  # dimensionless, pre-built into A
    Ka_OH_A: float = 0.499
    Ka_OH_B: float = 17_197.0  # J/mol
    Ka_H2_A: float = 0.249
    Ka_H2_B: float = 34_099.0  # J/mol

    # Equilibrium constants (van't Hoff form: log10 Keq = a/T + b)
    Keq1_a: float = 3066.0
    Keq1_b: float = -10.592
    Keq2_a: float = -2073.0
    Keq2_b: float = 2.029

    catalyst_density: float = 1190.0  # kg/m³

    # Stoichiometry
    stoichiometry: dict[str, dict[str, float]] = field(default_factory=lambda: {
        "methanol_synthesis": {"CO2": -1, "H2": -3, "CH3OH": 1, "H2O": 1},
        "rwgs": {"CO2": -1, "H2": -1, "CO": 1, "H2O": 1},
    })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _Keq1(self, T: float) -> float:
        """Equilibrium constant for CO2 + 3H2 -> CH3OH + H2O."""
        return 10 ** (self.Keq1_a / T + self.Keq1_b)

    def _Keq2(self, T: float) -> float:
        """Equilibrium constant for RWGS: CO2 + H2 -> CO + H2O."""
        return 10 ** (self.Keq2_a / T + self.Keq2_b)

    def _k1(self, T: float) -> float:
        return self.k1_A * math.exp(-self.k1_Ea / (R_GAS * T))

    def _k2(self, T: float) -> float:
        return self.k2_A * math.exp(-self.k2_Ea / (R_GAS * T))

    def _Ka_H2O_H2(self, T: float) -> float:
        return self.Ka_H2O_H2_A

    def _Ka_OH(self, T: float) -> float:
        return self.Ka_OH_A * math.exp(self.Ka_OH_B / (R_GAS * T))

    def _Ka_H2(self, T: float) -> float:
        return self.Ka_H2_A * math.exp(self.Ka_H2_B / (R_GAS * T))

    # ------------------------------------------------------------------
    # Rate calculation
    # ------------------------------------------------------------------

    def reaction_rates(
        self,
        T: float,
        P: float,
        y: dict[str, float],
    ) -> dict[str, float]:
        """Compute volumetric reaction rates [mol/(m³_cat·s)].

        Parameters
        ----------
        T : float
            Temperature [K].
        P : float
            Total pressure [Pa].
        y : dict
            Mole fractions ``{"CO2": ..., "H2": ..., "CO": ...,
            "CH3OH": ..., "H2O": ...}``.

        Returns
        -------
        dict
            ``{"r_methanol": ..., "r_rwgs": ...}`` in mol/(m³_cat·s).
        """
        P_bar = P / 1e5

        p_CO2 = y.get("CO2", 0) * P_bar
        p_H2 = max(y.get("H2", 0) * P_bar, 1e-20)
        p_CO = y.get("CO", 0) * P_bar
        p_CH3OH = y.get("CH3OH", 0) * P_bar
        p_H2O = y.get("H2O", 0) * P_bar

        k1 = self._k1(T)
        k2 = self._k2(T)
        Keq1 = self._Keq1(T)
        Keq2 = self._Keq2(T)

        KH2O_H2 = self._Ka_H2O_H2(T)
        KOH = self._Ka_OH(T)
        KH2 = self._Ka_H2(T)

        sqrt_pH2 = math.sqrt(p_H2)

        # Driving forces
        driving_1 = p_CO2 * p_H2 - p_CH3OH * p_H2O / (Keq1 * p_H2 ** 2)
        driving_2 = p_CO2 - p_CO * p_H2O / (Keq2 * p_H2)

        # Adsorption denominator
        denom = (
            1
            + KH2O_H2 * p_H2O / p_H2
            + KOH * sqrt_pH2
            + KH2 * p_H2
        ) ** 3

        r_methanol_per_kg = k1 * driving_1 / denom
        r_rwgs_per_kg = k2 * driving_2 / denom

        rho = self.catalyst_density
        return {
            "r_methanol": r_methanol_per_kg * rho,
            "r_rwgs": r_rwgs_per_kg * rho,
        }

    def species_rates(
        self,
        T: float,
        P: float,
        y: dict[str, float],
    ) -> dict[str, float]:
        """Net production rate of each species [mol/(m³_cat·s)]."""
        r = self.reaction_rates(T, P, y)
        rm = r["r_methanol"]
        rw = r["r_rwgs"]

        return {
            "CO2": -rm - rw,
            "H2": -3 * rm - rw,
            "CH3OH": rm,
            "H2O": rm + rw,
            "CO": rw,
        }
