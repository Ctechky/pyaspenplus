"""Interface to Aspen Process Economic Analyzer (APEA) results via COM."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyaspenplus.core.com_adapter import COMAdapter


@dataclass
class APEAResults:
    """Container for economics results read from APEA through the COM tree."""

    total_capital_cost: float = 0.0
    total_operating_cost: float = 0.0
    total_utilities_cost: float = 0.0
    total_raw_materials_cost: float = 0.0
    total_product_sales: float = 0.0
    equipment_costs: dict[str, float] = field(default_factory=dict)
    utility_costs: dict[str, float] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def net_operating_cost(self) -> float:
        return self.total_operating_cost - self.total_product_sales

    def summary(self) -> str:
        lines = [
            "APEA Results",
            f"  Total Capital Cost     : ${self.total_capital_cost:,.0f}",
            f"  Total Operating Cost   : ${self.total_operating_cost:,.0f}/yr",
            f"  Total Utilities Cost   : ${self.total_utilities_cost:,.0f}/yr",
            f"  Raw Materials Cost     : ${self.total_raw_materials_cost:,.0f}/yr",
            f"  Product Sales          : ${self.total_product_sales:,.0f}/yr",
        ]
        if self.equipment_costs:
            lines.append("  Equipment breakdown:")
            for name, cost in self.equipment_costs.items():
                lines.append(f"    {name:20s} : ${cost:,.0f}")
        return "\n".join(lines)


# Well-known APEA tree paths (Aspen Plus v11+)
_APEA_PATHS = {
    "total_capital_cost": "Results.TCI",
    "total_operating_cost": "Results.TOC",
    "total_utilities_cost": "Results.TUC",
    "total_raw_materials_cost": "Results.TRMC",
    "total_product_sales": "Results.TPS",
}


def read_apea(adapter: "COMAdapter") -> APEAResults:
    """Read APEA results from the COM variable tree.

    Falls back gracefully if specific paths are not available (e.g. APEA
    was not activated for the simulation).
    """
    results = APEAResults()

    def _try(path: str) -> Any:
        try:
            return adapter.get_apea_value(path)
        except Exception:
            return None

    for attr, path in _APEA_PATHS.items():
        val = _try(path)
        if val is not None:
            setattr(results, attr, float(val))
            results.raw[path] = val

    # Per-block equipment cost
    try:
        block_names = adapter.get_block_names()
        for bname in block_names:
            val = _try(f"Blocks.{bname}.Results.PURCHASED_COST")
            if val is not None:
                results.equipment_costs[bname] = float(val)
    except Exception:
        pass

    return results
