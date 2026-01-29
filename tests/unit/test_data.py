"""
Unit tests for nuclear data management
"""

import pytest
import numpy as np
from picomc.data import CrossSectionData, NuclearDataManager


class TestCrossSectionData:
    """Unit tests for CrossSectionData class"""

    @pytest.fixture
    def xs_data(self, sample_energies, sample_cross_sections):
        """Create CrossSectionData instance with test data"""
        xs = CrossSectionData()
        xs.energies = sample_energies
        xs.elastic = sample_cross_sections["elastic"]
        xs.capture = sample_cross_sections["capture"]
        xs.fission = sample_cross_sections["fission"]
        xs.total = xs.elastic + xs.capture + xs.fission
        return xs

    def test_empty_cross_section_data(self):
        """Test that empty data returns zeros"""
        xs = CrossSectionData()
        result = xs.get_xs_at_energy(1.0e6)

        assert result["total"] == 0.0
        assert result["elastic"] == 0.0
        assert result["capture"] == 0.0
        assert result["fission"] == 0.0

    def test_interpolation_at_grid_point(self, xs_data):
        """Test that interpolation returns exact values at grid points"""
        energy = 1.0e6
        result = xs_data.get_xs_at_energy(energy)

        # Find index in energy grid
        idx = np.where(xs_data.energies == energy)[0][0]

        assert abs(result["elastic"] - xs_data.elastic[idx]) < 1e-10
        assert abs(result["capture"] - xs_data.capture[idx]) < 1e-10
        assert abs(result["fission"] - xs_data.fission[idx]) < 1e-10

    def test_interpolation_between_points(self, xs_data):
        """Test linear interpolation between grid points"""
        # Energy between 1.0 and 100.0 eV
        energy = 50.0
        result = xs_data.get_xs_at_energy(energy)

        # Should be between the two bounding values
        idx1 = 2  # 1.0 eV
        idx2 = 3  # 100.0 eV

        assert xs_data.elastic[idx1] >= result["elastic"] >= xs_data.elastic[idx2]
        assert result["total"] > 0

    def test_extrapolation_below_grid(self, xs_data):
        """Test behavior for energy below grid"""
        energy = 1e-10  # Below minimum energy
        result = xs_data.get_xs_at_energy(energy)

        # Should extrapolate to first value
        assert result["elastic"] == xs_data.elastic[0]

    def test_extrapolation_above_grid(self, xs_data):
        """Test behavior for energy above grid"""
        energy = 1e10  # Above maximum energy
        result = xs_data.get_xs_at_energy(energy)

        # Should extrapolate to last value
        assert result["elastic"] == xs_data.elastic[-1]

    def test_single_point_data(self):
        """Test with single energy point"""
        xs = CrossSectionData()
        xs.energies = np.array([1.0e6])
        xs.elastic = np.array([5.0])
        xs.capture = np.array([2.0])
        xs.fission = np.array([1.0])
        xs.total = np.array([8.0])

        result = xs.get_xs_at_energy(1.0e6)

        assert result["elastic"] == 5.0
        assert result["capture"] == 2.0
        assert result["fission"] == 1.0
        assert result["total"] == 8.0


class TestNuclearDataManager:
    """Unit tests for NuclearDataManager class"""

    def test_add_material(self):
        """Test adding a material with default cross sections"""
        dm = NuclearDataManager()
        dm.add_material("test_material", number_density=0.05)

        assert "test_material" in dm.materials
        assert dm.materials["test_material"]["number_density"] == 0.05
        assert len(dm.materials["test_material"]["xs_data"].energies) > 0

    def test_get_material_xs(self):
        """Test retrieving material cross sections"""
        dm = NuclearDataManager()
        dm.add_material("test_material", number_density=0.05)

        xs = dm.get_material_xs("test_material", 2.0e6)

        assert "total" in xs
        assert "elastic" in xs
        assert "capture" in xs
        assert "fission" in xs
        assert all(v >= 0 for v in xs.values())

    def test_get_macroscopic_xs(self):
        """Test macroscopic cross section calculation"""
        dm = NuclearDataManager()
        number_density = 0.05
        dm.add_material("test_material", number_density=number_density)

        micro_xs = dm.get_material_xs("test_material", 2.0e6)
        macro_xs = dm.get_macroscopic_xs("test_material", 2.0e6)

        # Macroscopic = microscopic * number_density
        assert abs(macro_xs["total"] - micro_xs["total"] * number_density) < 1e-10
        assert abs(macro_xs["elastic"] - micro_xs["elastic"] * number_density) < 1e-10

    def test_material_not_found_creates_default(self):
        """Test that requesting unknown material creates it with defaults"""
        dm = NuclearDataManager()

        # This should create the material automatically
        xs = dm.get_material_xs("unknown_material", 2.0e6)

        assert "unknown_material" in dm.materials
        assert all(v >= 0 for v in xs.values())
