"""Tests for the optimization module (unit-level, no COM needed)."""

import pytest
import numpy as np

from pyaspenplus.optimization.variable import DecisionVariable
from pyaspenplus.optimization.base import OptimizationResult


class TestDecisionVariable:
    def test_default_initial_is_midpoint(self):
        dv = DecisionVariable("x", path="A.B", bounds=(10, 20))
        assert dv.initial == 15.0

    def test_clip(self):
        dv = DecisionVariable("x", path="A.B", bounds=(0, 1))
        assert dv.clip(-0.5) == 0.0
        assert dv.clip(1.5) == 1.0
        assert dv.clip(0.5) == 0.5

    def test_custom_initial(self):
        dv = DecisionVariable("x", path="A.B", bounds=(0, 10), initial=3.0)
        assert dv.initial == 3.0


class TestOptimizationResult:
    def test_summary(self):
        result = OptimizationResult(
            optimal_values={"temp": 250.0, "pres": 75.0},
            optimal_objective=-0.123,
            success=True,
            message="done",
            n_evaluations=42,
        )
        s = result.summary()
        assert "succeeded" in s
        assert "250" in s
        assert "42" in s
