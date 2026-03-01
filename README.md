# pyaspenplus

Open-source Python library for interfacing with **Aspen Plus** process simulations.

`pyaspenplus` provides dual-mode access to Aspen Plus models:

- **COM mode** — full read/write control of a live Aspen Plus instance via the Windows COM interface (requires Aspen Plus installed).
- **Parser mode** — lightweight reading of `.bkp` backup files without needing Aspen Plus on the machine.

## Features

| Module | Description |
|---|---|
| **Simulation** | Unified entry point — load from `.apw` (COM) or `.bkp` (parser) |
| **Models** | Blocks, Streams, and Flowsheet topology |
| **Reactions** | Stoichiometry, kinetic parameters, reaction type info |
| **Materials** | Component properties, feed specifications |
| **Economics** | APEA results, CAPEX/OPEX correlations, levelized cost |
| **Optimization** | Pluggable interface for scipy, Pyomo, pymoo, and Bayesian optimizers |

## Installation

```bash
pip install pyaspenplus            # core (COM + parser)
pip install pyaspenplus[scipy]     # + scipy.optimize
pip install pyaspenplus[all]       # + every optional backend
pip install pyaspenplus[dev]       # + dev/test tools
```

## Quick Start

### COM mode (requires Aspen Plus)

```python
from pyaspenplus import Simulation

sim = Simulation.from_file("model.apw")

# Inspect the flowsheet
for block in sim.flowsheet.blocks:
    print(block.name, block.block_type)

for stream in sim.flowsheet.streams:
    print(stream.name, stream.temperature, stream.pressure)

# Read reactions
for rxn in sim.reactions:
    print(rxn.name, rxn.stoichiometry)
```

### Parser mode (no Aspen Plus needed)

```python
from pyaspenplus import Simulation

sim = Simulation.from_bkp("model.bkp")
print(sim.info.title, sim.info.components)
```

### Optimization

```python
from pyaspenplus import Simulation
from pyaspenplus.optimization import DecisionVariable, optimize
from pyaspenplus.economics import CostEstimator

sim = Simulation.from_file("model.apw")

variables = [
    DecisionVariable("temp", path="Blocks.REACTOR.Input.TEMP", bounds=(200, 300)),
    DecisionVariable("pres", path="Blocks.REACTOR.Input.PRES", bounds=(50, 100)),
]

def objective(sim):
    product = sim.flowsheet.get_stream("PRODUCT").get_flow("CH3OH")
    cost = CostEstimator(sim).total_annual_cost()
    return -product / cost

result = optimize(sim, variables, objective, method="scipy-differential_evolution")
print(result.optimal_values, result.optimal_objective)
```

## Methanol Synthesis Example

A built-in example for CO₂ hydrogenation to methanol (Bussche & Froment kinetics on Cu/ZnO/Al₂O₃) is included:

```python
from pyaspenplus.examples.methanol import MethanolSynthesis

model = MethanolSynthesis()
rates = model.reaction_rates(T=523.15, P=75e5, y={"CO2": 0.03, "H2": 0.82, "CO": 0.01})
```

## License

MIT — see [LICENSE](LICENSE).
