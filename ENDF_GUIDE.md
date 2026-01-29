# Using Nuclear Data Libraries with PicoMC

This guide explains how to use real nuclear data from ENDF, PENDF, and other format files with PicoMC.

## Supported Formats

PicoMC supports multiple nuclear data formats:
- **ENDF** (Evaluated Nuclear Data File) - Raw evaluated data
- **PENDF** (Pointwise ENDF) - Processed, linearized data (recommended)
- **ACE** (A Compact ENDF) - Future support planned

All parsing is done using the **endf-parserpy** library, which provides robust support for ENDF-6 format files.

## Installation

PicoMC requires the `endf-parserpy` library for nuclear data support:

```bash
pip install picomc
```

This will automatically install `endf-parserpy` and other dependencies.

## Using PENDF Data (Recommended)

PENDF files contain processed nuclear data with linearized cross sections, making them ideal for Monte Carlo simulations. They work with data from any library (JEFF, ENDF/B, JENDL, etc.).

PicoMC uses **endf-parserpy** to parse PENDF files, providing robust and accurate parsing of the ENDF-6 format.

### JEFF 4.0 PENDF Library

The JEFF 4.0 PENDF library is available from OECD-NEA:
- URL: https://data.oecd-nea.org/records/wgw94-qcx30
- Contains processed data for all isotopes at multiple temperatures
- Linearized cross sections ready for direct use

```python
from picomc import Simulator, BoxGeometry, NuclearDataManager
import numpy as np

# Create data manager (format auto-detected from filename)
data_manager = NuclearDataManager()

# Load PENDF file from JEFF 4.0
data_manager.load_pendf_file(
    filepath='path/to/jeff40/pendf/n-092_U_235.pendf',
    material_name='U235',
    number_density=0.048,  # atoms/barn-cm
    temperature=293.6      # Kelvin (optional, default is room temp)
)

# Create geometry and run simulation
geometry = BoxGeometry(size=100.0, material='U235')
sim = Simulator(geometry, data_manager)

source_pos = np.array([50.0, 50.0, 50.0])
particles = sim.create_point_source(source_pos, 1000, energy=2.0e6)
sim.add_source_particles(particles)
sim.run()
```

### Auto-Detect Format

The `load_library_file` method automatically detects the format:

```python
# Auto-detect format from filename
data_manager.load_library_file(
    filepath='path/to/data.pendf',  # or .endf, .ace
    material_name='U235',
    number_density=0.048,
    file_format='auto'  # 'auto', 'endf', 'pendf', or 'ace'
)
```

## Basic ENDF Usage

For raw ENDF files:

```python
from picomc import Simulator, BoxGeometry, NuclearDataManager
from picomc.geometry import VoxelizedGeometry
import numpy as np

# Create data manager with ENDF support enabled
data_manager = NuclearDataManager(use_endf=True)

# Load ENDF file for U-235
data_manager.load_endf_file(
    filepath='path/to/n-092_U_235.endf',
    material_name='U235',
    number_density=0.048  # atoms/barn-cm (natural uranium metal)
)

# Create geometry and simulator
geometry = BoxGeometry(size=100.0, material='U235')
sim = Simulator(geometry, data_manager)

# Run simulation as usual
source_pos = np.array([50.0, 50.0, 50.0])
particles = sim.create_point_source(source_pos, 1000, energy=2.0e6)
sim.add_source_particles(particles)
sim.run()
```

## ENDF File Format

PicoMC expects ENDF-6 format files. The parser will extract:

- **MF=3, MT=1**: Total cross section
- **MF=3, MT=2**: Elastic scattering cross section
- **MF=3, MT=18**: Fission cross section (if present)
- **MF=3, MT=102**: Radiative capture cross section

## Multiple Materials

You can load multiple materials and use them in your geometry:

```python
data_manager = NuclearDataManager(use_endf=True)

# Load U-235
data_manager.load_endf_file(
    'path/to/n-092_U_235.endf',
    'U235',
    0.048
)

# Load H-1 (for water moderator)
data_manager.load_endf_file(
    'path/to/n-001_H_001.endf',
    'H1',
    0.1  # Typical for water
)

# Note: Current implementation uses single material per geometry
# Multi-material geometries can be implemented by extending the Geometry class
```

## Number Density

The `number_density` parameter is in units of **atoms/barn-cm**.

Common values:
- Water (H2O): ~0.1 atoms/barn-cm
- Uranium metal: ~0.048 atoms/barn-cm
- Iron: ~0.085 atoms/barn-cm

To convert from mass density (g/cm³):

