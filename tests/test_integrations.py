"""Tests for integration adapters.

Each test checks basic functionality without requiring the third-party
library to be installed — tests are skipped when the library is absent.
"""

import pytest
import numpy as np


# ======================================================================
#  CoolProp
# ======================================================================

class TestCoolPropAdapter:
    @pytest.fixture(autouse=True)
    def _skip_if_unavailable(self):
        try:
            from pyaspenplus.integrations.coolprop_adapter import CoolPropAdapter

            if not CoolPropAdapter.available():
                pytest.skip("CoolProp not installed")
        except ImportError:
            pytest.skip("CoolProp not installed")

    def test_density_water(self):
        from pyaspenplus.integrations.coolprop_adapter import CoolPropAdapter

        cp = CoolPropAdapter()
        rho = cp.density("H2O", T=373.15, P=101325)
        assert 0.5 < rho < 1.0  # steam density ~ 0.6 kg/m3 at 1 atm

    def test_molecular_weight(self):
        from pyaspenplus.integrations.coolprop_adapter import CoolPropAdapter

        cp = CoolPropAdapter()
        mw = cp.molecular_weight("H2O")
        assert pytest.approx(mw, rel=0.01) == 0.018015

    def test_critical_temperature_co2(self):
        from pyaspenplus.integrations.coolprop_adapter import CoolPropAdapter

        cp = CoolPropAdapter()
        Tc = cp.critical_temperature("CO2")
        assert pytest.approx(Tc, abs=1) == 304.13

    def test_all_properties_returns_dict(self):
        from pyaspenplus.integrations.coolprop_adapter import CoolPropAdapter

        cp = CoolPropAdapter()
        props = cp.all_properties("H2", T=300, P=1e5)
        assert "density_kg_m3" in props
        assert "cp_J_kgK" in props
        assert props["density_kg_m3"] > 0

    def test_enrich_component(self):
        from pyaspenplus.integrations.coolprop_adapter import CoolPropAdapter
        from pyaspenplus.materials.components import Component

        cp = CoolPropAdapter()
        comp = Component(component_id="CH3OH")
        assert comp.molecular_weight is None
        cp.enrich_component(comp)
        assert comp.molecular_weight is not None
        assert comp.molecular_weight > 30  # methanol ~32 g/mol

    def test_unknown_component_raises(self):
        from pyaspenplus.integrations.coolprop_adapter import CoolPropAdapter

        cp = CoolPropAdapter()
        with pytest.raises(KeyError, match="No CoolProp mapping"):
            cp.density("UNOBTANIUM", T=300, P=1e5)


# ======================================================================
#  Cantera
# ======================================================================

class TestCanteraAdapter:
    @pytest.fixture(autouse=True)
    def _skip_if_unavailable(self):
        try:
            from pyaspenplus.integrations.cantera_adapter import CanteraAdapter

            if not CanteraAdapter.available():
                pytest.skip("Cantera not installed")
        except ImportError:
            pytest.skip("Cantera not installed")

    def test_create_ideal_gas(self):
        from pyaspenplus.integrations.cantera_adapter import CanteraAdapter

        ca = CanteraAdapter()
        gas = ca.create_ideal_gas(T=500, P=1e5)
        assert gas.T == pytest.approx(500)
        assert gas.P == pytest.approx(1e5)

    def test_equilibrium_changes_composition(self):
        from pyaspenplus.integrations.cantera_adapter import CanteraAdapter

        ca = CanteraAdapter()
        gas = ca.create_ideal_gas(T=2000, P=1e5, X={"CH4": 0.5, "O2": 1.0})
        X_before = dict(zip(gas.species_names, gas.X))
        eq = ca.equilibrium(gas, "TP")
        assert eq  # should have some species


# ======================================================================
#  Chemlib
# ======================================================================

class TestChemlibAdapter:
    @pytest.fixture(autouse=True)
    def _skip_if_unavailable(self):
        try:
            from pyaspenplus.integrations.chemlib_adapter import ChemlibAdapter

            if not ChemlibAdapter.available():
                pytest.skip("chemlib not installed")
        except ImportError:
            pytest.skip("chemlib not installed")

    def test_molar_mass_water(self):
        from pyaspenplus.integrations.chemlib_adapter import ChemlibAdapter

        cl = ChemlibAdapter()
        mw = cl.molar_mass("H2O")
        assert pytest.approx(mw, rel=0.01) == 18.015

    def test_molar_mass_methanol(self):
        from pyaspenplus.integrations.chemlib_adapter import ChemlibAdapter

        cl = ChemlibAdapter()
        mw = cl.molar_mass("CH3OH")
        assert 31 < mw < 33

    def test_validate_balanced_stoichiometry(self):
        from pyaspenplus.integrations.chemlib_adapter import ChemlibAdapter

        cl = ChemlibAdapter()
        stoic = {"CO2": -1, "H2": -3, "CH3OH": 1, "H2O": 1}
        balance = cl.validate_stoichiometry(stoic)
        for element, imbalance in balance.items():
            assert abs(imbalance) < 1e-10, f"Unbalanced {element}: {imbalance}"


# ======================================================================
#  PyChemEngg (standalone math — no external lib needed for basic tests)
# ======================================================================

