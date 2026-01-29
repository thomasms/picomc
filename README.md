# Pico MC

A modular, pythonic Monte Carlo simulator for neutron transport with ENDF data support.

## Features

- **Modular Architecture**: Separate modules for geometry, physics, transport, tallying, and nuclear data
- **Pythonic API**: Clean interfaces inspired by Geant4, with no input deck requirements
- **ENDF Integration**: Support for reading nuclear data from ENDF files using endf-parserpy
- **Customizable**: Hook system for overriding logic at event and step levels
- **Extensible**: Easy to add new geometries, physics processes, and tallies

## Installation

```bash
# Basic installation
pip install -e .

# With ENDF support
pip install -e ".[endf]"
```

## Quick Start

```python
import numpy as np
from picomc import Simulator, BoxGeometry, NuclearDataManager, FluxTally
from picomc.geometry import VoxelizedGeometry

# Setup nuclear data
data_manager = NuclearDataManager(use_endf=False)
data_manager._add_default_material('default', number_density=0.1)

# Create geometry
geometry = BoxGeometry(size=100.0, material='default')
voxel_geometry = VoxelizedGeometry(geometry, num_bins=10)

# Create simulator
sim = Simulator(voxel_geometry, data_manager)

# Add tally
tally = FluxTally(voxel_geometry)
sim.set_tally(tally)

# Create source and run
source_pos = np.array([50.0, 50.0, 50.0])
particles = sim.create_point_source(source_pos, num_particles=1000, energy=2.0e6)
sim.add_source_particles(particles)
sim.run()

# Get results
results = sim.get_results()
print(results['statistics'])
```

## Package Structure

```
picomc/
├── __init__.py       # Package entry point
├── particle.py       # Particle and Event classes
├── geometry.py       # Geometry definitions
├── physics.py        # Physics interactions
├── transport.py      # Transport engine
├── data.py          # Nuclear data management
├── tally.py         # Scoring and tallies
└── simulator.py     # Main simulator orchestrator
```

## Customization

The package supports customization through hooks at multiple levels:

### Event-Level Hooks
```python
def my_pre_event_hook(particle):
    print(f"Starting to track particle at {particle.position}")

sim.pre_event_hook = my_pre_event_hook
```

### Step-Level Hooks
```python
def my_post_step_hook(particle, event):
    if event.interaction_type == 'fission':
        print(f"Fission produced {len(event.secondary_particles)} neutrons")

sim.transport.post_step_hook = my_post_step_hook
```

## Using ENDF Data

To use real nuclear data from ENDF files:

```python
# Create data manager with ENDF support
data_manager = NuclearDataManager(use_endf=True)

# Load ENDF file for a specific isotope
data_manager.load_endf_file(
    'path/to/n-092_U_235.endf',
    material_name='U235',
    number_density=0.048  # atoms/barn-cm
)
```

## Examples

- **`example.py`**: Basic usage showing the complete workflow
- **`example_advanced.py`**: Advanced customization with custom physics and hooks
- **`ENDF_GUIDE.md`**: Comprehensive guide for using ENDF nuclear data files

Run the basic example:
```bash
python example.py
```

Run the advanced customization example:
```bash
python example_advanced.py
```

## Legacy Code

The original simple implementation is preserved in `picomc.py` for reference.
