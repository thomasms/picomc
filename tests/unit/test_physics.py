"""
Unit tests for physics interactions
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock
from picomc.physics import PhysicsEngine, NEUTRON_MASS_ENERGY_FACTOR
from picomc.particle import Particle
from picomc.data import NuclearDataManager


class TestPhysicsConstants:
    """Test physical constants"""

    def test_neutron_mass_energy_factor(self):
        """Test neutron mass-energy factor is reasonable"""
        assert NEUTRON_MASS_ENERGY_FACTOR > 0
        assert NEUTRON_MASS_ENERGY_FACTOR < 1e-7


class TestPhysicsEngine:
    """Unit tests for PhysicsEngine class"""

    @pytest.fixture
    def data_manager(self):
        """Create a mock data manager"""
        dm = NuclearDataManager()
        dm.add_material("test_material", number_density=0.05)
        return dm

    @pytest.fixture
    def physics_engine(self, data_manager):
        """Create physics engine with test data"""
        return PhysicsEngine(data_manager)

    @pytest.fixture
    def test_particle(self):
        """Create a test particle"""
        return Particle(
            position=np.array([0.0, 0.0, 0.0]),
            direction=np.array([1.0, 0.0, 0.0]),
            energy=2.0e6,
            is_source=True,
        )

    def test_sample_distance_positive(self, physics_engine, test_particle):
        """Test that sampled distance is positive"""
        dist = physics_engine.sample_distance(test_particle, "test_material")
        assert dist > 0

    def test_sample_distance_with_zero_xs(self, physics_engine, test_particle):
        """Test behavior with zero total cross section"""
        # Create mock data manager with zero cross sections
        mock_dm = Mock()
        mock_dm.get_macroscopic_xs.return_value = {
            "total": 0.0,
            "elastic": 0.0,
            "capture": 0.0,
            "fission": 0.0,
        }
        engine = PhysicsEngine(mock_dm)

        dist = engine.sample_distance(test_particle, "test_material")
        assert dist == np.inf

    def test_sample_interaction_type_returns_valid(self, physics_engine, test_particle):
        """Test that interaction type is one of the valid options"""
        interaction = physics_engine.sample_interaction_type(test_particle, "test_material")
        assert interaction in ["elastic", "capture", "fission"]

    def test_sample_isotropic_direction(self, physics_engine):
        """Test isotropic direction sampling"""
        direction = physics_engine.sample_isotropic_direction()

        # Check unit vector
        assert abs(np.linalg.norm(direction) - 1.0) < 1e-10

        # Check components are reasonable
        assert -1.0 <= direction[0] <= 1.0
        assert -1.0 <= direction[1] <= 1.0
        assert -1.0 <= direction[2] <= 1.0

    def test_sample_fission_neutrons_positive(self, physics_engine, test_particle, random_seed):
        """Test that fission neutron count is positive"""
        nu = physics_engine.sample_fission_neutrons(test_particle.energy, "test_material")
        assert nu > 0
        assert isinstance(nu, (int, np.integer))

    def test_sample_fission_energy_in_range(self, physics_engine, test_particle, random_seed):
        """Test that fission energy is in reasonable range"""
        energy = physics_engine.sample_fission_energy(test_particle.energy, "test_material")
        # Fission energies typically between 0.1 and 10 MeV
        assert energy > 0
        assert energy < 20e6  # 20 MeV is very high for fission neutrons

    def test_get_velocity_calculation(self, physics_engine):
        """Test velocity calculation from energy"""
        energy = 2.0e6  # eV
        velocity = physics_engine.get_velocity(energy)

        # Check that velocity is positive
        assert velocity > 0

        # Check that E = factor * v^2
        calculated_energy = NEUTRON_MASS_ENERGY_FACTOR * velocity**2
        assert abs(calculated_energy - energy) < 1e-5

    def test_process_interaction_elastic(self, physics_engine, test_particle):
        """Test elastic scattering changes direction"""
        # Mock to always return elastic
        physics_engine.sample_interaction_type = Mock(return_value="elastic")

        original_energy = test_particle.energy
        event = physics_engine.process_interaction(test_particle, "test_material")

        assert event.interaction_type == "elastic"
        assert test_particle.energy == original_energy  # Energy unchanged in elastic
        assert test_particle.alive  # Particle still alive

    def test_process_interaction_capture(self, physics_engine, test_particle):
        """Test capture kills particle"""
        # Mock to always return capture
        physics_engine.sample_interaction_type = Mock(return_value="capture")

        event = physics_engine.process_interaction(test_particle, "test_material")

        assert event.interaction_type == "capture"
        assert not test_particle.alive  # Particle should be dead

    def test_process_interaction_fission(self, physics_engine, test_particle, random_seed):
        """Test fission creates secondaries"""
        # Mock to always return fission
        physics_engine.sample_interaction_type = Mock(return_value="fission")

        event = physics_engine.process_interaction(test_particle, "test_material")

        assert event.interaction_type == "fission"
        assert not test_particle.alive  # Particle should be dead
        assert len(event.secondary_particles) > 0  # Should have secondaries

    def test_hooks_are_called(self, physics_engine, test_particle):
        """Test that pre/post interaction hooks are called"""
        pre_hook_called = []
        post_hook_called = []

        def pre_hook(particle, material):
            pre_hook_called.append(True)

        def post_hook(event):
            post_hook_called.append(True)

        physics_engine.pre_interaction_hook = pre_hook
        physics_engine.post_interaction_hook = post_hook

        physics_engine.process_interaction(test_particle, "test_material")

        assert len(pre_hook_called) == 1
        assert len(post_hook_called) == 1
