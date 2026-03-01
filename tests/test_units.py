"""Tests for unit conversion utilities."""

import pytest

from pyaspenplus.utils.units import (
    convert_molar_flow,
    convert_pressure,
    convert_temperature,
)


class TestTemperatureConversion:
    def test_c_to_k(self):
        assert convert_temperature(0, "C", "K") == pytest.approx(273.15)

    def test_k_to_c(self):
        assert convert_temperature(373.15, "K", "C") == pytest.approx(100.0)

    def test_same_unit(self):
        assert convert_temperature(42, "K", "K") == 42

    def test_f_to_c(self):
        assert convert_temperature(212, "F", "C") == pytest.approx(100.0)

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            convert_temperature(0, "X", "K")


class TestPressureConversion:
    def test_bar_to_pa(self):
        assert convert_pressure(1, "bar", "Pa") == pytest.approx(1e5)

    def test_atm_to_bar(self):
        assert convert_pressure(1, "atm", "bar") == pytest.approx(1.01325)

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            convert_pressure(1, "bananas", "Pa")


class TestMolarFlowConversion:
    def test_kmol_hr_to_mol_s(self):
        # 3600 kmol/hr * (1000 mol/kmol) / (3600 s/hr) = 1000 mol/s
        assert convert_molar_flow(3600, "kmol/hr", "mol/s") == pytest.approx(1000.0)

    def test_same_unit(self):
        assert convert_molar_flow(10, "mol/s", "mol/s") == 10
