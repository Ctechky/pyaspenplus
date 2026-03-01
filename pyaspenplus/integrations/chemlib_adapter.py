"""Chemlib integration — stoichiometry, molar mass, and solution chemistry.

Provides quick access to molar-mass lookups, reaction balancing, and
molarity calculations using the ``chemlib`` library.

Install: ``pip install chemlib``
"""

from __future__ import annotations

from typing import Any

try:
    from chemlib import Compound, Reaction as CReaction

    _CHEMLIB_AVAILABLE = True
except ImportError:
    _CHEMLIB_AVAILABLE = False


def _require_chemlib() -> None:
    if not _CHEMLIB_AVAILABLE:
        raise ImportError(
            "chemlib is required for this feature. "
            "Install with: pip install chemlib"
        )


class ChemlibAdapter:
    """Bridge to chemlib for stoichiometric and molar-mass calculations.

    Usage::

        cl = ChemlibAdapter()
        mw = cl.molar_mass("CH3OH")          # 32.04 g/mol
        balanced = cl.balance_equation("CO2 + H2 --> CH3OH + H2O")
        print(balanced)
    """

    def __init__(self) -> None:
        _require_chemlib()

    # ------------------------------------------------------------------
    # Molar mass
    # ------------------------------------------------------------------

    @staticmethod
    def molar_mass(formula: str) -> float:
        """Molar mass [g/mol] of *formula* (e.g. ``'CH3OH'``)."""
        _require_chemlib()
        c = Compound(formula)
        mm = c.molar_mass
        return mm() if callable(mm) else mm

    @staticmethod
    def composition(formula: str) -> dict[str, float]:
        """Mass-percent composition of *formula*."""
        _require_chemlib()
        c = Compound(formula)
        pbm = c.percentage_by_mass
        return pbm() if callable(pbm) else pbm

    # ------------------------------------------------------------------
    # Reaction balancing
    # ------------------------------------------------------------------

    @staticmethod
    def balance_equation(equation: str) -> dict[str, Any]:
        """Balance a chemical equation string.

        Parameters
        ----------
        equation : str
            Equation in the form ``"CO2 + H2 --> CH3OH + H2O"``.

        Returns
        -------
        dict
            ``{"balanced": str, "coefficients": list[int]}``.
        """
        _require_chemlib()
        parts = equation.replace("-->", "->").split("->")
        if len(parts) != 2:
            raise ValueError("Equation must contain exactly one '->' or '-->'.")

        reactants = [s.strip() for s in parts[0].split("+")]
        products = [s.strip() for s in parts[1].split("+")]

        rxn = CReaction(reactants, products)
        rxn.balance()

        return {
            "balanced": rxn.formula,
            "coefficients": rxn.coefficients,
            "reactants": reactants,
            "products": products,
        }

    # ------------------------------------------------------------------
    # Validate pyaspenplus stoichiometry
    # ------------------------------------------------------------------

    @staticmethod
    def validate_stoichiometry(stoichiometry: dict[str, float]) -> dict[str, float]:
        """Check element balance for a stoichiometry dict.

        Returns a dict of element imbalances (should all be ~0 for a
        balanced reaction).
        """
        _require_chemlib()

        element_balance: dict[str, float] = {}
        for species, coeff in stoichiometry.items():
            try:
                c = Compound(species)
            except Exception:
                continue
            for element, count in c.occurences.items():
                element_balance[element] = (
                    element_balance.get(element, 0.0) + coeff * count
                )
        return element_balance

    @staticmethod
    def available() -> bool:
        return _CHEMLIB_AVAILABLE
