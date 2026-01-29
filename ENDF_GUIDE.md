# Using ENDF Data with PicoMC

This guide explains how to use real nuclear data from ENDF (Evaluated Nuclear Data File) format files with PicoMC.

## Installation

First, install picomc with ENDF support:

```bash
pip install -e ".[endf]"
```

This will install the `endf-parserpy` library.

## Basic ENDF Usage

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
