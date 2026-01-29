"""
Unit tests for particle and event classes
"""

import pytest
import numpy as np
from picomc.particle import Particle, Event


class TestParticle:
    """Unit tests for Particle class"""

    def test_particle_initialization(self):
        """Test particle can be initialized with basic parameters"""
        position = np.array([1.0, 2.0, 3.0])
        direction = np.array([1.0, 0.0, 0.0])
        energy = 2.0e6

        particle = Particle(position, direction, energy, is_source=True)

        assert np.allclose(particle.position, position)
        assert np.allclose(particle.direction, direction)
        assert particle.energy == energy
        assert particle.alive
        assert particle.is_source

    def test_particle_direction_normalization(self):
        """Test that direction vector is normalized"""
        position = np.array([0.0, 0.0, 0.0])
        direction = np.array([3.0, 4.0, 0.0])  # Not normalized
        energy = 1.0e6

        particle = Particle(position, direction, energy)

        # Direction should be normalized to unit vector
        assert abs(np.linalg.norm(particle.direction) - 1.0) < 1e-10

    def test_particle_copy(self):
        """Test particle copying creates independent copy"""
        original = Particle(
            np.array([1.0, 2.0, 3.0]),
            np.array([1.0, 0.0, 0.0]),
            2.0e6,
            weight=0.5,
            time=1.0,
            is_source=False,
        )

        copy = original.copy()

        # Check values are equal
        assert np.allclose(copy.position, original.position)
        assert np.allclose(copy.direction, original.direction)
        assert copy.energy == original.energy
        assert copy.weight == original.weight
        assert copy.time == original.time
        assert copy.is_source == original.is_source

        # Check they are independent
        copy.position[0] = 999.0
        assert original.position[0] != 999.0

    def test_particle_default_values(self):
        """Test particle default parameter values"""
        particle = Particle(np.array([0.0, 0.0, 0.0]), np.array([1.0, 0.0, 0.0]), 1.0e6)

        assert particle.weight == 1.0
        assert particle.time == 0.0
        assert particle.is_source == False
        assert particle.alive == True

    def test_particle_repr(self):
        """Test particle string representation"""
        particle = Particle(
            np.array([1.0, 2.0, 3.0]), np.array([1.0, 0.0, 0.0]), 2.0e6, is_source=True
        )

        repr_str = repr(particle)
        assert "Particle" in repr_str
        assert "2.00e+06" in repr_str or "2e+06" in repr_str


class TestEvent:
    """Unit tests for Event class"""

    @pytest.fixture
    def test_particle(self):
        """Create a test particle"""
        return Particle(np.array([1.0, 2.0, 3.0]), np.array([1.0, 0.0, 0.0]), 2.0e6)

    def test_event_initialization(self, test_particle):
        """Test event can be initialized"""
        position = np.array([5.0, 6.0, 7.0])
        event = Event(test_particle, "elastic", position, material="uranium")

        assert event.particle == test_particle
        assert event.interaction_type == "elastic"
        assert np.allclose(event.position, position)
        assert event.material == "uranium"
        assert len(event.secondary_particles) == 0

    def test_add_secondary(self, test_particle):
        """Test adding secondary particles"""
        event = Event(test_particle, "fission", test_particle.position.copy())

        secondary1 = Particle(np.array([1.0, 2.0, 3.0]), np.array([0.0, 1.0, 0.0]), 1.0e6)
        secondary2 = Particle(np.array([1.0, 2.0, 3.0]), np.array([0.0, 0.0, 1.0]), 1.5e6)

        event.add_secondary(secondary1)
        event.add_secondary(secondary2)

        assert len(event.secondary_particles) == 2
        assert event.secondary_particles[0] == secondary1
        assert event.secondary_particles[1] == secondary2

    def test_event_repr(self, test_particle):
        """Test event string representation"""
        event = Event(test_particle, "fission", np.array([1.0, 2.0, 3.0]))

        repr_str = repr(event)
        assert "Event" in repr_str
        assert "fission" in repr_str

    def test_event_interaction_types(self, test_particle):
        """Test various interaction types can be created"""
        types = ["elastic", "capture", "fission", "escape"]

        for interaction_type in types:
            event = Event(test_particle, interaction_type, test_particle.position.copy())
            assert event.interaction_type == interaction_type

    def test_event_position_copy(self, test_particle):
        """Test that event position is independent of input"""
        position = np.array([5.0, 6.0, 7.0])
        event = Event(test_particle, "elastic", position)

        # Modify original position
        position[0] = 999.0

        # Event position should be unchanged
        assert event.position[0] != 999.0
