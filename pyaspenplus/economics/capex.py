"""Capital-cost estimation using standard correlations.

Implements bare-module / purchased-equipment correlations from:
- Turton et al. (2018) *Analysis, Synthesis and Design of Chemical Processes*
- Guthrie (1974)
- CEPCI indexing for inflation adjustment
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# CEPCI values for common reference years
CEPCI_INDEX: dict[int, float] = {
    2001: 397.0,
    2007: 525.4,
    2010: 550.8,
    2013: 567.3,
    2018: 603.1,
    2019: 607.5,
    2020: 596.2,
    2021: 708.0,
    2022: 816.0,
    2023: 800.0,
    2024: 810.0,
}


def cepci_factor(from_year: int, to_year: int) -> float:
    """Return the CEPCI cost-escalation factor from *from_year* to *to_year*."""
    if from_year not in CEPCI_INDEX or to_year not in CEPCI_INDEX:
        available = sorted(CEPCI_INDEX.keys())
        raise ValueError(
            f"CEPCI data not available for year {from_year} or {to_year}. "
            f"Available: {available}"
        )
    return CEPCI_INDEX[to_year] / CEPCI_INDEX[from_year]


@dataclass
class EquipmentCost:
    """Cost result for a single piece of equipment."""

    name: str = ""
    equipment_type: str = ""
    purchased_cost: float = 0.0
    bare_module_cost: float = 0.0
    material_factor: float = 1.0
    pressure_factor: float = 1.0
    sizing_parameter: float = 0.0
    sizing_unit: str = ""

    def __repr__(self) -> str:
        return (
            f"EquipmentCost({self.name!r}, purchased=${self.purchased_cost:,.0f}, "
            f"bare_module=${self.bare_module_cost:,.0f})"
        )


# ------------------------------------------------------------------
# Turton correlation data (log10 Cp0 = K1 + K2*log10(A) + K3*(log10(A))^2)
# where A is the capacity/sizing parameter.
# Each entry: (K1, K2, K3, A_min, A_max, sizing_unit, base_year)
# ------------------------------------------------------------------

_TURTON_DATA: dict[str, tuple[float, float, float, float, float, str, int]] = {
    "compressor_centrifugal": (2.2897, 1.3604, -0.1027, 450, 3000, "kW", 2001),
    "heat_exchanger_fixed": (4.3247, -0.3030, 0.1634, 10, 1000, "m2", 2001),
    "heat_exchanger_utube": (4.1884, -0.2503, 0.1974, 10, 1000, "m2", 2001),
    "pump_centrifugal": (3.3892, 0.0536, 0.1538, 1, 300, "kW", 2001),
    "vessel_vertical": (3.4974, 0.4485, 0.1074, 0.3, 520, "m3", 2001),
    "vessel_horizontal": (3.5565, 0.3776, 0.0905, 0.1, 628, "m3", 2001),
    "reactor_jacketed": (4.1052, 0.5320, -0.0005, 0.5, 100, "m3", 2001),
    "tower_tray": (3.4974, 0.4485, 0.1074, 0.3, 520, "m3", 2001),
    "fired_heater": (2.6558, 0.8158, -0.0640, 1000, 100000, "kW", 2001),
}

# Bare-module factors (FM * FP multiplied later)
_BARE_MODULE_FACTORS: dict[str, float] = {
    "compressor_centrifugal": 2.15,
    "heat_exchanger_fixed": 3.17,
    "heat_exchanger_utube": 3.17,
    "pump_centrifugal": 3.30,
    "vessel_vertical": 4.16,
    "vessel_horizontal": 3.05,
    "reactor_jacketed": 4.16,
    "tower_tray": 4.16,
    "fired_heater": 2.19,
}


def purchased_equipment_cost(
    equipment_type: str,
    sizing_parameter: float,
    *,
    cost_year: int = 2023,
) -> EquipmentCost:
    """Estimate purchased equipment cost using Turton correlations.

    Parameters
    ----------
    equipment_type : str
        Key into the correlation table (e.g. ``"heat_exchanger_fixed"``).
    sizing_parameter : float
        Capacity parameter *A* in the correlation's native unit.
    cost_year : int
        Target year for CEPCI adjustment.
    """
    key = equipment_type.lower().replace(" ", "_").replace("-", "_")
    if key not in _TURTON_DATA:
        available = sorted(_TURTON_DATA.keys())
        raise ValueError(
            f"Unknown equipment type '{equipment_type}'. Available: {available}"
        )

    K1, K2, K3, A_min, A_max, unit, base_year = _TURTON_DATA[key]
    A = max(A_min, min(sizing_parameter, A_max))

    log_A = math.log10(A)
    log_Cp0 = K1 + K2 * log_A + K3 * log_A ** 2
    Cp0 = 10 ** log_Cp0

    escalation = cepci_factor(base_year, cost_year)
    purchased = Cp0 * escalation

    fbm = _BARE_MODULE_FACTORS.get(key, 3.0)
    bare_module = purchased * fbm

    return EquipmentCost(
        equipment_type=key,
        purchased_cost=purchased,
        bare_module_cost=bare_module,
        sizing_parameter=sizing_parameter,
        sizing_unit=unit,
    )


def total_capital_investment(
    equipment_costs: list[EquipmentCost],
    *,
    contingency: float = 0.18,
    fee: float = 0.03,
) -> float:
    """Compute total capital investment (TCI) from bare-module costs.

    TCI = (1 + contingency + fee) * sum(bare_module_costs)
    """
    total_bm = sum(ec.bare_module_cost for ec in equipment_costs)
    return total_bm * (1 + contingency + fee)
