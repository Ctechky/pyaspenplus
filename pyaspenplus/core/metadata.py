"""Metadata access for Aspen Plus simulations.

Provides a unified :class:`SimulationInfo` that can be populated from either
COM automation or a parsed ``.bkp`` file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyaspenplus.core.bkp_parser import BKPParseResult
    from pyaspenplus.core.com_adapter import COMAdapter


@dataclass
class SimulationInfo:
    """High-level metadata about an Aspen Plus simulation."""

    title: str = ""
    description: str = ""
    author: str = ""
    version: str = ""
    created: str = ""
    modified: str = ""
    aspen_version: str = ""
    property_method: str = ""
    components: list[str] = field(default_factory=list)
    input_units: str = ""

    def summary(self) -> str:
        """Return a human-readable summary string."""
        lines = [
            f"Title          : {self.title}",
            f"Description    : {self.description}",
            f"Author         : {self.author}",
            f"Property Method: {self.property_method}",
            f"Components     : {', '.join(self.components)}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        comps = ", ".join(self.components[:5])
        if len(self.components) > 5:
            comps += f" … (+{len(self.components) - 5})"
        return (
            f"SimulationInfo(title={self.title!r}, "
            f"method={self.property_method!r}, "
            f"components=[{comps}])"
        )


def info_from_com(adapter: "COMAdapter") -> SimulationInfo:
    """Populate :class:`SimulationInfo` by querying the COM adapter."""
    info = SimulationInfo()
    try:
        info.title = adapter.get_value("Data.Setup.SimulationOptions.Input.TITLE") or ""
    except Exception:
        pass
    try:
        info.components = adapter.get_component_ids()
    except Exception:
        pass
    try:
        info.property_method = adapter.get_value(
            "Data.Properties.Specifications.Global.Input.GESSION"
        ) or ""
    except Exception:
        pass
    return info


def info_from_bkp(parsed: "BKPParseResult") -> SimulationInfo:
    """Populate :class:`SimulationInfo` from a parsed ``.bkp`` result."""
    info = SimulationInfo()
    info.title = parsed.metadata.title
    info.description = parsed.metadata.description
    info.author = parsed.metadata.author
    info.aspen_version = parsed.metadata.aspen_version
    info.property_method = parsed.property_method
    info.components = [c.component_id for c in parsed.components]
    return info


def set_metadata_com(adapter: "COMAdapter", key: str, value: Any) -> None:
    """Write a metadata field via COM.  Supported keys: ``title``."""
    key_map = {
        "title": "Data.Setup.SimulationOptions.Input.TITLE",
    }
    path = key_map.get(key.lower())
    if path is None:
        raise KeyError(f"Unsupported metadata key: {key}")
    adapter.set_value(path, value)