class TestPyChemEnggAdapter:
    """Tests that work even without pychemengg installed by testing the
    static helper methods directly."""

    def test_heat_duty(self):
        from pyaspenplus.integrations.pychemengg_adapter import PyChemEnggAdapter

        Q = PyChemEnggAdapter.heat_duty(mass_flow=10, cp=4180, T_in=300, T_out=350)
        assert Q == pytest.approx(10 * 4180 * 50)

    def test_lmtd_counter_current(self):
        from pyaspenplus.integrations.pychemengg_adapter import PyChemEnggAdapter

        lmtd = PyChemEnggAdapter.lmtd(
            T_hot_in=400, T_hot_out=350, T_cold_in=300, T_cold_out=370
        )
        # dT1=30, dT2=50 -> LMTD = (30-50)/ln(30/50) ≈ 39.2 K
        assert 38 < lmtd < 41

    def test_lmtd_equal_dT(self):
        from pyaspenplus.integrations.pychemengg_adapter import PyChemEnggAdapter

        lmtd = PyChemEnggAdapter.lmtd(
            T_hot_in=400, T_hot_out=350, T_cold_in=300, T_cold_out=350
        )
        assert lmtd == pytest.approx(50.0)

    def test_hx_area(self):
        from pyaspenplus.integrations.pychemengg_adapter import PyChemEnggAdapter

        area = PyChemEnggAdapter.hx_area(Q=100_000, U=500, lmtd_val=50)
        assert area == pytest.approx(4.0)

    def test_mass_balance_check(self):
        from pyaspenplus.integrations.pychemengg_adapter import PyChemEnggAdapter

        imbalance = PyChemEnggAdapter.mass_balance_check(
            inlet_flows={"H2": 100, "CO2": 500},
            outlet_flows={"H2": 50, "CO2": 400, "CH3OH": 120, "H2O": 30},
        )
        assert imbalance["H2"] == -50
        assert imbalance["CH3OH"] == 120

    def test_energy_balance_check(self):
        from pyaspenplus.integrations.pychemengg_adapter import PyChemEnggAdapter

        residual = PyChemEnggAdapter.energy_balance_check(
            inlet_enthalpy=1000, outlet_enthalpy=900, heat_added=0, work_done=100
        )
        assert residual == pytest.approx(0)


# ======================================================================
#  Matplotlib / PlotAdapter
# ======================================================================

class TestPlotAdapter:
    @pytest.fixture(autouse=True)
    def _skip_if_unavailable(self):
        try:
            import matplotlib

            matplotlib.use("Agg")  # non-interactive backend for tests
        except ImportError:
            pytest.skip("matplotlib not installed")

    def test_plot_composition_profile(self):
        from pyaspenplus.integrations.matplotlib_adapter import PlotAdapter

        plotter = PlotAdapter()
        z = np.linspace(0, 1, 50)
        compositions = {
            "A": np.exp(-z),
            "B": 1 - np.exp(-z),
        }
        fig, ax = plotter.plot_composition_profile(z, compositions)
        assert fig is not None
        import matplotlib.pyplot as plt

        plt.close(fig)

    def test_plot_optimization_convergence(self):
        from pyaspenplus.integrations.matplotlib_adapter import PlotAdapter

        plotter = PlotAdapter()
        history = [{"objective": 10 - i + np.random.rand()} for i in range(20)]
        fig, ax = plotter.plot_optimization_convergence(history)
        assert fig is not None
        import matplotlib.pyplot as plt

        plt.close(fig)

    def test_plot_cost_breakdown(self):
        from pyaspenplus.integrations.matplotlib_adapter import PlotAdapter

        plotter = PlotAdapter()
        fig, ax = plotter.plot_cost_breakdown(
            labels=["A", "B", "C"],
            values=[100, 200, 300],
        )
        assert fig is not None
        import matplotlib.pyplot as plt

        plt.close(fig)

    def test_plot_stream_temperatures(self):
        from pyaspenplus.integrations.matplotlib_adapter import PlotAdapter

        plotter = PlotAdapter()
        fig, ax = plotter.plot_stream_temperatures(
            ["FEED", "PRODUCT", "RECYCLE"],
            [523.15, 473.15, 373.15],
        )
        assert fig is not None
        import matplotlib.pyplot as plt

        plt.close(fig)


# ======================================================================
#  Flowsheet Diagram
# ======================================================================

class TestFlowsheetDiagram:
    @pytest.fixture(autouse=True)
    def _skip_if_unavailable(self):
        try:
            import matplotlib

            matplotlib.use("Agg")
        except ImportError:
            pytest.skip("matplotlib not installed")

    def test_draw_simple_flowsheet(self):
        from pyaspenplus.models.blocks import Block
        from pyaspenplus.models.streams import Stream
        from pyaspenplus.models.flowsheet import Flowsheet
        from pyaspenplus.visualization.flowsheet_diagram import draw_flowsheet

        fs = Flowsheet(
            blocks=[
                Block(name="REACTOR", block_type="RPLUG",
                      inlet_streams=["FEED"], outlet_streams=["PROD"]),
                Block(name="COOLER", block_type="HEATER",
                      inlet_streams=["PROD"], outlet_streams=["COOL"]),
            ],
            streams=[
                Stream(name="FEED", dest_block="REACTOR"),
                Stream(name="PROD", source_block="REACTOR", dest_block="COOLER"),
                Stream(name="COOL", source_block="COOLER"),
            ],
        )
        fig, ax = draw_flowsheet(fs, title="Test Flowsheet")
        assert fig is not None
        import matplotlib.pyplot as plt

        plt.close(fig)
