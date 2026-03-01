"""Flowsheet topology — blocks, streams, and their connectivity."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pyaspenplus.models.blocks import Block
from pyaspenplus.models.streams import Stream

if TYPE_CHECKING:
    from pyaspenplus.core.com_adapter import COMAdapter


@dataclass
class Flowsheet:
    """Directed graph of blocks connected by streams."""

    blocks: list[Block] = field(default_factory=list)
    streams: list[Stream] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def get_block(self, name: str) -> Block:
        """Return the block with *name*, raising ``KeyError`` if missing."""
        for b in self.blocks:
            if b.name == name:
                return b
        raise KeyError(f"Block not found: {name}")

    def get_stream(self, name: str) -> Stream:
        """Return the stream with *name*, raising ``KeyError`` if missing."""
        for s in self.streams:
            if s.name == name:
                return s
        raise KeyError(f"Stream not found: {name}")

    def block_names(self) -> list[str]:
        return [b.name for b in self.blocks]

    def stream_names(self) -> list[str]:
        return [s.name for s in self.streams]

    # ------------------------------------------------------------------
    # Topology queries
    # ------------------------------------------------------------------

    def upstream_blocks(self, block_name: str) -> list[Block]:
        """Return blocks whose outlet streams feed into *block_name*."""
        target = self.get_block(block_name)
        upstream: list[Block] = []
        for inlet_name in target.inlet_streams:
            for b in self.blocks:
                if inlet_name in b.outlet_streams and b.name != block_name:
                    upstream.append(b)
        return upstream

    def downstream_blocks(self, block_name: str) -> list[Block]:
        """Return blocks fed by the outlets of *block_name*."""
        target = self.get_block(block_name)
        downstream: list[Block] = []
        for outlet_name in target.outlet_streams:
            for b in self.blocks:
                if outlet_name in b.inlet_streams and b.name != block_name:
                    downstream.append(b)
        return downstream

    def inlet_streams_of(self, block_name: str) -> list[Stream]:
        target = self.get_block(block_name)
        return [self.get_stream(s) for s in target.inlet_streams if s in self.stream_names()]

    def outlet_streams_of(self, block_name: str) -> list[Stream]:
        target = self.get_block(block_name)
        return [self.get_stream(s) for s in target.outlet_streams if s in self.stream_names()]

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Flowsheet(blocks={len(self.blocks)}, streams={len(self.streams)})"
        )

    def summary(self) -> str:
        lines = [repr(self)]
        for b in self.blocks:
            lines.append(f"  {b}")
        for s in self.streams:
            lines.append(f"  {s}")
        return "\n".join(lines)


# ------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------


def flowsheet_from_com(adapter: "COMAdapter") -> Flowsheet:
    """Build a :class:`Flowsheet` by querying the COM adapter."""
    from pyaspenplus.models.blocks import block_from_com
    from pyaspenplus.models.streams import stream_from_com

    components = adapter.get_component_ids()
    block_names = adapter.get_block_names()
    stream_names = adapter.get_stream_names()

    blocks = [block_from_com(n, adapter) for n in block_names]
    streams = [stream_from_com(n, adapter, components) for n in stream_names]

    _resolve_connectivity(blocks, streams, adapter)
    return Flowsheet(blocks=blocks, streams=streams)


def flowsheet_from_bkp(parsed: "Any") -> Flowsheet:
    """Build a :class:`Flowsheet` from a :class:`BKPParseResult`."""
    from pyaspenplus.models.blocks import block_from_bkp
    from pyaspenplus.models.streams import stream_from_bkp

    blocks = [block_from_bkp(b) for b in parsed.blocks]
    streams = [stream_from_bkp(s) for s in parsed.streams]

    _link_streams_to_blocks(blocks, streams)
    return Flowsheet(blocks=blocks, streams=streams)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _resolve_connectivity(
    blocks: list[Block],
    streams: list[Stream],
    adapter: "COMAdapter",
) -> None:
    """Fill in inlet/outlet lists and stream source/dest from the COM tree."""
    for block in blocks:
        try:
            inlets = adapter.get_attribute_names(
                f"Data.Blocks.{block.name}.Connections.Inlets"
            )
            block.inlet_streams = inlets
        except Exception:
            pass
        try:
            outlets = adapter.get_attribute_names(
                f"Data.Blocks.{block.name}.Connections.Outlets"
            )
            block.outlet_streams = outlets
        except Exception:
            pass

    block_map = {b.name: b for b in blocks}
    for stream in streams:
        for b in blocks:
            if stream.name in b.outlet_streams:
                stream.source_block = b.name
            if stream.name in b.inlet_streams:
                stream.dest_block = b.name


def _link_streams_to_blocks(blocks: list[Block], streams: list[Stream]) -> None:
    """Cross-reference blocks and streams from BKP data."""
    stream_map = {s.name: s for s in streams}
    for block in blocks:
        for sname in block.outlet_streams:
            if sname in stream_map:
                stream_map[sname].source_block = block.name
        for sname in block.inlet_streams:
            if sname in stream_map:
                stream_map[sname].dest_block = block.name
