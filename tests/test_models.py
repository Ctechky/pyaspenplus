"""Tests for models (blocks, streams, flowsheet)."""

import pytest

from pyaspenplus.models.blocks import Block, Reactor, block_class_for
from pyaspenplus.models.streams import Stream
from pyaspenplus.models.flowsheet import Flowsheet


class TestBlock:
    def test_block_class_for_reactor(self):
        cls = block_class_for("RPLUG")
        assert cls is Reactor

    def test_block_class_for_unknown(self):
        cls = block_class_for("WEIRD_BLOCK")
        assert cls is Block

    def test_parameter_access(self):
        b = Block(name="B1", parameters={"TEMP": 300})
        assert b.get_parameter("TEMP") == 300
        assert b.get_parameter("MISSING", 0) == 0


class TestStream:
    def test_composition_returns_mole_fracs(self):
        s = Stream(name="S1", mole_fractions={"H2": 0.5, "CO2": 0.5})
        assert s.composition == {"H2": 0.5, "CO2": 0.5}

    def test_get_flow(self):
        s = Stream(name="S1", component_molar_flows={"H2": 10.0})
        assert s.get_flow("H2") == 10.0

    def test_get_flow_missing_raises(self):
        s = Stream(name="S1")
        with pytest.raises(KeyError):
            s.get_flow("H2")


class TestFlowsheet:
    def test_get_block(self):
        fs = Flowsheet(blocks=[Block(name="A"), Block(name="B")])
        assert fs.get_block("A").name == "A"

    def test_get_block_missing_raises(self):
        fs = Flowsheet()
        with pytest.raises(KeyError):
            fs.get_block("X")

    def test_get_stream(self):
        fs = Flowsheet(streams=[Stream(name="S1")])
        assert fs.get_stream("S1").name == "S1"

    def test_downstream_blocks(self):
        b1 = Block(name="B1", outlet_streams=["S1"])
        b2 = Block(name="B2", inlet_streams=["S1"])
        fs = Flowsheet(blocks=[b1, b2])
        down = fs.downstream_blocks("B1")
        assert len(down) == 1
        assert down[0].name == "B2"
