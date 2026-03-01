"""Reaction representations — stoichiometry, kinetics, and reaction sets."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyaspenplus.core.com_adapter import COMAdapter


class ReactionType(enum.Enum):
    """Aspen Plus reaction type classification."""

    KINETIC = "KINETIC"
    EQUILIBRIUM = "EQUILIBRIUM"
    CONVERSION = "CONVERSION"
    POWERLAW = "POWERLAW"
    LHHW = "LHHW"
    GENERAL = "GENERAL"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_string(cls, s: str) -> "ReactionType":
        s_upper = s.strip().upper()
        for member in cls:
            if member.value == s_upper:
                return member
        return cls.UNKNOWN


@dataclass
class KineticParameters:
    """Arrhenius-type kinetic parameters: k = A * T^n * exp(-Ea / RT)."""

    pre_exponential: float | None = None  # A
    activation_energy: float | None = None  # Ea  [J/mol]
    temperature_exponent: float = 0.0  # n
    reference_temperature: float | None = None  # T_ref [K]
    extra: dict[str, float] = field(default_factory=dict)

    def rate_constant(self, temperature: float) -> float:
        """Evaluate k at *temperature* [K] using Arrhenius equation."""
        import math

        R = 8.314  # J/(mol·K)
        A = self.pre_exponential or 0.0
        Ea = self.activation_energy or 0.0
        n = self.temperature_exponent
        return A * (temperature ** n) * math.exp(-Ea / (R * temperature))


@dataclass
class Reaction:
    """A single chemical reaction with optional kinetic data.

    Stoichiometry is stored as ``{component: coefficient}`` where
    *negative* values are reactants and *positive* values are products.
    """

    name: str = ""
    reaction_type: ReactionType = ReactionType.UNKNOWN

    stoichiometry: dict[str, float] = field(default_factory=dict)
    kinetics: KineticParameters | None = None
    heat_of_reaction: float | None = None  # J/mol

    # Raw Aspen parameter dump
    raw_parameters: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def reactants(self) -> dict[str, float]:
        return {k: abs(v) for k, v in self.stoichiometry.items() if v < 0}

    @property
    def products(self) -> dict[str, float]:
        return {k: v for k, v in self.stoichiometry.items() if v > 0}

    @property
    def equation_string(self) -> str:
        """Human-readable stoichiometric equation string."""
        lhs = " + ".join(
            f"{abs(v):.4g} {k}" if abs(v) != 1 else k
            for k, v in self.stoichiometry.items()
            if v < 0
        )
        rhs = " + ".join(
            f"{v:.4g} {k}" if v != 1 else k
            for k, v in self.stoichiometry.items()
            if v > 0
        )
        return f"{lhs} -> {rhs}"

    @property
    def kinetic_parameters(self) -> dict[str, Any]:
        """Flat dict of kinetic parameters for quick inspection."""
        if self.kinetics is None:
            return {}
        d: dict[str, Any] = {
            "A": self.kinetics.pre_exponential,
            "Ea": self.kinetics.activation_energy,
            "n": self.kinetics.temperature_exponent,
        }
        d.update(self.kinetics.extra)
        return {k: v for k, v in d.items() if v is not None}

    def __repr__(self) -> str:
        return f"Reaction({self.name!r}, type={self.reaction_type.value}, eq={self.equation_string!r})"


@dataclass
class ReactionSet:
    """An ordered collection of :class:`Reaction` objects."""

    name: str = ""
    reactions: list[Reaction] = field(default_factory=list)

    def __iter__(self):
        return iter(self.reactions)

    def __len__(self):
        return len(self.reactions)

    def __getitem__(self, idx: int | str) -> Reaction:
        if isinstance(idx, int):
            return self.reactions[idx]
        for r in self.reactions:
            if r.name == idx:
                return r
        raise KeyError(f"Reaction not found: {idx}")

    def __repr__(self) -> str:
        return f"ReactionSet({self.name!r}, n={len(self.reactions)})"


# ------------------------------------------------------------------
# Factory helpers
# ------------------------------------------------------------------


def reactions_from_com(adapter: "COMAdapter") -> list[Reaction]:
    """Extract reactions from the Aspen Plus COM tree."""
    reactions: list[Reaction] = []
    try:
        rxn_names = adapter.get_attribute_names("Data.Reactions.Reactions")
    except Exception:
        return reactions

    for rname in rxn_names:
        rxn = Reaction(name=rname)
        try:
            rtype = adapter.get_value(f"Data.Reactions.Reactions.{rname}.Input.TYPE")
            rxn.reaction_type = ReactionType.from_string(str(rtype))
        except Exception:
            pass

        try:
            stoic_node = adapter.get_node(f"Data.Reactions.Reactions.{rname}.Input.STOIC")
            for i in range(stoic_node.Elements.Count):
                el = stoic_node.Elements.Item(i)
                rxn.stoichiometry[el.Name] = el.Value
        except Exception:
            pass

        reactions.append(rxn)
    return reactions


def reactions_from_bkp(parsed: Any) -> list[Reaction]:
    """Build reactions from a :class:`BKPParseResult`."""
    reactions: list[Reaction] = []
    for rd in parsed.reactions:
        rxn = Reaction(
            name=rd.name,
            reaction_type=ReactionType.from_string(rd.reaction_type),
            stoichiometry=dict(rd.stoichiometry),
            raw_parameters=dict(rd.parameters),
        )
        reactions.append(rxn)
    return reactions
