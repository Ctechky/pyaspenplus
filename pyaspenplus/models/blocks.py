"""Block representations for Aspen Plus unit-operation models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyaspenplus.core.com_adapter import COMAdapter


@dataclass
class Block:
    """A unit-operation block in the flowsheet.

    Subclasses provide convenience accessors for common block types, but the
    generic :class:`Block` works for any Aspen Plus block.
    """

    name: str = ""
    block_type: str = ""  # e.g. "RPlug", "RadFrac", "Heater", "Flash2"

    inlet_streams: list[str] = field(default_factory=list)
    outlet_streams: list[str] = field(default_factory=list)

    # Key input parameters (type-specific)
    parameters: dict[str, Any] = field(default_factory=dict)
    # Key output results
    results: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"Block({self.name!r}, type={self.block_type!r}, "
            f"in={self.inlet_streams}, out={self.outlet_streams})"
        )

    # ------------------------------------------------------------------
    # Parameter helpers
    # ------------------------------------------------------------------

    def get_parameter(self, key: str, default: Any = None) -> Any:
        return self.parameters.get(key, default)

    def set_parameter(
        self,
        key: str,
        value: Any,
        *,
        adapter: "COMAdapter | None" = None,
    ) -> None:
        """Set a parameter locally and optionally push it to Aspen via COM."""
        self.parameters[key] = value
        if adapter is not None:
            adapter.set_value(f"Data.Blocks.{self.name}.Input.{key}", value)

    def get_result(self, key: str, default: Any = None) -> Any:
        return self.results.get(key, default)


# ------------------------------------------------------------------
# Convenience subclasses
# ------------------------------------------------------------------


class Reactor(Block):
    """Block subclass with reactor-specific helpers."""

    @property
    def temperature(self) -> float | None:
        return self.parameters.get("TEMP")

    @property
    def pressure(self) -> float | None:
        return self.parameters.get("PRES")

    @property
    def volume(self) -> float | None:
        return self.parameters.get("VOL")


class HeatExchanger(Block):
    """Block subclass for heat-exchanger models (Heater, HeatX, MHeatX)."""

    @property
    def duty(self) -> float | None:
        return self.results.get("NET_DUTY") or self.results.get("DUTY")

    @property
    def area(self) -> float | None:
        return self.results.get("AREA")


class Column(Block):
    """Block subclass for distillation column models (RadFrac, DSTWU)."""

    @property
    def num_stages(self) -> int | None:
        val = self.parameters.get("NSTAGE")
        return int(val) if val is not None else None

    @property
    def reflux_ratio(self) -> float | None:
        return self.results.get("MOLE_RR") or self.parameters.get("RFRAC")


class Separator(Block):
    """Block subclass for separator models (Flash2, Flash3, Sep, Sep2)."""
    pass


# ------------------------------------------------------------------
# Type-to-class mapping
# ------------------------------------------------------------------

_BLOCK_TYPE_MAP: dict[str, type[Block]] = {
    "RPLUG": Reactor,
    "RCSTR": Reactor,
    "RSTOIC": Reactor,
    "RGIBBS": Reactor,
    "RYIELD": Reactor,
    "RBATCH": Reactor,
    "HEATER": HeatExchanger,
    "HEATX": HeatExchanger,
    "MHEATX": HeatExchanger,
    "RADFRAC": Column,
    "DSTWU": Column,
    "DISTL": Column,
    "PETROFRAC": Column,
    "FLASH2": Separator,
    "FLASH3": Separator,
    "SEP": Separator,
    "SEP2": Separator,
}


def block_class_for(block_type: str) -> type[Block]:
    """Return the most specific Block subclass for *block_type*."""
    return _BLOCK_TYPE_MAP.get(block_type.upper(), Block)


# ------------------------------------------------------------------
# Factory helpers
# ------------------------------------------------------------------


def block_from_com(name: str, adapter: "COMAdapter") -> Block:
    """Build a :class:`Block` from the COM variable tree."""
    btype = ""
    try:
        btype = adapter.get_value(f"Data.Blocks.{name}.Input.TYPE")
    except Exception:
        pass

    cls = block_class_for(btype)
    blk = cls(name=name, block_type=btype)

    def _try(path: str) -> Any:
        try:
            return adapter.get_value(path)
        except Exception:
            return None

    for param_key in ("TEMP", "PRES", "VOL", "NSTAGE", "RFRAC"):
        v = _try(f"Data.Blocks.{name}.Input.{param_key}")
        if v is not None:
            blk.parameters[param_key] = v

    for res_key in ("NET_DUTY", "DUTY", "AREA", "MOLE_RR"):
        v = _try(f"Data.Blocks.{name}.Output.{res_key}")
        if v is not None:
            blk.results[res_key] = v

    return blk


def block_from_bkp(bkp_block: Any) -> Block:
    """Build a :class:`Block` from a :class:`BKPBlockData` object."""
    cls = block_class_for(bkp_block.block_type)
    return cls(
        name=bkp_block.name,
        block_type=bkp_block.block_type,
        inlet_streams=list(bkp_block.inlet_streams),
        outlet_streams=list(bkp_block.outlet_streams),
        parameters=dict(bkp_block.parameters),
    )
