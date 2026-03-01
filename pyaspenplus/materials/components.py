"""Component property access for Aspen Plus simulations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyaspenplus.core.com_adapter import COMAdapter


@dataclass
class Component:
    """Physical and thermodynamic properties of a single chemical component."""

    component_id: str = ""
    formula: str = ""
    alias: str = ""
    cas_number: str = ""

    # Key scalar properties
    molecular_weight: float | None = None  # g/mol
    normal_boiling_point: float | None = None  # K
    critical_temperature: float | None = None  # K
    critical_pressure: float | None = None  # Pa
    acentric_factor: float | None = None

    # Extensible property bag
    properties: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"Component({self.component_id!r}, MW={self.molecular_weight}, "
            f"formula={self.formula!r})"
        )


@dataclass
class ComponentList:
    """Ordered list of components in a simulation with lookup by ID."""

    components: list[Component] = field(default_factory=list)

    def __iter__(self):
        return iter(self.components)

    def __len__(self):
        return len(self.components)

    def __getitem__(self, key: int | str) -> Component:
        if isinstance(key, int):
            return self.components[key]
        for c in self.components:
            if c.component_id == key:
                return c
        raise KeyError(f"Component not found: {key}")

    def __contains__(self, key: str) -> bool:
        return any(c.component_id == key for c in self.components)

    @property
    def ids(self) -> list[str]:
        return [c.component_id for c in self.components]

    def __repr__(self) -> str:
        return f"ComponentList({self.ids})"


# ------------------------------------------------------------------
# Factory helpers
# ------------------------------------------------------------------


def components_from_com(adapter: "COMAdapter") -> ComponentList:
    """Build a :class:`ComponentList` from the COM variable tree."""
    comp_ids = adapter.get_component_ids()
    comps: list[Component] = []

    for cid in comp_ids:
        comp = Component(component_id=cid)

        def _try(path: str) -> Any:
            try:
                return adapter.get_value(path)
            except Exception:
                return None

        base = f"Data.Components.Specifications.Selection.{cid}"
        comp.formula = _try(f"{base}.Formula") or ""
        comp.molecular_weight = _try(
            f"Data.Components.Specifications.Properties.Scalar.{cid}.MW"
        )
        comp.normal_boiling_point = _try(
            f"Data.Components.Specifications.Properties.Scalar.{cid}.TB"
        )
        comp.critical_temperature = _try(
            f"Data.Components.Specifications.Properties.Scalar.{cid}.TC"
        )
        comp.critical_pressure = _try(
            f"Data.Components.Specifications.Properties.Scalar.{cid}.PC"
        )
        comp.acentric_factor = _try(
            f"Data.Components.Specifications.Properties.Scalar.{cid}.OMEGA"
        )
        comps.append(comp)

    return ComponentList(components=comps)


def components_from_bkp(parsed: Any) -> ComponentList:
    """Build a :class:`ComponentList` from a :class:`BKPParseResult`."""
    comps: list[Component] = []
    for bc in parsed.components:
        comps.append(
            Component(
                component_id=bc.component_id,
                formula=bc.formula,
                alias=bc.alias,
            )
        )
    return ComponentList(components=comps)
