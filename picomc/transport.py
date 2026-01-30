"""
Transport logic for particle tracking
"""

from typing import List, Optional
from picomc.particle import Particle, Event
from picomc.geometry import Geometry
from picomc.physics import PhysicsEngine
from picomc.tally import FluxTally


class TransportEngine:
    """
    Engine for transporting particles through geometry

    Supports hooks for customization at the step level
    """

    def __init__(
        self, geometry: Geometry, physics: PhysicsEngine, tally: Optional[FluxTally] = None
    ):
        """
        Initialize transport engine

        Args:
            geometry: Geometry definition
            physics: Physics engine
            tally: Optional flux tally
        """
        self.geometry = geometry
        self.physics = physics
        self.tally = tally

        # Hooks for customization
        self.pre_step_hook = None
        self.post_step_hook = None

    def transport_particle(self, particle: Particle) -> List[Event]:
        """
        Transport a single particle until it dies or escapes

        Args:
            particle: Particle to transport

        Returns:
            List of events that occurred during transport
        """
        events = []

        while particle.alive:
            # Check if particle is inside geometry
            if not self.geometry.is_inside(particle.position):
                # Particle already outside - create escape event
                event = Event(particle, "escape", particle.position.copy())
                events.append(event)
                particle.alive = False
                break

            # Call pre-step hook if defined
            if self.pre_step_hook:
                self.pre_step_hook(particle)

            # Get material at current position
            material = self.geometry.get_material(particle.position)
            if material is None:
                # Outside material region - escape
                event = Event(particle, "escape", particle.position.copy())
                events.append(event)
                particle.alive = False
                break

            # Sample distance to next interaction
            dist_interaction = self.physics.sample_distance(particle, material)

            # Calculate distance to boundary
            dist_boundary = self.geometry.distance_to_boundary(
                particle.position, particle.direction
            )

            # Determine if particle reaches boundary or interacts
            if dist_boundary < dist_interaction:
                # Particle escapes before interaction
                new_pos = particle.position + particle.direction * dist_boundary

                # Score flux for this track segment
                if self.tally:
                    self.tally.score_track(particle.position, new_pos, particle.weight)

                # Update particle time
                velocity = self.physics.get_velocity(particle.energy)
                particle.time += dist_boundary / velocity

                # Create escape event
                event = Event(particle, "escape", new_pos, material)
                events.append(event)
                particle.alive = False

            else:
                # Particle interacts
                new_pos = particle.position + particle.direction * dist_interaction

                # Score flux for this track segment
                if self.tally:
                    self.tally.score_track(particle.position, new_pos, particle.weight)

                # Update particle position and time
                velocity = self.physics.get_velocity(particle.energy)
                particle.time += dist_interaction / velocity
                particle.position = new_pos

                # Process interaction
                event = self.physics.process_interaction(particle, material)
                events.append(event)

            # Call post-step hook if defined
            if self.post_step_hook:
                self.post_step_hook(particle, events[-1])

        return events
