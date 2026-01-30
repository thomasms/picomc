"""
Tally and scoring classes
"""

import numpy as np
from typing import Optional
from picomc.geometry import VoxelizedGeometry


class FluxTally:
    """Flux tally on a voxelized geometry"""

    def __init__(self, geometry: VoxelizedGeometry):
        """
        Initialize flux tally

        Args:
            geometry: Voxelized geometry for scoring
        """
        self.geometry = geometry
        self.num_bins = geometry.num_bins
        self.voxel_volume = geometry.voxel_size**3

        # Initialize tally array
        self.tally = np.zeros((self.num_bins, self.num_bins, self.num_bins))
        self.num_histories = 0

    def score_track(self, pos_start: np.ndarray, pos_end: np.ndarray, weight: float = 1.0):
        """
        Score a particle track for flux

        Args:
            pos_start: Starting position
            pos_end: Ending position
            weight: Particle weight
        """
        # Simple approximation: score track length in starting voxel
        # More sophisticated ray tracing could be implemented
        track_length = np.linalg.norm(pos_end - pos_start)

        if self.geometry.is_inside(pos_start):
            ix, iy, iz = self.geometry.get_voxel_indices(pos_start)
            self.tally[ix, iy, iz] += track_length * weight

    def increment_history(self):
        """Increment history counter"""
        self.num_histories += 1

    def get_normalized_flux(self) -> np.ndarray:
        """
        Get normalized flux tally

        Returns:
            Flux per unit volume per source particle
        """
        if self.num_histories == 0:
            return self.tally.copy()

        return self.tally / (self.voxel_volume * self.num_histories)

    def get_slice(self, axis: str, index: Optional[int] = None) -> np.ndarray:
        """
        Get a 2D slice of the flux

        Args:
            axis: Axis to slice ('x', 'y', or 'z')
            index: Index along axis (default: middle)

        Returns:
            2D array of flux values
        """
        flux = self.get_normalized_flux()

        if index is None:
            index = self.num_bins // 2

        if axis.lower() == "x":
            return flux[index, :, :]
        elif axis.lower() == "y":
            return flux[:, index, :]
        elif axis.lower() == "z":
            return flux[:, :, index]
        else:
            raise ValueError(f"Invalid axis: {axis}")


class StatisticsCollector:
    """Collector for simulation statistics"""

    def __init__(self):
        """Initialize statistics collector"""
        self.absorbed = 0
        self.escaped = 0
        self.fission_events = 0
        self.total_neutrons = 0

    def record_escape(self):
        """Record particle escape"""
        self.escaped += 1

    def record_absorption(self):
        """Record particle absorption"""
        self.absorbed += 1

    def record_fission(self):
        """Record fission event"""
        self.fission_events += 1

    def record_neutron(self):
        """Record neutron tracked"""
        self.total_neutrons += 1

    def get_summary(self) -> dict:
        """Get summary statistics"""
        total = self.total_neutrons
        if total == 0:
            return {
                "total_neutrons": 0,
                "absorbed": 0,
                "escaped": 0,
                "fission_events": 0,
                "absorption_fraction": 0.0,
                "escape_fraction": 0.0,
            }

        return {
            "total_neutrons": total,
            "absorbed": self.absorbed,
            "escaped": self.escaped,
            "fission_events": self.fission_events,
            "absorption_fraction": self.absorbed / total,
            "escape_fraction": self.escaped / total,
        }

    def print_summary(self):
        """Print summary statistics"""
        summary = self.get_summary()
        print(f"Total neutrons tracked: {summary['total_neutrons']}")
        print(f"Absorbed: {summary['absorbed']} ({summary['absorption_fraction'] * 100:.2f}%)")
        print(f"Escaped: {summary['escaped']} ({summary['escape_fraction'] * 100:.2f}%)")
        print(f"Fission events: {summary['fission_events']}")
