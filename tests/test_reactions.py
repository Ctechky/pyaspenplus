"""Tests for the reactions module."""

import pytest

from pyaspenplus.reactions.reaction import (
    KineticParameters,
    Reaction,
    ReactionSet,
    ReactionType,
)


class TestReaction:
    def test_reactants_and_products(self):
        rxn = Reaction(
            name="methanol",
            stoichiometry={"CO2": -1, "H2": -3, "CH3OH": 1, "H2O": 1},
        )
        assert rxn.reactants == {"CO2": 1, "H2": 3}
        assert rxn.products == {"CH3OH": 1, "H2O": 1}

    def test_equation_string(self):
        rxn = Reaction(
            name="test",
            stoichiometry={"A": -1, "B": -2, "C": 1},
        )
        eq = rxn.equation_string
        assert "A" in eq
        assert "->" in eq
        assert "C" in eq

    def test_reaction_type_from_string(self):
        assert ReactionType.from_string("KINETIC") == ReactionType.KINETIC
        assert ReactionType.from_string("unknown_stuff") == ReactionType.UNKNOWN


class TestKineticParameters:
    def test_rate_constant(self):
        kp = KineticParameters(
            pre_exponential=1e10,
            activation_energy=50000,
        )
        k_500 = kp.rate_constant(500)
        k_600 = kp.rate_constant(600)
        assert k_600 > k_500  # rate constant increases with temperature

    def test_zero_activation_energy(self):
        kp = KineticParameters(pre_exponential=42.0, activation_energy=0)
        assert kp.rate_constant(300) == pytest.approx(42.0)


class TestReactionSet:
    def test_iteration(self):
        rs = ReactionSet(reactions=[
            Reaction(name="r1"),
            Reaction(name="r2"),
        ])
        assert len(rs) == 2
        names = [r.name for r in rs]
        assert names == ["r1", "r2"]

    def test_lookup_by_name(self):
        rs = ReactionSet(reactions=[
            Reaction(name="rxn_A"),
            Reaction(name="rxn_B"),
        ])
        assert rs["rxn_B"].name == "rxn_B"

    def test_lookup_missing_raises(self):
        rs = ReactionSet(reactions=[])
        with pytest.raises(KeyError):
            rs["missing"]
