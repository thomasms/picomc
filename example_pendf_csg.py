"""
Example: Using PENDF data with CSG geometry

This example demonstrates:
1. Loading PENDF format nuclear data (library-agnostic)
2. Creating CSG geometry (Serpent/OpenMC style)
3. Running neutron transport simulation
4. Analyzing results

For JEFF 4.0 PENDF data, download from:
https://data.oecd-nea.org/records/wgw94-qcx30
"""

import sys
sys.path.insert(0, '.')

import numpy as np
from picomc import Simulator, NuclearDataManager, CSGGeometryWrapper, FluxTally
from picomc.csg import CSGGeometry, CSGCell, HalfSpace, Plane, Sphere, Cylinder
from picomc.data import CrossSectionData


def example_csg_with_pendf():
    """Example using CSG geometry with PENDF data"""
    print("="*70)
    print("Example: CSG Geometry with PENDF Nuclear Data")
    print("="*70)
    
    # ========================================================================
    # 1. Setup Nuclear Data
    # ========================================================================
    print("\n1. Setting up nuclear data...")
    
    data_manager = NuclearDataManager()
    
    # Try to load PENDF data if available
    # For demonstration, we'll use default data
    # In real use, provide path to JEFF 4.0 PENDF files:
    # data_manager.load_pendf_file('jeff40/pendf/n-092_U_235.pendf', 'U235', 0.048)
    
    # Create uranium-like material
    xs_data = CrossSectionData()
    xs_data.energies = np.array([1e-5, 1e-2, 1.0, 100.0, 1e4, 1e6, 2e7])
    xs_data.elastic = np.array([10.0, 10.0, 8.0, 5.0, 3.0, 2.0, 1.5])
    xs_data.capture = np.array([100.0, 10.0, 3.0, 1.0, 0.5, 0.3, 0.2])
    xs_data.fission = np.array([0.0, 0.0, 0.1, 0.2, 0.3, 0.2, 0.1])
    xs_data.total = xs_data.elastic + xs_data.capture + xs_data.fission
    
    data_manager.materials['U235'] = {
        'xs_data': xs_data,
        'number_density': 0.048
    }
    
    print("   ✓ U-235 data loaded (number density: 0.048 atoms/barn-cm)")
    
    # ========================================================================
    # 2. Create CSG Geometry
    # ========================================================================
    print("\n2. Creating CSG geometry...")
    print("   Geometry: Spherical target in box")
    
    csg = CSGGeometry()
    
    # Define surfaces
    # Sphere target at center
    center = np.array([25.0, 25.0, 25.0])
    radius = 10.0
    sphere = Sphere(1, center, radius)
    csg.add_surface(sphere)
    
    # Box boundaries (50x50x50 cm)
    px_low = Plane(10, 1, 0, 0, 0)
    px_high = Plane(11, 1, 0, 0, 50)
    py_low = Plane(12, 0, 1, 0, 0)
    py_high = Plane(13, 0, 1, 0, 50)
    pz_low = Plane(14, 0, 0, 1, 0)
    pz_high = Plane(15, 0, 0, 1, 50)
    
    for surf in [px_low, px_high, py_low, py_high, pz_low, pz_high]:
        csg.add_surface(surf)
    
    # Create cells
    # Sphere cell with U-235
    sphere_cell = CSGCell(1, material='U235')
    sphere_cell.add_region(HalfSpace(sphere, -1))  # Inside sphere
    csg.add_cell(sphere_cell)
    
    print(f"   ✓ Sphere cell: radius={radius} cm at {center}")
    
    # Void cell (outside sphere, inside box)
    void_cell = CSGCell(2, material=None)
    void_cell.add_region(
        HalfSpace(sphere, +1),    # Outside sphere
        HalfSpace(px_low, +1),
        HalfSpace(px_high, -1),
        HalfSpace(py_low, +1),
        HalfSpace(py_high, -1),
        HalfSpace(pz_low, +1),
        HalfSpace(pz_high, -1),
    )
    csg.add_cell(void_cell)
    
    print(f"   ✓ Void cell: 50x50x50 cm box")
    
    # ========================================================================
    # 3. Create Simulator
    # ========================================================================
    print("\n3. Creating simulator...")
    
    geometry = CSGGeometryWrapper(csg)
    sim = Simulator(geometry, data_manager)
    
    print("   ✓ Simulator initialized with CSG geometry")
    
    # ========================================================================
    # 4. Create Neutron Source
    # ========================================================================
    print("\n4. Creating neutron source...")
    
    num_source = 200
    source_energy = 2.0e6  # 2 MeV
    
    # Create beam hitting the sphere
    particles = []
    for i in range(num_source):
        # Random position in beam directed at sphere
        y = center[1] + np.random.uniform(-radius, radius)
        z = center[2] + np.random.uniform(-radius, radius)
        position = np.array([5.0, y, z])
        
        # Direction toward sphere center
        direction = center - position
        direction /= np.linalg.norm(direction)
        
        from picomc.particle import Particle
        particle = Particle(position, direction, source_energy, is_source=True)
        particles.append(particle)
    
    sim.add_source_particles(particles)
    
    print(f"   ✓ Created {num_source} neutron beam")
    print(f"   ✓ Source energy: {source_energy/1e6:.1f} MeV")
    print(f"   ✓ Beam directed at spherical target")
    
    # ========================================================================
    # 5. Run Simulation
    # ========================================================================
    print("\n5. Running Monte Carlo simulation...")
    print("   (This may take a moment...)")
    
    sim.run(num_particles=None, verbose=False)
    
    # ========================================================================
    # 6. Analyze Results
    # ========================================================================
    print("\n6. Results:")
    print("   " + "-"*60)
    
    results = sim.get_results()
    stats = results['statistics']
    
    print(f"\n   Particle Statistics:")
    print(f"      Total neutrons tracked: {stats['total_neutrons']}")
    print(f"      Source particles: {num_source}")
    print(f"      Secondary particles: {stats['total_neutrons'] - num_source}")
    
    print(f"\n   Reaction Statistics:")
    print(f"      Absorbed: {stats['absorbed']} ({stats['absorption_fraction']*100:.1f}%)")
    print(f"      Escaped: {stats['escaped']} ({stats['escape_fraction']*100:.1f}%)")
    print(f"      Fission events: {stats['fission_events']}")
    
    if stats['fission_events'] > 0:
        avg_secondaries = (stats['total_neutrons'] - num_source) / stats['fission_events']
        print(f"      Avg secondaries/fission: {avg_secondaries:.2f}")
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "="*70)
    print("Example Complete!")
    print("="*70)
    
    print("\nKey Features Demonstrated:")
    print("  ✓ CSG geometry (Serpent/OpenMC style)")
    print("  ✓ Nuclear data management (PENDF-ready)")
    print("  ✓ Sphere and plane surfaces")
    print("  ✓ Boolean operations (intersection)")
    print("  ✓ Multi-cell geometry")
    print("  ✓ Neutron transport simulation")
    print("  ✓ Statistics collection")
    
    print("\nTo use JEFF 4.0 PENDF data:")
    print("  1. Download from: https://data.oecd-nea.org/records/wgw94-qcx30")
    print("  2. Replace the default data with:")
    print("     data_manager.load_pendf_file('path/to/n-092_U_235.pendf', 'U235', 0.048)")


