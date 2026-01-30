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

## Nuclear Data Components

PicoMC extracts and uses the following nuclear data from ENDF/PENDF files:

### Cross Sections (MF=3)
- **MT=1**: Total cross section
- **MT=2**: Elastic scattering
- **MT=18**: Fission
- **MT=102**: Radiative capture
- **MT=51-91**: Inelastic scattering levels (summed)

### Fission Neutron Multiplicity - Nubar (MF=1)
- **MT=452**: Total nubar (prompt + delayed)
- **MT=455**: Delayed nubar
- **MT=456**: Prompt nubar

Energy-dependent nubar data is used to sample the number of neutrons produced per fission event using a Poisson distribution.

### Fission Neutron Energy Spectrum (MF=5, MT=18)
- **Watt Spectrum** (LF=11): χ(E) = C * exp(-E/a) * sinh(sqrt(b*E))
  - Parameters a and b are extracted from ENDF data
  - Default U-235: a = 0.988 MeV, b = 2.249 MeV⁻¹
- **Tabulated Spectrum** (LF=1): χ(E) as tabulated function

The fission spectrum determines the energy distribution of neutrons born in fission events.

## Using PENDF Data (Recommended)

PENDF files contain processed nuclear data with linearized cross sections, making them ideal for Monte Carlo simulations. They work with data from any library (JEFF, ENDF/B, JENDL, etc.).

PicoMC uses **endf-parserpy** to parse PENDF files, providing robust and accurate parsing of the ENDF-6 format.

### JEFF 4.0 PENDF Library

The JEFF 4.0 PENDF library is available from OECD-NEA:
- URL: https://data.oecd-nea.org/records/wgw94-qcx30
- Contains processed data for all isotopes at multiple temperatures
- Linearized cross sections ready for direct use
- Includes fission data (nubar and spectrum) where applicable

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

## Fission Physics with Real ENDF Data

PicoMC uses real nuclear data from ENDF/PENDF files for accurate fission physics simulations.

### What Data is Used

1. **Nubar (ν)** - Average neutrons per fission
   - Source: ENDF MF=1, MT=452 (total), MT=455 (delayed), MT=456 (prompt)
   - Energy-dependent: ν = f(E_incident)
   - Sampled using Poisson distribution

2. **Fission Spectrum** - Energy distribution of fission neutrons
   - Source: ENDF MF=5, MT=18
   - **Watt Spectrum** (most common): χ(E) = C * exp(-E/a) * sinh(sqrt(b*E))
   - **Tabulated**: χ(E) from tabulated data
   - Default U-235: a = 0.988 MeV, b = 2.249 MeV⁻¹

### Example: Fission Chain Reaction

```python
from picomc import Simulator, BoxGeometry, NuclearDataManager
import numpy as np

# Create data manager and load U-235 data with fission info
data_manager = NuclearDataManager()
data_manager.load_pendf_file(
    'path/to/jeff40/pendf/n-092_U_235.pendf',
    'U235_fuel',
    number_density=0.048,  # atoms/barn-cm
    temperature=293.6
)

# Check what fission data was loaded
material = data_manager.materials['U235_fuel']
if 'nubar_data' in material:
    nubar_data = material['nubar_data']
    print(f"Nubar data loaded: {len(nubar_data.energies)} energy points")
    print(f"Nubar range: {nubar_data.total[0]:.3f} to {nubar_data.total[-1]:.3f}")

if 'fission_spectrum' in material:
    spec = material['fission_spectrum']
    print(f"Fission spectrum type: {spec.spectrum_type}")
    if spec.spectrum_type == 'watt':
        print(f"  Watt parameters: a={spec.params['a']/1e6:.3f} MeV, b={spec.params['b']*1e6:.3f} MeV^-1")

# Create geometry and simulator
geometry = BoxGeometry(size=50.0, material='U235_fuel')
sim = Simulator(geometry, data_manager, enable_fission=True)

# Create neutron source at center
source_pos = np.array([25.0, 25.0, 25.0])
particles = sim.create_point_source(source_pos, n_particles=100, energy=2.0e6)
sim.add_source_particles(particles)

# Run simulation
sim.run()
results = sim.get_results()

# Analyze fission statistics
print(f"\nResults:")
print(f"Total particles tracked: {results['statistics']['total_neutrons']}")
print(f"Fission events: {results['statistics']['fissions']}")
print(f"Absorbed: {results['statistics']['absorbed']}")
print(f"Escaped: {results['statistics']['escaped']}")
```

