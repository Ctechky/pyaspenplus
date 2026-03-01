# pyaspenplus

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-102%20passed-brightgreen.svg)](#testing-status)

Open-source Python library for interfacing with **Aspen Plus** process simulations, integrating with the scientific Python ecosystem for analysis, visualization, and optimization.

> **Note:** This library has been developed and unit-tested with Python-side logic (BKP parsing, economics, kinetics, integrations). **COM automation with a live Aspen Plus instance has NOT yet been tested** — the COM adapter is implemented following the documented Aspen Plus COM API but requires Aspen Plus to be installed for verification. Contributions and testing feedback are welcome.

---

## Architecture

`pyaspenplus` provides **three modes** of access to Aspen Plus models:

- **COM mode** — full read/write control of a live Aspen Plus instance via the Windows COM interface (`pywin32`). Requires Aspen Plus installed.
- **Parser mode** — read AND write `.bkp` (backup) files without needing Aspen Plus. Modify stream conditions, block parameters, and component flows directly in the file.
- **Batch mode** — run Aspen Plus simulations via command line (`AspenPlus.exe /f /r`) using `subprocess`. No COM needed, just Aspen Plus installed.

```
User Code
   |
   v
Simulation  ──>  COM Adapter (pywin32)  ──>  Aspen Plus (live)
   |
   |──>  BKP Writer (modify inputs)  ──>  .bkp files (read+write)
   |          |
   |          +──>  Batch Runner (subprocess)  ──>  AspenPlus.exe /f /r
   |          |
   |          +──>  BKP Parser (read results)  <──  output .bkp
   |
   +── Models (Blocks, Streams, Flowsheet)
   +── Reactions (stoichiometry, kinetics)
   +── Materials (components, feeds)
   +── Economics (APEA + custom CAPEX/OPEX)
   +── Optimization (scipy / Pyomo / pymoo / BO)
   +── Integrations (CoolProp, Cantera, chemlib, chemics, ...)
   +── Visualization (Matplotlib / Seaborn)
```

## Features

### Core Modules

| Module | Description |
|---|---|
| `core.simulation` | Unified entry point — COM, BKP parser, BKP writer, batch runner |
| `core.com_adapter` | COM automation wrapper for Aspen Plus via `pywin32` |
| `core.bkp_parser` | `.bkp` file parser — extract components, blocks, streams, reactions |
| `core.bkp_writer` | `.bkp` file writer — modify stream/block inputs and save back |
| `core.batch_runner` | Command-line runner — execute `AspenPlus.exe` via subprocess |
| `core.metadata` | Read/write simulation metadata (title, author, property method) |
| `models` | Block, Stream, and Flowsheet classes with topology queries |
| `reactions` | Reaction stoichiometry, kinetic parameters (Arrhenius), type classification |
| `materials` | Component properties (MW, Tc, Pc, omega), feed specifications |
| `economics` | APEA COM reader, Turton CAPEX correlations (CEPCI-indexed), OPEX models, NPV, levelized cost |
| `optimization` | Pluggable optimizer with `DecisionVariable` mapping to Aspen tree paths |
| `examples.methanol` | Bussche & Froment (1996) kinetics for CO2 hydrogenation to methanol |

### Optimization Backends

| Backend | Method strings | Install |
|---|---|---|
| scipy.optimize | `scipy-nelder_mead`, `scipy-differential_evolution`, `scipy-dual_annealing`, `scipy-slsqp` | `pip install pyaspenplus[scipy]` |
| Pyomo | `pyomo` | `pip install pyaspenplus[pyomo]` |
| pymoo | `pymoo-nsga2`, `pymoo-de`, `pymoo-pso` | `pip install pyaspenplus[evolutionary]` |
| scikit-optimize | `bayesian` | `pip install pyaspenplus[bayesian]` |

### Integration Adapters

| Library | Adapter | What it provides |
|---|---|---|
| [CoolProp](http://www.coolprop.org/) | `integrations.coolprop_adapter` | Thermophysical properties (density, enthalpy, Cp, viscosity, Tc, Pc, omega). Auto-enriches `Component` objects. |
| [Cantera](https://cantera.org/) | `integrations.cantera_adapter` | Kinetics engine, batch/PFR reactor simulation, equilibrium, YAML export |
| [chemlib](https://github.com/harirakul/chemlib) | `integrations.chemlib_adapter` | Molar mass, reaction balancing, stoichiometry validation |
| [PyChemEngg](https://pypi.org/project/pychemengg/) | `integrations.pychemengg_adapter` | Heat duty, LMTD, HX sizing, mass/energy balance checks |
| [chemics](https://chemics.github.io/) | `integrations.chemics_adapter` | Gas viscosity, thermal conductivity, MW, fluidization velocity |
| [polykin](https://github.com/HugoMVale/polykin) | `integrations.polykin_adapter` | DIPPR correlations, Antoine vapor pressure |
| [Matplotlib](https://matplotlib.org/) | `integrations.matplotlib_adapter` | Stream temperatures, composition profiles, optimization convergence, cost breakdowns |

### Visualization

| Feature | Description |
|---|---|
| `visualization.flowsheet_diagram` | Auto-layout flowsheet rendering (blocks as colored boxes, streams as arrows) |
| Composition profiles | Line plots of species mole fractions along a reactor |
| Cost breakdown | Pie charts for OPEX breakdown |
| Optimization convergence | Scatter + best-so-far line plots |
| Sensitivity analysis | Parameter sweep plots |

---

## Installation

```bash
# Core library
pip install pyaspenplus

# With specific integration
pip install pyaspenplus[scipy]         # scipy.optimize
pip install pyaspenplus[coolprop]      # CoolProp thermophysical properties
pip install pyaspenplus[plotting]      # Matplotlib + Seaborn

# Everything
pip install pyaspenplus[all]

# Development
pip install pyaspenplus[dev]
```

### Individual integration libraries

```bash
pip install CoolProp          # thermophysical properties
pip install chemlib            # stoichiometry, molar mass
pip install chemics            # gas properties, particle properties
pip install polykin            # polymer kinetics, DIPPR correlations
pip install pychemengg         # material/energy balances
pip install matplotlib seaborn # visualization
conda install -c cantera cantera  # kinetics engine (conda recommended on Windows)
```

---

## Quick Start

### COM mode (requires Aspen Plus installed)

```python
from pyaspenplus import Simulation

sim = Simulation.from_file("model.apw")

# Model info
print(sim.info.title, sim.info.components, sim.info.property_method)

# Flowsheet
for block in sim.flowsheet.blocks:
    print(block.name, block.block_type, block.parameters)

for stream in sim.flowsheet.streams:
    print(stream.name, stream.temperature, stream.pressure, stream.composition)

# Reactions
for rxn in sim.reactions:
    print(rxn.name, rxn.equation_string, rxn.kinetic_parameters)

# Modify and re-run
sim.set_value("Blocks.REACTOR.Input.TEMP", 280)
sim.run()

sim.close()
```

### Parser mode (no Aspen Plus needed)

```python
from pyaspenplus import Simulation

sim = Simulation.from_bkp("model.bkp")
print(sim.info.summary())

for block in sim.flowsheet.blocks:
    print(block.name, block.block_type)
```

### BKP write-back (modify inputs without Aspen Plus)

```python
from pyaspenplus import Simulation

sim = Simulation.from_bkp("model.bkp")

# Modify inputs directly in the .bkp file
sim.set_bkp_stream_temp("FEED", 550.0)
sim.set_bkp_stream_pressure("FEED", 80.0)
sim.set_bkp_stream_flow("FEED", "H2", 0.90)
sim.set_bkp_block_param("REACTOR", "TEMP", 260.0)

# Save modified file
sim.save_bkp("model_modified.bkp")

# See what changed
print(sim.bkp_changes)
```

### Batch mode (command line, no COM needed)

```python
from pyaspenplus import Simulation

# Modify + run + read results — all without COM
sim = Simulation.from_bkp("model.bkp")
sim.set_bkp_stream_temp("FEED", 550.0)
sim.save_bkp("model_run.bkp")

# Run via AspenPlus.exe command line
result = sim.batch_run("model_run.bkp")
print(result.summary())  # SUCCESS/FAILED, elapsed time

# Results are auto-parsed — access as usual
for stream in sim.flowsheet.streams:
    print(stream.name, stream.temperature)
```

```python
# Or use the low-level BatchRunner directly
from pyaspenplus.core.batch_runner import BatchRunner

runner = BatchRunner()  # auto-detects AspenPlus.exe
# runner = BatchRunner(r"C:\Program Files\AspenTech\...\AspenPlus.exe")
# or set ASPENPLUS_EXE environment variable

result = runner.run("model.bkp", timeout=600)
run_result, parsed = runner.run_and_parse("model.bkp")
```

### Economics

```python
from pyaspenplus.economics import CostEstimator
from pyaspenplus.economics.capex import purchased_equipment_cost

# Equipment costing (Turton correlations, CEPCI-indexed)
reactor = purchased_equipment_cost("reactor_jacketed", sizing_parameter=5.0)
hx = purchased_equipment_cost("heat_exchanger_fixed", sizing_parameter=50)
print(f"Reactor bare-module cost: ${reactor.bare_module_cost:,.0f}")

# Full cost analysis
cost = CostEstimator(sim)
cost.add_equipment_cost(reactor)
cost.add_equipment_cost(hx)
opex = cost.estimate_opex(
    raw_material_prices={"H2": 2.5, "CO2": 0.04},
    raw_material_flows={"H2": 500, "CO2": 1500},
    hours_per_year=8000,
)
lcop = cost.levelized_cost(product_flow_kg_per_hr=800)
print(f"Levelized cost of product: ${lcop:.2f}/kg")
```

### Optimization

```python
from pyaspenplus import Simulation
from pyaspenplus.optimization import DecisionVariable, optimize

sim = Simulation.from_file("model.apw")

variables = [
    DecisionVariable("temp", path="Blocks.REACTOR.Input.TEMP", bounds=(200, 300)),
    DecisionVariable("pres", path="Blocks.REACTOR.Input.PRES", bounds=(50, 100)),
]

def objective(sim):
    product = sim.flowsheet.get_stream("PRODUCT").get_flow("CH3OH")
    return -product  # minimize negative = maximize

# Swap backends freely
result = optimize(sim, variables, objective, method="scipy-differential_evolution")
result = optimize(sim, variables, objective, method="pymoo-nsga2", n_gen=50)
result = optimize(sim, variables, objective, method="bayesian", n_calls=30)
print(result.summary())
```

### CoolProp Integration

```python
from pyaspenplus.integrations import CoolPropAdapter

cp = CoolPropAdapter()
props = cp.all_properties("H2O", T=523.15, P=75e5)
print(props)  # density, enthalpy, entropy, Cp, viscosity, thermal conductivity, MW

# Auto-enrich pyaspenplus components with CoolProp data
cp.enrich_component_list(sim.components)
```

### Methanol Synthesis Example

```python
from pyaspenplus.examples.methanol import MethanolSynthesis

model = MethanolSynthesis()
profile = model.solve_pfr(length=0.15, n_points=200)

# Plot with built-in visualization
from pyaspenplus.integrations import PlotAdapter
plotter = PlotAdapter()
fig, ax = plotter.plot_composition_profile(
    profile["z"],
    {sp: profile[f"y_{sp}"] for sp in ["CO2", "H2", "CO", "CH3OH", "H2O"]},
    title="Methanol Synthesis PFR Profile",
)
fig.savefig("pfr_profile.png", dpi=200)
```

---

## Project Structure

```
pyaspenplus/
├── core/                  # Simulation, COM, BKP parser/writer, batch runner, metadata
├── models/                # Block, Stream, Flowsheet
├── reactions/             # Reaction, ReactionSet, kinetics
├── materials/             # Component, ComponentList, Feed
├── economics/             # APEA, CAPEX (Turton), OPEX, CostEstimator
├── optimization/          # DecisionVariable, scipy/Pyomo/pymoo/Bayesian adapters
├── integrations/          # CoolProp, Cantera, chemlib, chemics, polykin, matplotlib
├── visualization/         # Flowsheet diagrams, plotting utilities
├── examples/methanol/     # Bussche & Froment kinetics, PFR solver
└── utils/                 # Unit conversion, logging
```

---

## Testing Status

| Category | Tests | Status |
|---|---|---|
| BKP parser | 8 | Passed |
| BKP writer (read-modify-write) | 13 | Passed |
| Batch runner | 5 | Passed |
| Simulation BKP write-back | 4 | Passed |
| Economics (CAPEX/OPEX) | 8 | Passed |
| Methanol kinetics + PFR | 7 | Passed |
| Models (blocks/streams/flowsheet) | 8 | Passed |
| Optimization (variables/results) | 4 | Passed |
| Reactions | 8 | Passed |
| Simulation + metadata | 5 | Passed |
| Unit conversions | 8 | Passed |
| CoolProp integration | 6 | Passed |
| chemlib integration | 3 | Passed |
| PyChemEngg integration | 6 | Passed |
| Matplotlib + flowsheet | 5 | Passed |
| Cantera integration | 2 | Skipped (not installed) |
| **Total** | **104** | **102 passed, 2 skipped** |

### What has NOT been tested yet

- **COM automation with a live Aspen Plus instance** — the `COMAdapter` class is implemented based on the documented Aspen Plus COM API (`Apwn.Document`, `Application.Tree.FindNode`, etc.) but has not been verified against a running Aspen Plus installation. The COM adapter needs testing with:
  - Opening `.apw` files
  - Reading the variable tree (blocks, streams, components)
  - Running simulations
  - Reading APEA economic results
  - The optimization loop (set variables -> run -> read results)
- **Batch runner with a live Aspen Plus instance** — the `BatchRunner` class is implemented but needs testing on a machine with Aspen Plus installed to verify command-line arguments and output parsing
- **Cantera integration** — requires `conda install -c cantera cantera` on Windows

### What HAS been tested

- All Python-side logic: BKP parsing, BKP write-back (modify + save), batch runner framework, data models, reaction classes, kinetics, economics correlations, optimization framework, unit conversions
- Full modify-save-reparse cycle: change stream/block values in `.bkp` files and verify the output is parseable with correct values
- Integration adapters: CoolProp, chemlib, chemics, polykin, pychemengg, Matplotlib
- Methanol synthesis example: Bussche & Froment kinetics, isothermal PFR solver
- Visualization: composition profiles, cost breakdowns, flowsheet diagrams

---

## Version History

### v0.3.0 — BKP Write-Back & Batch Runner

- **BKP Writer** (`core.bkp_writer`) — modify stream temperatures, pressures, flows, component fractions, and block parameters directly in `.bkp` files. Save with auto-backup.
- **Batch Runner** (`core.batch_runner`) — run Aspen Plus via `AspenPlus.exe /f /r` command line (subprocess), bypassing COM entirely. Auto-detects install path or uses `ASPENPLUS_EXE` env variable.
- **Simulation integration** — new `set_bkp_*`, `save_bkp()`, and `batch_run()` methods on the `Simulation` class for a full modify-run-read cycle without COM.
- **22 new tests** (102 total, 102 passed, 2 skipped)

### v0.2.0 — Integration Adapters & Visualization

- **7 integration adapters**: CoolProp, Cantera, chemlib, PyChemEngg, chemics, polykin, Matplotlib
- **Visualization module**: flowsheet diagrams, composition profiles, cost breakdowns, optimization convergence plots
- **`available_integrations()`** helper to check which optional libraries are installed
- Fixed methanol PFR solver to account for inert species (N2)
- Fixed Unicode errors in OPEX summary on Windows console
- **22 new tests** (82 total, 80 passed, 2 skipped)

### v0.1.0 — Initial Release

- **Core**: COM adapter (`pywin32`), BKP parser, metadata reader/writer
- **Models**: Block, Stream, Flowsheet with topology queries
- **Reactions**: Stoichiometry, Arrhenius kinetic parameters, reaction type classification
- **Materials**: Component properties, feed specifications
- **Economics**: APEA COM reader, Turton CAPEX correlations (CEPCI-indexed), OPEX models, NPV, levelized cost
- **Optimization**: Pluggable interface for scipy, Pyomo, pymoo, and Bayesian (scikit-optimize/BoTorch)
- **Example**: Bussche & Froment (1996) methanol synthesis kinetics with isothermal PFR solver
- **60 tests** (60 passed)

---

## Contributing

Contributions are very welcome, especially:

1. **Testing with Aspen Plus** — if you have Aspen Plus installed, please test the COM adapter and report issues
2. **Additional block types** — extend the Block subclass hierarchy
3. **More cost correlations** — add equipment cost data
4. **New integration adapters** — wrap additional chemical engineering libraries
5. **BKP parser improvements** — handle more `.bkp` file variations

```bash
git clone https://github.com/Ctechky/pyaspenplus.git
cd pyaspenplus
pip install -e ".[dev,all]"
pytest tests/ -v
```

## License

MIT — see [LICENSE](LICENSE).
