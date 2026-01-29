"""
Example script demonstrating the new picomc API

This shows how to use the refactored picomc package with:
- Modular structure
- Pythonic interface
- Hook capabilities for customization
- Optional ENDF data integration
"""

import numpy as np
import matplotlib.pyplot as plt
from picomc import Simulator, BoxGeometry, NuclearDataManager, FluxTally
from picomc.geometry import VoxelizedGeometry


def main():
    # ============================================================
    # 1. Setup nuclear data
    # ============================================================
    print("Setting up nuclear data...")
    
    # Create data manager (use_endf=False uses default cross sections)
    # Set use_endf=True and load ENDF files for real data
    data_manager = NuclearDataManager(use_endf=False)
    
    # Add a default material (for demonstration)
    # Number density typical values:
    # - Water: ~0.1 atoms/barn-cm
    # - Uranium metal: ~0.048 atoms/barn-cm
    # In real use: data_manager.load_endf_file('path/to/endf', 'U235', number_density=0.048)
    data_manager._add_default_material('default', number_density=0.05)
    
    # ============================================================
    # 2. Setup geometry
    # ============================================================
    print("Setting up geometry...")
    
    box_size = 100.0  # cm
    geometry = BoxGeometry(size=box_size, material='default')
    
    # Create voxelized geometry for tallying
    num_bins = 10
    voxel_geometry = VoxelizedGeometry(geometry, num_bins=num_bins)
    
    # ============================================================
    # 3. Create simulator
    # ============================================================
    print("Creating simulator...")
    
    sim = Simulator(voxel_geometry, data_manager)
    
    # ============================================================
    # 4. Setup tally
    # ============================================================
    tally = FluxTally(voxel_geometry)
    sim.set_tally(tally)
    
    # ============================================================
    # 5. Optional: Add custom hooks for event/step level control
    # ============================================================
    
    # Example: Pre-event hook to log every 50th particle
    particle_count = [0]
    def pre_event_hook(particle):
        particle_count[0] += 1
        if particle_count[0] % 50 == 0:
            print(f"  Processing particle {particle_count[0]}: E={particle.energy:.2e} eV")
    
    # Uncomment to enable hook:
    # sim.pre_event_hook = pre_event_hook
    
    # Example: Post-step hook to monitor fission events
    # def post_step_hook(particle, event):
    #     if event.interaction_type == 'fission':
    #         print(f"  Fission at {event.position} producing {len(event.secondary_particles)} neutrons")
    # 
    # sim.transport.post_step_hook = post_step_hook
    
    # ============================================================
    # 6. Create source and run simulation
    # ============================================================
    print("\nCreating source particles...")
    
    # Create point source at center
    source_position = np.array([box_size/2, box_size/2, box_size/2])
    num_source = 1000
    energy = 2.0e6  # 2 MeV
    
    source_particles = sim.create_point_source(source_position, num_source, energy)
    sim.add_source_particles(source_particles)
    
    print(f"\nRunning simulation with {num_source} source particles...")
    sim.run(verbose=True)
    
    # ============================================================
    # 7. Get and visualize results
    # ============================================================
    print("\nVisualizing results...")
    
    results = sim.get_results()
    flux = results['flux']
    stats = results['statistics']
    
    # Create plots
    fig, axs = plt.subplots(1, 3, figsize=(18, 6))
    
    mid = num_bins // 2
    extent = [0, box_size, 0, box_size]
    
    # XY slice at middle Z
    im0 = axs[0].imshow(flux[:, :, mid].T, origin='lower',
                        extent=extent, cmap='inferno')
    axs[0].set_title('Flux distribution (XY plane, Z=middle)')
    axs[0].set_xlabel('X (cm)')
    axs[0].set_ylabel('Y (cm)')
    fig.colorbar(im0, ax=axs[0], fraction=0.046, pad=0.04)
    
    # XZ slice at middle Y
    im1 = axs[1].imshow(flux[:, mid, :].T, origin='lower',
                        extent=extent, cmap='inferno')
    axs[1].set_title('Flux distribution (XZ plane, Y=middle)')
    axs[1].set_xlabel('X (cm)')
    axs[1].set_ylabel('Z (cm)')
    fig.colorbar(im1, ax=axs[1], fraction=0.046, pad=0.04)
    
    # YZ slice at middle X
    im2 = axs[2].imshow(flux[mid, :, :].T, origin='lower',
                        extent=extent, cmap='inferno')
    axs[2].set_title('Flux distribution (YZ plane, X=middle)')
    axs[2].set_xlabel('Y (cm)')
    axs[2].set_ylabel('Z (cm)')
    fig.colorbar(im2, ax=axs[2], fraction=0.046, pad=0.04)
    
    plt.tight_layout()
    plt.savefig('flux_distribution.png', dpi=150)
    print("Flux distribution saved to 'flux_distribution.png'")
    
    # Optionally show plot
    # plt.show()
    
    print("\n" + "="*60)
    print("Example complete!")
    print("="*60)
    print("\nKey features demonstrated:")
    print("  ✓ Modular package structure")
    print("  ✓ Clean, pythonic API")
    print("  ✓ Nuclear data management (ready for ENDF integration)")
    print("  ✓ Hook capabilities for customization")
    print("  ✓ Event and step level access")


if __name__ == "__main__":
    main()
