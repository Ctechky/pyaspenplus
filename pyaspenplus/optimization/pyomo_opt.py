"""Pyomo adapter for pyaspenplus.

Uses a Pyomo ``ConcreteModel`` with an ``ExternalFunction``-style callback
that runs the Aspen simulation for each evaluation.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from pyaspenplus.optimization.base import (
    ObjectiveEvaluator,
    OptimizerBase,
    OptimizationResult,
)
from pyaspenplus.optimization.variable import DecisionVariable


class PyomoOptimizer(OptimizerBase):
    """Adapter that formulates the problem in Pyomo and solves with a chosen solver.

    Because the Aspen objective is a black-box, this adapter builds a Pyomo
    model with external grey-box / callback evaluation, suitable for
    derivative-free solvers (e.g. ``"mindtpy"``, ``"bonmin"``, or a
    scipy-backed Pyomo solver).
    """

    def __init__(self, solver: str = "ipopt") -> None:
        self._solver_name = solver

    def optimize(
        self,
        evaluator: ObjectiveEvaluator,
        variables: list[DecisionVariable],
        **kwargs: Any,
    ) -> OptimizationResult:
        try:
            import pyomo.environ as pyo
        except ImportError as exc:
            raise ImportError(
                "Pyomo is required for this optimizer. Install with: "
                "pip install pyaspenplus[pyomo]"
            ) from exc

        model = pyo.ConcreteModel()

        model.var_indices = pyo.RangeSet(0, len(variables) - 1)
        model.x = pyo.Var(model.var_indices, within=pyo.Reals)

        for i, dv in enumerate(variables):
            model.x[i].setlb(dv.lower)
            model.x[i].setub(dv.upper)
            model.x[i].value = dv.initial

        # Black-box objective via a Python callback wrapper
        _eval_cache: dict[tuple, float] = {}

        def _obj_rule(m: Any) -> float:
            x_vals = tuple(pyo.value(m.x[i]) for i in m.var_indices)
            if x_vals in _eval_cache:
                return _eval_cache[x_vals]
            val = float(evaluator(np.array(x_vals)))
            _eval_cache[x_vals] = val
            return val

        model.obj = pyo.Objective(rule=_obj_rule, sense=pyo.minimize)

        solver = pyo.SolverFactory(self._solver_name)
        solver_result = solver.solve(model, tee=kwargs.pop("tee", False), **kwargs)

        opt_vals = {
            v.name: float(pyo.value(model.x[i]))
            for i, v in enumerate(variables)
        }
        opt_obj = float(pyo.value(model.obj))

        success = (
            solver_result.solver.termination_condition
            == pyo.TerminationCondition.optimal
        )

        return OptimizationResult(
            optimal_values=opt_vals,
            optimal_objective=opt_obj,
            success=success,
            message=str(solver_result.solver.termination_condition),
            raw=solver_result,
        )
