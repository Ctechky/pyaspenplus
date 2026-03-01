"""pyaspenplus — Open-source Python library for Aspen Plus simulation interfacing."""

from pyaspenplus.core.simulation import Simulation

__version__ = "0.3.0"
__all__ = ["Simulation"]


def available_integrations() -> dict[str, bool]:
    """Return availability status of each optional integration."""
    status: dict[str, bool] = {}
    try:
        from pyaspenplus.integrations.coolprop_adapter import CoolPropAdapter
        status["CoolProp"] = CoolPropAdapter.available()
    except Exception:
        status["CoolProp"] = False
    try:
        from pyaspenplus.integrations.cantera_adapter import CanteraAdapter
        status["Cantera"] = CanteraAdapter.available()
    except Exception:
        status["Cantera"] = False
    try:
        from pyaspenplus.integrations.chemlib_adapter import ChemlibAdapter
        status["chemlib"] = ChemlibAdapter.available()
    except Exception:
        status["chemlib"] = False
    try:
        from pyaspenplus.integrations.pychemengg_adapter import PyChemEnggAdapter
        status["PyChemEngg"] = PyChemEnggAdapter.available()
    except Exception:
        status["PyChemEngg"] = False
    try:
        from pyaspenplus.integrations.chemics_adapter import ChemicsAdapter
        status["chemics"] = ChemicsAdapter.available()
    except Exception:
        status["chemics"] = False
    try:
        from pyaspenplus.integrations.polykin_adapter import PolykinAdapter
        status["polykin"] = PolykinAdapter.available()
    except Exception:
        status["polykin"] = False
    try:
        from pyaspenplus.integrations.matplotlib_adapter import PlotAdapter
        status["matplotlib"] = PlotAdapter.available()
    except Exception:
        status["matplotlib"] = False
    return status
