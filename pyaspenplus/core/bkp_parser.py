"""Parser for Aspen Plus ``.bkp`` (backup) files.

BKP files are structured text files with hierarchical keyword-value sections.
They use indentation-based nesting with keywords like ``DYNAMICS``,
``FLOWSHEET``, ``STREAM``, ``BLOCK``, etc.  This parser extracts the key
simulation data without requiring a running Aspen Plus instance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pyaspenplus.utils.logger import get_logger

log = get_logger("bkp_parser")


class BKPParserError(Exception):
    """Raised when a .bkp file cannot be parsed."""


# ---------------------------------------------------------------------------
# Data containers returned by the parser
# ---------------------------------------------------------------------------


@dataclass
class BKPMetadata:
    """File-level metadata extracted from a .bkp header."""

    title: str = ""
    description: str = ""
    author: str = ""
    version: str = ""
    created: str = ""
    modified: str = ""
    aspen_version: str = ""


@dataclass
class BKPComponent:
    """A component entry from the Components section."""

    component_id: str = ""
    formula: str = ""
    alias: str = ""


@dataclass
class BKPStreamData:
    """Data extracted for a single stream."""

    name: str = ""
    source_block: str = ""
    dest_block: str = ""
    substream: str = "MIXED"
    temperature: float | None = None
    pressure: float | None = None
    total_flow: float | None = None
    component_flows: dict[str, float] = field(default_factory=dict)
    mole_fractions: dict[str, float] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class BKPBlockData:
    """Data extracted for a single block."""

    name: str = ""
    block_type: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    inlet_streams: list[str] = field(default_factory=list)
    outlet_streams: list[str] = field(default_factory=list)


@dataclass
class BKPReactionData:
    """Reaction data extracted from the Reactions section."""

    name: str = ""
    reaction_type: str = ""
    stoichiometry: dict[str, float] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class BKPParseResult:
    """Complete result from parsing a .bkp file."""

    metadata: BKPMetadata = field(default_factory=BKPMetadata)
    components: list[BKPComponent] = field(default_factory=list)
    streams: list[BKPStreamData] = field(default_factory=list)
    blocks: list[BKPBlockData] = field(default_factory=list)
    reactions: list[BKPReactionData] = field(default_factory=list)
    property_method: str = ""
    raw_sections: dict[str, list[str]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Section-level line accumulator
# ---------------------------------------------------------------------------

_SECTION_HEADERS = re.compile(
    r"^(TITLE|DESCRIPTION|IN-UNITS|DEF-STREAMS|DATABANKS|PROP-SOURCES|"
    r"COMPONENTS|FLOWSHEET|PROPERTIES|STREAM|BLOCK|REACTIONS|"
    r"EO-CONV-OPTI|CONV-OPTIONS|RUN-CONTROL|DESIGN-SPEC|CALCULATOR|"
    r"OPTIMIZATION|SENSITIVITY|ENRTL-RK|HENRY-COMPS|CHEMISTRY|"
    r"DEF-STREAMS|SOLVE|REPORT|PARAM)\b",
    re.IGNORECASE,
)

_BLOCK_TYPE_RE = re.compile(r"^BLOCK\s+(\S+)\s+(\S+)", re.IGNORECASE)
_STREAM_HEADER_RE = re.compile(r"^STREAM\s+(\S+)", re.IGNORECASE)
_FLOWSHEET_BLOCK_RE = re.compile(
    r"BLOCK\s+(\S+)\s+IN=(.+?)\s+OUT=(.+)", re.IGNORECASE
)
_COMPONENT_RE = re.compile(r"^\s+(\S+)\s+(\S+)\s*/\s*(.+)", re.IGNORECASE)
_COMPONENT_SIMPLE_RE = re.compile(r"^\s+(\S+)\s+(\S+)", re.IGNORECASE)
_PROPERTY_METHOD_RE = re.compile(r"^PROPERTIES\s+(\S+)", re.IGNORECASE)


class BKPParser:
    """Parse an Aspen Plus ``.bkp`` file into structured data.

    Usage::

        parser = BKPParser("model.bkp")
        result = parser.parse()
        print(result.components)
    """

    def __init__(self, filepath: str | Path) -> None:
        self._filepath = Path(filepath).resolve()
        if not self._filepath.exists():
            raise FileNotFoundError(f"BKP file not found: {self._filepath}")

    def parse(self) -> BKPParseResult:
        """Read and parse the .bkp file, returning a :class:`BKPParseResult`."""
        log.info("Parsing BKP file: %s", self._filepath)
        text = self._filepath.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()

        result = BKPParseResult()
        sections = self._split_sections(lines)
        result.raw_sections = sections

        self._parse_metadata(sections, result)
        self._parse_components(sections, result)
        self._parse_flowsheet(sections, result)
        self._parse_property_method(sections, result)
        self._parse_streams(sections, result)
        self._parse_blocks(sections, result)
        self._parse_reactions(sections, result)

        log.info(
            "Parsed %d components, %d blocks, %d streams, %d reactions.",
            len(result.components),
            len(result.blocks),
            len(result.streams),
            len(result.reactions),
        )
        return result

    # ------------------------------------------------------------------
    # Section splitting
    # ------------------------------------------------------------------

    @staticmethod
    def _split_sections(lines: list[str]) -> dict[str, list[str]]:
        """Group consecutive lines under their section header keyword."""
        sections: dict[str, list[str]] = {}
        current_key: str | None = None
        for line in lines:
            header_match = _SECTION_HEADERS.match(line.strip())
            if header_match:
                current_key = header_match.group(1).upper()
                sections.setdefault(current_key, [])
                sections[current_key].append(line)
            elif current_key is not None:
                sections[current_key].append(line)
        return sections

    # ------------------------------------------------------------------
    # Individual section parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_metadata(
        sections: dict[str, list[str]], result: BKPParseResult
    ) -> None:
        if "TITLE" in sections:
            title_lines = [
                l.strip() for l in sections["TITLE"][1:] if l.strip()
            ]
            result.metadata.title = " ".join(title_lines)
        if "DESCRIPTION" in sections:
            desc_lines = [
                l.strip() for l in sections["DESCRIPTION"][1:] if l.strip()
            ]
            result.metadata.description = " ".join(desc_lines)

    @staticmethod
    def _parse_components(
        sections: dict[str, list[str]], result: BKPParseResult
    ) -> None:
        if "COMPONENTS" not in sections:
            return
        for line in sections["COMPONENTS"][1:]:
            m = _COMPONENT_RE.match(line)
            if m:
                result.components.append(
                    BKPComponent(
                        component_id=m.group(1),
                        formula=m.group(2),
                        alias=m.group(3).strip(),
                    )
                )
                continue
            m = _COMPONENT_SIMPLE_RE.match(line)
            if m:
                result.components.append(
                    BKPComponent(component_id=m.group(1), formula=m.group(2))
                )

    @staticmethod
    def _parse_flowsheet(
        sections: dict[str, list[str]], result: BKPParseResult
    ) -> None:
        if "FLOWSHEET" not in sections:
            return
        for line in sections["FLOWSHEET"]:
            m = _FLOWSHEET_BLOCK_RE.search(line)
            if m:
                bname = m.group(1)
                inlets = m.group(2).split()
                outlets = m.group(3).split()
                existing = next(
                    (b for b in result.blocks if b.name == bname), None
                )
                if existing:
                    existing.inlet_streams = inlets
                    existing.outlet_streams = outlets
                else:
                    result.blocks.append(
                        BKPBlockData(
                            name=bname,
                            inlet_streams=inlets,
                            outlet_streams=outlets,
                        )
                    )

    @staticmethod
    def _parse_property_method(
        sections: dict[str, list[str]], result: BKPParseResult
    ) -> None:
        if "PROPERTIES" not in sections:
            return
        for line in sections["PROPERTIES"]:
            m = _PROPERTY_METHOD_RE.match(line.strip())
            if m:
                result.property_method = m.group(1)
                break

    @staticmethod
    def _parse_streams(
        sections: dict[str, list[str]], result: BKPParseResult
    ) -> None:
        if "STREAM" not in sections:
            return

        current: BKPStreamData | None = None
        substream = "MIXED"
        in_flow_section = False

        for line in sections["STREAM"]:
            stripped = line.strip()

            m = _STREAM_HEADER_RE.match(stripped)
            if m:
                current = BKPStreamData(name=m.group(1))
                result.streams.append(current)
                in_flow_section = False
                continue

            if current is None:
                continue

            upper = stripped.upper()

            if upper.startswith("SUBSTREAM"):
                parts = stripped.split()
                if len(parts) >= 2:
                    substream = parts[1]
                    current.substream = substream
                in_flow_section = False
            elif upper.startswith("TEMP"):
                parts = stripped.split()
                if len(parts) >= 2:
                    try:
                        current.temperature = float(parts[1])
                    except ValueError:
                        pass
            elif upper.startswith("PRES"):
                parts = stripped.split()
                if len(parts) >= 2:
                    try:
                        current.pressure = float(parts[1])
                    except ValueError:
                        pass
            elif upper.startswith("FLOW") and "FLOW" in upper:
                in_flow_section = True
            elif upper.startswith("MOLE-FRAC") or upper.startswith("MASS-FRAC"):
                in_flow_section = True
            elif in_flow_section:
                parts = stripped.split()
                if len(parts) == 2:
                    try:
                        current.component_flows[parts[0]] = float(parts[1])
                    except ValueError:
                        in_flow_section = False

    @staticmethod
    def _parse_blocks(
        sections: dict[str, list[str]], result: BKPParseResult
    ) -> None:
        if "BLOCK" not in sections:
            return

        current: BKPBlockData | None = None
        param_key: str = ""

        for line in sections["BLOCK"]:
            stripped = line.strip()

            m = _BLOCK_TYPE_RE.match(stripped)
            if m:
                bname, btype = m.group(1), m.group(2)
                existing = next(
                    (b for b in result.blocks if b.name == bname), None
                )
                if existing:
                    existing.block_type = btype
                    current = existing
                else:
                    current = BKPBlockData(name=bname, block_type=btype)
                    result.blocks.append(current)
                continue

            if current is None:
                continue

            if stripped.startswith("PARAM"):
                parts = stripped.split()
                if len(parts) >= 2:
                    param_key = parts[0]
                    try:
                        current.parameters[param_key] = float(parts[1])
                    except ValueError:
                        current.parameters[param_key] = parts[1]
            elif "=" in stripped:
                k, _, v = stripped.partition("=")
                k, v = k.strip(), v.strip()
                if k:
                    try:
                        current.parameters[k] = float(v)
                    except ValueError:
                        current.parameters[k] = v

    @staticmethod
    def _parse_reactions(
        sections: dict[str, list[str]], result: BKPParseResult
    ) -> None:
        if "REACTIONS" not in sections:
            return

        current: BKPReactionData | None = None
        in_stoich = False

        for line in sections["REACTIONS"]:
            stripped = line.strip()
            upper = stripped.upper()

            if upper.startswith("REACTIONS") and not upper.startswith("REACTIONS "):
                continue

            if upper.startswith("REACTIONS "):
                parts = stripped.split()
                if len(parts) >= 2:
                    current = BKPReactionData(name=parts[1])
                    if len(parts) >= 3:
                        current.reaction_type = parts[2]
                    result.reactions.append(current)
                in_stoich = False
                continue

            if current is None:
                continue

            if upper.startswith("STOIC"):
                in_stoich = True
                parts = stripped.split()
                for i in range(1, len(parts) - 1, 2):
                    try:
                        current.stoichiometry[parts[i]] = float(parts[i + 1])
                    except (ValueError, IndexError):
                        break
            elif in_stoich and stripped and not stripped.startswith(";"):
                parts = stripped.split()
                for i in range(0, len(parts) - 1, 2):
                    try:
                        current.stoichiometry[parts[i]] = float(parts[i + 1])
                    except (ValueError, IndexError):
                        in_stoich = False
                        break
