"""
Unit tests for random sampling utilities

These functions are tested with fixed random seeds for reproducibility.
"""

import pytest
import numpy as np
from picomc.random_sampling import (
    sample_exponential_distance,
    sample_interaction_type_from_xs,
    sample_isotropic_direction,
    sample_fission_multiplicity,
    sample_fission_spectrum_energy,
    compute_velocity_from_energy,
    normalize_direction,
)


class TestExponentialDistance:
    """Test exponential distance sampling"""

    def test_positive_cross_section(self, random_seed):
        """Test with positive cross section"""
        sigma = 0.1  # cm^-1
        distance = sample_exponential_distance(sigma)
        assert distance > 0
        assert distance < np.inf

    def test_zero_cross_section(self):
        """Test with zero cross section returns infinity"""
        distance = sample_exponential_distance(0.0)
        assert distance == np.inf

    def test_negative_cross_section(self):
        """Test with negative cross section returns infinity"""
        distance = sample_exponential_distance(-0.5)
        assert distance == np.inf

    def test_statistical_mean(self, random_seed):
        """Test that mean distance follows exponential distribution"""
        sigma = 0.5
        n_samples = 10000
        distances = [sample_exponential_distance(sigma) for _ in range(n_samples)]
        mean_distance = np.mean(distances)

        # Mean of exponential distribution is 1/lambda
        expected_mean = 1.0 / sigma
        # Allow 5% tolerance
        assert abs(mean_distance - expected_mean) / expected_mean < 0.05


class TestInteractionTypeSampling:
    """Test interaction type sampling"""

    def test_only_elastic(self, random_seed):
        """Test when only elastic scattering is possible"""
        interaction = sample_interaction_type_from_xs(1.0, 0.0, 0.0, 1.0)
        assert interaction == "elastic"

    def test_only_capture(self, random_seed):
        """Test when only capture is possible"""
        interaction = sample_interaction_type_from_xs(0.0, 1.0, 0.0, 1.0)
        assert interaction in ["capture", "fission"]

    def test_only_fission(self, random_seed):
        """Test when only fission is possible"""
        interaction = sample_interaction_type_from_xs(0.0, 0.0, 1.0, 1.0)
        assert interaction == "fission"

    def test_zero_total_xs(self):
        """Test with zero total cross section"""
        interaction = sample_interaction_type_from_xs(0.0, 0.0, 0.0, 0.0)
        assert interaction == "elastic"

    def test_mixed_cross_sections(self, random_seed):
        """Test with mixed cross sections"""
        interactions = [
            sample_interaction_type_from_xs(5.0, 3.0, 2.0, 10.0) for _ in range(100)
        ]

        # All should be valid types
        assert all(i in ["elastic", "capture", "fission"] for i in interactions)

        # Check we get some variety
        assert len(set(interactions)) > 1


class TestIsotropicDirection:
    """Test isotropic direction sampling"""

    def test_unit_vector(self, random_seed):
        """Test that sampled direction is a unit vector"""
        direction = sample_isotropic_direction()
        norm = np.linalg.norm(direction)
        assert abs(norm - 1.0) < 1e-10

    def test_components_in_range(self, random_seed):
        """Test that all components are in [-1, 1]"""
        for _ in range(10):
            direction = sample_isotropic_direction()
            assert all(-1.0 <= c <= 1.0 for c in direction)

    def test_isotropic_distribution(self, random_seed):
        """Test that directions are roughly isotropically distributed"""
        n_samples = 1000
        directions = np.array([sample_isotropic_direction() for _ in range(n_samples)])

        # Mean should be close to zero for isotropic distribution
        mean_direction = np.mean(directions, axis=0)
        assert np.linalg.norm(mean_direction) < 0.1


class TestFissionMultiplicity:
    """Test fission neutron multiplicity sampling"""

    def test_positive_count(self, random_seed):
        """Test that multiplicity is positive"""
        nu = sample_fission_multiplicity(2.5)
        assert nu >= 0
        assert isinstance(nu, (int, np.integer))

    def test_statistical_mean(self, random_seed):
        """Test that mean follows Poisson distribution"""
        mean_nu = 2.5
        n_samples = 10000
        counts = [sample_fission_multiplicity(mean_nu) for _ in range(n_samples)]
        observed_mean = np.mean(counts)

        # Allow 5% tolerance
        assert abs(observed_mean - mean_nu) / mean_nu < 0.05


class TestFissionSpectrumEnergy:
    """Test fission energy spectrum sampling"""

    def test_above_minimum(self, random_seed):
        """Test that energy is above minimum"""
        minimum = 0.5e6
        energy = sample_fission_spectrum_energy(minimum=minimum)
        assert energy >= minimum

    def test_reasonable_range(self, random_seed):
        """Test that energy is in reasonable range"""
        scale = 1.0e6
        minimum = 0.5e6
        for _ in range(100):
            energy = sample_fission_spectrum_energy(scale, minimum)
            # Should be in range [minimum, minimum + 10*scale] with high probability
            assert minimum <= energy < minimum + 20 * scale


class TestVelocityCalculation:
    """Test velocity calculation from energy"""

    def test_positive_energy(self):
        """Test with positive energy"""
        energy = 2.0e6  # eV
        velocity = compute_velocity_from_energy(energy)
        assert velocity > 0

    def test_zero_energy(self):
        """Test with zero energy"""
        velocity = compute_velocity_from_energy(0.0)
        assert velocity == 0.0

    def test_energy_velocity_relationship(self):
        """Test that E = factor * v^2"""
        energy = 2.0e6
        factor = 5.227e-9
        velocity = compute_velocity_from_energy(energy, factor)

        # Check relationship
        calculated_energy = factor * velocity**2
        assert abs(calculated_energy - energy) < 1e-5


class TestNormalizeDirection:
    """Test direction normalization"""

    def test_already_normalized(self):
        """Test with already normalized vector"""
        direction = np.array([1.0, 0.0, 0.0])
        normalized = normalize_direction(direction)
        assert np.allclose(normalized, direction)

    def test_not_normalized(self):
        """Test with non-normalized vector"""
        direction = np.array([3.0, 4.0, 0.0])
        normalized = normalize_direction(direction)

        # Check it's now normalized
        assert abs(np.linalg.norm(normalized) - 1.0) < 1e-10

        # Check direction is preserved
        assert np.allclose(normalized, np.array([0.6, 0.8, 0.0]))

    def test_zero_vector(self):
        """Test with zero vector"""
        direction = np.array([0.0, 0.0, 0.0])
        normalized = normalize_direction(direction)

        # Should return zero vector unchanged
        assert np.allclose(normalized, direction)
