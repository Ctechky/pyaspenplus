"""Read-modify-write support for Aspen Plus ``.bkp`` files.

Enables changing simulation inputs (stream conditions, block parameters,
component flows) in a ``.bkp`` file and saving the result — all without
requiring Aspen Plus or COM automation.

The approach preserves the original file structure: only the targeted
numeric values are replaced in-place so that Aspen Plus can still open
the modified file.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from pyaspenplus.utils.logger import get_logger

log = get_logger("bkp_writer")


class BKPWriterError(Exception):
    """Raised when a BKP write operation fails."""


class BKPWriter:
    """Modify values inside an Aspen Plus ``.bkp`` file and save.

    Usage::

        w = BKPWriter("model.bkp")
        w.set_stream_temp("FEED", 523.15)
        w.set_stream_pressure("FEED", 75.0)
        w.set_block_param("REACTOR", "TEMP", 250.0)
        w.save("model_modified.bkp")  # or w.save() to overwrite
    """

    def __init__(self, filepath: str | Path) -> None:
        self._filepath = Path(filepath).resolve()
        if not self._filepath.exists():
            raise FileNotFoundError(f"BKP file not found: {self._filepath}")
        self._lines: list[str] = self._filepath.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines(keepends=True)
        self._changes: list[str] = []
        log.info("BKPWriter loaded %d lines from %s", len(self._lines), self._filepath)

    @property
    def filepath(self) -> Path:
        return self._filepath

    @property
    def change_log(self) -> list[str]:
        """Human-readable list of modifications made."""
        return list(self._changes)

    # ------------------------------------------------------------------
    # Stream modifications
    # ------------------------------------------------------------------

    def set_stream_temp(self, stream_name: str, value: float) -> None:
        """Set the temperature input for *stream_name*."""
        self._set_stream_field(stream_name, "TEMP", value)

    def set_stream_pressure(self, stream_name: str, value: float) -> None:
        """Set the pressure input for *stream_name*."""
        self._set_stream_field(stream_name, "PRES", value)

    def set_stream_total_flow(self, stream_name: str, value: float) -> None:
        """Set the total molar/mass flow for *stream_name*."""
        self._set_stream_field(stream_name, "TOTFLOW", value)

    def set_stream_component_flow(
        self, stream_name: str, component: str, value: float
    ) -> None:
        """Set flow of a specific component in *stream_name*."""
        self._set_in_stream_flow_section(stream_name, component, value)

    def set_stream_mole_frac(
        self, stream_name: str, component: str, value: float
    ) -> None:
        """Set mole fraction of a specific component in *stream_name*."""
        self._set_in_stream_flow_section(stream_name, component, value)

    # ------------------------------------------------------------------
    # Block modifications
    # ------------------------------------------------------------------

    def set_block_param(
        self, block_name: str, param_keyword: str, value: float | str
    ) -> None:
        """Change a parameter inside a BLOCK section.

        Handles both ``PARAM TEMP 523`` and ``TEMP 523`` line formats.
        """
        block_re = re.compile(
            rf"^BLOCK\s+{re.escape(block_name)}\s+", re.IGNORECASE
        )
        next_block_re = re.compile(r"^BLOCK\s+\S+\s+", re.IGNORECASE)
        # Match "PARAM TEMP 523.15" or just "TEMP 523.15"
        param_re = re.compile(
            rf"^(\s*(?:PARAM\s+)?{re.escape(param_keyword)}\s+)(\S+)(.*)",
            re.IGNORECASE,
        )

        in_block = False
        replaced = False
        for i, line in enumerate(self._lines):
            if block_re.match(line):
                in_block = True
                continue
            if in_block and next_block_re.match(line):
                break
            if in_block:
                m = param_re.match(line)
                if m:
                    old_val = m.group(2)
                    new_line = f"{m.group(1)}{value}{m.group(3)}"
                    if not new_line.endswith("\n"):
                        new_line += "\n"
                    self._lines[i] = new_line
                    self._changes.append(
                        f"BLOCK {block_name}: {param_keyword} {old_val} -> {value}"
                    )
                    replaced = True
                    log.info(
                        "Block %s: %s = %s (was %s)",
                        block_name, param_keyword, value, old_val,
                    )
                    break

        if not replaced:
            raise BKPWriterError(
                f"Could not find parameter '{param_keyword}' "
                f"in BLOCK {block_name}."
            )

    # ------------------------------------------------------------------
    # Generic key-value setter
    # ------------------------------------------------------------------

    def set_value_by_path(self, section: str, key: str, value: float | str) -> None:
        """Set a key-value pair inside any named section.

        Parameters
        ----------
        section : str
            Top-level section keyword (e.g. ``"PROPERTIES"``, ``"SOLVE"``).
        key : str
            Keyword on the line to match (e.g. ``"PARAM"``).
        value : float | str
            New value.
        """
        sect_re = re.compile(rf"^{re.escape(section)}\b", re.IGNORECASE)
        next_sect_re = re.compile(
            r"^(TITLE|DESCRIPTION|IN-UNITS|DEF-STREAMS|DATABANKS|"
            r"PROP-SOURCES|COMPONENTS|FLOWSHEET|PROPERTIES|STREAM|BLOCK|"
            r"REACTIONS|EO-CONV-OPTI|CONV-OPTIONS|RUN-CONTROL|"
            r"DESIGN-SPEC|CALCULATOR|OPTIMIZATION|SENSITIVITY|SOLVE|"
            r"REPORT|PARAM)\b",
            re.IGNORECASE,
        )
        key_re = re.compile(
            rf"^(\s*{re.escape(key)}\s+)(\S+)(.*)", re.IGNORECASE
        )

        in_section = False
        for i, line in enumerate(self._lines):
            if sect_re.match(line.strip()):
                in_section = True
                continue
            if in_section and next_sect_re.match(line.strip()):
                break
            if in_section:
                m = key_re.match(line)
                if m:
                    old_val = m.group(2)
                    new_line = f"{m.group(1)}{value}{m.group(3)}"
                    if not new_line.endswith("\n"):
                        new_line += "\n"
                    self._lines[i] = new_line
                    self._changes.append(
                        f"{section}.{key}: {old_val} -> {value}"
                    )
                    log.info("%s.%s = %s (was %s)", section, key, value, old_val)
                    return

        raise BKPWriterError(
            f"Could not find key '{key}' in section '{section}'."
        )

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self, filepath: str | Path | None = None, *, backup: bool = True) -> Path:
        """Write the (possibly modified) BKP content to disk.

        Parameters
        ----------
        filepath : str | Path | None
            Destination path.  ``None`` overwrites the original file.
        backup : bool
            If overwriting the original, create a ``.bkp.bak`` copy first.

        Returns
        -------
        Path
            The path that was written.
        """
        dest = Path(filepath).resolve() if filepath else self._filepath
        if dest == self._filepath and backup:
            bak = self._filepath.with_suffix(self._filepath.suffix + ".bak")
            shutil.copy2(self._filepath, bak)
            log.info("Backup saved to %s", bak)

        dest.write_text("".join(self._lines), encoding="utf-8")
        log.info(
            "Saved BKP (%d changes) to %s", len(self._changes), dest
        )
        return dest

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _find_stream_section(self, stream_name: str) -> tuple[int, int]:
        """Return (start, end) line indices for a STREAM section."""
        start_re = re.compile(
            rf"^STREAM\s+{re.escape(stream_name)}\b", re.IGNORECASE
        )
        next_re = re.compile(r"^(STREAM\s+\S|BLOCK\s+\S|FLOWSHEET|PROPERTIES|REACTIONS)", re.IGNORECASE)

        start = -1
        for i, line in enumerate(self._lines):
            if start == -1:
                if start_re.match(line.strip()):
                    start = i
            else:
                if next_re.match(line.strip()):
                    return start, i
        if start != -1:
            return start, len(self._lines)
        raise BKPWriterError(f"Stream '{stream_name}' not found in BKP file.")

    def _set_stream_field(
        self, stream_name: str, keyword: str, value: float
    ) -> None:
        """Replace a scalar field (TEMP, PRES, TOTFLOW) inside a STREAM section."""
        s, e = self._find_stream_section(stream_name)
        field_re = re.compile(
            rf"^(\s*{re.escape(keyword)}\s+)(\S+)(.*)", re.IGNORECASE
        )
        for i in range(s, e):
            m = field_re.match(self._lines[i])
            if m:
                old_val = m.group(2)
                new_line = f"{m.group(1)}{value}{m.group(3)}"
                if not new_line.endswith("\n"):
                    new_line += "\n"
                self._lines[i] = new_line
                self._changes.append(
                    f"STREAM {stream_name}: {keyword} {old_val} -> {value}"
                )
                log.info(
                    "Stream %s: %s = %s (was %s)",
                    stream_name, keyword, value, old_val,
                )
                return
        raise BKPWriterError(
            f"Field '{keyword}' not found in STREAM {stream_name}."
        )

    def _set_in_stream_flow_section(
        self, stream_name: str, component: str, value: float
    ) -> None:
        """Replace a component flow/fraction line inside a STREAM section."""
        s, e = self._find_stream_section(stream_name)
        comp_re = re.compile(
            rf"^(\s+{re.escape(component)}\s+)(\S+)(.*)", re.IGNORECASE
        )
        for i in range(s, e):
            m = comp_re.match(self._lines[i])
            if m:
                old_val = m.group(2)
                new_line = f"{m.group(1)}{value}{m.group(3)}"
                if not new_line.endswith("\n"):
                    new_line += "\n"
                self._lines[i] = new_line
                self._changes.append(
                    f"STREAM {stream_name}: {component} {old_val} -> {value}"
                )
                log.info(
                    "Stream %s: %s = %s (was %s)",
                    stream_name, component, value, old_val,
                )
                return
        raise BKPWriterError(
            f"Component '{component}' not found in STREAM {stream_name}."
        )
