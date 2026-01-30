"""
Parallel Monte Carlo simulation using multiprocessing
"""

import numpy as np
from multiprocessing import Pool, cpu_count
from typing import List, Optional
from picomc.simulator import Simulator
from picomc.particle import Particle
from picomc.geometry import Geometry
from picomc.data import NuclearDataManager
from picomc.tally import FluxTally, StatisticsCollector


def _run_particle_batch(args):
    """
    Worker function to process a batch of particles
    
    This function runs in a separate process and returns aggregated results.
    
    Args:
        args: Tuple of (geometry, data_manager, particles, tally_config, verbose_worker)
    
    Returns:
        Dictionary with statistics and tally data from this batch
    """
    geometry, data_manager, particles, tally_config, verbose_worker = args
    
    # Create a local simulator in this worker process
    sim = Simulator(geometry, data_manager)
    
    # Set up tally if provided
    if tally_config is not None:
        voxels, bounds = tally_config
        tally = FluxTally(voxels, bounds)
        sim.set_tally(tally)
    
    # Add particles and run
    sim.add_source_particles(particles)
    sim.run(verbose=verbose_worker)
    
    # Return results from this batch
    return sim.get_results()


class ParallelSimulator:
    """
    Parallel Monte Carlo simulator using multiprocessing
    
    Distributes particle histories across multiple CPU cores for faster execution.
    Each worker process simulates a batch of particles independently, then results
    are aggregated.
    """
    
    def __init__(
        self,
        geometry: Geometry,
        data_manager: NuclearDataManager,
        n_jobs: Optional[int] = None,
    ):
        """
        Initialize parallel simulator
        
        Args:
            geometry: Geometry definition
            data_manager: Nuclear data manager
            n_jobs: Number of worker processes (default: cpu_count() - 1)
        """
        self.geometry = geometry
        self.data_manager = data_manager
        
        # Determine number of workers
        if n_jobs is None:
            self.n_jobs = max(1, cpu_count() - 1)
        else:
            self.n_jobs = max(1, min(n_jobs, cpu_count()))
        
        # Storage for source particles
        self.source_particles = []
        
        # Tally configuration (will be recreated in each worker)
        self.tally_config = None
        
        # Results storage
        self.results = None
    
    def set_tally(self, tally: FluxTally):
        """
        Configure tally for parallel simulation
        
        The tally will be recreated in each worker process.
        
        Args:
            tally: FluxTally configuration
        """
        self.tally_config = (tally.voxels, tally.bounds)
    
    def add_source_particles(self, particles: List[Particle]):
        """
        Add source particles for simulation
        
        Args:
            particles: List of source particles
        """
        self.source_particles.extend(particles)
    
    def create_point_source(
        self, position: np.ndarray, num_particles: int, energy: float = 2.0e6
    ) -> List[Particle]:
        """
        Create isotropic point source
        
        Args:
            position: Source position (cm)
            num_particles: Number of source particles
            energy: Source energy in eV (default: 2 MeV)
        
        Returns:
            List of source particles
        """
        # Use a temporary simulator to create particles
        temp_sim = Simulator(self.geometry, self.data_manager)
        return temp_sim.create_point_source(position, num_particles, energy)
    
    def run(self, verbose: bool = True):
        """
        Run parallel simulation
        
        Distributes particles across worker processes and aggregates results.
        
        Args:
            verbose: Print progress information
        """
        if len(self.source_particles) == 0:
            raise ValueError("No source particles defined")
        
        if verbose:
            print(f"Running parallel simulation with {self.n_jobs} workers...")
            print(f"Total particles: {len(self.source_particles)}")
        
        # Split particles into batches for workers
        batch_size = len(self.source_particles) // self.n_jobs
        if batch_size == 0:
            batch_size = 1
        
        batches = []
        for i in range(0, len(self.source_particles), batch_size):
            batch = self.source_particles[i : i + batch_size]
            batches.append(batch)
        
        if verbose:
            print(f"Created {len(batches)} batches (avg {batch_size} particles/batch)")
        
        # Prepare arguments for workers (verbose_worker=False to avoid clutter)
        worker_args = [
            (
                self.geometry,
                self.data_manager,
                batch,
                self.tally_config,
                False,  # verbose_worker
            )
            for batch in batches
        ]
        
        # Run in parallel using process pool
        with Pool(processes=self.n_jobs) as pool:
            batch_results = pool.map(_run_particle_batch, worker_args)
        
        # Aggregate results from all batches
        self.results = self._aggregate_results(batch_results)
        
        if verbose:
            print("\nParallel simulation complete!")
            self._print_summary()
    
    def _aggregate_results(self, batch_results: List[dict]) -> dict:
        """
        Aggregate results from multiple worker batches
        
        Args:
            batch_results: List of result dictionaries from workers
        
        Returns:
            Aggregated results dictionary
        """
        # Aggregate statistics
        total_stats = {
            "neutrons": 0,
            "escapes": 0,
            "absorptions": 0,
            "fissions": 0,
        }
        
        for result in batch_results:
            stats = result["statistics"]
            total_stats["neutrons"] += stats["neutrons"]
            total_stats["escapes"] += stats["escapes"]
            total_stats["absorptions"] += stats["absorptions"]
            total_stats["fissions"] += stats["fissions"]
        
        aggregated = {"statistics": total_stats}
        
        # Aggregate flux tally if present
        if "flux" in batch_results[0]:
            # Sum flux from all batches
            total_flux = np.zeros_like(batch_results[0]["flux"])
            for result in batch_results:
                total_flux += result["flux"]
            aggregated["flux"] = total_flux
        
        return aggregated
    
    def _print_summary(self):
        """Print simulation summary"""
        if self.results is None:
            return
        
        stats = self.results["statistics"]
        print("\nStatistics:")
        print(f"  Total neutrons: {stats['neutrons']}")
        print(f"  Escapes: {stats['escapes']}")
        print(f"  Absorptions: {stats['absorptions']}")
        print(f"  Fissions: {stats['fissions']}")
    
    def get_results(self) -> dict:
        """
        Get simulation results
        
        Returns:
            Dictionary with aggregated statistics and tally data
        """
        if self.results is None:
            raise RuntimeError("No results available. Run simulation first.")
        return self.results
    
    def reset(self):
        """Reset simulation state"""
        self.source_particles.clear()
        self.results = None
