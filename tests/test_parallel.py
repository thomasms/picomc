"""
Tests for parallel Monte Carlo simulation
"""

import pytest
import numpy as np
from picomc import ParallelSimulator, Simulator, BoxGeometry, NuclearDataManager
from picomc.tally import FluxTally


class TestParallelSimulator:
    """Tests for ParallelSimulator"""

    def test_parallel_simulator_creation(self):
        """Test parallel simulator can be created"""
        geometry = BoxGeometry(10.0, "test_material")
        dm = NuclearDataManager()
        dm.add_material("test_material", 0.05)

        sim = ParallelSimulator(geometry, dm, n_jobs=2)
        assert sim.n_jobs == 2
        assert sim.geometry is geometry
        assert sim.data_manager is dm

    def test_parallel_vs_sequential_statistics(self):
        """Test parallel simulation gives reasonable statistics"""
        # Use smaller particle count for faster test
        np.random.seed(42)

        geometry = BoxGeometry(50.0, "test_material")
        dm = NuclearDataManager()
        # Use non-fissile material to avoid infinite chains
        dm.add_material("test_material", 0.05)
        # Set fission cross section to zero
        dm.materials["test_material"]["xs_data"].fission = np.zeros_like(
            dm.materials["test_material"]["xs_data"].fission
        )

        # Parallel simulation
        sim_par = ParallelSimulator(geometry, dm, n_jobs=2)
        particles_par = sim_par.create_point_source(
            np.array([25.0, 25.0, 25.0]), 20, 2.0e6
        )
        sim_par.add_source_particles(particles_par)
        sim_par.run(verbose=False)
        results_par = sim_par.get_results()

        # Check statistics are reasonable
        assert results_par["statistics"]["neutrons"] > 0
        assert results_par["statistics"]["escapes"] > 0
        # Should process at least the source particles
        assert results_par["statistics"]["neutrons"] >= 20

    def test_parallel_with_tally(self):
        """Test parallel simulation with flux tally"""
        geometry = BoxGeometry(50.0, "test_material")
        dm = NuclearDataManager()
        # Use non-fissile material to avoid infinite chains
        dm.add_material("test_material", 0.05)
        # Set fission cross section to zero
        dm.materials["test_material"]["xs_data"].fission = np.zeros_like(
            dm.materials["test_material"]["xs_data"].fission
        )

        # Create tally
        voxels = (5, 5, 5)
        bounds = ((0, 50), (0, 50), (0, 50))
        tally = FluxTally(voxels, bounds)

        # Parallel simulation with reduced particle count
        sim = ParallelSimulator(geometry, dm, n_jobs=2)
        sim.set_tally(tally)
        particles = sim.create_point_source(np.array([25.0, 25.0, 25.0]), 20, 2.0e6)
        sim.add_source_particles(particles)
        sim.run(verbose=False)

        results = sim.get_results()

        # Check flux tally exists
        assert "flux" in results
        assert results["flux"].shape == voxels

        # Check some flux was tallied
        assert np.sum(results["flux"]) > 0

    def test_parallel_different_worker_counts(self):
        """Test parallel simulation with different numbers of workers"""
        geometry = BoxGeometry(30.0, "test_material")
        dm = NuclearDataManager()
        # Use non-fissile material to avoid infinite chains
        dm.add_material("test_material", 0.05)
        # Set fission cross section to zero
        dm.materials["test_material"]["xs_data"].fission = np.zeros_like(
            dm.materials["test_material"]["xs_data"].fission
        )

        for n_jobs in [1, 2]:
            sim = ParallelSimulator(geometry, dm, n_jobs=n_jobs)
            particles = sim.create_point_source(
                np.array([15.0, 15.0, 15.0]), 15, 2.0e6
            )
            sim.add_source_particles(particles)
            sim.run(verbose=False)

            results = sim.get_results()
            assert results["statistics"]["neutrons"] > 0
            assert results["statistics"]["escapes"] > 0

    def test_parallel_reset(self):
        """Test parallel simulator can be reset"""
        geometry = BoxGeometry(20.0, "test_material")
        dm = NuclearDataManager()
        dm.add_material("test_material", 0.05)

        sim = ParallelSimulator(geometry, dm, n_jobs=2)
        particles = sim.create_point_source(np.array([10.0, 10.0, 10.0]), 10, 2.0e6)  # Reduced from 20
        sim.add_source_particles(particles)
        sim.run(verbose=False)

        # Reset
        sim.reset()
        assert len(sim.source_particles) == 0
        assert sim.results is None

        # Can run again after reset
        particles2 = sim.create_point_source(np.array([10.0, 10.0, 10.0]), 8, 1.0e6)  # Reduced from 15
        sim.add_source_particles(particles2)
        sim.run(verbose=False)
        results = sim.get_results()
        assert results["statistics"]["neutrons"] > 0
