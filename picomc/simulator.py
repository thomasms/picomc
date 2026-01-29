"""
Main simulator orchestrator
"""

import numpy as np
from typing import List, Optional, Callable
from picomc.particle import Particle, Event
from picomc.geometry import Geometry, BoxGeometry, VoxelizedGeometry
from picomc.physics import PhysicsEngine
from picomc.transport import TransportEngine
from picomc.tally import FluxTally, StatisticsCollector
from picomc.data import NuclearDataManager


class Simulator:
    """
    Main Monte Carlo simulator
    
    Provides a pythonic interface with hooks for customization at various levels
    """
    
    def __init__(self, geometry: Geometry, data_manager: NuclearDataManager):
        """
        Initialize simulator
        
        Args:
            geometry: Geometry definition
            data_manager: Nuclear data manager
        """
        self.geometry = geometry
        self.data_manager = data_manager
        
        # Create physics and transport engines
        self.physics = PhysicsEngine(data_manager)
        self.transport = TransportEngine(geometry, self.physics)
        
        # Particle bank and statistics
        self.particle_bank = []
        self.stats = StatisticsCollector()
        
        # Tally (can be set later)
        self.tally = None
        
        # Hooks for event-level customization
        self.pre_event_hook = None
        self.post_event_hook = None
        
    def set_tally(self, tally: FluxTally):
        """Set flux tally for the simulation"""
        self.tally = tally
        self.transport.tally = tally
        
    def add_source_particles(self, particles: List[Particle]):
        """
        Add source particles to the particle bank
        
        Args:
            particles: List of source particles
        """
        self.particle_bank.extend(particles)
        
    def create_point_source(self, position: np.ndarray, num_particles: int,
                           energy: float = 2.0e6) -> List[Particle]:
        """
        Create isotropic point source
        
        Args:
            position: Source position (cm)
            num_particles: Number of source particles
            energy: Source energy in eV (default: 2 MeV)
            
        Returns:
            List of source particles
        """
        particles = []
        for _ in range(num_particles):
            direction = self.physics.sample_isotropic_direction()
            particle = Particle(
                position.copy(),
                direction,
                energy,
                weight=1.0,
                time=0.0
            )
            particles.append(particle)
        return particles
    
    def run(self, num_particles: Optional[int] = None, verbose: bool = True):
        """
        Run the simulation
        
        Args:
            num_particles: Number of particles to simulate (if None, use particle bank)
            verbose: Print progress information
        """
        # If num_particles specified, must have added source
        if num_particles is not None and len(self.particle_bank) == 0:
            raise ValueError("No source particles defined. Use add_source_particles() first.")
        
        # Process particles from bank
        history_count = 0
        
        while self.particle_bank:
            particle = self.particle_bank.pop(0)
            
            # Increment history counter for source particles
            if particle.time == 0.0:  # Source particle
                history_count += 1
                if self.tally:
                    self.tally.increment_history()
                
                if verbose and history_count % 100 == 0:
                    print(f"Processing history {history_count}...")
            
            # Call pre-event hook if defined
            if self.pre_event_hook:
                self.pre_event_hook(particle)
            
            # Track particle
            self.stats.record_neutron()
            events = self.transport.transport_particle(particle)
            
            # Process events and collect secondaries
            for event in events:
                # Record statistics
                if event.interaction_type == 'escape':
                    self.stats.record_escape()
                elif event.interaction_type == 'capture':
                    self.stats.record_absorption()
                elif event.interaction_type == 'fission':
                    self.stats.record_fission()
                    # Add secondary particles to bank
                    self.particle_bank.extend(event.secondary_particles)
            
            # Call post-event hook if defined
            if self.post_event_hook:
                self.post_event_hook(particle, events)
            
            # Stop if we've processed enough source particles
            if num_particles is not None and history_count >= num_particles:
                # Clear remaining particle bank
                self.particle_bank.clear()
                break
        
        if verbose:
            print(f"\nSimulation complete!")
            self.stats.print_summary()
    
    def get_results(self) -> dict:
        """
        Get simulation results
        
        Returns:
            Dictionary with statistics and tally data
        """
        results = {
            'statistics': self.stats.get_summary()
        }
        
        if self.tally:
            results['flux'] = self.tally.get_normalized_flux()
        
        return results
    
    def reset(self):
        """Reset simulation state"""
        self.particle_bank.clear()
        self.stats = StatisticsCollector()
        if self.tally:
            self.tally.tally.fill(0)
            self.tally.num_histories = 0
