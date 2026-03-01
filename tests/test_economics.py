"""Tests for the economics module."""

import pytest

from pyaspenplus.economics.capex import (
    EquipmentCost,
    cepci_factor,
    purchased_equipment_cost,
    total_capital_investment,
)
from pyaspenplus.economics.opex import estimate_opex


class TestCEPCI:
    def test_same_year_factor(self):
        assert cepci_factor(2020, 2020) == pytest.approx(1.0)

    def test_factor_increases(self):
        assert cepci_factor(2001, 2023) > 1.0

    def test_unknown_year_raises(self):
        with pytest.raises(ValueError, match="CEPCI data not available"):
            cepci_factor(1900, 2023)


class TestPurchasedEquipmentCost:
    def test_heat_exchanger(self):
        ec = purchased_equipment_cost("heat_exchanger_fixed", 100)
        assert ec.purchased_cost > 0
        assert ec.bare_module_cost > ec.purchased_cost
        assert ec.sizing_unit == "m2"

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown equipment type"):
            purchased_equipment_cost("warp_drive", 1000)


class TestTotalCapitalInvestment:
    def test_basic_tci(self):
        costs = [
            EquipmentCost(bare_module_cost=100_000),
            EquipmentCost(bare_module_cost=200_000),
        ]
        tci = total_capital_investment(costs, contingency=0.18, fee=0.03)
        assert tci == pytest.approx(300_000 * 1.21)


class TestOPEX:
    def test_raw_material_costs(self):
        result = estimate_opex(
            raw_material_prices={"H2": 2.5, "CO2": 0.04},
            raw_material_flows={"H2": 100, "CO2": 500},
            hours_per_year=8000,
            n_operators=0,
        )
        h2_cost = next(r for r in result.raw_material_costs if r.component == "H2")
        assert h2_cost.annual_cost == pytest.approx(100 * 8000 * 2.5)

    def test_total_opex_includes_all(self):
        result = estimate_opex(
            raw_material_prices={"H2": 1.0},
            raw_material_flows={"H2": 10},
            utility_consumptions={"electricity": 50},
            hours_per_year=8000,
            n_operators=2,
            operator_salary=50_000,
            maintenance_fraction=0.05,
            fixed_capital=1_000_000,
        )
        assert result.total_opex > 0
        assert result.total_utilities > 0
        assert result.labor_cost == 100_000
        assert result.maintenance_cost == 50_000