```python
# Example: Uranium metal at 19.1 g/cm³
mass_density = 19.1  # g/cm³
atomic_mass = 235.0  # g/mol
avogadro = 6.022e23  # atoms/mol

# atoms/cm³
atom_density_cm3 = (mass_density * avogadro) / atomic_mass

# Convert to atoms/barn-cm (1 barn = 1e-24 cm²)
number_density = atom_density_cm3 * 1e-24
print(f"Number density: {number_density:.4f} atoms/barn-cm")
# Output: ~0.0488 atoms/barn-cm
```

## Energy-Dependent Cross Sections

ENDF files contain cross sections as a function of energy. PicoMC automatically:

1. Reads the energy grid and cross section values
2. Interpolates cross sections at the particle's current energy
3. Uses linear interpolation (log-log interpolation can be added for better accuracy)

## Fallback Behavior

If ENDF parsing fails or `endf-parserpy` is not installed:

- PicoMC will issue a warning
- It will fall back to simple analytical cross sections for demonstration
- This allows testing without requiring ENDF files

## Where to Get ENDF Files

ENDF data can be obtained from:

- [NNDC/BNL](https://www.nndc.bnl.gov/endf/): National Nuclear Data Center
- [IAEA](https://www-nds.iaea.org/): International Atomic Energy Agency
- [JEFF](https://www.oecd-nea.org/dbdata/jeff/): Joint Evaluated Fission and Fusion File
- [JENDL](https://wwwndc.jaea.go.jp/): Japanese Evaluated Nuclear Data Library

Look for ENDF-6 format files (typically with `.endf` or `.txt` extension).

## Limitations and Future Work

Current implementation:
- ✅ Energy-dependent cross sections (total, elastic, capture, fission)
- ❌ Angular distributions (currently uses isotropic)
- ❌ Energy distributions for scattered neutrons (currently elastic in CoM)
- ❌ Resonance processing (uses pointwise data as-is)
- ❌ Temperature dependence (uses 0K or single temperature)

These features can be added by extending the `NuclearDataManager` and `PhysicsEngine` classes.

## Example: Comparing ENDF vs. Default Data

```python
import matplotlib.pyplot as plt
import numpy as np

# Setup with default data
dm_default = NuclearDataManager(use_endf=False)
dm_default._add_default_material('default', 0.048)

# Setup with ENDF data (if available)
dm_endf = NuclearDataManager(use_endf=True)
try:
    dm_endf.load_endf_file('path/to/U235.endf', 'U235', 0.048)
    have_endf = True
except:
    have_endf = False

if have_endf:
    # Compare cross sections
    energies = np.logspace(0, 7, 100)  # 1 eV to 10 MeV
    
    xs_default = [dm_default.get_macroscopic_xs('default', e) for e in energies]
    xs_endf = [dm_endf.get_macroscopic_xs('U235', e) for e in energies]
    
    plt.figure(figsize=(10, 6))
    plt.loglog(energies, [x['total'] for x in xs_default], label='Default')
    plt.loglog(energies, [x['total'] for x in xs_endf], label='ENDF')
    plt.xlabel('Energy (eV)')
    plt.ylabel('Macroscopic Cross Section (cm⁻¹)')
    plt.title('Total Cross Section Comparison')
    plt.legend()
    plt.grid(True)
    plt.show()
```

## CSG Geometry (Serpent/OpenMC Style)

PicoMC now supports Constructive Solid Geometry (CSG) similar to Serpent and OpenMC codes.

### Basic CSG Example

```python
from picomc import Simulator, NuclearDataManager, CSGGeometryWrapper
from picomc.csg import CSGGeometry, CSGCell, HalfSpace, Plane, Sphere
import numpy as np

# Create CSG geometry
csg = CSGGeometry()

# Define surfaces
# Box boundaries
px_low = Plane(1, 1, 0, 0, 0)    # x = 0
px_high = Plane(2, 1, 0, 0, 50)  # x = 50
py_low = Plane(3, 0, 1, 0, 0)    # y = 0
py_high = Plane(4, 0, 1, 0, 50)  # y = 50
pz_low = Plane(5, 0, 0, 1, 0)    # z = 0
pz_high = Plane(6, 0, 0, 1, 50)  # z = 50

# Sphere at center
sphere = Sphere(10, np.array([25, 25, 25]), radius=10)

# Add surfaces to geometry
for surf in [px_low, px_high, py_low, py_high, pz_low, pz_high, sphere]:
    csg.add_surface(surf)

# Create cells
# Sphere cell (uranium)
sphere_cell = CSGCell(1, material='U235')
sphere_cell.add_region(HalfSpace(sphere, -1))  # Inside sphere
csg.add_cell(sphere_cell)

# Void cell (outside sphere, inside box)
void_cell = CSGCell(2, material=None)
void_cell.add_region(
    HalfSpace(sphere, +1),    # Outside sphere
    HalfSpace(px_low, +1),    # x > 0
    HalfSpace(px_high, -1),   # x < 50
    HalfSpace(py_low, +1),    # y > 0
    HalfSpace(py_high, -1),   # y < 50
    HalfSpace(pz_low, +1),    # z > 0
    HalfSpace(pz_high, -1),   # z < 50
)
csg.add_cell(void_cell)

# Wrap CSG for use in simulator
geometry = CSGGeometryWrapper(csg)

# Load nuclear data and run simulation
data_manager = NuclearDataManager()
data_manager.load_pendf_file('path/to/U235.pendf', 'U235', 0.048)

sim = Simulator(geometry, data_manager)
particles = sim.create_point_source(np.array([25, 25, 25]), 1000, energy=2.0e6)
sim.add_source_particles(particles)
sim.run()
```

### CSG Primitives

Available surface types:

- **Plane**: `Plane(id, A, B, C, D)` - Equation: Ax + By + Cz - D = 0
- **Sphere**: `Sphere(id, center, radius)`
- **Cylinder**: `Cylinder(id, center, radius, axis='z')`

### Boolean Operations

Cells are defined by boolean combinations of half-spaces:

```python
# Intersection (AND) - all conditions must be true
cell.add_region(
    HalfSpace(surf1, +1),
    HalfSpace(surf2, -1),
    HalfSpace(surf3, +1),
)

# Union (OR) - multiple regions
cell.add_region(HalfSpace(surf1, +1))  # Region 1
cell.add_region(HalfSpace(surf2, -1))  # Region 2
# Particle in cell if in Region 1 OR Region 2
```

### Half-Space Sense

- `HalfSpace(surface, +1)`: Positive side (surface.evaluate() > 0)
- `HalfSpace(surface, -1)`: Negative side (surface.evaluate() < 0)

For a sphere:
- `-1` (negative) = inside sphere
- `+1` (positive) = outside sphere

For a plane z=5:
- `-1` (negative) = below plane (z < 5)
- `+1` (positive) = above plane (z > 5)

## Complete Example: JEFF 4.0 with CSG

```python
from picomc import Simulator, NuclearDataManager, CSGGeometryWrapper
from picomc.csg import CSGGeometry, CSGCell, HalfSpace, Sphere, Cylinder, Plane
import numpy as np

# Load JEFF 4.0 PENDF data
dm = NuclearDataManager()
dm.load_pendf_file('jeff40/pendf/n-092_U_235.pendf', 'U235', 0.048, temperature=293.6)
dm.load_pendf_file('jeff40/pendf/n-001_H_001.pendf', 'H1', 0.1, temperature=293.6)

# Create CSG geometry: uranium cylinder in water box
csg = CSGGeometry()

# Uranium fuel cylinder (radius 5 cm, along z-axis)
fuel_cyl = Cylinder(1, np.array([25, 25, 0]), radius=5, axis='z')
csg.add_surface(fuel_cyl)

# Water box boundaries
box_surfaces = [
    Plane(10, 1, 0, 0, 0),    # x_min
    Plane(11, 1, 0, 0, 50),   # x_max
    Plane(12, 0, 1, 0, 0),    # y_min
    Plane(13, 0, 1, 0, 50),   # y_max
    Plane(14, 0, 0, 1, 0),    # z_min
    Plane(15, 0, 0, 1, 50),   # z_max
]
for surf in box_surfaces:
    csg.add_surface(surf)

# Fuel cell
fuel_cell = CSGCell(1, material='U235')
fuel_cell.add_region(
    HalfSpace(fuel_cyl, -1),  # Inside cylinder
    HalfSpace(box_surfaces[4], +1),  # z > 0
    HalfSpace(box_surfaces[5], -1),  # z < 50
)
csg.add_cell(fuel_cell)

# Water cell
water_cell = CSGCell(2, material='H1')
water_cell.add_region(
    HalfSpace(fuel_cyl, +1),  # Outside cylinder
    *[HalfSpace(s, +1 if i % 2 == 0 else -1) for i, s in enumerate(box_surfaces)]
)
csg.add_cell(water_cell)

# Run simulation
geometry = CSGGeometryWrapper(csg)
sim = Simulator(geometry, dm)

# Neutron source
particles = sim.create_point_source(np.array([25, 25, 25]), 10000, energy=2.0e6)
sim.add_source_particles(particles)
sim.run()

results = sim.get_results()
print(f"Total neutrons: {results['statistics']['total_neutrons']}")
print(f"Absorbed: {results['statistics']['absorbed']}")
print(f"Escaped: {results['statistics']['escaped']}")
```

## Testing

Run the included tests to verify functionality:

```bash
# Test CSG geometry
python tests/test_csg.py

# Test neutron transport with various geometries
python tests/test_neutron_box.py
```