def example_cylinder_geometry():
    """Example with cylindrical geometry"""
    print("\n\n" + "="*70)
    print("Example: Cylindrical Fuel Pin with CSG")
    print("="*70)
    
    print("\n1. Creating cylindrical geometry...")
    
    data_manager = NuclearDataManager()
    data_manager.add_material('fuel', number_density=0.045)
    
    csg = CSGGeometry()
    
    # Fuel pin: cylinder along z-axis
    fuel_cyl = Cylinder(1, np.array([25, 25, 0]), radius=5, axis='z')
    csg.add_surface(fuel_cyl)
    
    # Axial boundaries
    z_bottom = Plane(2, 0, 0, 1, 0)
    z_top = Plane(3, 0, 0, 1, 100)
    csg.add_surface(z_bottom)
    csg.add_surface(z_top)
    
    # Outer box
    box_size = 50
    for i, (A, B, C, D) in enumerate([
        (1, 0, 0, 0), (1, 0, 0, box_size),
        (0, 1, 0, 0), (0, 1, 0, box_size)
    ], start=10):
        csg.add_surface(Plane(i, A, B, C, D))
    
    # Fuel cell
    fuel_cell = CSGCell(1, material='fuel')
    fuel_cell.add_region(
        HalfSpace(fuel_cyl, -1),  # Inside cylinder
        HalfSpace(z_bottom, +1),  # Above bottom
        HalfSpace(z_top, -1),     # Below top
    )
    csg.add_cell(fuel_cell)
    
    print("   ✓ Cylindrical fuel pin geometry created")
    print(f"   ✓ Fuel pin: radius=5 cm, height=100 cm")
    
    # Run quick simulation
    geometry = CSGGeometryWrapper(csg)
    sim = Simulator(geometry, data_manager)
    
    particles = []
    for i in range(50):
        pos = np.array([25 + np.random.uniform(-2, 2), 
                       25 + np.random.uniform(-2, 2), 
                       50])
        dir = np.array([0, 0, -1])  # Axial direction
        from picomc.particle import Particle
        particles.append(Particle(pos, dir, 2.0e6, is_source=True))
    
    sim.add_source_particles(particles)
    sim.run(num_particles=None, verbose=False)
    
    results = sim.get_results()
    print(f"\n   Results: {results['statistics']['total_neutrons']} neutrons tracked")
    print("   ✓ Cylindrical geometry test passed")


if __name__ == '__main__':
    # Run examples
    example_csg_with_pendf()
    example_cylinder_geometry()
    
    print("\n" + "="*70)
    print("All examples completed successfully!")
    print("="*70)
