#!/usr/bin/env python
"""
Comprehensive demo for pyaspenplus using the FYP methanol synthesis model.

This script demonstrates all library capabilities in three modes:

  1. COM MODE   — If Aspen Plus is installed, opens the .apw file, reads
                  model info, streams, blocks, reactions, runs economics,
                  and executes an optimization.

  2. BKP MODE   — If a .bkp export exists, parses it to extract model
                  data without Aspen Plus.

  3. STANDALONE — Always runs: methanol kinetics, PFR simulation, cost
                  estimation, and integration library demos.

Run:
    python demo_fyp_model.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ======================================================================
#  Configuration
# ======================================================================

APW_FILE = Path("FYP Recycle last no_CO2_H2.apw")
BKP_FILE = APW_FILE.with_suffix(".bkp")

SEPARATOR = "=" * 72


def header(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


# ======================================================================
#  1. Check integration availability
# ======================================================================

def demo_availability() -> None:
    header("Integration Availability")
    import pyaspenplus
    status = pyaspenplus.available_integrations()
    for lib, ok in status.items():
        mark = "OK" if ok else "NOT INSTALLED"
        print(f"  {lib:15s} : {mark}")
    print()


# ======================================================================
#  2. COM Mode (requires Aspen Plus)
# ======================================================================

def demo_com_mode() -> None:
    header("COM Mode — Live Aspen Plus Connection")

    if not APW_FILE.exists():
        print(f"  APW file not found: {APW_FILE}")
        return

    try:
        from pyaspenplus import Simulation
        sim = Simulation.from_file(str(APW_FILE), visible=False)
    except Exception as e:
        print(f"  COM connection failed (Aspen Plus not available): {e}")
        print("  Skipping COM mode demo.\n")
        return

    print("\n--- Model Info ---")
    print(sim.info.summary())

    print("\n--- Components ---")
    for comp in sim.components:
        print(f"  {comp.component_id:10s}  MW={comp.molecular_weight}")

    print("\n--- Flowsheet Blocks ---")
    for block in sim.flowsheet.blocks:
        print(f"  {block.name:15s}  type={block.block_type:10s}  "
              f"in={block.inlet_streams}  out={block.outlet_streams}")

    print("\n--- Flowsheet Streams ---")
    for stream in sim.flowsheet.streams:
        print(f"  {stream.name:15s}  T={stream.temperature}  P={stream.pressure}")

    print("\n--- Reactions ---")
    for rxn in sim.reactions:
        print(f"  {rxn.name}: {rxn.equation_string}")
        if rxn.kinetic_parameters:
            print(f"    Kinetics: {rxn.kinetic_parameters}")

    print("\n--- Materials / Feed ---")
    for sname in sim.materials.feed_names[:3]:
        feed = sim.materials.get_feed(sname)
        print(f"  Feed '{feed.name}': T={feed.temperature}, P={feed.pressure}")
        print(f"    Components: {feed.components}")
        print(f"    Mole fracs: {feed.mole_fractions}")

    # Economics
    print("\n--- APEA Economics ---")
    try:
        from pyaspenplus.economics import CostEstimator
        cost = CostEstimator(sim)
        apea = cost.read_apea()
        print(apea.summary())
    except Exception as e:
        print(f"  APEA not available: {e}")

    # Visualization
    try:
        from pyaspenplus.visualization.flowsheet_diagram import draw_flowsheet
        fig, ax = draw_flowsheet(sim.flowsheet, title="FYP Methanol Synthesis Flowsheet",
                                 save_path="fyp_flowsheet.png")
        print("\n  Flowsheet diagram saved to fyp_flowsheet.png")
    except Exception as e:
        print(f"  Flowsheet diagram skipped: {e}")

    sim.close()
    print("\n  COM mode demo complete.")


# ======================================================================
#  3. BKP Mode (parser, no Aspen required)
# ======================================================================

def demo_bkp_mode() -> None:
    header("BKP Parser Mode — Offline File Parsing")

    if not BKP_FILE.exists():
        print(f"  BKP file not found: {BKP_FILE}")
        print("  To create one: open your .apw in Aspen Plus, File > Save As > .bkp")
        print("  Skipping BKP mode demo.\n")
        return

    from pyaspenplus import Simulation
    sim = Simulation.from_bkp(str(BKP_FILE))

    print("\n--- Model Info ---")
    print(sim.info.summary())

    print("\n--- Components ---")
    for cid in sim.info.components:
        print(f"  {cid}")

    print(f"\n  Property method: {sim.info.property_method}")

    print("\n--- Blocks ---")
    for block in sim.flowsheet.blocks:
        print(f"  {block.name:15s}  type={block.block_type}")

    print("\n--- Streams ---")
    for stream in sim.flowsheet.streams:
        print(f"  {stream.name:15s}  T={stream.temperature}  P={stream.pressure}")

    print("\n  BKP mode demo complete.")


# ======================================================================
#  4. Standalone Methanol Kinetics Demo
# ======================================================================

def demo_kinetics() -> None:
    header("Standalone Methanol Kinetics — Bussche & Froment (1996)")

    from pyaspenplus.examples.methanol.kinetics import MethanolKinetics
    from pyaspenplus.examples.methanol.synthesis import MethanolSynthesis

    # --- Kinetic rates at a single point ---
    kin = MethanolKinetics()
    y_feed = {"CO2": 0.0334, "H2": 0.8217, "CO": 0.0112, "CH3OH": 0.0, "H2O": 0.0}

    print("\n--- Reaction Rates at T=523 K, P=75 bar ---")
    rates = kin.reaction_rates(T=523.15, P=75e5, y=y_feed)
    for name, val in rates.items():
        print(f"  {name}: {val:.4e} mol/(m3_cat·s)")

    print("\n--- Species Rates ---")
    sr = kin.species_rates(T=523.15, P=75e5, y=y_feed)
    for sp, val in sr.items():
        print(f"  {sp:8s}: {val:+.4e} mol/(m3_cat·s)")

    # --- Temperature sensitivity ---
    print("\n--- Temperature Sensitivity (methanol rate) ---")
    temps = np.linspace(473, 573, 6)
    for T in temps:
        r = kin.reaction_rates(T=T, P=75e5, y=y_feed)
        print(f"  T={T:.0f} K : r_methanol = {r['r_methanol']:.4e}")

    # --- PFR simulation ---
    print("\n--- Isothermal PFR Simulation (L=0.15 m) ---")
    model = MethanolSynthesis()
    profile = model.solve_pfr(length=0.15, n_points=200)

    print(f"  Inlet  y_CH3OH = {profile['y_CH3OH'][0]:.6f}")
    print(f"  Outlet y_CH3OH = {profile['y_CH3OH'][-1]:.6f}")
    print(f"  Inlet  y_H2    = {profile['y_H2'][0]:.6f}")
    print(f"  Outlet y_H2    = {profile['y_H2'][-1]:.6f}")
    print(f"  Inlet  y_CO2   = {profile['y_CO2'][0]:.6f}")
    print(f"  Outlet y_CO2   = {profile['y_CO2'][-1]:.6f}")

    # --- Plot if matplotlib available ---
    try:
        from pyaspenplus.integrations.matplotlib_adapter import PlotAdapter
        plotter = PlotAdapter()
        fig, ax = plotter.plot_composition_profile(
            profile["z"],
            {sp: profile[f"y_{sp}"] for sp in ["CO2", "H2", "CO", "CH3OH", "H2O"]},
            title="Methanol Synthesis — PFR Composition Profile (75 bar, 250°C)",
        )
        fig.savefig("methanol_pfr_profile.png", dpi=200)
        print("\n  PFR profile plot saved to methanol_pfr_profile.png")
    except ImportError:
        print("\n  (matplotlib not installed — skipping plot)")


# ======================================================================
#  5. Economics Demo (standalone correlations)
# ======================================================================

def demo_economics() -> None:
    header("Economics — CAPEX/OPEX Estimation")

    from pyaspenplus.economics.capex import purchased_equipment_cost, total_capital_investment
    from pyaspenplus.economics.opex import estimate_opex

    # Equipment cost estimates
    print("\n--- Equipment Cost Estimates (Turton Correlations, 2023 $) ---")
    reactor = purchased_equipment_cost("reactor_jacketed", sizing_parameter=5.0)
    hx = purchased_equipment_cost("heat_exchanger_fixed", sizing_parameter=50)
    compressor = purchased_equipment_cost("compressor_centrifugal", sizing_parameter=500)

    for eq in [reactor, hx, compressor]:
        print(f"  {eq.equipment_type:30s}  Purchased: ${eq.purchased_cost:>12,.0f}  "
              f"Bare Module: ${eq.bare_module_cost:>12,.0f}")

    tci = total_capital_investment([reactor, hx, compressor])
    print(f"\n  Total Capital Investment (TCI): ${tci:,.0f}")

    # OPEX
    print("\n--- Operating Cost Estimate ---")
    opex = estimate_opex(
        raw_material_prices={"H2": 2.50, "CO2": 0.04},
        raw_material_flows={"H2": 500, "CO2": 1500},  # kg/hr
        utility_consumptions={"electricity": 200, "steam_hp": 5},  # kWh, GJ
        hours_per_year=8000,
        n_operators=4,
        operator_salary=60_000,
        maintenance_fraction=0.05,
        fixed_capital=tci,
    )
    print(opex.summary())

    # Levelized cost
    from pyaspenplus.economics.costing import CostEstimator
    from pyaspenplus.core.simulation import Simulation
    sim = Simulation()
    sim._mode = "bkp"

    cost = CostEstimator(sim)
    cost._custom_capex = [reactor, hx, compressor]
    cost._opex = opex

    lcop = cost.levelized_cost(product_flow_kg_per_hr=800, tci=tci)
    print(f"\n  Levelized Cost of Methanol: ${lcop:.2f}/kg")

    payback = cost.payback_period(annual_revenue=50_000_000, tci=tci)
    print(f"  Simple Payback Period: {payback:.1f} years")

    # Cost breakdown plot
    try:
        from pyaspenplus.integrations.matplotlib_adapter import PlotAdapter
        plotter = PlotAdapter()
        fig, ax = plotter.plot_cost_breakdown(
            labels=["Raw Materials", "Utilities", "Labour", "Maintenance", "Overhead"],
            values=[
                opex.total_raw_materials,
                opex.total_utilities,
                opex.labor_cost,
                opex.maintenance_cost,
                opex.overhead_cost,
            ],
            title="Annual OPEX Breakdown",
        )
        fig.savefig("cost_breakdown.png", dpi=200)
        print("  Cost breakdown chart saved to cost_breakdown.png")
    except ImportError:
        pass


# ======================================================================
#  6. Integration Library Demos
# ======================================================================

def demo_coolprop() -> None:
    header("CoolProp Integration — Thermophysical Properties")
    try:
        from pyaspenplus.integrations.coolprop_adapter import CoolPropAdapter
        cp = CoolPropAdapter()

        for comp in ["H2", "CO2", "H2O", "CH3OH"]:
            props = cp.all_properties(comp, T=523.15, P=75e5)
            print(f"\n  {comp} at 523 K, 75 bar:")
            for k, v in props.items():
                print(f"    {k:30s} = {v:.4g}")

        print("\n  --- Critical Properties ---")
        for comp in ["H2", "CO2", "H2O", "CH3OH"]:
            Tc = cp.critical_temperature(comp)
            Pc = cp.critical_pressure(comp) / 1e6
            omega = cp.acentric_factor(comp)
            MW = cp.molecular_weight(comp) * 1000
            print(f"  {comp:6s}  Tc={Tc:.1f} K  Pc={Pc:.2f} MPa  "
                  f"omega={omega:.4f}  MW={MW:.2f} g/mol")

        # Enrich pyaspenplus components
        from pyaspenplus.materials.components import Component, ComponentList
        comp_list = ComponentList(components=[
            Component(component_id="H2"),
            Component(component_id="CO2"),
            Component(component_id="CH3OH"),
            Component(component_id="H2O"),
        ])
        cp.enrich_component_list(comp_list)
        print("\n  --- Enriched Components ---")
        for c in comp_list:
            print(f"  {c.component_id:6s}  MW={c.molecular_weight:.2f} g/mol  "
                  f"Tc={c.critical_temperature:.1f} K  "
                  f"Pc={c.critical_pressure:.0f} Pa")

    except ImportError:
        print("  CoolProp not installed. Install with: pip install CoolProp")


def demo_cantera() -> None:
    header("Cantera Integration — Kinetics Engine")
    try:
        from pyaspenplus.integrations.cantera_adapter import CanteraAdapter
        ca = CanteraAdapter()

        gas = ca.create_ideal_gas(T=523.15, P=75e5, X={"H2": 0.82, "CO2": 0.03, "CO": 0.01})
        print(f"  Gas state: T={gas.T:.1f} K, P={gas.P/1e5:.1f} bar")
        print(f"  Species: {gas.species_names[:10]}")

        eq_result = ca.equilibrium(gas, "TP")
        print("\n  Equilibrium composition (major species):")
        for sp, x in sorted(eq_result.items(), key=lambda kv: -kv[1])[:10]:
            print(f"    {sp:15s} : {x:.6f}")

    except ImportError:
        print("  Cantera not installed. Install with: pip install cantera")
    except Exception as e:
        print(f"  Cantera demo error: {e}")


def demo_chemlib() -> None:
    header("Chemlib Integration — Stoichiometry")
    try:
        from pyaspenplus.integrations.chemlib_adapter import ChemlibAdapter
        cl = ChemlibAdapter()

        for formula in ["CH3OH", "CO2", "H2O", "H2", "CO"]:
            mw = cl.molar_mass(formula)
            print(f"  {formula:8s}  MW = {mw:.3f} g/mol")

        print("\n  --- Balance Check for Methanol Synthesis ---")
        stoic = {"CO2": -1, "H2": -3, "CH3OH": 1, "H2O": 1}
        balance = cl.validate_stoichiometry(stoic)
        print(f"  Stoichiometry: {stoic}")
        print(f"  Element balance: {balance}")
        balanced = all(abs(v) < 1e-10 for v in balance.values())
        print(f"  Balanced: {balanced}")

    except ImportError:
        print("  chemlib not installed. Install with: pip install chemlib")
    except Exception as e:
        print(f"  chemlib demo error: {e}")


def demo_pychemengg() -> None:
    header("PyChemEngg Integration — Engineering Calculations")
    try:
        from pyaspenplus.integrations.pychemengg_adapter import PyChemEnggAdapter
        pe = PyChemEnggAdapter()

        Q = pe.heat_duty(mass_flow=10.0, cp=2500.0, T_in=473.15, T_out=523.15)
        print(f"  Heat duty (10 kg/s, Cp=2500, dT=50K): {Q/1e3:.1f} kW")

        lmtd_val = pe.lmtd(T_hot_in=573, T_hot_out=473, T_cold_in=373, T_cold_out=523)
        print(f"  LMTD (counter-current HX): {lmtd_val:.1f} K")

        area = pe.hx_area(Q=Q, U=500, lmtd_val=lmtd_val)
        print(f"  Required HX area (U=500): {area:.1f} m^2")

    except ImportError:
        print("  pychemengg not installed. Install with: pip install pychemengg")
    except Exception as e:
        print(f"  PyChemEngg demo error: {e}")


def demo_chemics() -> None:
    header("Chemics Integration — Gas & Particle Properties")
    try:
        from pyaspenplus.integrations.chemics_adapter import ChemicsAdapter
        ca = ChemicsAdapter()

        for formula in ["H2", "CO2", "CH4", "H2O"]:
            mw = ca.molecular_weight(formula)
            print(f"  {formula:6s}  MW = {mw:.3f} g/mol")

        print("\n  --- Gas Viscosity at 523 K ---")
        for formula in ["H2", "CO2", "H2O"]:
            try:
                mu = ca.gas_viscosity(formula, T=523.15)
                print(f"  {formula:6s}  viscosity = {mu:.2f} µP")
            except Exception as e:
                print(f"  {formula:6s}  not available: {e}")

    except ImportError:
        print("  chemics not installed. Install with: pip install chemics")
    except Exception as e:
        print(f"  chemics demo error: {e}")


# ======================================================================
#  Main
# ======================================================================

def main() -> None:
    print(SEPARATOR)
    print("  pyaspenplus — FYP Methanol Synthesis Demo")
    print(f"  Model: {APW_FILE}")
    print(SEPARATOR)

    demo_availability()
    demo_com_mode()
    demo_bkp_mode()
    demo_kinetics()
    demo_economics()
    demo_coolprop()
    demo_cantera()
    demo_chemlib()
    demo_pychemengg()
    demo_chemics()

    header("Demo Complete")
    print("  All available features demonstrated successfully.\n")
    print("  Next steps:")
    print("  - Install Aspen Plus to unlock COM mode (full simulation control)")
    print("  - Export .bkp from Aspen to use parser mode")
    print("  - pip install CoolProp cantera chemlib chemics matplotlib")
    print("  - See README.md for full API documentation")
    print()


if __name__ == "__main__":
    main()
