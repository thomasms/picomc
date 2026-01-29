"""
Test neutrons incident on a box of material

This test demonstrates:
1. Creating a box geometry (both standard and CSG)
2. Loading nuclear data (with fallback to default)
3. Running neutron transport simulation
4. Collecting and analyzing results
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from picomc import Simulator, BoxGeometry, NuclearDataManager, FluxTally, CSGGeometryWrapper
from picomc.geometry import VoxelizedGeometry
from picomc.csg import CSGGeometry, CSGCell, HalfSpace, Plane, Sphere
from picomc.data import CrossSectionData


def test_box_standard_geometry():
    """Test with standard box geometry"""
    print("\n" + "=" * 60)
    print("Test 1: Neutrons on Box (Standard Geometry)")
    print("=" * 60)

    # Create data manager with simple cross sections
    dm = NuclearDataManager(use_endf=False)

    # Add material with reduced fission to avoid runaway
    xs_data = CrossSectionData()
    xs_data.energies = np.array([1e-5, 1e-2, 1.0, 100.0, 1e4, 1e6, 2e7])
    xs_data.elastic = np.array([10.0, 10.0, 8.0, 5.0, 3.0, 2.0, 1.5])
    xs_data.capture = np.array([1000.0, 10.0, 3.0, 1.0, 0.5, 0.3, 0.2])
    xs_data.fission = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # No fission
    xs_data.total = xs_data.elastic + xs_data.capture + xs_data.fission

    dm.materials["test_material"] = {"xs_data": xs_data, "number_density": 0.05}

    # Create box geometry
    box_size = 50.0  # cm
    geometry = BoxGeometry(size=box_size, material="test_material")
    voxel_geom = VoxelizedGeometry(geometry, num_bins=5)

    # Create simulator
    sim = Simulator(voxel_geom, dm)
    tally = FluxTally(voxel_geom)
    sim.set_tally(tally)

    # Create source: neutrons incident from one side
    # Place source particles at edge, all moving inward
    num_particles = 50
    particles = []

    for i in range(num_particles):
        # Random position on one face
        y = np.random.uniform(0, box_size)
        z = np.random.uniform(0, box_size)
        position = np.array([0.1, y, z])  # Just inside box

        # Direction into box (mostly +x)
        direction = np.array([1.0, 0.0, 0.0])
        direction /= np.linalg.norm(direction)

        from picomc.particle import Particle

        particle = Particle(position, direction, energy=2.0e6, is_source=True)
        particles.append(particle)

    sim.add_source_particles(particles)

    print(f"\nSimulating {num_particles} neutrons incident on {box_size} cm box...")
    sim.run(num_particles=None, verbose=False)

    # Get results
    results = sim.get_results()
    stats = results["statistics"]

    print(f"\nResults:")
    print(f"  Total neutrons tracked: {stats['total_neutrons']}")
    print(f"  Absorbed: {stats['absorbed']} ({stats['absorption_fraction']*100:.1f}%)")
    print(f"  Escaped: {stats['escaped']} ({stats['escape_fraction']*100:.1f}%)")

    # Verify some neutrons were tracked
    assert stats["total_neutrons"] >= num_particles, "Should track at least source particles"
    assert stats["absorbed"] > 0, "Some neutrons should be absorbed"

    print("\n✓ Standard box geometry test passed")
    pass


def test_box_csg_geometry():
    """Test with CSG geometry"""
    print("\n" + "=" * 60)
    print("Test 2: Neutrons on Box (CSG Geometry)")
    print("=" * 60)

    # Create data manager
    dm = NuclearDataManager(use_endf=False)
    xs_data = CrossSectionData()
    xs_data.energies = np.array([1e-5, 1e-2, 1.0, 100.0, 1e4, 1e6, 2e7])
    xs_data.elastic = np.array([10.0, 10.0, 8.0, 5.0, 3.0, 2.0, 1.5])
    xs_data.capture = np.array([1000.0, 10.0, 3.0, 1.0, 0.5, 0.3, 0.2])
    xs_data.fission = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    xs_data.total = xs_data.elastic + xs_data.capture + xs_data.fission

    dm.materials["csg_material"] = {"xs_data": xs_data, "number_density": 0.05}

    # Create CSG box
    csg = CSGGeometry()

    # Define box with planes
    box_size = 50.0
    px_low = Plane(1, 1, 0, 0, 0)
    px_high = Plane(2, 1, 0, 0, box_size)
    py_low = Plane(3, 0, 1, 0, 0)
    py_high = Plane(4, 0, 1, 0, box_size)
    pz_low = Plane(5, 0, 0, 1, 0)
    pz_high = Plane(6, 0, 0, 1, box_size)

    for surf in [px_low, px_high, py_low, py_high, pz_low, pz_high]:
        csg.add_surface(surf)

    # Create cell
    box_cell = CSGCell(1, material="csg_material")
    box_cell.add_region(
        HalfSpace(px_low, +1),
        HalfSpace(px_high, -1),
        HalfSpace(py_low, +1),
        HalfSpace(py_high, -1),
        HalfSpace(pz_low, +1),
        HalfSpace(pz_high, -1),
    )
    csg.add_cell(box_cell)

    # Wrap CSG geometry
    geometry = CSGGeometryWrapper(csg)

    # Create simulator
    sim = Simulator(geometry, dm)

    # Create source
    num_particles = 30
    particles = []

    for i in range(num_particles):
        y = np.random.uniform(5, box_size - 5)
        z = np.random.uniform(5, box_size - 5)
        position = np.array([5.0, y, z])
        direction = np.array([1.0, 0.0, 0.0])
        direction /= np.linalg.norm(direction)

        from picomc.particle import Particle

        particle = Particle(position, direction, energy=2.0e6, is_source=True)
        particles.append(particle)

    sim.add_source_particles(particles)

    print(f"\nSimulating {num_particles} neutrons with CSG geometry...")
    sim.run(num_particles=None, verbose=False)

    # Get results
    results = sim.get_results()
    stats = results["statistics"]

    print(f"\nResults:")
    print(f"  Total neutrons tracked: {stats['total_neutrons']}")
    print(f"  Absorbed: {stats['absorbed']} ({stats['absorption_fraction']*100:.1f}%)")
    print(f"  Escaped: {stats['escaped']} ({stats['escape_fraction']*100:.1f}%)")

    assert stats["total_neutrons"] >= num_particles, "Should track source particles"

    print("\n✓ CSG geometry test passed")
    pass


def test_sphere_target_csg():
    """Test neutrons on a spherical target using CSG"""
    print("\n" + "=" * 60)
    print("Test 3: Neutrons on Spherical Target (CSG)")
    print("=" * 60)

    # Create data manager
    dm = NuclearDataManager(use_endf=False)
    dm.add_material("sphere_material", number_density=0.05)

    # Create CSG with sphere
    csg = CSGGeometry()

    # Sphere at center
    center = np.array([25.0, 25.0, 25.0])
    radius = 10.0
    sphere = Sphere(1, center, radius)
    csg.add_surface(sphere)

    # Sphere cell
    sphere_cell = CSGCell(1, material="sphere_material")
    sphere_cell.add_region(HalfSpace(sphere, -1))  # Inside sphere
    csg.add_cell(sphere_cell)

    # Outer box for void
    px_low = Plane(10, 1, 0, 0, 0)
    px_high = Plane(11, 1, 0, 0, 50)
    py_low = Plane(12, 0, 1, 0, 0)
    py_high = Plane(13, 0, 1, 0, 50)
    pz_low = Plane(14, 0, 0, 1, 0)
    pz_high = Plane(15, 0, 0, 1, 50)

    for surf in [px_low, px_high, py_low, py_high, pz_low, pz_high]:
        csg.add_surface(surf)

    void_cell = CSGCell(2, material=None)
    void_cell.add_region(
        HalfSpace(sphere, +1),  # Outside sphere
        HalfSpace(px_low, +1),
        HalfSpace(px_high, -1),
        HalfSpace(py_low, +1),
        HalfSpace(py_high, -1),
        HalfSpace(pz_low, +1),
        HalfSpace(pz_high, -1),
    )
    csg.add_cell(void_cell)

    # Wrap and create simulator
    geometry = CSGGeometryWrapper(csg)
    sim = Simulator(geometry, dm)

    # Create beam hitting sphere
    num_particles = 40
    particles = []

    for i in range(num_particles):
        # Random position in beam
        y = center[1] + np.random.uniform(-radius / 2, radius / 2)
        z = center[2] + np.random.uniform(-radius / 2, radius / 2)
        position = np.array([5.0, y, z])

        # Aimed at sphere center
        direction = center - position
        direction /= np.linalg.norm(direction)

        from picomc.particle import Particle

        particle = Particle(position, direction, energy=2.0e6, is_source=True)
        particles.append(particle)

    sim.add_source_particles(particles)

    print(f"\nSimulating {num_particles} neutrons incident on sphere...")
    print(f"  Sphere: radius={radius} cm at {center}")
    sim.run(num_particles=None, verbose=False)

    results = sim.get_results()
    stats = results["statistics"]

    print(f"\nResults:")
    print(f"  Total neutrons tracked: {stats['total_neutrons']}")
    print(f"  Absorbed: {stats['absorbed']} ({stats['absorption_fraction']*100:.1f}%)")
    print(f"  Escaped: {stats['escaped']} ({stats['escape_fraction']*100:.1f}%)")

    assert stats["total_neutrons"] >= num_particles

    print("\n✓ Spherical target test passed")
    pass


if __name__ == "__main__":
    print("=" * 60)
    print("NEUTRON TRANSPORT TESTS")
    print("Testing neutrons incident on material targets")
    print("=" * 60)

    try:
        test_box_standard_geometry()
        test_box_csg_geometry()
        test_sphere_target_csg()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nValidated:")
        print("  ✓ Standard box geometry")
        print("  ✓ CSG box geometry")
        print("  ✓ CSG spherical target")
        print("  ✓ Neutron transport and statistics")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
