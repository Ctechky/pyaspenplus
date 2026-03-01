"""Unified Simulation entry point for pyaspenplus.

Provides two loading strategies:

- ``Simulation.from_file(path)`` — opens an ``.apw`` or ``.bkp`` file via the
  Aspen Plus COM automation server (requires Aspen Plus installed).
- ``Simulation.from_bkp(path)`` — parses a ``.bkp`` file without Aspen Plus.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyaspenplus.core.bkp_parser import BKPParser, BKPParseResult
from pyaspenplus.core.metadata import (
    SimulationInfo,
    info_from_bkp,
    info_from_com,
    set_metadata_com,
)
from pyaspenplus.materials.components import (
    ComponentList,
    components_from_bkp,
    components_from_com,
)
from pyaspenplus.materials.feed import MaterialManager
from pyaspenplus.models.flowsheet import (
    Flowsheet,
    flowsheet_from_bkp,
    flowsheet_from_com,
)
from pyaspenplus.reactions.reaction import (
    Reaction,
    ReactionSet,
    reactions_from_bkp,
    reactions_from_com,
)
from pyaspenplus.utils.logger import get_logger

log = get_logger("simulation")


class Simulation:
    """High-level handle to an Aspen Plus simulation.

    Do not instantiate directly — use :meth:`from_file` (COM) or
    :meth:`from_bkp` (parser).
    """

    def __init__(self) -> None:
        self._mode: str = "none"  # "com" | "bkp"
        self._adapter: Any = None  # COMAdapter (only in COM mode)
        self._parsed: BKPParseResult | None = None
        self._info: SimulationInfo | None = None
        self._flowsheet: Flowsheet | None = None
        self._components: ComponentList | None = None
        self._reactions: ReactionSet | None = None
        self._materials: MaterialManager | None = None

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_file(
        cls,
        filepath: str | Path,
        *,
        visible: bool = False,
        timeout: int = 120,
    ) -> "Simulation":
        """Open an Aspen Plus file via COM automation.

        Parameters
        ----------
        filepath : str | Path
            Path to ``.apw`` or ``.bkp`` file.
        visible : bool
            Show the Aspen Plus GUI.
        timeout : int
            Seconds to wait for Aspen Plus to initialise.
        """
        from pyaspenplus.core.com_adapter import COMAdapter

        sim = cls()
        sim._mode = "com"
        sim._adapter = COMAdapter(filepath, visible=visible, timeout=timeout)
        sim._adapter.connect()
        log.info("Simulation loaded via COM: %s", filepath)
        return sim

    @classmethod
    def from_bkp(cls, filepath: str | Path) -> "Simulation":
        """Parse a ``.bkp`` file without Aspen Plus.

        Parameters
        ----------
        filepath : str | Path
            Path to a ``.bkp`` backup file.
        """
        sim = cls()
        sim._mode = "bkp"
        parser = BKPParser(filepath)
        sim._parsed = parser.parse()
        log.info("Simulation loaded via BKP parser: %s", filepath)
        return sim

    # ------------------------------------------------------------------
    # Properties (lazy-loaded)
    # ------------------------------------------------------------------

    @property
    def mode(self) -> str:
        """Return ``'com'`` or ``'bkp'``."""
        return self._mode

    @property
    def info(self) -> SimulationInfo:
        """Simulation-level metadata (title, components, property method, …)."""
        if self._info is None:
            if self._mode == "com":
                self._info = info_from_com(self._adapter)
            elif self._parsed is not None:
                self._info = info_from_bkp(self._parsed)
            else:
                self._info = SimulationInfo()
        return self._info

    @property
    def flowsheet(self) -> Flowsheet:
        """The simulation flowsheet (blocks + streams)."""
        if self._flowsheet is None:
            if self._mode == "com":
                self._flowsheet = flowsheet_from_com(self._adapter)
            elif self._parsed is not None:
                self._flowsheet = flowsheet_from_bkp(self._parsed)
            else:
                self._flowsheet = Flowsheet()
        return self._flowsheet

    @property
    def components(self) -> ComponentList:
        """Component property data."""
        if self._components is None:
            if self._mode == "com":
                self._components = components_from_com(self._adapter)
            elif self._parsed is not None:
                self._components = components_from_bkp(self._parsed)
            else:
                self._components = ComponentList()
        return self._components

    @property
    def reactions(self) -> ReactionSet:
        """Reaction data (stoichiometry, kinetics, type)."""
        if self._reactions is None:
            if self._mode == "com":
                rxns = reactions_from_com(self._adapter)
            elif self._parsed is not None:
                rxns = reactions_from_bkp(self._parsed)
            else:
                rxns = []
            self._reactions = ReactionSet(reactions=rxns)
        return self._reactions

    @property
    def materials(self) -> MaterialManager:
        """Material / feed stream manager."""
        if self._materials is None:
            adapter = self._adapter if self._mode == "com" else None
            self._materials = MaterialManager(self.flowsheet.streams, adapter=adapter)
        return self._materials

    # ------------------------------------------------------------------
    # Simulation control (COM only)
    # ------------------------------------------------------------------

    def run(self, *, timeout: int | None = None) -> None:
        """Run the simulation (COM mode only)."""
        self._require_com("run")
        self._adapter.run(timeout=timeout)
        self._invalidate_cache()

    def reinit(self) -> None:
        """Re-initialise the simulation (COM mode only)."""
        self._require_com("reinit")
        self._adapter.reinit()
        self._invalidate_cache()

    # ------------------------------------------------------------------
    # Variable tree access (COM only)
    # ------------------------------------------------------------------

    def get_value(self, path: str) -> Any:
        """Read a value from the Aspen variable tree (COM mode only)."""
        self._require_com("get_value")
        return self._adapter.get_value(path)

    def set_value(self, path: str, value: Any) -> None:
        """Write a value into the Aspen variable tree (COM mode only)."""
        self._require_com("set_value")
        self._adapter.set_value(path, value)

    # ------------------------------------------------------------------
    # Metadata mutation (COM only)
    # ------------------------------------------------------------------

    def set_metadata(self, key: str, value: Any) -> None:
        """Update a file-level metadata field (COM mode only)."""
        self._require_com("set_metadata")
        set_metadata_com(self._adapter, key, value)
        self._info = None  # refresh on next access

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the simulation and release resources."""
        if self._adapter is not None:
            self._adapter.close()
        self._invalidate_cache()

    def __enter__(self) -> "Simulation":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"Simulation(mode={self._mode!r}, info={self.info!r})"

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @property
    def adapter(self) -> Any:
        """Direct access to the underlying :class:`COMAdapter` (or ``None``)."""
        return self._adapter

    def _require_com(self, op: str) -> None:
        if self._mode != "com" or self._adapter is None:
            raise RuntimeError(
                f"'{op}' requires COM mode. "
                "Load with Simulation.from_file() instead of from_bkp()."
            )

    def _invalidate_cache(self) -> None:
        """Clear cached data so the next property access re-reads from Aspen."""
        self._info = None
        self._flowsheet = None
        self._components = None
        self._reactions = None
        self._materials = None
