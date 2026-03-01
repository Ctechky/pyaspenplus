"""Cantera integration — chemical kinetics and reactor modelling.

Bridges pyaspenplus reaction data with Cantera's powerful kinetics engine
for mechanism validation, sensitivity analysis, and standalone reactor
simulations.

Install: ``pip install cantera``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    import cantera as ct

    _CANTERA_AVAILABLE = True
except ImportError:
    _CANTERA_AVAILABLE = False


def _require_cantera() -> None:
    if not _CANTERA_AVAILABLE:
        raise ImportError(
            "Cantera is required for this feature. "
            "Install with: pip install cantera"
        )


class CanteraAdapter:
    """Bridge between pyaspenplus and Cantera for kinetics & reactor analysis.

    Usage::

        adapter = CanteraAdapter()

        # Create a Cantera Solution from pyaspenplus components
        gas = adapter.create_solution(
            species=["H2", "CO2", "CO", "CH3OH", "H2O"],
            mechanism="methanol.yaml",
        )

        # Run an ideal-gas reactor
        result = adapter.run_pfr(gas, length=0.15, area=2e-4,
                                 T=523, P=75e5,
                                 X={"H2": 0.82, "CO2": 0.03, "CO": 0.01})
    """

    def __init__(self) -> None:
        _require_cantera()

    # ------------------------------------------------------------------
    # Solution creation
    # ------------------------------------------------------------------

    @staticmethod
    def create_ideal_gas(
        species: list[str] | None = None,
        mechanism: str | None = None,
        *,
        T: float = 300.0,
        P: float = 101325.0,
        X: dict[str, float] | None = None,
    ) -> "ct.Solution":
        """Create a Cantera ``Solution`` object.

        Parameters
        ----------
        species : list[str], optional
            Species names (used with built-in Cantera mechanisms).
        mechanism : str, optional
            Path to a ``.yaml`` / ``.cti`` mechanism file.
        T, P : float
            Initial temperature [K] and pressure [Pa].
        X : dict
            Initial mole fractions.
        """
        _require_cantera()
        if mechanism:
            gas = ct.Solution(mechanism)
        else:
            gas = ct.Solution("gri30.yaml")

        if X:
            gas.TPX = T, P, X
        else:
            gas.TP = T, P
        return gas

    # ------------------------------------------------------------------
    # Reactor simulations
    # ------------------------------------------------------------------

    @staticmethod
    def run_batch_reactor(
        gas: "ct.Solution",
        residence_time: float = 1.0,
        n_steps: int = 500,
    ) -> dict[str, Any]:
        """Run a constant-volume batch reactor and return time profiles.

        Returns dict with keys: ``t``, ``T``, ``P``, and species names.
        """
        _require_cantera()
        import numpy as np

        reactor = ct.IdealGasReactor(gas)
        sim = ct.ReactorNet([reactor])

        t_arr = np.linspace(0, residence_time, n_steps)
        T_arr = np.zeros(n_steps)
        P_arr = np.zeros(n_steps)
        Y_arr = np.zeros((n_steps, gas.n_species))

        for i, t in enumerate(t_arr):
            sim.advance(t)
            T_arr[i] = reactor.T
            P_arr[i] = reactor.thermo.P
            Y_arr[i, :] = reactor.thermo.Y

        result: dict[str, Any] = {"t": t_arr, "T": T_arr, "P": P_arr}
        for j, name in enumerate(gas.species_names):
            result[name] = Y_arr[:, j]
        return result

    @staticmethod
    def run_pfr(
        gas: "ct.Solution",
        length: float = 1.0,
        area: float = 1e-4,
        *,
        n_steps: int = 200,
        u_inlet: float = 0.1,
    ) -> dict[str, Any]:
        """Approximate a plug-flow reactor by stepping a series of CSTRs.

        Parameters
        ----------
        gas : ct.Solution
            Configured inlet gas state.
        length : float
            Reactor length [m].
        area : float
            Cross-sectional area [m^2].
        n_steps : int
            Number of CSTR steps.
        u_inlet : float
            Inlet velocity [m/s].

        Returns dict with ``z`` (position) and species mole fractions.
        """
        _require_cantera()
        import numpy as np

        dz = length / n_steps
        dt = dz / u_inlet

        z_arr = np.linspace(0, length, n_steps)
        T_arr = np.zeros(n_steps)
        X_arr = np.zeros((n_steps, gas.n_species))

        reactor = ct.IdealGasConstPressureReactor(gas)
        sim = ct.ReactorNet([reactor])

        for i in range(n_steps):
            T_arr[i] = reactor.T
            X_arr[i, :] = reactor.thermo.X
            sim.advance(sim.time + dt)

        result: dict[str, Any] = {"z": z_arr, "T": T_arr}
        for j, name in enumerate(gas.species_names):
            result[f"X_{name}"] = X_arr[:, j]
        return result

    # ------------------------------------------------------------------
    # Equilibrium calculations
    # ------------------------------------------------------------------

    @staticmethod
    def equilibrium(
        gas: "ct.Solution",
        condition: str = "TP",
    ) -> dict[str, float]:
        """Compute chemical equilibrium and return the final mole fractions.

        Parameters
        ----------
        gas : ct.Solution
            Must have T, P, X already set.
        condition : str
            Equilibrium specification, e.g. ``"TP"`` or ``"HP"``.
        """
        _require_cantera()
        gas.equilibrate(condition)
        return {sp: x for sp, x in zip(gas.species_names, gas.X) if x > 1e-15}

    # ------------------------------------------------------------------
    # Export pyaspenplus reactions to Cantera format
    # ------------------------------------------------------------------

    @staticmethod
    def reactions_to_yaml(reactions: Any) -> str:
        """Convert pyaspenplus ``ReactionSet`` to a YAML-like string for Cantera."""
        lines = ["# Auto-generated from pyaspenplus reactions", "reactions:"]
        for rxn in reactions:
            stoic = rxn.stoichiometry
            reactants = " + ".join(
                f"{abs(v)} {k}" if abs(v) != 1 else k
                for k, v in stoic.items() if v < 0
            )
            products = " + ".join(
                f"{v} {k}" if v != 1 else k
                for k, v in stoic.items() if v > 0
            )
            lines.append(f"- equation: {reactants} => {products}")

            if rxn.kinetics:
                kp = rxn.kinetics
                lines.append("  rate-constant: {")
                if kp.pre_exponential is not None:
                    lines.append(f"    A: {kp.pre_exponential},")
                lines.append(f"    b: {kp.temperature_exponent},")
                if kp.activation_energy is not None:
                    lines.append(f"    Ea: {kp.activation_energy}")
                lines.append("  }")
        return "\n".join(lines)

    @staticmethod
    def available() -> bool:
        return _CANTERA_AVAILABLE
