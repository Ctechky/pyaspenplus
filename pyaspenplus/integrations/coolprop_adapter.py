"""CoolProp integration — thermophysical property lookups.

Provides a drop-in alternative to Aspen's property system for common
pure-component and mixture calculations using the CoolProp library.

Install: ``pip install CoolProp``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    import CoolProp.CoolProp as CP
    from CoolProp.CoolProp import PropsSI

    _COOLPROP_AVAILABLE = True
except ImportError:
    _COOLPROP_AVAILABLE = False

_ASPEN_TO_COOLPROP: dict[str, str] = {
    "H2": "Hydrogen",
    "CO2": "CarbonDioxide",
    "CO": "CarbonMonoxide",
    "CH3OH": "Methanol",
    "MEOH": "Methanol",
    "H2O": "Water",
    "N2": "Nitrogen",
    "O2": "Oxygen",
    "CH4": "Methane",
    "C2H6": "Ethane",
    "C3H8": "Propane",
    "NH3": "Ammonia",
    "H2S": "HydrogenSulfide",
    "AR": "Argon",
    "HE": "Helium",
    "C2H4": "Ethylene",
    "C2H5OH": "Ethanol",
    "ETOH": "Ethanol",
}


def _require_coolprop() -> None:
    if not _COOLPROP_AVAILABLE:
        raise ImportError(
            "CoolProp is required for this feature. "
            "Install with: pip install CoolProp"
        )


def _resolve_name(aspen_id: str) -> str:
    """Map an Aspen component ID to a CoolProp fluid name."""
    name = _ASPEN_TO_COOLPROP.get(aspen_id.upper())
    if name is None:
        raise KeyError(
            f"No CoolProp mapping for Aspen component '{aspen_id}'. "
            f"Known mappings: {sorted(_ASPEN_TO_COOLPROP.keys())}"
        )
    return name


class CoolPropAdapter:
    """Query thermophysical properties via CoolProp.

    Usage::

        cp = CoolPropAdapter()
        rho = cp.density("H2O", T=373.15, P=101325)
        h = cp.enthalpy("H2O", T=373.15, P=101325)
        props = cp.all_properties("CO2", T=300, P=5e6)
    """

    def __init__(self, name_map: dict[str, str] | None = None) -> None:
        _require_coolprop()
        self._name_map = dict(_ASPEN_TO_COOLPROP)
        if name_map:
            self._name_map.update(name_map)

    def _name(self, aspen_id: str) -> str:
        name = self._name_map.get(aspen_id.upper())
        if name is None:
            raise KeyError(f"No CoolProp mapping for '{aspen_id}'")
        return name

    # ------------------------------------------------------------------
    # Single-property queries
    # ------------------------------------------------------------------

    def density(self, component: str, T: float, P: float) -> float:
        """Mass density [kg/m^3] at temperature *T* [K] and pressure *P* [Pa]."""
        return PropsSI("D", "T", T, "P", P, self._name(component))

    def enthalpy(self, component: str, T: float, P: float) -> float:
        """Specific enthalpy [J/kg] at *T* [K], *P* [Pa]."""
        return PropsSI("H", "T", T, "P", P, self._name(component))

    def entropy(self, component: str, T: float, P: float) -> float:
        """Specific entropy [J/(kg*K)] at *T* [K], *P* [Pa]."""
        return PropsSI("S", "T", T, "P", P, self._name(component))

    def cp(self, component: str, T: float, P: float) -> float:
        """Isobaric heat capacity [J/(kg*K)]."""
        return PropsSI("C", "T", T, "P", P, self._name(component))

    def viscosity(self, component: str, T: float, P: float) -> float:
        """Dynamic viscosity [Pa*s]."""
        return PropsSI("V", "T", T, "P", P, self._name(component))

    def thermal_conductivity(self, component: str, T: float, P: float) -> float:
        """Thermal conductivity [W/(m*K)]."""
        return PropsSI("L", "T", T, "P", P, self._name(component))

    def vapor_pressure(self, component: str, T: float) -> float:
        """Saturation pressure [Pa] at temperature *T* [K]."""
        return PropsSI("P", "T", T, "Q", 0, self._name(component))

    def molecular_weight(self, component: str) -> float:
        """Molar mass [kg/mol]."""
        return PropsSI("M", "T", 300, "P", 1e5, self._name(component))

    # ------------------------------------------------------------------
    # Critical properties
    # ------------------------------------------------------------------

    def critical_temperature(self, component: str) -> float:
        """Critical temperature [K]."""
        return PropsSI("Tcrit", "T", 0, "P", 0, self._name(component))

    def critical_pressure(self, component: str) -> float:
        """Critical pressure [Pa]."""
        return PropsSI("Pcrit", "T", 0, "P", 0, self._name(component))

    def acentric_factor(self, component: str) -> float:
        """Acentric factor [-]."""
        return PropsSI("acentric", "T", 0, "P", 0, self._name(component))

    # ------------------------------------------------------------------
    # Bulk query
    # ------------------------------------------------------------------

    def all_properties(self, component: str, T: float, P: float) -> dict[str, float]:
        """Return a dict of common thermophysical properties."""
        return {
            "density_kg_m3": self.density(component, T, P),
            "enthalpy_J_kg": self.enthalpy(component, T, P),
            "entropy_J_kgK": self.entropy(component, T, P),
            "cp_J_kgK": self.cp(component, T, P),
            "viscosity_Pa_s": self.viscosity(component, T, P),
            "thermal_conductivity_W_mK": self.thermal_conductivity(component, T, P),
            "molecular_weight_kg_mol": self.molecular_weight(component),
        }

    # ------------------------------------------------------------------
    # Enhancement for pyaspenplus Component objects
    # ------------------------------------------------------------------

    def enrich_component(self, component: Any) -> None:
        """Fill missing properties on a :class:`Component` using CoolProp."""
        cid = component.component_id
        try:
            name = self._name(cid)
        except KeyError:
            return

        if component.molecular_weight is None:
            component.molecular_weight = self.molecular_weight(cid) * 1000  # kg/mol -> g/mol
        if component.critical_temperature is None:
            component.critical_temperature = self.critical_temperature(cid)
        if component.critical_pressure is None:
            component.critical_pressure = self.critical_pressure(cid)
        if component.acentric_factor is None:
            component.acentric_factor = self.acentric_factor(cid)

    def enrich_component_list(self, comp_list: Any) -> None:
        """Enrich all components in a :class:`ComponentList`."""
        for comp in comp_list:
            self.enrich_component(comp)

    @staticmethod
    def available() -> bool:
        return _COOLPROP_AVAILABLE
