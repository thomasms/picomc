"""
Particle and event classes for Monte Carlo simulation
"""

import numpy as np
from typing import Optional


class Particle:
    """Represents a neutron particle in the simulation"""

    def __init__(
        self,
        position: np.ndarray,
        direction: np.ndarray,
        energy: float,
        weight: float = 1.0,
        time: float = 0.0,
        is_source: bool = False,
    ):
        """
        Initialize a particle

        Args:
            position: 3D position vector (cm)
            direction: 3D direction unit vector
            energy: Energy in eV
            weight: Statistical weight
            time: Time since start (s)
            is_source: Whether this is a source particle (not a secondary)
        """
        self.position = np.array(position, dtype=float)
        self.direction = np.array(direction, dtype=float)
        # Normalize direction
        norm = np.linalg.norm(self.direction)
        if norm > 0:
            self.direction /= norm
        self.energy = float(energy)
        self.weight = float(weight)
        self.time = float(time)
        self.is_source = is_source
        self.alive = True

    def copy(self) -> "Particle":
        """Create a copy of this particle"""
        p = Particle(
            self.position.copy(),
            self.direction.copy(),
            self.energy,
            self.weight,
            self.time,
            self.is_source,
        )
        p.alive = self.alive
        return p

    def __repr__(self):
        return (
            f"Particle(pos={self.position}, dir={self.direction}, "
            f"E={self.energy:.2e} eV, w={self.weight:.2f}, alive={self.alive})"
        )


class Event:
    """Represents a physics event during particle transport"""

    def __init__(
        self,
        particle: Particle,
        interaction_type: str,
        position: np.ndarray,
        material: Optional[str] = None,
    ):
        """
        Initialize an event

        Args:
            particle: The particle involved in the event
            interaction_type: Type of interaction (scatter, absorb, fission, escape)
            position: Position where event occurred
            material: Material where event occurred
        """
        self.particle = particle
        self.interaction_type = interaction_type
        self.position = np.array(position, dtype=float)
        self.material = material
        self.secondary_particles = []

    def add_secondary(self, particle: Particle):
        """Add a secondary particle from this event"""
        self.secondary_particles.append(particle)

    def __repr__(self):
        return (
            f"Event({self.interaction_type} at {self.position}, "
            f"secondaries={len(self.secondary_particles)})"
        )
