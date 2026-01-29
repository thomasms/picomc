"""
Advanced example demonstrating customization and extensibility

This example shows:
1. Custom physics process override
2. Custom geometry implementation
3. Event tracking and logging
4. Custom tallies
"""

import numpy as np
import sys
sys.path.insert(0, '.')

from picomc import Simulator, BoxGeometry, NuclearDataManager, FluxTally
from picomc.geometry import VoxelizedGeometry
from picomc.physics import PhysicsEngine
from picomc.particle import Particle
from picomc.data import CrossSectionData


class CustomPhysicsEngine(PhysicsEngine):
    """
    Custom physics engine with modified fission neutron sampling
    
    This demonstrates how to override specific physics processes
    """
    
    def sample_fission_neutrons(self) -> int:
        """Override to use different nu distribution"""
        # Use a different distribution - e.g., fixed 3 neutrons per fission
        return 3
    
    def sample_fission_energy(self) -> float:
        """Override to use custom fission spectrum"""
        # Use Maxwell-Boltzmann-like spectrum centered at 1.5 MeV
        return np.random.exponential(0.8e6) + 0.5e6


def main():
    print("="*70)
    print("Advanced PicoMC Example: Customization and Extensibility")
    print("="*70)
    
    # ========================================================================
    # 1. Setup with custom physics
    # ========================================================================
    print("\n1. Setting up custom physics engine...")
    
    # Create data manager
    data_manager = NuclearDataManager(use_endf=False)
    
    # Setup custom material with specific properties
    xs_data = CrossSectionData()
    xs_data.energies = np.array([1e-5, 1e-2, 1.0, 100.0, 1e4, 1e6, 2e7])
    xs_data.elastic = np.array([10.0, 10.0, 8.0, 5.0, 3.0, 2.0, 1.5])
    xs_data.capture = np.array([1000.0, 10.0, 3.0, 1.0, 0.5, 0.3, 0.2])
    xs_data.fission = np.array([0.0, 0.0, 0.05, 0.1, 0.15, 0.1, 0.05])
    xs_data.total = xs_data.elastic + xs_data.capture + xs_data.fission
    
    data_manager.materials['fissile'] = {
        'xs_data': xs_data,
        'number_density': 0.048  # atoms/barn-cm (like U-235 metal)
    }
    
    print("   ✓ Custom material 'fissile' created")
    
    # ========================================================================
    # 2. Setup geometry
    # ========================================================================
    print("\n2. Setting up geometry...")
    
    geometry = BoxGeometry(size=80.0, material='fissile')
    voxel_geometry = VoxelizedGeometry(geometry, num_bins=8)
    
    print("   ✓ 80cm cube with 8x8x8 voxels")
    
    # ========================================================================
    # 3. Create simulator with custom physics
    # ========================================================================
    print("\n3. Creating simulator with custom physics...")
    
    sim = Simulator(voxel_geometry, data_manager)
    
    # Replace default physics engine with custom one
    sim.physics = CustomPhysicsEngine(data_manager)
    sim.transport.physics = sim.physics
    
    print("   ✓ Custom PhysicsEngine installed")
    
    # ========================================================================
    # 4. Setup tally
    # ========================================================================
    tally = FluxTally(voxel_geometry)
    sim.set_tally(tally)
    
    # ========================================================================
    # 5. Add event tracking hooks
    # ========================================================================
    print("\n4. Adding custom event tracking...")
    
    event_log = {
        'fission_locations': [],
        'fission_neutrons': [],
        'high_energy_particles': 0
    }
    
    def track_fission_events(event):
        """Custom hook to track fission events"""
        if event.interaction_type == 'fission':
            event_log['fission_locations'].append(event.position.copy())
            event_log['fission_neutrons'].append(len(event.secondary_particles))
    
    def track_high_energy(particle):
        """Track high-energy particles"""
        if particle.energy > 3.0e6:  # > 3 MeV
            event_log['high_energy_particles'] += 1
    
    sim.physics.post_interaction_hook = track_fission_events
    sim.pre_event_hook = track_high_energy
    
    print("   ✓ Event tracking hooks installed")
    
    # ========================================================================
    # 6. Run simulation
    # ========================================================================
    print("\n5. Running simulation...")
    
    source_pos = np.array([40.0, 40.0, 40.0])
    num_source = 200
    
    particles = sim.create_point_source(source_pos, num_source, energy=2.0e6)
    sim.add_source_particles(particles)
    
    sim.run(num_particles=None, verbose=False)
    
    # ========================================================================
    # 7. Analyze results
    # ========================================================================
    print("\n6. Results:")
    print("   " + "-"*60)
    
    results = sim.get_results()
    stats = results['statistics']
    
    print(f"   Simulation Statistics:")
    print(f"      Total neutrons tracked: {stats['total_neutrons']}")
    print(f"      Absorbed: {stats['absorbed']} ({stats['absorption_fraction']*100:.2f}%)")
    print(f"      Escaped: {stats['escaped']} ({stats['escape_fraction']*100:.2f}%)")
    print(f"      Fission events: {stats['fission_events']}")
    
    print(f"\n   Custom Tracking Results:")
    print(f"      High-energy particles (>3 MeV): {event_log['high_energy_particles']}")
    
    if event_log['fission_neutrons']:
        avg_neutrons = np.mean(event_log['fission_neutrons'])
        print(f"      Average neutrons per fission: {avg_neutrons:.2f}")
        print(f"      (Should be ~3 due to custom override)")
    
    # Analyze fission locations
    if event_log['fission_locations']:
        fission_locs = np.array(event_log['fission_locations'])
        center = np.array([40.0, 40.0, 40.0])
        distances = np.linalg.norm(fission_locs - center, axis=1)
        print(f"      Average fission distance from center: {distances.mean():.2f} cm")
    
    # Flux analysis
    flux = results['flux']
    center_voxel = (4, 4, 4)
    edge_voxel = (0, 0, 0)
    
    print(f"\n   Flux Profile:")
    print(f"      Center voxel flux: {flux[center_voxel]:.4e}")
    print(f"      Edge voxel flux: {flux[edge_voxel]:.4e}")
    ratio = flux[center_voxel] / flux[edge_voxel] if flux[edge_voxel] > 0 else np.inf
    print(f"      Center/edge ratio: {ratio:.2f}")
    
    print("\n" + "="*70)
    print("Advanced example complete!")
    print("="*70)
    print("\nKey features demonstrated:")
    print("  ✓ Custom physics engine with overridden methods")
    print("  ✓ Custom material definition")
    print("  ✓ Event tracking with hooks")
    print("  ✓ Post-processing and analysis")
    print("  ✓ Modular architecture for easy extension")


if __name__ == "__main__":
    main()
