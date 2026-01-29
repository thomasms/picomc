"""
Geometry classes for defining simulation spaces
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Tuple, Optional


class Geometry(ABC):
    """Abstract base class for geometry definitions"""
    
    @abstractmethod
    def is_inside(self, position: np.ndarray) -> bool:
        """Check if position is inside the geometry"""
        pass
    
    @abstractmethod
    def distance_to_boundary(self, position: np.ndarray, direction: np.ndarray) -> float:
        """Calculate distance to geometry boundary along direction"""
        pass
    
    @abstractmethod
    def get_material(self, position: np.ndarray) -> Optional[str]:
        """Get material at given position"""
        pass


class BoxGeometry(Geometry):
    """Simple box geometry"""
    
    def __init__(self, size: float, material: str = "default"):
        """
        Initialize a box geometry
        
        Args:
            size: Size of the cubic box (cm)
            material: Material filling the box
        """
        self.size = float(size)
        self.material = material
        
    def is_inside(self, position: np.ndarray) -> bool:
        """Check if position is inside the box"""
        return np.all(position >= 0) and np.all(position <= self.size)
    
    def distance_to_boundary(self, position: np.ndarray, direction: np.ndarray) -> float:
        """
        Calculate distance to box boundary along direction
        
        Returns minimum positive distance to any boundary
        """
        distances = []
        for i in range(3):
            if direction[i] > 1e-10:
                dist_bound = (self.size - position[i]) / direction[i]
                if dist_bound > 0:
                    distances.append(dist_bound)
            elif direction[i] < -1e-10:
                dist_bound = -position[i] / direction[i]
                if dist_bound > 0:
                    distances.append(dist_bound)
        
        if not distances:
            return np.inf
        
        return min(distances)
    
    def get_material(self, position: np.ndarray) -> Optional[str]:
        """Get material at position (if inside)"""
        if self.is_inside(position):
            return self.material
        return None


class VoxelizedGeometry(Geometry):
    """Voxelized geometry for tally scoring"""
    
    def __init__(self, box_geometry: BoxGeometry, num_bins: int):
        """
        Initialize voxelized geometry
        
        Args:
            box_geometry: Underlying box geometry
            num_bins: Number of voxels per dimension
        """
        self.box = box_geometry
        self.num_bins = num_bins
        self.voxel_size = box_geometry.size / num_bins
        
    def is_inside(self, position: np.ndarray) -> bool:
        """Check if position is inside"""
        return self.box.is_inside(position)
    
    def distance_to_boundary(self, position: np.ndarray, direction: np.ndarray) -> float:
        """Distance to boundary"""
        return self.box.distance_to_boundary(position, direction)
    
    def get_material(self, position: np.ndarray) -> Optional[str]:
        """Get material at position"""
        return self.box.get_material(position)
    
    def get_voxel_indices(self, position: np.ndarray) -> Tuple[int, int, int]:
        """
        Get voxel indices for a position
        
        Returns tuple of (ix, iy, iz) clamped to valid range
        """
        ix = min(max(int(position[0] / self.voxel_size), 0), self.num_bins - 1)
        iy = min(max(int(position[1] / self.voxel_size), 0), self.num_bins - 1)
        iz = min(max(int(position[2] / self.voxel_size), 0), self.num_bins - 1)
        return ix, iy, iz
