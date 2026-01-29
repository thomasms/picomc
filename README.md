# Pico MC

A modular, pythonic Monte Carlo simulator for neutron transport with ENDF/PENDF data support and CSG geometry.

## Features

- **Modular Architecture**: Separate modules for geometry, physics, transport, tallying, and nuclear data
- **Pythonic API**: Clean interfaces inspired by Geant4, with no input deck requirements
- **Nuclear Data Support**: 
  - **PENDF** format (processed, linearized data) - **Recommended**
  - **ENDF** format (raw evaluated data)
  - Library-agnostic: works with JEFF, ENDF/B, JENDL, etc.
- **CSG Geometry**: Constructive Solid Geometry similar to Serpent and OpenMC
  - Surface primitives: planes, spheres, cylinders
  - Boolean operations for complex geometries
  - Cell-based material definitions
- **Customizable**: Hook system for overriding logic at event and step levels
- **Extensible**: Easy to add new geometries, physics processes, and tallies

## Installation

```bash
# Basic installation
pip install -e .

# With ENDF support (optional)
pip install -e ".[endf]"
```

## Quick Start

### Using Simple Geometry

```python
import numpy as np
from picomc import Simulator, BoxGeometry, NuclearDataManager, FluxTally
from picomc.geometry import VoxelizedGeometry

# Setup nuclear data
data_manager = NuclearDataManager()
data_manager.add_material('default', number_density=0.05)

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

### Using CSG Geometry (Serpent/OpenMC style)

```python
from picomc import Simulator, NuclearDataManager, CSGGeometryWrapper
from picomc.csg import CSGGeometry, CSGCell, HalfSpace, Sphere, Plane
import numpy as np

# Load nuclear data (PENDF format recommended)
dm = NuclearDataManager()
dm.load_pendf_file('path/to/n-092_U_235.pendf', 'U235', 0.048)
# Or use default data for testing:
# dm.add_material('U235', number_density=0.048)

# Create CSG geometry
csg = CSGGeometry()

# Define sphere target
sphere = Sphere(1, center=np.array([25, 25, 25]), radius=10)
csg.add_surface(sphere)

# Create cell with material
cell = CSGCell(1, material='U235')
cell.add_region(HalfSpace(sphere, -1))  # Inside sphere
csg.add_cell(cell)

# Wrap and simulate
geometry = CSGGeometryWrapper(csg)
sim = Simulator(geometry, dm)

particles = sim.create_point_source(np.array([25, 25, 25]), 1000, energy=2.0e6)
sim.add_source_particles(particles)
sim.run()
```

## Package Structure

```
picomc/
├── __init__.py       # Package entry point
├── particle.py       # Particle and Event classes
├── geometry.py       # Geometry definitions (box, voxelized, CSG wrapper)
├── csg.py           # CSG primitives and operations
├── physics.py        # Physics interactions
├── transport.py      # Transport engine
├── data.py          # Nuclear data management (ENDF/PENDF)
├── pendf_parser.py  # PENDF format parser
├── tally.py         # Scoring and tallies
└── simulator.py     # Main simulator orchestrator
```

## Nuclear Data Libraries

### JEFF 4.0 PENDF (Recommended)

Download from OECD-NEA: https://data.oecd-nea.org/records/wgw94-qcx30

```python
dm = NuclearDataManager()
dm.load_pendf_file('jeff40/pendf/n-092_U_235.pendf', 'U235', 0.048, temperature=293.6)
```

PENDF files contain processed, linearized cross sections ready for Monte Carlo use.
Works with any library: JEFF, ENDF/B, JENDL, etc.

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

## Examples and Tests

### Examples

- **`example.py`**: Basic usage showing the complete workflow
- **`example_advanced.py`**: Advanced customization with custom physics and hooks
- **`example_pendf_csg.py`**: PENDF data with CSG geometry
- **`ENDF_GUIDE.md`**: Comprehensive guide for nuclear data files

Run examples:
```bash
python example.py
python example_advanced.py
python example_pendf_csg.py
```

### Tests

Verify functionality:
```bash
# Test CSG geometry primitives
python tests/test_csg.py

# Test neutron transport with various geometries
python tests/test_neutron_box.py
```

## Using Nuclear Data

### PENDF Format (Recommended)

```python
# Load JEFF 4.0 PENDF data
dm = NuclearDataManager()
dm.load_pendf_file(
    'path/to/jeff40/pendf/n-092_U_235.pendf',
    material_name='U235',
    number_density=0.048,  # atoms/barn-cm
    temperature=293.6      # Kelvin
)
```

### ENDF Format

```python
# Load raw ENDF data (requires endf-parserpy)
dm = NuclearDataManager(use_endf=True)
dm.load_endf_file(
    'path/to/n-092_U_235.endf',
    material_name='U235',
    number_density=0.048
)
```

### Auto-Detect Format

```python
# Automatically detect format from filename
dm.load_library_file(
    filepath='path/to/data.pendf',
    material_name='U235',
    number_density=0.048,
    file_format='auto'  # or 'endf', 'pendf', 'ace'
)
```

## Testing

### Running Tests

The project includes comprehensive unit and integration tests using pytest:

```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest tests/ --cov=picomc --cov-report=term-missing

# Run only unit tests
pytest tests/unit/

# Run specific test file
pytest tests/test_csg.py -v

# Run tests with specific markers
pytest tests/ -m unit
```

### Development Setup

Install development dependencies:

```bash
pip install -e ".[dev]"
```

This installs:
- pytest and pytest-cov for testing
- flake8 for linting
- black for code formatting

### Linting and Formatting

```bash
# Check code style
flake8 picomc

# Format code with black
black picomc tests

# Check formatting without changes
black --check picomc tests
```

### Continuous Integration

The project uses GitHub Actions for CI. Every push and pull request runs:
- Tests on Python 3.8, 3.9, 3.10, and 3.11
- Code linting with flake8
- Code formatting check with black
- Coverage reporting

See `.github/workflows/ci.yml` for details.

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── test_csg.py           # CSG geometry tests (12 tests)
├── test_neutron_box.py   # Integration tests (3 tests)
└── unit/
    ├── test_data.py      # Nuclear data tests (10 tests)
    ├── test_particle.py  # Particle class tests (10 tests)
    └── test_physics.py   # Physics engine tests (14 tests)
```

Total: **49 tests** with good code coverage.

## Legacy Code

The original simple implementation is preserved in `picomc.py` for reference.
