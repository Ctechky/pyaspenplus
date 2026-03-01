"""Operating-cost estimation models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UtilityCost:
    """Annual utility cost for a single utility type."""

    utility_name: str = ""
    consumption: float = 0.0  # native units per year
    unit: str = ""
    unit_price: float = 0.0  # $/unit
    annual_cost: float = 0.0  # $/yr


@dataclass
class RawMaterialCost:
    """Annual cost for a single raw material."""

    component: str = ""
    consumption: float = 0.0  # kg/yr or kmol/yr
    unit: str = "kg/yr"
    unit_price: float = 0.0  # $/unit
    annual_cost: float = 0.0


@dataclass
class OPEXResult:
    """Summary of annual operating expenditure."""

    raw_material_costs: list[RawMaterialCost] = field(default_factory=list)
    utility_costs: list[UtilityCost] = field(default_factory=list)
    labor_cost: float = 0.0
    maintenance_cost: float = 0.0
    overhead_cost: float = 0.0

    @property
    def total_raw_materials(self) -> float:
        return sum(r.annual_cost for r in self.raw_material_costs)

    @property
    def total_utilities(self) -> float:
        return sum(u.annual_cost for u in self.utility_costs)

    @property
    def total_opex(self) -> float:
        return (
            self.total_raw_materials
            + self.total_utilities
            + self.labor_cost
            + self.maintenance_cost
            + self.overhead_cost
        )

    def summary(self) -> str:
        lines = [
            "OPEX Breakdown ($/yr)",
            f"  Raw Materials : ${self.total_raw_materials:>14,.0f}",
            f"  Utilities     : ${self.total_utilities:>14,.0f}",
            f"  Labor         : ${self.labor_cost:>14,.0f}",
            f"  Maintenance   : ${self.maintenance_cost:>14,.0f}",
            f"  Overhead      : ${self.overhead_cost:>14,.0f}",
            f"  ────────────────────────────",
            f"  Total OPEX    : ${self.total_opex:>14,.0f}",
        ]
        return "\n".join(lines)


# ------------------------------------------------------------------
# Default utility prices (US Gulf Coast, 2023 indicative)
# ------------------------------------------------------------------

DEFAULT_UTILITY_PRICES: dict[str, float] = {
    "electricity": 0.07,  # $/kWh
    "steam_lp": 15.0,  # $/GJ
    "steam_mp": 17.0,
    "steam_hp": 20.0,
    "cooling_water": 0.35,  # $/GJ
    "chilled_water": 4.50,
    "refrigerant": 8.00,
    "natural_gas": 4.00,  # $/GJ
}


def estimate_opex(
    *,
    raw_material_prices: dict[str, float] | None = None,
    raw_material_flows: dict[str, float] | None = None,
    utility_consumptions: dict[str, float] | None = None,
    utility_prices: dict[str, float] | None = None,
    hours_per_year: float = 8000.0,
    n_operators: int = 4,
    operator_salary: float = 60_000.0,
    maintenance_fraction: float = 0.05,
    fixed_capital: float = 0.0,
    overhead_fraction: float = 0.60,
) -> OPEXResult:
    """Estimate annual operating cost from prices, flows, and utility data.

    Parameters
    ----------
    raw_material_prices : dict
        ``{component: price_per_kg}``.
    raw_material_flows : dict
        ``{component: flow_in_kg_per_hr}``.
    utility_consumptions : dict
        ``{utility_name: consumption_per_hr}``  (kWh for electricity, GJ for thermal).
    utility_prices : dict
        ``{utility_name: unit_price}``  — merged with defaults.
    hours_per_year : float
        Operating hours per year (default 8000).
    n_operators : int
        Number of operators per shift.
    operator_salary : float
        Annual salary per operator.
    maintenance_fraction : float
        Maintenance cost as fraction of fixed capital.
    fixed_capital : float
        Total fixed capital investment (for maintenance estimate).
    overhead_fraction : float
        Overhead as fraction of labour + maintenance.
    """
    result = OPEXResult()

    # Raw materials
    if raw_material_prices and raw_material_flows:
        for comp, price in raw_material_prices.items():
            flow = raw_material_flows.get(comp, 0.0)
            annual = flow * hours_per_year * price
            result.raw_material_costs.append(
                RawMaterialCost(
                    component=comp,
                    consumption=flow * hours_per_year,
                    unit="kg/yr",
                    unit_price=price,
                    annual_cost=annual,
                )
            )

    # Utilities
    prices = dict(DEFAULT_UTILITY_PRICES)
    if utility_prices:
        prices.update(utility_prices)

    if utility_consumptions:
        for uname, consumption in utility_consumptions.items():
            price = prices.get(uname, 0.0)
            annual = consumption * hours_per_year * price
            result.utility_costs.append(
                UtilityCost(
                    utility_name=uname,
                    consumption=consumption * hours_per_year,
                    unit_price=price,
                    annual_cost=annual,
                )
            )

    # Labour
    result.labor_cost = n_operators * operator_salary

    # Maintenance
    result.maintenance_cost = maintenance_fraction * fixed_capital

    # Overhead
    result.overhead_cost = overhead_fraction * (result.labor_cost + result.maintenance_cost)

    return result
