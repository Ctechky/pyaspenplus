"""pymoo multi-objective evolutionary optimizer adapter."""

from __future__ import annotations

from typing import Any

import numpy as np

from pyaspenplus.optimization.base import (
    ObjectiveEvaluator,
    OptimizerBase,
    OptimizationResult,
)
from pyaspenplus.optimization.variable import DecisionVariable

_PYMOO_ALGO_MAP: dict[str, str] = {
    "pymoo-nsga2": "NSGA2",
    "pymoo-nsga3": "NSGA3",
    "pymoo-de": "DE",
    "pymoo-pso": "PSO",
    "nsga2": "NSGA2",
}


class PymooOptimizer(OptimizerBase):
    """Adapter for :mod:`pymoo` evolutionary / multi-objective algorithms."""

    def __init__(self, method: str = "pymoo-nsga2") -> None:
        self._method_key = method.lower()

    def optimize(
        self,
        evaluator: ObjectiveEvaluator,
        variables: list[DecisionVariable],
        *,
        n_gen: int = 50,
        pop_size: int = 20,
        objectives: list[Any] | None = None,
        **kwargs: Any,
    ) -> OptimizationResult:
        try:
            from pymoo.algorithms.moo.nsga2 import NSGA2
            from pymoo.algorithms.soo.nonconvex.de import DE
            from pymoo.algorithms.soo.nonconvex.pso import PSO
            from pymoo.core.problem import Problem
            from pymoo.optimize import minimize as pymoo_minimize
        except ImportError as exc:
            raise ImportError(
                "pymoo is required. Install with: pip install pyaspenplus[evolutionary]"
            ) from exc

        n_var = len(variables)
        xl = np.array([v.lower for v in variables])
        xu = np.array([v.upper for v in variables])

        n_obj = len(objectives) if objectives else 1
        multi = n_obj > 1

        # Store objective functions for multi-obj
        obj_fns = objectives if multi else [evaluator.objective_fn]

        class AspenProblem(Problem):
            def __init__(self) -> None:
                super().__init__(n_var=n_var, n_obj=n_obj, xl=xl, xu=xu)

            def _evaluate(self, X: np.ndarray, out: dict, *args: Any, **kw: Any) -> None:
                F = np.zeros((X.shape[0], n_obj))
                for i, x in enumerate(X):
                    if multi:
                        for var, val in zip(variables, x):
                            evaluator.simulation.set_value(var.path, float(val))
                        evaluator.simulation.run()
                        for j, fn in enumerate(obj_fns):
                            F[i, j] = fn(evaluator.simulation)
                        evaluator.eval_count += 1
                    else:
                        F[i, 0] = float(evaluator(x))
                out["F"] = F

        problem = AspenProblem()

        algo_name = _PYMOO_ALGO_MAP.get(self._method_key, "NSGA2")
        if algo_name == "NSGA2":
            algorithm = NSGA2(pop_size=pop_size)
        elif algo_name == "DE":
            algorithm = DE(pop_size=pop_size)
        elif algo_name == "PSO":
            algorithm = PSO(pop_size=pop_size)
        else:
            algorithm = NSGA2(pop_size=pop_size)

        raw = pymoo_minimize(problem, algorithm, ("n_gen", n_gen), verbose=False, **kwargs)

        if raw.X is not None and raw.X.ndim == 1:
            best_x = raw.X
            best_f = float(raw.F[0]) if raw.F.ndim > 0 else float(raw.F)
        elif raw.X is not None:
            idx = np.argmin(raw.F[:, 0])
            best_x = raw.X[idx]
            best_f = float(raw.F[idx, 0])
        else:
            best_x = np.array([v.initial for v in variables])
            best_f = float("inf")

        return OptimizationResult(
            optimal_values={v.name: float(xi) for v, xi in zip(variables, best_x)},
            optimal_objective=best_f,
            success=raw.X is not None,
            message=f"pymoo {algo_name} completed, {n_gen} generations",
            raw=raw,
        )
