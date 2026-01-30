"""
Unit tests for fission physics using real ENDF data
"""

import pytest
import numpy as np
from picomc.data import NubarData, FissionSpectrumData, NuclearDataManager


class TestNubarData:
    """Test nubar (neutrons per fission) data handling"""

    def test_empty_nubar_returns_default(self):
        """Test that empty nubar data returns default value"""
        nubar_data = NubarData()
        assert nubar_data.get_nubar_at_energy(1e6) == 2.5

    def test_single_point_nubar(self):
        """Test nubar with single data point"""
        nubar_data = NubarData()
        nubar_data.energies = np.array([1e6])
        nubar_data.total = np.array([2.43])

        assert nubar_data.get_nubar_at_energy(1e6) == 2.43
        assert nubar_data.get_nubar_at_energy(0.0) == 2.43

    def test_nubar_interpolation(self):
        """Test linear interpolation of nubar"""
        nubar_data = NubarData()
        nubar_data.energies = np.array([0.0, 1e6, 2e7])
        nubar_data.total = np.array([2.43, 2.5, 2.8])

        # Test interpolation at midpoint
        nubar_mid = nubar_data.get_nubar_at_energy(0.5e6)
        assert 2.43 < nubar_mid < 2.5

        # Test exact grid point
        assert nubar_data.get_nubar_at_energy(1e6) == pytest.approx(2.5)

    def test_nubar_extrapolation(self):
        """Test extrapolation behavior"""
        nubar_data = NubarData()
        nubar_data.energies = np.array([1e6, 2e7])
        nubar_data.total = np.array([2.5, 2.8])

        # Below range - should extrapolate
        nubar_low = nubar_data.get_nubar_at_energy(0.0)
        assert nubar_low > 0

        # Above range - should extrapolate
        nubar_high = nubar_data.get_nubar_at_energy(3e7)
        assert nubar_high > 0


class TestFissionSpectrumData:
    """Test fission neutron energy spectrum"""

    def test_empty_spectrum_returns_default(self):
        """Test that empty spectrum returns default energy"""
        spectrum = FissionSpectrumData()
        energy = spectrum.sample_energy()
        assert energy > 0
        assert energy < 20e6  # Reasonable upper bound

    def test_watt_spectrum_sampling(self):
        """Test Watt spectrum sampling"""
        spectrum = FissionSpectrumData()
        spectrum.spectrum_type = "watt"
        spectrum.params = {"a": 0.988e6, "b": 2.249e-6}  # U-235 parameters

        # Sample multiple times to check distribution
        energies = [spectrum.sample_energy() for _ in range(1000)]

        # All energies should be positive
        assert all(e > 0 for e in energies)

        # Mean energy should be around 2 MeV for U-235
        mean_energy = np.mean(energies)
        assert 1.0e6 < mean_energy < 3.0e6

        # Most energies should be below 10 MeV
        assert sum(e < 10e6 for e in energies) > 950

    def test_tabulated_spectrum_sampling(self):
        """Test tabulated spectrum sampling"""
        spectrum = FissionSpectrumData()
        spectrum.spectrum_type = "tabulated"

        # Create simple tabulated spectrum
        energies = np.array([0.1e6, 1.0e6, 2.0e6, 5.0e6])
        chi = np.array([0.1, 0.5, 0.3, 0.1])  # Probability distribution

        spectrum.params = {"energies": energies, "chi": chi}

        # Sample multiple times
        samples = [spectrum.sample_energy() for _ in range(100)]

        # All samples should be within the energy range
        assert all(0.1e6 <= e <= 5.0e6 for e in samples)

        # Most samples should be around the peak (1 MeV)
        near_peak = sum(0.5e6 <= e <= 2.5e6 for e in samples)
        assert near_peak > 50  # At least half should be near peak

    def test_watt_spectrum_parameters(self):
        """Test Watt spectrum with different parameters"""
        spectrum = FissionSpectrumData()
        spectrum.spectrum_type = "watt"

        # Test with larger 'a' (higher mean energy)
        spectrum.params = {"a": 2.0e6, "b": 2.249e-6}
        energies_high = [spectrum.sample_energy() for _ in range(500)]

        # Test with smaller 'a' (lower mean energy)
        spectrum.params = {"a": 0.5e6, "b": 2.249e-6}
        energies_low = [spectrum.sample_energy() for _ in range(500)]

        # Larger 'a' should have higher mean energy
        assert np.mean(energies_high) > np.mean(energies_low)


