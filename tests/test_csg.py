"""
Test CSG geometry functionality

Tests for Constructive Solid Geometry primitives and operations
"""

import pytest
import numpy as np
from picomc.csg import (
    Plane,
    Sphere,
    Cylinder,
    HalfSpace,
    CSGCell,
    CSGGeometry,
    SurfaceSense,
)


class TestPlane:
    """Test plane surface"""

    def test_plane_evaluation(self):
        """Test plane evaluation at different points"""
        # Create a plane at z=5
        plane = Plane(1, 0, 0, 1, 5)  # z - 5 = 0

        # Test evaluation
        assert plane.evaluate(np.array([0, 0, 10])) > 0, "Point above plane should be positive"
        assert plane.evaluate(np.array([0, 0, 0])) < 0, "Point below plane should be negative"
        assert abs(plane.evaluate(np.array([0, 0, 5]))) < 1e-10, "Point on plane should be zero"

    def test_plane_distance(self):
        """Test distance calculation to plane"""
        plane = Plane(1, 0, 0, 1, 5)  # z - 5 = 0

        # Test distance
        pos = np.array([0, 0, 0])
        direction = np.array([0, 0, 1])  # Moving up
        dist = plane.distance(pos, direction)
        assert abs(dist - 5) < 1e-10, f"Distance to plane should be 5, got {dist}"


class TestSphere:
    """Test sphere surface"""

    def test_sphere_evaluation(self):
        """Test sphere evaluation at different points"""
        # Create sphere at origin with radius 10
        sphere = Sphere(2, np.array([0, 0, 0]), 10)

        # Test evaluation
        assert sphere.evaluate(np.array([15, 0, 0])) > 0, "Point outside sphere should be positive"
        assert sphere.evaluate(np.array([5, 0, 0])) < 0, "Point inside sphere should be negative"
        assert abs(sphere.evaluate(np.array([10, 0, 0]))) < 1e-6, "Point on surface should be zero"

    def test_sphere_distance_from_center(self):
        """Test distance from center to surface"""
        sphere = Sphere(2, np.array([0, 0, 0]), 10)

        pos = np.array([0, 0, 0])
        direction = np.array([1, 0, 0])
        dist = sphere.distance(pos, direction)
        assert abs(dist - 10) < 1e-10, f"Distance from center to surface should be 10, got {dist}"

    def test_sphere_distance_from_outside(self):
        """Test distance from outside point"""
        sphere = Sphere(2, np.array([0, 0, 0]), 10)

        pos = np.array([20, 0, 0])
        direction = np.array([-1, 0, 0])
        dist = sphere.distance(pos, direction)
        assert abs(dist - 10) < 1e-10, f"Distance from outside should be 10, got {dist}"


class TestCylinder:
    """Test cylinder surface"""

    def test_cylinder_evaluation(self):
        """Test cylinder evaluation at different points"""
        # Create cylinder along z-axis, radius 5, centered at origin
        cylinder = Cylinder(3, np.array([0, 0, 0]), 5, axis="z")

        # Test evaluation
        assert (
            cylinder.evaluate(np.array([10, 0, 5])) > 0
        ), "Point outside cylinder should be positive"
        assert (
            cylinder.evaluate(np.array([2, 0, 5])) < 0
        ), "Point inside cylinder should be negative"

    def test_cylinder_distance(self):
        """Test distance calculation to cylinder"""
        cylinder = Cylinder(3, np.array([0, 0, 0]), 5, axis="z")

        pos = np.array([0, 0, 0])
        direction = np.array([1, 0, 0])
        dist = cylinder.distance(pos, direction)
        assert abs(dist - 5) < 1e-10, f"Distance to cylinder should be 5, got {dist}"


class TestHalfSpace:
    """Test half-space"""

    def test_halfspace_positive(self):
        """Test positive half-space containment"""
        plane = Plane(1, 0, 0, 1, 0)  # z = 0 plane
        hs_positive = HalfSpace(plane, +1)  # z > 0

        assert hs_positive.contains(
            np.array([0, 0, 5])
        ), "Point above plane should be in positive half-space"
        assert not hs_positive.contains(
            np.array([0, 0, -5])
        ), "Point below plane should not be in positive half-space"

    def test_halfspace_negative(self):
        """Test negative half-space containment"""
        plane = Plane(1, 0, 0, 1, 0)  # z = 0 plane
        hs_negative = HalfSpace(plane, -1)  # z < 0

        assert hs_negative.contains(
            np.array([0, 0, -5])
        ), "Point below plane should be in negative half-space"
        assert not hs_negative.contains(
            np.array([0, 0, 5])
        ), "Point above plane should not be in negative half-space"


