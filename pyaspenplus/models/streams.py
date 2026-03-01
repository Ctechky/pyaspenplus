"""Stream representations for Aspen Plus simulations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyaspenplus.core.com_adapter import COMAdapter


@dataclass
class Stream:
    """A material, heat, or work stream in the flowsheet.

    Attributes can be populated from COM results or from a parsed .bkp file.
    """

    name: str = ""
    stream_class: str = "MATERIAL"  # MATERIAL | HEAT | WORK
    substream: str = "MIXED"

    # Thermodynamic state
    temperature: float | None = None  # K (SI)
    pressure: float | None = None  # Pa (SI)
    vapor_fraction: float | None = None
    total_molar_flow: float | None = None  # kmol/hr
    total_mass_flow: float | None = None  # kg/hr

    # Composition
    component_molar_flows: dict[str, float] = field(default_factory=dict)
    component_mass_flows: dict[str, float] = field(default_factory=dict)
    mole_fractions: dict[str, float] = field(default_factory=dict)
    mass_fractions: dict[str, float] = field(default_factory=dict)

    # Connectivity
    source_block: str = ""
    dest_block: str = ""

    # Raw property bag for anything not covered above
    properties: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def composition(self) -> dict[str, float]:
        """Return mole fractions (preferred) or whatever is available."""
        return self.mole_fractions or self.mass_fractions

    def get_flow(self, component: str, basis: str = "molar") -> float:
        """Return the flow of *component* on a molar or mass basis."""
        src = self.component_molar_flows if basis == "molar" else self.component_mass_flows
        val = src.get(component)
        if val is None:
            raise KeyError(f"Component '{component}' not found in stream '{self.name}'")
        return val

    def __repr__(self) -> str:
        return (
            f"Stream({self.name!r}, T={self.temperature}, P={self.pressure}, "
            f"class={self.stream_class})"
        )

    # ------------------------------------------------------------------
    # COM-based mutators (only work when backed by a live simulation)
    # ------------------------------------------------------------------

    def set_temperature(self, value: float, *, adapter: "COMAdapter | None" = None) -> None:
        """Set the stream temperature.  Pushes to Aspen if *adapter* is provided."""
        self.temperature = value
        if adapter is not None:
            adapter.set_value(f"Data.Streams.{self.name}.Input.TEMP.MIXED", value)

    def set_pressure(self, value: float, *, adapter: "COMAdapter | None" = None) -> None:
        self.pressure = value
        if adapter is not None:
            adapter.set_value(f"Data.Streams.{self.name}.Input.PRES.MIXED", value)

    def set_flow_rate(
        self,
        value: float,
        unit: str = "kmol/hr",
        *,
        adapter: "COMAdapter | None" = None,
    ) -> None:
        self.total_molar_flow = value
        if adapter is not None:
            adapter.set_value(f"Data.Streams.{self.name}.Input.TOTFLOW.MIXED", value)

    def set_component_flow(
        self,
        component: str,
        value: float,
        *,
        adapter: "COMAdapter | None" = None,
    ) -> None:
        self.component_molar_flows[component] = value
        if adapter is not None:
            adapter.set_value(
                f"Data.Streams.{self.name}.Input.FLOW.MIXED.{component}", value
            )


# ------------------------------------------------------------------
# Factory helpers
# ------------------------------------------------------------------


def stream_from_com(name: str, adapter: "COMAdapter", components: list[str]) -> Stream:
    """Build a :class:`Stream` by reading results from the COM adapter."""
    s = Stream(name=name)

    def _try(path: str) -> Any:
        try:
            return adapter.get_value(path)
        except Exception:
            return None

    base = f"Data.Streams.{name}.Output"
    s.temperature = _try(f"{base}.TEMP_OUT.MIXED")
    s.pressure = _try(f"{base}.PRES_OUT.MIXED")
    s.vapor_fraction = _try(f"{base}.VFRAC_OUT.MIXED")
    s.total_molar_flow = _try(f"{base}.TOT_FLOW.MIXED")
    s.total_mass_flow = _try(f"{base}.MASSFLMX.MIXED")

    for comp in components:
        val = _try(f"{base}.MOLEFLOW.MIXED.{comp}")
        if val is not None:
            s.component_molar_flows[comp] = val
        val = _try(f"{base}.MOLEFRAC.MIXED.{comp}")
        if val is not None:
            s.mole_fractions[comp] = val
        val = _try(f"{base}.MASSFLOW.MIXED.{comp}")
        if val is not None:
            s.component_mass_flows[comp] = val
        val = _try(f"{base}.MASSFRAC.MIXED.{comp}")
        if val is not None:
            s.mass_fractions[comp] = val

    return s


def stream_from_bkp(bkp_stream: Any) -> Stream:
    """Build a :class:`Stream` from a :class:`BKPStreamData` object."""
    s = Stream(
        name=bkp_stream.name,
        substream=bkp_stream.substream,
        temperature=bkp_stream.temperature,
        pressure=bkp_stream.pressure,
        source_block=bkp_stream.source_block,
        dest_block=bkp_stream.dest_block,
        component_molar_flows=dict(bkp_stream.component_flows),
        mole_fractions=dict(bkp_stream.mole_fractions),
        properties=dict(bkp_stream.properties),
    )
    return s