class TestNuclearDataManagerFission:
    """Test NuclearDataManager fission data methods"""

    @pytest.fixture
    def data_manager(self):
        """Create data manager with default material"""
        dm = NuclearDataManager()
        dm.add_material("test_fuel", number_density=0.05)
        return dm

    def test_get_nubar_default(self, data_manager):
        """Test getting nubar from default material"""
        nubar = data_manager.get_nubar("test_fuel", 1e6)
        assert 2.0 < nubar < 3.0  # Reasonable range

    def test_get_nubar_energy_dependence(self, data_manager):
        """Test nubar energy dependence"""
        nubar_low = data_manager.get_nubar("test_fuel", 1e5)
        nubar_high = data_manager.get_nubar("test_fuel", 2e7)

        # Higher energy should give more neutrons
        assert nubar_high > nubar_low

    def test_sample_fission_energy_default(self, data_manager):
        """Test sampling fission energy from default material"""
        energy = data_manager.sample_fission_energy("test_fuel", 2e6)
        assert energy > 0
        assert energy < 20e6

    def test_sample_fission_energy_distribution(self, data_manager):
        """Test fission energy distribution shape"""
        energies = [data_manager.sample_fission_energy("test_fuel", 2e6) for _ in range(1000)]

        # Check distribution properties
        mean_energy = np.mean(energies)
        assert 1.0e6 < mean_energy < 3.0e6  # Around 2 MeV peak

        # Most energies should be below 10 MeV
        below_10mev = sum(e < 10e6 for e in energies)
        assert below_10mev > 900

    def test_get_nubar_missing_material(self, data_manager):
        """Test nubar for non-existent material returns default"""
        nubar = data_manager.get_nubar("missing_material", 1e6)
        assert nubar == 2.5  # Default value

    def test_sample_fission_energy_missing_material(self, data_manager):
        """Test fission energy for non-existent material"""
        energy = data_manager.sample_fission_energy("missing_material", 2e6)
        assert energy > 0  # Should still return something


class TestFissionPhysicsIntegration:
    """Integration tests for fission physics with PhysicsEngine"""

    @pytest.fixture
    def setup(self):
        """Create physics engine with data manager"""
        from picomc.physics import PhysicsEngine

        dm = NuclearDataManager()
        dm.add_material("fuel", number_density=0.05)
        engine = PhysicsEngine(dm)
        return engine, dm

    def test_fission_neutron_count_uses_nubar(self, setup):
        """Test that fission neutron count uses nubar"""
        engine, dm = setup

        # Sample many fission events
        counts = [engine.sample_fission_neutrons(2e6, "fuel") for _ in range(1000)]

        # Mean should be close to nubar at this energy
        mean_count = np.mean(counts)
        nubar = dm.get_nubar("fuel", 2e6)

        # Statistical check: mean should be within 10% of nubar
        assert abs(mean_count - nubar) / nubar < 0.1

    def test_fission_neutron_energy_uses_spectrum(self, setup):
        """Test that fission neutron energy uses spectrum"""
        engine, dm = setup

        # Sample many fission neutron energies
        energies = [engine.sample_fission_energy(2e6, "fuel") for _ in range(1000)]

        # Check distribution matches expected Watt spectrum
        mean_energy = np.mean(energies)
        assert 1.0e6 < mean_energy < 3.0e6

    def test_fission_process_creates_secondaries(self, setup):
        """Test that fission event creates secondary particles"""
        from picomc.particle import Particle

        engine, dm = setup

        # Create test particle
        particle = Particle(
            position=np.array([0.0, 0.0, 0.0]),
            direction=np.array([1.0, 0.0, 0.0]),
            energy=2.0e6,
            is_source=True,
        )

        # Mock to always return fission
        engine.sample_interaction_type = lambda p, m: "fission"

        # Process fission
        event = engine.process_interaction(particle, "fuel")

        # Check results
        assert event.interaction_type == "fission"
        assert not particle.alive  # Original particle should be dead
        assert len(event.secondary_particles) > 0  # Should have secondaries

        # Check secondary energies are from fission spectrum
        for secondary in event.secondary_particles:
            assert secondary.energy > 0
            assert secondary.energy < 20e6
            assert not secondary.is_source  # Secondaries are not source particles
