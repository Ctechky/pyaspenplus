"""Decision variables that map optimizer values to Aspen Plus tree paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DecisionVariable:
    """A single optimisation decision variable.

    Parameters
    ----------
    name : str
        Human-readable name for the variable.
    path : str
        Aspen Plus variable-tree path (dot-separated), e.g.
        ``"Blocks.REACTOR.Input.TEMP"``.
    bounds : tuple[float, float]
        Lower and upper bounds ``(lb, ub)``.
    initial : float | None
        Starting value.  Defaults to midpoint of bounds.
    var_type : str
        ``"continuous"`` or ``"integer"``.
    """

    name: str
    path: str
    bounds: tuple[float, float]
    initial: float | None = None
    var_type: str = "continuous"

    def __post_init__(self) -> None:
        if self.initial is None:
            self.initial = (self.bounds[0] + self.bounds[1]) / 2.0

    @property
    def lower(self) -> float:
        return self.bounds[0]

    @property
    def upper(self) -> float:
        return self.bounds[1]

    def clip(self, value: float) -> float:
        """Clip *value* to the variable's bounds."""
        return max(self.lower, min(value, self.upper))

    def __repr__(self) -> str:
        return (
            f"DecisionVariable({self.name!r}, path={self.path!r}, "
            f"bounds={self.bounds})"
        )
