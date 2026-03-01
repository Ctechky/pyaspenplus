"""Abstract optimizer interface and the top-level ``optimize`` dispatcher."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

import numpy as np

from pyaspenplus.optimization.variable import DecisionVariable
from pyaspenplus.utils.logger import get_logger

if TYPE_CHECKING:
    from pyaspenplus.core.simulation import Simulation

log = get_logger("optimization")


@dataclass
class OptimizationResult:
    """Container for the outcome of an optimisation run."""

    optimal_values: dict[str, float] = field(default_factory=dict)
    optimal_objective: float = float("inf")
    n_evaluations: int = 0
    success: bool = False
    message: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)
    raw: Any = None  # backend-specific result object

    def summary(self) -> str:
        lines = [
            f"Optimization {'succeeded' if self.success else 'FAILED'}: {self.message}",
            f"  Objective : {self.optimal_objective:.6g}",
            f"  Evaluations: {self.n_evaluations}",
            "  Variables:",
        ]
        for name, val in self.optimal_values.items():
            lines.append(f"    {name:20s} = {val:.6g}")
        return "\n".join(lines)


# ------------------------------------------------------------------
# Objective wrapper
# ------------------------------------------------------------------


class ObjectiveEvaluator:
    """Wraps a user-supplied objective function so each call:

    1. Sets decision-variable values on the Aspen simulation.
    2. Runs the simulation.
    3. Evaluates the objective and returns a scalar (or vector for multi-obj).
    """

    def __init__(
        self,
        simulation: "Simulation",
        variables: list[DecisionVariable],
        objective_fn: Callable[["Simulation"], float | list[float]],
    ) -> None:
        self.simulation = simulation
        self.variables = variables
        self.objective_fn = objective_fn
        self.eval_count = 0
        self.history: list[dict[str, Any]] = []

    def __call__(self, x: np.ndarray) -> float | np.ndarray:
        for var, val in zip(self.variables, x):
            self.simulation.set_value(var.path, float(val))

        self.simulation.run()
        obj = self.objective_fn(self.simulation)
        self.eval_count += 1

        record = {str(v.name): float(xi) for v, xi in zip(self.variables, x)}
        record["objective"] = obj
        self.history.append(record)

        log.debug("Eval #%d  obj=%.6g  vars=%s", self.eval_count, obj, record)
        return obj


# ------------------------------------------------------------------
# Abstract base
# ------------------------------------------------------------------


class OptimizerBase(abc.ABC):
    """Interface that every optimizer adapter must implement."""

    @abc.abstractmethod
    def optimize(
        self,
        evaluator: ObjectiveEvaluator,
        variables: list[DecisionVariable],
        **kwargs: Any,
    ) -> OptimizationResult:
        ...


# ------------------------------------------------------------------
# Registry + top-level dispatcher
# ------------------------------------------------------------------

_REGISTRY: dict[str, type[OptimizerBase]] = {}


def register_optimizer(name: str, cls: type[OptimizerBase]) -> None:
    _REGISTRY[name.lower()] = cls


def list_optimizers() -> list[str]:
    return sorted(_REGISTRY.keys())


def optimize(
    simulation: "Simulation",
    variables: list[DecisionVariable],
    objective: Callable[["Simulation"], float | list[float]],
    *,
    method: str = "scipy-nelder_mead",
    **kwargs: Any,
) -> OptimizationResult:
    """Run an optimisation using the specified *method* backend.

    Parameters
    ----------
    simulation : Simulation
        A COM-mode simulation handle.
    variables : list[DecisionVariable]
        Decision variables with Aspen tree paths and bounds.
    objective : callable
        ``f(sim) -> float`` — the function to minimise.
    method : str
        Backend identifier, e.g. ``"scipy-nelder_mead"``,
        ``"pymoo-nsga2"``, ``"bayesian"``.
    **kwargs
        Passed through to the backend optimizer.
    """
    evaluator = ObjectiveEvaluator(simulation, variables, objective)

    # Lazy-load adapters to avoid hard dependency on optional packages
    method_lower = method.lower()

    if method_lower.startswith("scipy"):
        from pyaspenplus.optimization.scipy_opt import ScipyOptimizer

        optimizer: OptimizerBase = ScipyOptimizer(method=method_lower)
    elif method_lower.startswith("pymoo") or method_lower.startswith("nsga"):
        from pyaspenplus.optimization.evolutionary import PymooOptimizer

        optimizer = PymooOptimizer(method=method_lower)
    elif method_lower.startswith("bayesian") or method_lower.startswith("skopt"):
        from pyaspenplus.optimization.bayesian_opt import BayesianOptimizer

        optimizer = BayesianOptimizer()
    elif method_lower.startswith("pyomo"):
        from pyaspenplus.optimization.pyomo_opt import PyomoOptimizer

        optimizer = PyomoOptimizer()
    else:
        cls = _REGISTRY.get(method_lower)
        if cls is None:
            raise ValueError(
                f"Unknown optimizer method '{method}'. "
                f"Available: {list_optimizers() + ['scipy-*', 'pymoo-*', 'bayesian', 'pyomo']}"
            )
        optimizer = cls()

    log.info("Starting optimization with method=%s", method)
    result = optimizer.optimize(evaluator, variables, **kwargs)
    result.history = evaluator.history
    result.n_evaluations = evaluator.eval_count
    log.info(
        "Optimization finished: success=%s, obj=%.6g, evals=%d",
        result.success,
        result.optimal_objective,
        result.n_evaluations,
    )
    return result
