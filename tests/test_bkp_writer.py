"""Tests for BKP write-back and batch runner modules."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pyaspenplus.core.bkp_writer import BKPWriter, BKPWriterError
from pyaspenplus.core.batch_runner import BatchRunner, find_aspen_executable, BatchRunResult


# ---------------------------------------------------------------------------
# Fixture: minimal BKP content
# ---------------------------------------------------------------------------

SAMPLE_BKP = textwrap.dedent("""\
    TITLE
        Methanol synthesis test model

    IN-UNITS MET

    COMPONENTS
        CO2 CO2 / Carbon-dioxide
        H2 H2 / Hydrogen
        CH3OH CH4O / Methanol
        H2O H2O / Water
        CO CO / Carbon-monoxide
        N2 N2 / Nitrogen

    FLOWSHEET
        BLOCK REACTOR IN=FEED OUT=PRODUCT

    PROPERTIES RK-SOAVE

    STREAM FEED
        SUBSTREAM MIXED
        TEMP 523.15
        PRES 75.0
        TOTFLOW 100.0
        MOLE-FRAC
            CO2 0.0300
            H2 0.8200
            CH3OH 0.0000
            H2O 0.0000
            CO 0.0100
            N2 0.1400

    BLOCK REACTOR RSTOIC
        PARAM TEMP 523.15
        PARAM PRES 75.0
        PARAM DUTY 0.0
