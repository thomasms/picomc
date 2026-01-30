"""
Example: Using parallel simulation and JEFF library bootstrap

This example demonstrates:
1. How to use ParallelSimulator for faster simulations
2. How to load JEFF 4.0 nuclear data library
3. Performance comparison between sequential and parallel execution
"""

import numpy as np
import time
from picomc import (
    Simulator,
    ParallelSimulator,
    BoxGeometry,
    NuclearDataManager,
    FluxTally,
)


def example_parallel_simulation():
    """Example of parallel Monte Carlo simulation"""
    print("=" * 70)
    print("Example: Parallel Monte Carlo Simulation")
    print("=" * 70)

    # Setup geometry and data
    geometry = BoxGeometry(50.0, "U235")
    dm = NuclearDataManager()
    dm.add_material("U235", 0.048)  # Typical U-235 number density

    # Create source
    source_position = np.array([25.0, 25.0, 25.0])
    source_energy = 2.0e6  # 2 MeV
    num_particles = 500

    # Sequential simulation
    print("\n1. Sequential Simulation")
    print("-" * 70)
    sim_seq = Simulator(geometry, dm)
    particles = sim_seq.create_point_source(source_position, num_particles, source_energy)
    sim_seq.add_source_particles(particles)

    start_time = time.time()
    sim_seq.run(verbose=False)
    seq_time = time.time() - start_time

    results_seq = sim_seq.get_results()
    print(f"Time: {seq_time:.2f} seconds")
    print(f"Neutrons: {results_seq['statistics']['neutrons']}")
    print(f"Escapes: {results_seq['statistics']['escapes']}")
    print(f"Fissions: {results_seq['statistics']['fissions']}")

    # Parallel simulation with 4 workers
    print("\n2. Parallel Simulation (4 workers)")
    print("-" * 70)
    sim_par = ParallelSimulator(geometry, dm, n_jobs=4)
    particles = sim_par.create_point_source(source_position, num_particles, source_energy)
    sim_par.add_source_particles(particles)

    start_time = time.time()
    sim_par.run(verbose=False)
    par_time = time.time() - start_time

    results_par = sim_par.get_results()
    print(f"Time: {par_time:.2f} seconds")
    print(f"Neutrons: {results_par['statistics']['neutrons']}")
    print(f"Escapes: {results_par['statistics']['escapes']}")
    print(f"Fissions: {results_par['statistics']['fissions']}")

    # Performance comparison
    print("\n3. Performance Comparison")
    print("-" * 70)
    if par_time > 0:
        speedup = seq_time / par_time
        print(f"Sequential time: {seq_time:.2f} s")
        print(f"Parallel time:   {par_time:.2f} s")
        print(f"Speedup:         {speedup:.2f}x")
        print(f"Efficiency:      {speedup/4*100:.1f}%")

    print("\n✓ Parallel simulation complete!")


def example_jeff_library():
    """Example of loading JEFF 4.0 library"""
    print("\n" + "=" * 70)
    print("Example: JEFF 4.0 Library Loading")
    print("=" * 70)

    dm = NuclearDataManager()

    # Method 1: Load specific isotopes from JEFF 4.0
    print("\n1. Loading JEFF 4.0 Library")
    print("-" * 70)
    print("To use JEFF 4.0 library:")
    print("  1. Download files from: https://data.oecd-nea.org/records/wgw94-qcx30")
    print("  2. Place in: ~/.picomc/data/jeff40/")
    print("  3. Use bootstrap script: python bootstrap_jeff.py --help")

    # Example code (commented out as files need to be downloaded first)
    print("\nExample code:")
    print("""
    dm = NuclearDataManager()
    
    # Load specific isotopes from JEFF 4.0
    try:
        materials = dm.load_jeff40_library(['U235', 'Pu239', 'H1'])
        print(f"Loaded: {list(materials.keys())}")
        
        # Get information about a material
        info = dm.get_material_info('U235')
        print(f"\\nU-235 Info:")
        print(f"  Energy range: {info['energy_range']}")
        print(f"  Data points: {info['num_energy_points']}")
        print(f"  Has fission: {info['has_fission']}")
        
    except FileNotFoundError as e:
        print(f"JEFF library not found: {e}")
    """)

    # Method 2: List loaded materials
    print("\n2. Material Management")
    print("-" * 70)
    dm.add_material("TestMaterial", 0.05)

    loaded = dm.list_loaded_materials()
    print(f"Loaded materials: {loaded}")

    if loaded:
        info = dm.get_material_info(loaded[0])
        print(f"\nMaterial info for {loaded[0]}:")
        for key, value in info.items():
            print(f"  {key}: {value}")

    print("\n✓ Library management complete!")


def example_combined():
    """Example combining parallel simulation with library loading"""
    print("\n" + "=" * 70)
    print("Example: Parallel Simulation with Custom Materials")
    print("=" * 70)

    # Create geometry and data manager
    geometry = BoxGeometry(30.0, "CustomMaterial")
    dm = NuclearDataManager()

    # Add custom material (could be from JEFF library)
    dm.add_material("CustomMaterial", 0.05)

    # Create flux tally
    voxels = (10, 10, 10)
    bounds = ((0, 30), (0, 30), (0, 30))
    tally = FluxTally(voxels, bounds)

    # Run parallel simulation with tally
    sim = ParallelSimulator(geometry, dm, n_jobs=2)
    sim.set_tally(tally)

    particles = sim.create_point_source(np.array([15, 15, 15]), 200, 2.0e6)
    sim.add_source_particles(particles)

    print("\nRunning parallel simulation with flux tally...")
    sim.run(verbose=False)

    results = sim.get_results()

    print(f"\nResults:")
    print(f"  Neutrons: {results['statistics']['neutrons']}")
    print(f"  Escapes: {results['statistics']['escapes']}")
    print(f"  Peak flux: {np.max(results['flux']):.2e}")

    print("\n✓ Combined example complete!")


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("PicoMC: Parallel Simulation and JEFF Library Examples")
    print("=" * 70)

    # Example 1: Parallel simulation
    try:
        example_parallel_simulation()
    except Exception as e:
        print(f"\n⚠ Parallel example failed (may not work in all environments): {e}")

    # Example 2: JEFF library
    example_jeff_library()

    # Example 3: Combined
    try:
        example_combined()
    except Exception as e:
        print(f"\n⚠ Combined example failed: {e}")

    print("\n" + "=" * 70)
    print("All examples complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
