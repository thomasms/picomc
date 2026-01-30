"""
CSG (Constructive Solid Geometry) support for PicoMC

Implements CSG geometry similar to Serpent and OpenMC codes:
- Surface-based geometry definition
- Cell-based regions with boolean operations
- Common primitives: planes, spheres, cylinders
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from enum import Enum

# Geometric tolerances
SURFACE_TOLERANCE = 1e-10  # Tolerance for surface evaluation (cm)
DISTANCE_TOLERANCE = 1e-10  # Minimum valid distance for intersections (cm)


class SurfaceSense(Enum):
    """Sense of a surface (positive or negative side)"""

    NEGATIVE = -1
    ON = 0
    POSITIVE = 1


class Surface(ABC):
    """Abstract base class for geometric surfaces"""

    def __init__(self, surface_id: int):
        """
        Initialize surface

        Args:
            surface_id: Unique identifier for this surface
        """
        self.id = surface_id

    @abstractmethod
    def evaluate(self, position: np.ndarray) -> float:
        """
        Evaluate surface equation at position

        Returns:
            >0 if on positive side, <0 if on negative side, =0 if on surface
        """
        pass

    @abstractmethod
    def distance(self, position: np.ndarray, direction: np.ndarray) -> float:
        """
        Calculate distance to surface along direction

        Returns:
            Distance to surface (inf if no intersection)
        """
        pass

    def sense(self, position: np.ndarray) -> SurfaceSense:
        """Determine which side of surface the position is on"""
        val = self.evaluate(position)
        if abs(val) < SURFACE_TOLERANCE:
            return SurfaceSense.ON
        return SurfaceSense.POSITIVE if val > 0 else SurfaceSense.NEGATIVE


class Plane(Surface):
    """Plane surface: Ax + By + Cz - D = 0"""

    def __init__(self, surface_id: int, A: float, B: float, C: float, D: float):
        """
        Initialize plane

        Args:
            surface_id: Unique ID
            A, B, C, D: Plane coefficients (Ax + By + Cz - D = 0)

        Raises:
            ValueError: If normal vector (A, B, C) is zero
        """
        super().__init__(surface_id)
        # Normalize normal vector
        norm = np.sqrt(A**2 + B**2 + C**2)
        if norm < SURFACE_TOLERANCE:
            raise ValueError("Plane normal vector cannot be zero")
        self.A = A / norm
        self.B = B / norm
        self.C = C / norm
        self.D = D / norm
        self.normal = np.array([self.A, self.B, self.C])

    def evaluate(self, position: np.ndarray) -> float:
        """Evaluate plane equation"""
        return self.A * position[0] + self.B * position[1] + self.C * position[2] - self.D

    def distance(self, position: np.ndarray, direction: np.ndarray) -> float:
        """Distance to plane"""
        denom = np.dot(direction, self.normal)
        if abs(denom) < SURFACE_TOLERANCE:
            return np.inf

        t = (self.D - np.dot(position, self.normal)) / denom
        return t if t > DISTANCE_TOLERANCE else np.inf


class Sphere(Surface):
    """Sphere surface: (x-x0)^2 + (y-y0)^2 + (z-z0)^2 - R^2 = 0"""

    def __init__(self, surface_id: int, center: np.ndarray, radius: float):
        """
        Initialize sphere

        Args:
            surface_id: Unique ID
            center: Center point [x, y, z]
            radius: Sphere radius
        """
        super().__init__(surface_id)
        self.center = np.array(center, dtype=float)
        self.radius = float(radius)

    def evaluate(self, position: np.ndarray) -> float:
        """Evaluate sphere equation"""
        diff = position - self.center
        return np.dot(diff, diff) - self.radius**2

    def distance(self, position: np.ndarray, direction: np.ndarray) -> float:
        """Distance to sphere using quadratic formula"""
        # Solve: |p + t*d - c|^2 = R^2
        # This gives: a*t^2 + b*t + c = 0
        L = position - self.center
        a = np.dot(direction, direction)
        b = 2 * np.dot(direction, L)
        c = np.dot(L, L) - self.radius**2

        discriminant = b**2 - 4 * a * c
        if discriminant < 0:
            return np.inf

        sqrt_disc = np.sqrt(discriminant)
        t1 = (-b - sqrt_disc) / (2 * a)
        t2 = (-b + sqrt_disc) / (2 * a)

        # Return smallest positive distance
        if t1 > DISTANCE_TOLERANCE:
            return t1
        elif t2 > DISTANCE_TOLERANCE:
            return t2
        return np.inf


class Cylinder(Surface):
    """Cylinder surface (aligned with axis)"""

    def __init__(self, surface_id: int, center: np.ndarray, radius: float, axis: str = "z"):
        """
        Initialize cylinder

        Args:
            surface_id: Unique ID
            center: Center point [x, y, z] (point on axis)
            radius: Cylinder radius
            axis: Axis of cylinder ('x', 'y', or 'z')
        """
        super().__init__(surface_id)
        self.center = np.array(center, dtype=float)
        self.radius = float(radius)
        self.axis = axis.lower()

        # Determine which coordinates are perpendicular to axis
        if self.axis == "x":
            self.perp_indices = [1, 2]  # y, z
            self.axis_index = 0
        elif self.axis == "y":
            self.perp_indices = [0, 2]  # x, z
            self.axis_index = 1
        else:  # z
            self.perp_indices = [0, 1]  # x, y
            self.axis_index = 2

    def evaluate(self, position: np.ndarray) -> float:
        """Evaluate cylinder equation"""
        # Distance from axis
        perp_dist_sq = 0
        for i in self.perp_indices:
            perp_dist_sq += (position[i] - self.center[i]) ** 2
        return perp_dist_sq - self.radius**2

    def distance(self, position: np.ndarray, direction: np.ndarray) -> float:
        """Distance to cylinder"""
        # Similar to sphere but only in perpendicular plane
        L = np.array([position[i] - self.center[i] for i in self.perp_indices])
        d = np.array([direction[i] for i in self.perp_indices])

        a = np.dot(d, d)
        if abs(a) < 1e-10:
            return np.inf

        b = 2 * np.dot(d, L)
        c = np.dot(L, L) - self.radius**2

        discriminant = b**2 - 4 * a * c
        if discriminant < 0:
            return np.inf

        sqrt_disc = np.sqrt(discriminant)
        t1 = (-b - sqrt_disc) / (2 * a)
        t2 = (-b + sqrt_disc) / (2 * a)

        if t1 > DISTANCE_TOLERANCE:
            return t1
        elif t2 > DISTANCE_TOLERANCE:
            return t2
        return np.inf


class HalfSpace:
    """
    Half-space defined by a surface and sense

    Represents the region on one side of a surface
    """

    def __init__(self, surface: Surface, sense: int):
        """
        Initialize half-space

        Args:
            surface: The surface defining the half-space
            sense: +1 for positive side, -1 for negative side
        """
        self.surface = surface
        self.sense = sense

    def contains(self, position: np.ndarray) -> bool:
        """Check if position is in this half-space"""
        val = self.surface.evaluate(position)
        # Use strict inequalities to avoid ambiguity at boundaries
        if self.sense > 0:
            return val > -SURFACE_TOLERANCE
        else:
            return val < SURFACE_TOLERANCE


class CSGCell:
    """
    CSG Cell defined by boolean operations on half-spaces

    Similar to cells in Serpent and OpenMC
    """

    def __init__(self, cell_id: int, material: Optional[str] = None):
        """
        Initialize cell

        Args:
            cell_id: Unique cell identifier
            material: Material filling this cell (None for void)
        """
        self.id = cell_id
        self.material = material
        self.regions = []  # List of region expressions (AND groups)

    def add_region(self, *half_spaces: HalfSpace):
        """
        Add a region (intersection of half-spaces)

        Multiple calls to add_region create a union
        """
        self.regions.append(list(half_spaces))

    def contains(self, position: np.ndarray) -> bool:
        """Check if position is in this cell"""
        # Union of intersections (OR of ANDs)
        for region in self.regions:
            # Check if in all half-spaces of this region (AND)
            if all(hs.contains(position) for hs in region):
                return True
        return False

    def distance_to_boundary(
        self, position: np.ndarray, direction: np.ndarray
    ) -> Tuple[float, Optional[Surface]]:
        """
        Calculate distance to cell boundary

        Returns:
            (distance, surface) tuple
        """
        min_dist = np.inf
        min_surface = None

        # Check all surfaces in all regions
        surfaces_checked = set()
        for region in self.regions:
            for hs in region:
                if hs.surface.id not in surfaces_checked:
                    dist = hs.surface.distance(position, direction)
                    if dist < min_dist:
                        min_dist = dist
                        min_surface = hs.surface
                    surfaces_checked.add(hs.surface.id)

        return min_dist, min_surface


class CSGGeometry:
    """
    CSG-based geometry manager

    Similar to geometry in Serpent and OpenMC
    """

    def __init__(self):
        self.surfaces = {}  # surface_id -> Surface
        self.cells = {}  # cell_id -> CSGCell

    def add_surface(self, surface: Surface):
        """Add a surface to the geometry"""
        self.surfaces[surface.id] = surface

    def add_cell(self, cell: CSGCell):
        """Add a cell to the geometry"""
        self.cells[cell.id] = cell

    def find_cell(self, position: np.ndarray) -> Optional[CSGCell]:
        """Find which cell contains the given position"""
        for cell in self.cells.values():
            if cell.contains(position):
                return cell
        return None

    def get_material(self, position: np.ndarray) -> Optional[str]:
        """Get material at position"""
        cell = self.find_cell(position)
        return cell.material if cell else None

    def is_inside(self, position: np.ndarray) -> bool:
        """Check if position is inside any cell"""
        return self.find_cell(position) is not None

    def distance_to_boundary(self, position: np.ndarray, direction: np.ndarray) -> float:
        """Calculate distance to nearest boundary"""
        cell = self.find_cell(position)
        if cell is None:
            return 0.0

        dist, _ = cell.distance_to_boundary(position, direction)
        return dist
