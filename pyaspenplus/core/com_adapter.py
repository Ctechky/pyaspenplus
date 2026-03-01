"""COM automation adapter for Aspen Plus via pywin32.

Wraps the Aspen Plus COM interface (``Apwn.Document``) to provide
connection management, variable tree access, and simulation execution.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from pyaspenplus.utils.logger import get_logger

log = get_logger("com_adapter")

try:
    import win32com.client as win32
    import pythoncom

    _COM_AVAILABLE = True
except ImportError:
    _COM_AVAILABLE = False


class COMAdapterError(Exception):
    """Raised when a COM operation fails."""


class COMAdapter:
    """Low-level wrapper around the Aspen Plus COM automation server.

    Parameters
    ----------
    filepath : str | Path
        Path to an ``.apw`` or ``.bkp`` Aspen Plus file.
    visible : bool
        Whether to show the Aspen Plus GUI window.
    timeout : int
        Maximum seconds to wait for Aspen Plus to finish initialising.
    """

    ASPEN_PROG_ID = "Apwn.Document"

    def __init__(
        self,
        filepath: str | Path,
        *,
        visible: bool = False,
        timeout: int = 120,
    ) -> None:
        if not _COM_AVAILABLE:
            raise COMAdapterError(
                "pywin32 is not installed. Install it with: pip install pywin32"
            )

        self._filepath = Path(filepath).resolve()
        if not self._filepath.exists():
            raise FileNotFoundError(f"File not found: {self._filepath}")

        self._visible = visible
        self._timeout = timeout
        self._app: Any = None
        self._connected = False

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Launch Aspen Plus and open the simulation file."""
        if self._connected:
            return

        log.info("Launching Aspen Plus COM server …")
        pythoncom.CoInitialize()
        try:
            self._app = win32.Dispatch(self.ASPEN_PROG_ID)
        except Exception as exc:
            raise COMAdapterError(
                f"Could not launch Aspen Plus COM server ({self.ASPEN_PROG_ID}). "
                "Make sure Aspen Plus is installed."
            ) from exc

        self._app.Visible = self._visible
        log.info("Opening file: %s", self._filepath)
        self._app.InitFromArchive2(str(self._filepath))
        self._wait_for_ready()
        self._connected = True
        log.info("Connected to Aspen Plus.")

    def close(self) -> None:
        """Close the simulation and release the COM object."""
        if self._app is not None:
            try:
                self._app.Close()
                self._app.Quit()
            except Exception:
                pass
            self._app = None
        self._connected = False
        log.info("Disconnected from Aspen Plus.")

    def __enter__(self) -> "COMAdapter":
        self.connect()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Simulation control
    # ------------------------------------------------------------------

    def run(self, *, timeout: int | None = None) -> None:
        """Run the simulation and block until completion."""
        self._ensure_connected()
        log.info("Running simulation …")
        self._app.Engine.Run2()
        self._wait_for_ready(timeout=timeout or self._timeout * 3)
        log.info("Simulation finished.")

    def reinit(self) -> None:
        """Re-initialise the simulation (reset results, keep inputs)."""
        self._ensure_connected()
        self._app.Reinit()
        self._wait_for_ready()

    # ------------------------------------------------------------------
    # Variable tree access
    # ------------------------------------------------------------------

    def get_node(self, path: str) -> Any:
        """Return the COM tree node at *path* (backslash-separated)."""
        self._ensure_connected()
        node = self._app.Tree.FindNode(path.replace(".", "\\"))
        if node is None:
            raise COMAdapterError(f"Node not found: {path}")
        return node

    def get_value(self, path: str) -> Any:
        """Read a scalar value from the Aspen variable tree."""
        return self.get_node(path).Value

    def set_value(self, path: str, value: Any) -> None:
        """Write a scalar value into the Aspen variable tree."""
        self.get_node(path).Value = value

    def get_attribute_names(self, path: str) -> list[str]:
        """Return child element names under *path*."""
        node = self.get_node(path)
        return [node.Elements.Item(i).Name for i in range(node.Elements.Count)]

    # ------------------------------------------------------------------
    # Convenience readers
    # ------------------------------------------------------------------

    def get_block_names(self) -> list[str]:
        """Return names of all blocks on the flowsheet."""
        return self.get_attribute_names("Data.Blocks")

    def get_stream_names(self) -> list[str]:
        """Return names of all streams on the flowsheet."""
        return self.get_attribute_names("Data.Streams")

    def get_component_ids(self) -> list[str]:
        """Return the component IDs defined in the simulation."""
        return self.get_attribute_names("Data.Components.Specifications.Selection")

    def get_block_type(self, block_name: str) -> str:
        """Return the Aspen block-type string (e.g. ``RadFrac``, ``RPlug``)."""
        return self.get_value(f"Data.Blocks.{block_name}.Input.TYPE")

    def get_stream_value(self, stream_name: str, prop: str) -> Any:
        """Read a single property from a stream's output results."""
        return self.get_value(f"Data.Streams.{stream_name}.Output.{prop}")

    # ------------------------------------------------------------------
    # APEA (Aspen Process Economic Analyzer) helpers
    # ------------------------------------------------------------------

    def get_apea_value(self, path: str) -> Any:
        """Read a value from the economics tree (``Data.EconData.*``)."""
        return self.get_value(f"Data.EconData.{path}")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        if not self._connected or self._app is None:
            raise COMAdapterError("Not connected. Call .connect() first.")

    def _wait_for_ready(self, *, timeout: int | None = None) -> None:
        """Block until Aspen Plus reports ready or *timeout* seconds elapse."""
        deadline = time.time() + (timeout or self._timeout)
        while time.time() < deadline:
            try:
                # Engine.IsRunning is False when Aspen is idle/ready
                if not self._app.Engine.IsRunning:
                    return
            except Exception:
                pass
            time.sleep(1)
        raise COMAdapterError(
            f"Aspen Plus did not become ready within {timeout or self._timeout}s."
        )

    @property
    def app(self) -> Any:
        """Direct access to the underlying COM application object."""
        self._ensure_connected()
        return self._app

    @property
    def filepath(self) -> Path:
        return self._filepath

    @property
    def is_connected(self) -> bool:
        return self._connected
