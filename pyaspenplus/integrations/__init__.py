"""Integration adapters for external chemical engineering Python libraries.

Each adapter wraps a third-party library with a consistent interface that
plugs into the pyaspenplus data model.  All dependencies are optional —
a clear ``ImportError`` message is raised if the library is not installed.
"""

from pyaspenplus.integrations.coolprop_adapter import CoolPropAdapter
from pyaspenplus.integrations.cantera_adapter import CanteraAdapter
from pyaspenplus.integrations.chemlib_adapter import ChemlibAdapter
from pyaspenplus.integrations.matplotlib_adapter import PlotAdapter

__all__ = [
    "CoolPropAdapter",
    "CanteraAdapter",
    "ChemlibAdapter",
    "PlotAdapter",
]
