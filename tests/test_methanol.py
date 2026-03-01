"""Tests for the methanol synthesis example."""

import pytest
import numpy as np

from pyaspenplus.examples.methanol.kinetics import MethanolKinetics
from pyaspenplus.examples.methanol.synthesis import MethanolSynthesis


class TestMethanolKinetics:
    def test_rates_are_nonzero(self):
        kin = MethanolKinetics()
        rates = kin.reaction_rates(
            T=523.15,
            P=75e5,
            y={"CO2": 0.03, "H2": 0.82, "CO": 0.01, "CH3OH": 0.0, "H2O": 0.0},
        )
        assert rates["r_methanol"] != 0
        assert rates["r_rwgs"] != 0

    def test_methanol_rate_positive_at_fresh_feed(self):
        kin = MethanolKinetics()
        rates = kin.reaction_rates(
            T=523.15,
            P=75e5,
            y={"CO2": 0.05, "H2": 0.90, "CO": 0.0, "CH3OH": 0.0, "H2O": 0.0},
        )
        assert rates["r_methanol"] > 0

    def test_species_rates_mass_balance(self):
        kin = MethanolKinetics()
        sr = kin.species_rates(
            T=523.15,
            P=75e5,
            y={"CO2": 0.03, "H2": 0.82, "CO": 0.01, "CH3OH": 0.005, "H2O": 0.005},
        )
        # C balance: CO2 consumed = CH3OH + CO produced
        c_in = -sr["CO2"]
        c_out = sr["CH3OH"] + sr["CO"]
        assert c_in == pytest.approx(c_out, rel=1e-10)

    def test_temperature_effect(self):
        kin = MethanolKinetics()
        y = {"CO2": 0.03, "H2": 0.82, "CO": 0.01, "CH3OH": 0.0, "H2O": 0.0}
        r_low = kin.reaction_rates(T=473.15, P=75e5, y=y)
        r_high = kin.reaction_rates(T=573.15, P=75e5, y=y)
        # Higher T should change rates (kinetics vs equilibrium trade-off)
        assert r_low["r_methanol"] != r_high["r_methanol"]


class TestMethanolSynthesis:
    def test_solve_pfr_returns_profiles(self):
        model = MethanolSynthesis()
        profile = model.solve_pfr(length=0.05, n_points=50)
        assert "z" in profile
        assert "y_CH3OH" in profile
        assert len(profile["z"]) == 50

    def test_methanol_increases_along_reactor(self):
        model = MethanolSynthesis()
        profile = model.solve_pfr(length=0.15, n_points=100)
        y_meoh = profile["y_CH3OH"]
        assert y_meoh[-1] > y_meoh[0]

    def test_h2_decreases_along_reactor(self):
        model = MethanolSynthesis()
        profile = model.solve_pfr(length=0.15, n_points=100)
        y_h2 = profile["y_H2"]
        assert y_h2[-1] < y_h2[0]
