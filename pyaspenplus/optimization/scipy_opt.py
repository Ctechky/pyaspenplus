"""scipy.optimize adapter for pyaspenplus."""

from __future__ import annotations

from typing import Any

import numpy as np

from pyaspenplus.optimization.base import (
    ObjectiveEvaluator,
    OptimizerBase,
    OptimizationResult,
)
from pyaspenplus.optimization.variable import DecisionVariable

# Method aliases: "scipy-nelder_mead" -> "Nelder-Mead", etc.
_SCIPY_METHOD_MAP: dict[str, str] = {
    "scipy-nelder_mead": "Nelder-Mead",
    "scipy-powell": "Powell",
    "scipy-cobyla": "COBYLA",
    "scipy-slsqp": "SLSQP",
    "scipy-differential_evolution": "differential_evolution",
    "scipy-dual_annealing": "dual_annealing",
    "scipy-shgo": "shgo",
    "scipy-basin_hopping": "basinhopping",
}


class ScipyOptimizer(OptimizerBase):
    """Adapter for :mod:`scipy.optimize` solvers."""

    def __init__(self, method: str = "scipy-nelder_mead") -> None:
        self._method_key = method.lower()

    def optimize(
        self,
        evaluator: ObjectiveEvaluator,
        variables: list[DecisionVariable],
        **kwargs: Any,
    ) -> OptimizationResult:
        try:
            import scipy.optimize as sopt
        except ImportError as exc:
            raise ImportError(
                "scipy is required for this optimizer. Install with: "
                "pip install pyaspenplus[scipy]"
            ) from exc

        bounds = [(v.lower, v.upper) for v in variables]
        x0 = np.array([v.initial for v in variables], dtype=float)

        scipy_method = _SCIPY_METHOD_MAP.get(self._method_key, "Nelder-Mead")

        if scipy_method == "differential_evolution":
            raw = sopt.differential_evolution(evaluator, bounds=bounds, **kwargs)
        elif scipy_method == "dual_annealing":
            raw = sopt.dual_annealing(evaluator, bounds=bounds, x0=x0, **kwargs)
        elif scipy_method == "shgo":
            raw = sopt.shgo(evaluator, bounds=bounds, **kwargs)
        elif scipy_method == "basinhopping":
            raw = sopt.basinhopping(evaluator, x0, **kwargs)
        else:
            raw = sopt.minimize(
                evaluator,
                x0,
                method=scipy_method,
                bounds=bounds,
                **kwargs,
            )

        result = OptimizationResult(
            optimal_values={v.name: float(xi) for v, xi in zip(variables, raw.x)},
            optimal_objective=float(raw.fun),
            success=bool(raw.success) if hasattr(raw, "success") else True,
            message=str(getattr(raw, "message", "")),
            raw=raw,
        )
        return result
