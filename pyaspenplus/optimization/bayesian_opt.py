"""Bayesian optimisation adapter using scikit-optimize."""

from __future__ import annotations

from typing import Any

import numpy as np

from pyaspenplus.optimization.base import (
    ObjectiveEvaluator,
    OptimizerBase,
    OptimizationResult,
)
from pyaspenplus.optimization.variable import DecisionVariable


class BayesianOptimizer(OptimizerBase):
    """Adapter for :func:`skopt.gp_minimize` (Gaussian-process Bayesian optimisation)."""

    def optimize(
        self,
        evaluator: ObjectiveEvaluator,
        variables: list[DecisionVariable],
        *,
        n_calls: int = 50,
        n_initial_points: int = 10,
        acq_func: str = "EI",
        **kwargs: Any,
    ) -> OptimizationResult:
        try:
            from skopt import gp_minimize
            from skopt.space import Real, Integer
        except ImportError as exc:
            raise ImportError(
                "scikit-optimize is required. Install with: "
                "pip install pyaspenplus[bayesian]"
            ) from exc

        dimensions = []
        for v in variables:
            if v.var_type == "integer":
                dimensions.append(Integer(int(v.lower), int(v.upper), name=v.name))
            else:
                dimensions.append(Real(v.lower, v.upper, name=v.name))

        def _wrapper(params: list) -> float:
            return float(evaluator(np.array(params, dtype=float)))

        x0 = [v.initial for v in variables]

        raw = gp_minimize(
            _wrapper,
            dimensions,
            n_calls=n_calls,
            n_initial_points=n_initial_points,
            acq_func=acq_func,
            x0=x0,
            **kwargs,
        )

        return OptimizationResult(
            optimal_values={v.name: float(xi) for v, xi in zip(variables, raw.x)},
            optimal_objective=float(raw.fun),
            success=True,
            message=f"Bayesian optimisation completed in {n_calls} calls",
            raw=raw,
        )
