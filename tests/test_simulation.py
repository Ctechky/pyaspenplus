"""Tests for the Simulation class and metadata."""

import pytest

from pyaspenplus.core.metadata import SimulationInfo
from pyaspenplus.core.simulation import Simulation


class TestSimulationInfo:
    def test_summary(self):
        info = SimulationInfo(
            title="Test Sim",
            property_method="NRTL",
            components=["H2O", "MEOH"],
        )
        s = info.summary()
        assert "Test Sim" in s
        assert "NRTL" in s
        assert "H2O" in s

    def test_repr_truncates_long_component_list(self):
        info = SimulationInfo(components=[f"C{i}" for i in range(10)])
        r = repr(info)
        assert "+" in r  # indicates truncation


class TestSimulationBKPMode:
    """Verify Simulation raises properly when operations require COM."""

    def test_run_requires_com(self):
        sim = Simulation()
        sim._mode = "bkp"
        with pytest.raises(RuntimeError, match="COM mode"):
            sim.run()

    def test_set_value_requires_com(self):
        sim = Simulation()
        sim._mode = "bkp"
        with pytest.raises(RuntimeError, match="COM mode"):
            sim.set_value("some.path", 42)

    def test_get_value_requires_com(self):
        sim = Simulation()
        sim._mode = "bkp"
        with pytest.raises(RuntimeError, match="COM mode"):
            sim.get_value("some.path")
