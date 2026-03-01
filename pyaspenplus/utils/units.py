"""Unit conversion utilities for common process engineering quantities."""

from __future__ import annotations

_TEMPERATURE_OFFSETS = {
    ("C", "K"): lambda t: t + 273.15,
    ("K", "C"): lambda t: t - 273.15,
    ("F", "C"): lambda t: (t - 32) * 5 / 9,
    ("C", "F"): lambda t: t * 9 / 5 + 32,
    ("F", "K"): lambda t: (t - 32) * 5 / 9 + 273.15,
    ("K", "F"): lambda t: (t - 273.15) * 9 / 5 + 32,
    ("R", "K"): lambda t: t * 5 / 9,
    ("K", "R"): lambda t: t * 9 / 5,
}

_PRESSURE_TO_PA: dict[str, float] = {
    "Pa": 1.0,
    "kPa": 1e3,
    "MPa": 1e6,
    "bar": 1e5,
    "atm": 101325.0,
    "psi": 6894.757,
    "mmHg": 133.322,
    "torr": 133.322,
}

_FLOW_TO_MOL_PER_S: dict[str, float] = {
    "mol/s": 1.0,
    "kmol/s": 1e3,
    "kmol/hr": 1e3 / 3600,
    "mol/hr": 1 / 3600,
    "lbmol/hr": 453.59237 / 3600,
}


def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    """Convert temperature between C, K, F, R."""
    if from_unit == to_unit:
        return value
    key = (from_unit.upper().rstrip("°"), to_unit.upper().rstrip("°"))
    try:
        return _TEMPERATURE_OFFSETS[key](value)
    except KeyError:
        raise ValueError(f"Unknown temperature conversion: {from_unit} -> {to_unit}")


def convert_pressure(value: float, from_unit: str, to_unit: str) -> float:
    """Convert pressure between Pa, kPa, MPa, bar, atm, psi, mmHg, torr."""
    if from_unit == to_unit:
        return value
    try:
        return value * _PRESSURE_TO_PA[from_unit] / _PRESSURE_TO_PA[to_unit]
    except KeyError:
        raise ValueError(f"Unknown pressure unit: {from_unit} or {to_unit}")


def convert_molar_flow(value: float, from_unit: str, to_unit: str) -> float:
    """Convert molar flow between mol/s, kmol/s, kmol/hr, mol/hr, lbmol/hr."""
    if from_unit == to_unit:
        return value
    try:
        return value * _FLOW_TO_MOL_PER_S[from_unit] / _FLOW_TO_MOL_PER_S[to_unit]
    except KeyError:
        raise ValueError(f"Unknown molar flow unit: {from_unit} or {to_unit}")
