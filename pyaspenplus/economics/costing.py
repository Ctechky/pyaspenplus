"""Unified cost estimator combining APEA results and custom correlations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from pyaspenplus.economics.apea import APEAResults, read_apea
from pyaspenplus.economics.capex import EquipmentCost, total_capital_investment
from pyaspenplus.economics.opex import OPEXResult, estimate_opex

if TYPE_CHECKING:
    from pyaspenplus.core.simulation import Simulation


@dataclass
class EconomicSummary:
    """Aggregated economics for a simulation."""

    total_capital_investment: float = 0.0
    annual_operating_cost: float = 0.0
    annual_revenue: float = 0.0
    npv: float = 0.0
    levelized_cost: float = 0.0
    payback_years: float = 0.0

    def summary(self) -> str:
        return (
            f"Economic Summary\n"
            f"  TCI              : ${self.total_capital_investment:>14,.0f}\n"
            f"  Annual OPEX      : ${self.annual_operating_cost:>14,.0f}/yr\n"
            f"  Annual Revenue   : ${self.annual_revenue:>14,.0f}/yr\n"
            f"  NPV              : ${self.npv:>14,.0f}\n"
            f"  Levelized Cost   : ${self.levelized_cost:>14.2f}/kg\n"
            f"  Payback          : {self.payback_years:>8.1f} yr"
        )


class CostEstimator:
    """High-level cost analysis for an Aspen Plus simulation.

    Combines APEA COM results (when available) with custom Python-side
    correlations for CAPEX and OPEX.

    Parameters
    ----------
    simulation : Simulation
        The loaded simulation handle.
    """

    def __init__(self, simulation: "Simulation") -> None:
        self._sim = simulation
        self._apea: APEAResults | None = None
        self._custom_capex: list[EquipmentCost] = []
        self._opex: OPEXResult | None = None

    # ------------------------------------------------------------------
    # APEA
    # ------------------------------------------------------------------

    def read_apea(self) -> APEAResults:
        """Read economics from APEA (COM mode only)."""
        if self._sim.mode != "com":
            raise RuntimeError("APEA results require COM mode.")
        self._apea = read_apea(self._sim.adapter)
        return self._apea

    # ------------------------------------------------------------------
    # Custom correlations
    # ------------------------------------------------------------------

    def add_equipment_cost(self, cost: EquipmentCost) -> None:
        """Register a custom equipment-cost estimate."""
        self._custom_capex.append(cost)

    def estimate_capex(
        self,
        equipment_costs: list[EquipmentCost] | None = None,
        *,
        contingency: float = 0.18,
        fee: float = 0.03,
    ) -> float:
        """Return total capital investment from custom correlations."""
        costs = equipment_costs or self._custom_capex
        return total_capital_investment(costs, contingency=contingency, fee=fee)

    def estimate_opex(self, **kwargs: Any) -> OPEXResult:
        """Estimate OPEX using :func:`~pyaspenplus.economics.opex.estimate_opex`."""
        self._opex = estimate_opex(**kwargs)
        return self._opex

    # ------------------------------------------------------------------
    # Aggregate metrics
    # ------------------------------------------------------------------

    def total_annual_cost(self) -> float:
        """Return best-available annual operating cost."""
        if self._apea is not None:
            return self._apea.total_operating_cost
        if self._opex is not None:
            return self._opex.total_opex
        return 0.0

    def npv(
        self,
        annual_revenue: float,
        *,
        plant_life: int = 20,
        discount_rate: float = 0.10,
        tci: float | None = None,
    ) -> float:
        """Compute net present value over *plant_life* years."""
        capex = tci or self.estimate_capex()
        opex = self.total_annual_cost()
        net_cash = annual_revenue - opex
        factors = np.array([(1 + discount_rate) ** -t for t in range(1, plant_life + 1)])
        return float(-capex + net_cash * factors.sum())

    def levelized_cost(
        self,
        product_flow_kg_per_hr: float,
        *,
        plant_life: int = 20,
        discount_rate: float = 0.10,
        hours_per_year: float = 8000.0,
        tci: float | None = None,
    ) -> float:
        """Compute levelized cost of the product [$/kg].

        LCOP = (annualised CAPEX + OPEX) / annual_production
        """
        capex = tci or self.estimate_capex()
        opex = self.total_annual_cost()

        crf = (discount_rate * (1 + discount_rate) ** plant_life) / (
            (1 + discount_rate) ** plant_life - 1
        )
        annualized_capex = capex * crf
        annual_production = product_flow_kg_per_hr * hours_per_year

        if annual_production == 0:
            return float("inf")
        return (annualized_capex + opex) / annual_production

    def payback_period(
        self,
        annual_revenue: float,
        *,
        tci: float | None = None,
    ) -> float:
        """Simple payback period in years."""
        capex = tci or self.estimate_capex()
        opex = self.total_annual_cost()
        net = annual_revenue - opex
        if net <= 0:
            return float("inf")
        return capex / net

    def summary(
        self,
        annual_revenue: float = 0.0,
        product_flow_kg_per_hr: float = 0.0,
        *,
        plant_life: int = 20,
        discount_rate: float = 0.10,
    ) -> EconomicSummary:
        """Compute a full :class:`EconomicSummary`."""
        tci = self.estimate_capex()
        return EconomicSummary(
            total_capital_investment=tci,
            annual_operating_cost=self.total_annual_cost(),
            annual_revenue=annual_revenue,
            npv=self.npv(annual_revenue, plant_life=plant_life, discount_rate=discount_rate, tci=tci),
            levelized_cost=(
                self.levelized_cost(
                    product_flow_kg_per_hr,
                    plant_life=plant_life,
                    discount_rate=discount_rate,
                    tci=tci,
                )
                if product_flow_kg_per_hr > 0
                else 0.0
            ),
            payback_years=self.payback_period(annual_revenue, tci=tci),
        )