""")


@pytest.fixture
def bkp_file(tmp_path: Path) -> Path:
    """Write a sample BKP file and return its path."""
    p = tmp_path / "test_model.bkp"
    p.write_text(SAMPLE_BKP, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# BKPWriter tests
# ---------------------------------------------------------------------------


class TestBKPWriter:

    def test_load(self, bkp_file: Path):
        w = BKPWriter(bkp_file)
        assert w.filepath == bkp_file
        assert len(w.change_log) == 0

    def test_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            BKPWriter(tmp_path / "nonexistent.bkp")

    def test_set_stream_temp(self, bkp_file: Path):
        w = BKPWriter(bkp_file)
        w.set_stream_temp("FEED", 600.0)
        assert len(w.change_log) == 1
        assert "600.0" in w.change_log[0]
        assert "523.15" in w.change_log[0]

    def test_set_stream_pressure(self, bkp_file: Path):
        w = BKPWriter(bkp_file)
        w.set_stream_pressure("FEED", 100.0)
        assert len(w.change_log) == 1
        assert "100.0" in w.change_log[0]

    def test_set_stream_total_flow(self, bkp_file: Path):
        w = BKPWriter(bkp_file)
        w.set_stream_total_flow("FEED", 200.0)
        assert len(w.change_log) == 1
        assert "200.0" in w.change_log[0]

    def test_set_stream_component_flow(self, bkp_file: Path):
        w = BKPWriter(bkp_file)
        w.set_stream_component_flow("FEED", "CO2", 0.05)
        assert len(w.change_log) == 1
        assert "0.05" in w.change_log[0]

    def test_set_block_param(self, bkp_file: Path):
        w = BKPWriter(bkp_file)
        w.set_block_param("REACTOR", "TEMP", 550.0)
        assert len(w.change_log) == 1
        assert "550.0" in w.change_log[0]

    def test_set_block_param_not_found(self, bkp_file: Path):
        w = BKPWriter(bkp_file)
        with pytest.raises(BKPWriterError, match="NONEXISTENT"):
            w.set_block_param("REACTOR", "NONEXISTENT", 1.0)

    def test_set_stream_not_found(self, bkp_file: Path):
        w = BKPWriter(bkp_file)
        with pytest.raises(BKPWriterError, match="NOSUCHSTREAM"):
            w.set_stream_temp("NOSUCHSTREAM", 300.0)

    def test_save_creates_file(self, bkp_file: Path, tmp_path: Path):
        w = BKPWriter(bkp_file)
        w.set_stream_temp("FEED", 600.0)
        out = tmp_path / "modified.bkp"
        result = w.save(out)
        assert result == out
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "600.0" in content
        assert "523.15" not in content.split("STREAM FEED")[1].split("BLOCK")[0]

    def test_save_overwrite_creates_backup(self, bkp_file: Path):
        w = BKPWriter(bkp_file)
        w.set_stream_temp("FEED", 600.0)
        w.save(backup=True)
        bak = bkp_file.with_suffix(".bkp.bak")
        assert bak.exists()
        original = bak.read_text(encoding="utf-8")
        assert "523.15" in original

    def test_multiple_changes(self, bkp_file: Path, tmp_path: Path):
        w = BKPWriter(bkp_file)
        w.set_stream_temp("FEED", 600.0)
        w.set_stream_pressure("FEED", 100.0)
        w.set_block_param("REACTOR", "TEMP", 550.0)
        assert len(w.change_log) == 3

        out = tmp_path / "multi.bkp"
        w.save(out)
        content = out.read_text(encoding="utf-8")
        assert "600.0" in content
        assert "100.0" in content
        assert "550.0" in content

    def test_roundtrip_parseable(self, bkp_file: Path, tmp_path: Path):
        """Modified file should still be parseable by BKPParser."""
        from pyaspenplus.core.bkp_parser import BKPParser

        w = BKPWriter(bkp_file)
        w.set_stream_temp("FEED", 600.0)
        w.set_stream_pressure("FEED", 100.0)
        out = tmp_path / "roundtrip.bkp"
        w.save(out)

        parser = BKPParser(out)
        result = parser.parse()
        assert len(result.components) == 6
        assert len(result.blocks) == 1
        feed = next(s for s in result.streams if s.name == "FEED")
        assert feed.temperature == pytest.approx(600.0)
        assert feed.pressure == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# BatchRunner tests
# ---------------------------------------------------------------------------


class TestBatchRunner:

    def test_find_aspen_executable_returns_none_or_path(self):
        result = find_aspen_executable()
        assert result is None or isinstance(result, Path)

    def test_runner_without_exe(self):
        runner = BatchRunner()
        if not runner.is_available:
            with pytest.raises(Exception):
                runner.run("dummy.bkp")

    def test_runner_with_fake_exe(self, tmp_path: Path):
        fake_exe = tmp_path / "AspenPlus.exe"
        fake_exe.write_text("not a real exe")
        runner = BatchRunner(fake_exe)
        assert runner.is_available
        assert runner.exe_path == fake_exe

    def test_run_result_summary(self):
        r = BatchRunResult(
            input_file=Path("test.bkp"),
            return_code=0,
            elapsed_seconds=42.5,
            success=True,
        )
        s = r.summary()
        assert "SUCCESS" in s
        assert "42.5" in s

    def test_run_result_failed_summary(self):
        r = BatchRunResult(
            input_file=Path("test.bkp"),
            return_code=1,
            elapsed_seconds=10.0,
            success=False,
            stderr="Error occurred",
        )
        s = r.summary()
        assert "FAILED" in s
        assert "Error occurred" in s


# ---------------------------------------------------------------------------
# Integration: Simulation with BKP write-back
# ---------------------------------------------------------------------------


class TestSimulationBKPWriteBack:

    def test_set_bkp_stream_temp(self, bkp_file: Path):
        from pyaspenplus.core.simulation import Simulation

        sim = Simulation.from_bkp(bkp_file)
        sim.set_bkp_stream_temp("FEED", 600.0)
        assert len(sim.bkp_changes) == 1

    def test_save_bkp(self, bkp_file: Path, tmp_path: Path):
        from pyaspenplus.core.simulation import Simulation

        sim = Simulation.from_bkp(bkp_file)
        sim.set_bkp_stream_temp("FEED", 600.0)
        sim.set_bkp_block_param("REACTOR", "PRES", 100.0)
        out = sim.save_bkp(tmp_path / "saved.bkp")
        assert out.exists()

    def test_writer_not_available_in_default(self):
        from pyaspenplus.core.simulation import Simulation

        sim = Simulation()
        with pytest.raises(RuntimeError, match="BKP mode"):
            sim.set_bkp_stream_temp("FEED", 500.0)

    def test_full_modify_parse_cycle(self, bkp_file: Path, tmp_path: Path):
        """Modify -> save -> re-parse and verify changes."""
        from pyaspenplus.core.simulation import Simulation

        sim = Simulation.from_bkp(bkp_file)
        sim.set_bkp_stream_temp("FEED", 700.0)
        sim.set_bkp_stream_pressure("FEED", 50.0)
        out = sim.save_bkp(tmp_path / "cycle.bkp")

        sim2 = Simulation.from_bkp(out)
        feed = next(s for s in sim2.flowsheet.streams if s.name == "FEED")
        assert feed.temperature == pytest.approx(700.0)
        assert feed.pressure == pytest.approx(50.0)