### Accessing Nubar and Fission Spectrum Directly

```python
# Get nubar at different energies
thermal_energy = 0.0253  # eV (thermal)
fast_energy = 2.0e6      # eV (2 MeV)

nubar_thermal = data_manager.get_nubar('U235_fuel', thermal_energy)
nubar_fast = data_manager.get_nubar('U235_fuel', fast_energy)

print(f"Nubar at thermal energy: {nubar_thermal:.3f}")
print(f"Nubar at 2 MeV: {nubar_fast:.3f}")

# Sample fission neutron energies
fission_energies = [
    data_manager.sample_fission_energy('U235_fuel', 2.0e6)
    for _ in range(1000)
]

import matplotlib.pyplot as plt
plt.hist(fission_energies, bins=50, density=True)
plt.xlabel('Energy (eV)')
plt.ylabel('Probability Density')
plt.title('Fission Neutron Energy Spectrum')
plt.xscale('log')
plt.show()
```

### Energy-Dependent Nubar Example

```python
import matplotlib.pyplot as plt
import numpy as np

# Get nubar as function of energy
energies = np.logspace(0, 7, 100)  # 1 eV to 10 MeV
nubars = [data_manager.get_nubar('U235_fuel', E) for E in energies]

plt.figure(figsize=(10, 6))
plt.semilogx(energies, nubars, linewidth=2)
plt.xlabel('Incident Neutron Energy (eV)')
plt.ylabel('Average Neutrons per Fission (ν)')
plt.title('Energy-Dependent Nubar for U-235')
plt.grid(True, which='both', alpha=0.3)
plt.axhline(y=2.5, color='r', linestyle='--', label='Typical thermal value')
plt.legend()
plt.show()
```

### Comparing Fission Spectra

```python
# Compare different materials or temperatures
materials = {
    'U235': 'path/to/U235.pendf',
    'Pu239': 'path/to/Pu239.pendf',
}

for name, filepath in materials.items():
    data_manager.load_pendf_file(filepath, name, 0.048)
    
    # Sample energies
    energies = [
        data_manager.sample_fission_energy(name, 2.0e6)
        for _ in range(5000)
    ]
    
    plt.hist(energies, bins=100, alpha=0.5, label=name, density=True)

plt.xlabel('Fission Neutron Energy (eV)')
plt.ylabel('Probability Density')
plt.title('Comparison of Fission Spectra')
plt.xscale('log')
plt.legend()
plt.show()
```

### Physics Improvements Over Simple Model

The real ENDF data provides several improvements:

1. **Energy-dependent nubar**: 
   - Thermal neutrons (0.025 eV): ν ≈ 2.43
   - Fast neutrons (2 MeV): ν ≈ 2.50
   - High energy (14 MeV): ν ≈ 2.8

2. **Accurate fission spectrum**:
   - Peak around 0.7 - 1.0 MeV (not at 2 MeV)
   - Proper high-energy tail
   - Material-specific differences

3. **Statistical fluctuations**:
   - Poisson distribution for number of neutrons
   - Proper sampling from Watt or tabulated spectrum

### Validation

Compare your results with published benchmarks:

```python
# ICSBEP benchmarks or MCNP/Serpent calculations
# Example: k-effective for critical assemblies

# Run simulation
initial_neutrons = 100
sim.run()
results = sim.get_results()

# Get average nubar at typical energy
typical_energy = 2.0e6  # eV
mean_nubar = data_manager.get_nubar('U235_fuel', typical_energy)

# Calculate multiplication factor
total_fissions = results['statistics']['fissions']
k_eff = (total_fissions * mean_nubar) / initial_neutrons

print(f"k-effective: {k_eff:.4f}")
print(f"Mean nubar used: {mean_nubar:.3f}")
```

### Notes on Data Quality

- **PENDF files** contain linearized data - best for Monte Carlo
- **Temperature effects** are important for thermal reactors
- **Delayed neutrons** (from nubar_delayed) can be important for time-dependent problems
- **Prompt neutrons** (from nubar_prompt) dominate in most fast systems

### Fallback Behavior

If ENDF/PENDF data is not available or parsing fails:

- Nubar: Uses default value of 2.5 (typical for U-235)
- Fission spectrum: Uses Watt spectrum with U-235 parameters
- Warning is issued to alert user

This ensures simulations can run for testing even without data files.
