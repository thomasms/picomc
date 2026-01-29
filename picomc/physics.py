"""
Physics interactions for neutron transport
"""

import numpy as np
from typing import Dict, Optional, List
from picomc.particle import Particle, Event
from picomc.data import NuclearDataManager

# Physical constants
NEUTRON_MASS_ENERGY_FACTOR = 5.227e-9  # E(eV) = NEUTRON_MASS_ENERGY_FACTOR * v(cm/s)^2
DEFAULT_NU = 2.5  # Average neutrons per fission for U-235
FISSION_ENERGY_SCALE = 1.0e6  # eV, exponential scale for fission spectrum
FISSION_ENERGY_MIN = 0.5e6  # eV, minimum fission neutron energy


class PhysicsEngine:
    """
    Engine for handling physics interactions

    Supports customization through inheritance or callback hooks
    """

    def __init__(self, data_manager: NuclearDataManager):
        """
        Initialize physics engine

        Args:
            data_manager: Nuclear data manager for cross sections
        """
        self.data_manager = data_manager

        # Hooks for customization (can be overridden)
        self.pre_interaction_hook = None
        self.post_interaction_hook = None

    def sample_distance(self, particle: Particle, material: str) -> float:
        """
        Sample distance to next interaction

        Args:
            particle: Current particle
            material: Material particle is in

        Returns:
            Distance to next interaction (cm)
        """
        xs = self.data_manager.get_macroscopic_xs(material, particle.energy)
        sigma_t = xs["total"]

        if sigma_t <= 0:
            return np.inf

        xi = np.random.random()
        return -np.log(xi) / sigma_t

    def sample_interaction_type(self, particle: Particle, material: str) -> str:
        """
        Sample type of interaction

        Args:
            particle: Current particle
            material: Material particle is in

        Returns:
            Interaction type: 'elastic', 'capture', or 'fission'
        """
        xs = self.data_manager.get_macroscopic_xs(material, particle.energy)

        sigma_t = xs["total"]
        if sigma_t <= 0:
            return "elastic"

        xi = np.random.random()

        # Sample interaction type based on relative cross sections
        if xi < xs["elastic"] / sigma_t:
            return "elastic"
        elif xi < (xs["elastic"] + xs["capture"]) / sigma_t:
            return "capture"
        else:
            return "fission"

    def process_interaction(self, particle: Particle, material: str) -> Event:
        """
        Process an interaction and create event with secondaries

        Args:
            particle: Particle undergoing interaction
            material: Material where interaction occurs

        Returns:
            Event object containing interaction details
        """
        # Call pre-interaction hook if defined
        if self.pre_interaction_hook:
            self.pre_interaction_hook(particle, material)

        interaction_type = self.sample_interaction_type(particle, material)
        event = Event(particle, interaction_type, particle.position.copy(), material)

        if interaction_type == "elastic":
            # Elastic scattering - change direction, may change energy
            new_direction = self.sample_isotropic_direction()
            particle.direction = new_direction
            # For now, keep energy same (elastic in CoM frame)
            # Could add energy loss for realistic scattering

        elif interaction_type == "capture":
            # Absorption - particle dies
            particle.alive = False

        else:  # fission
            # Fission - particle dies, create secondaries
            particle.alive = False
            num_neutrons = self.sample_fission_neutrons()

            for _ in range(num_neutrons):
                # Create fission neutrons
                direction = self.sample_isotropic_direction()
                # Fission neutrons typically born around 2 MeV
                energy = self.sample_fission_energy()

                secondary = Particle(
                    particle.position.copy(),
                    direction,
                    energy,
                    particle.weight,
                    particle.time,
                    is_source=False,  # Fission secondaries are not source particles
                )
                event.add_secondary(secondary)

        # Call post-interaction hook if defined
        if self.post_interaction_hook:
            self.post_interaction_hook(event)

        return event

    def sample_isotropic_direction(self) -> np.ndarray:
        """Sample isotropic direction in 3D"""
        phi = 2 * np.pi * np.random.random()
        cos_theta = 2 * np.random.random() - 1
        sin_theta = np.sqrt(1 - cos_theta**2)

        dx = sin_theta * np.cos(phi)
        dy = sin_theta * np.sin(phi)
        dz = cos_theta

        return np.array([dx, dy, dz])

    def sample_fission_neutrons(self) -> int:
        """
        Sample number of fission neutrons (nu)

        Uses Poisson distribution with DEFAULT_NU.
        In reality, should use nubar from ENDF data.
        """
        return np.random.poisson(DEFAULT_NU)

    def sample_fission_energy(self) -> float:
        """
        Sample fission neutron energy

        Uses simplified exponential + offset distribution.
        Real implementation should use Watt spectrum from ENDF data.

        Returns:
            Energy in eV
        """
        return np.random.exponential(FISSION_ENERGY_SCALE) + FISSION_ENERGY_MIN

    def get_velocity(self, energy: float) -> float:
        """
        Get neutron velocity from energy

        Args:
            energy: Energy in eV

        Returns:
            Velocity in cm/s
        """
        # E = 0.5 * m * v^2
        # For neutrons: E(eV) = NEUTRON_MASS_ENERGY_FACTOR * v(cm/s)^2
        return np.sqrt(energy / NEUTRON_MASS_ENERGY_FACTOR)
