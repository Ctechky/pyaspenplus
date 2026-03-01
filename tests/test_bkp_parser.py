"""Tests for the BKP file parser."""

import textwrap
import tempfile
from pathlib import Path

import pytest

from pyaspenplus.core.bkp_parser import BKPParser, BKPParserError


@pytest.fixture
def sample_bkp(tmp_path: Path) -> Path:
    """Create a minimal .bkp file for testing."""
    content = textwrap.dedent("""\
        ;This is a comment
        TITLE
            Methanol Synthesis Test Model

        DESCRIPTION
            A simple test simulation for methanol production.

        COMPONENTS
            H2 H2 / HYDROGEN
            CO2 CO2 / CARBON-DIOXIDE
            CO CO / CARBON-MONOXIDE
            CH3OH CH4O / METHANOL
            H2O H2O / WATER

        FLOWSHEET
            BLOCK REACTOR IN=FEED OUT=PRODUCT
            BLOCK HEATER IN=PRODUCT OUT=COOLED

        PROPERTIES RK-SOAVE

        STREAM FEED
            SUBSTREAM MIXED
            TEMP 250
            PRES 75
            FLOW
                H2 0.82
                CO2 0.03
                CO 0.01

        BLOCK REACTOR RPLUG
            PARAM TEMP=250
            PARAM PRES=75
            PARAM VOL=0.01

        BLOCK HEATER HEATER
    """)
    bkp_file = tmp_path / "test.bkp"
    bkp_file.write_text(content, encoding="utf-8")
    return bkp_file


class TestBKPParser:
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            BKPParser("nonexistent.bkp")

    def test_parse_components(self, sample_bkp: Path):
        result = BKPParser(sample_bkp).parse()
        ids = [c.component_id for c in result.components]
        assert "H2" in ids
        assert "CO2" in ids
        assert "CH3OH" in ids
        assert len(result.components) == 5

    def test_parse_property_method(self, sample_bkp: Path):
        result = BKPParser(sample_bkp).parse()
        assert result.property_method == "RK-SOAVE"

    def test_parse_metadata(self, sample_bkp: Path):
        result = BKPParser(sample_bkp).parse()
        assert "Methanol" in result.metadata.title

    def test_parse_flowsheet_blocks(self, sample_bkp: Path):
        result = BKPParser(sample_bkp).parse()
        block_names = [b.name for b in result.blocks]
        assert "REACTOR" in block_names
        assert "HEATER" in block_names

    def test_parse_streams(self, sample_bkp: Path):
        result = BKPParser(sample_bkp).parse()
        stream_names = [s.name for s in result.streams]
        assert "FEED" in stream_names

    def test_parse_stream_temperature(self, sample_bkp: Path):
        result = BKPParser(sample_bkp).parse()
        feed = next(s for s in result.streams if s.name == "FEED")
        assert feed.temperature == 250.0

    def test_parse_block_type(self, sample_bkp: Path):
        result = BKPParser(sample_bkp).parse()
        reactor = next(b for b in result.blocks if b.name == "REACTOR")
        assert reactor.block_type == "RPLUG"
