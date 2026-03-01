"""Feed / raw-material specification helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyaspenplus.core.com_adapter import COMAdapter
    from pyaspenplus.models.streams import Stream


@dataclass
class Feed:
    """Wraps an inlet stream to expose feed-specification semantics.

    Parameters
    ----------
    stream : Stream
        The underlying :class:`~pyaspenplus.models.streams.Stream` object.
    """

    stream: Any = None  # Stream

    @property
    def name(self) -> str:
        return self.stream.name if self.stream else ""

    @property
    def components(self) -> list[str]:
        if self.stream is None:
            return []
        return list(
            self.stream.mole_fractions.keys()
            or self.stream.component_molar_flows.keys()
        )

    @property
    def mole_fractions(self) -> dict[str, float]:
        return self.stream.mole_fractions if self.stream else {}

    @property
    def mass_fractions(self) -> dict[str, float]:
        return self.stream.mass_fractions if self.stream else {}

    @property
    def temperature(self) -> float | None:
        return self.stream.temperature if self.stream else None

    @property
    def pressure(self) -> float | None:
        return self.stream.pressure if self.stream else None

    @property
    def total_flow(self) -> float | None:
        return self.stream.total_molar_flow if self.stream else None

    # ------------------------------------------------------------------
    # Mutators (COM-backed)
    # ------------------------------------------------------------------

    def set_flow_rate(
        self,
        value: float,
        unit: str = "kmol/hr",
        *,
        adapter: "COMAdapter | None" = None,
    ) -> None:
        if self.stream is not None:
            self.stream.set_flow_rate(value, unit, adapter=adapter)

    def set_temperature(
        self, value: float, *, adapter: "COMAdapter | None" = None
    ) -> None:
        if self.stream is not None:
            self.stream.set_temperature(value, adapter=adapter)

    def set_pressure(
        self, value: float, *, adapter: "COMAdapter | None" = None
    ) -> None:
        if self.stream is not None:
            self.stream.set_pressure(value, adapter=adapter)

    def set_component_flow(
        self,
        component: str,
        value: float,
        *,
        adapter: "COMAdapter | None" = None,
    ) -> None:
        if self.stream is not None:
            self.stream.set_component_flow(component, value, adapter=adapter)

    def __repr__(self) -> str:
        return f"Feed({self.name!r}, components={self.components})"


class MaterialManager:
    """High-level interface for querying feed / raw-material streams.

    Typically accessed via ``sim.materials``.
    """

    def __init__(self, streams: list[Any], adapter: "COMAdapter | None" = None) -> None:
        self._streams = {s.name: s for s in streams}
        self._adapter = adapter

    def get_feed(self, name: str) -> Feed:
        """Return a :class:`Feed` wrapper around the named stream."""
        if name not in self._streams:
            raise KeyError(f"Stream not found: {name}")
        return Feed(stream=self._streams[name])

    @property
    def feed_names(self) -> list[str]:
        return list(self._streams.keys())

    def __repr__(self) -> str:
        return f"MaterialManager(feeds={self.feed_names})"