class TestCSGCell:
    """Test CSG cell for a simple box"""

    @pytest.fixture
    def box_cell(self):
        """Create a box cell for testing"""
        # Create a box using 6 planes
        # Box from (0,0,0) to (10,10,10)
        px_low = Plane(1, 1, 0, 0, 0)  # x = 0
        px_high = Plane(2, 1, 0, 0, 10)  # x = 10
        py_low = Plane(3, 0, 1, 0, 0)  # y = 0
        py_high = Plane(4, 0, 1, 0, 10)  # y = 10
        pz_low = Plane(5, 0, 0, 1, 0)  # z = 0
        pz_high = Plane(6, 0, 0, 1, 10)  # z = 10

        # Create cell (intersection of all half-spaces)
        cell = CSGCell(1, material="test_material")
        cell.add_region(
            HalfSpace(px_low, +1),  # x > 0
            HalfSpace(px_high, -1),  # x < 10
            HalfSpace(py_low, +1),  # y > 0
            HalfSpace(py_high, -1),  # y < 10
            HalfSpace(pz_low, +1),  # z > 0
            HalfSpace(pz_high, -1),  # z < 10
        )
        return cell

    def test_cell_containment(self, box_cell):
        """Test cell containment checks"""
        assert box_cell.contains(np.array([5, 5, 5])), "Center should be inside"
        assert not box_cell.contains(np.array([-1, 5, 5])), "Outside in -x should not be inside"
        assert not box_cell.contains(np.array([15, 5, 5])), "Outside in +x should not be inside"
        assert not box_cell.contains(np.array([5, 5, 15])), "Outside in +z should not be inside"

    def test_cell_distance_to_boundary(self, box_cell):
        """Test distance to cell boundary"""
        pos = np.array([5, 5, 5])
        direction = np.array([1, 0, 0])  # Moving in +x
        dist, surf = box_cell.distance_to_boundary(pos, direction)
        assert abs(dist - 5) < 1e-10, f"Distance to boundary should be 5, got {dist}"


class TestCSGGeometry:
    """Test complete CSG geometry"""

    def test_csg_geometry_sphere_in_box(self):
        """Test geometry with sphere in a box"""
        # Create simple geometry with sphere in a box
        geom = CSGGeometry()

        # Add sphere
        sphere = Sphere(1, np.array([5, 5, 5]), 2)
        geom.add_surface(sphere)

        # Create sphere cell
        sphere_cell = CSGCell(1, material="uranium")
        sphere_cell.add_region(HalfSpace(sphere, -1))  # Inside sphere
        geom.add_cell(sphere_cell)

        # Create outer box
        px_low = Plane(10, 1, 0, 0, 0)
        px_high = Plane(11, 1, 0, 0, 10)
        py_low = Plane(12, 0, 1, 0, 0)
        py_high = Plane(13, 0, 1, 0, 10)
        pz_low = Plane(14, 0, 0, 1, 0)
        pz_high = Plane(15, 0, 0, 1, 10)

        for surf in [px_low, px_high, py_low, py_high, pz_low, pz_high]:
            geom.add_surface(surf)

        # Create void region (outside sphere, inside box)
        void_cell = CSGCell(2, material=None)
        void_cell.add_region(
            HalfSpace(sphere, +1),  # Outside sphere
            HalfSpace(px_low, +1),
            HalfSpace(px_high, -1),
            HalfSpace(py_low, +1),
            HalfSpace(py_high, -1),
            HalfSpace(pz_low, +1),
            HalfSpace(pz_high, -1),
        )
        geom.add_cell(void_cell)

        # Test find_cell
        cell_center = geom.find_cell(np.array([5, 5, 5]))
        assert cell_center is not None, "Should find cell at center"
        assert cell_center.material == "uranium", "Center should be uranium"

        cell_corner = geom.find_cell(np.array([1, 1, 1]))
        assert cell_corner is not None, "Should find cell at corner"
        assert cell_corner.material is None, "Corner should be void"

        # Test get_material
        mat = geom.get_material(np.array([5, 5, 5]))
        assert mat == "uranium", f"Material at center should be uranium, got {mat}"
