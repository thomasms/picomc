"""
Random sampling utilities for Monte Carlo simulations

These functions are extracted to be easily testable and mockable.
"""

import numpy as np
from typing import Tuple


def sample_exponential_distance(sigma_total: float) -> float:
    """
    Sample distance to next interaction using exponential distribution
    
    Args:
        sigma_total: Total macroscopic cross section (cm^-1)
        
    Returns:
        Distance to next interaction (cm)
    """
    if sigma_total <= 0:
        return np.inf
    
    xi = np.random.random()
    return -np.log(xi) / sigma_total


def sample_interaction_type_from_xs(
    sigma_elastic: float, sigma_capture: float, sigma_fission: float, sigma_total: float
) -> str:
    """
    Sample interaction type based on cross sections
    
    Args:
        sigma_elastic: Elastic scattering cross section
        sigma_capture: Capture cross section
        sigma_fission: Fission cross section
        sigma_total: Total cross section
        
    Returns:
        Interaction type: 'elastic', 'capture', or 'fission'
    """
    if sigma_total <= 0:
        return "elastic"
    
    xi = np.random.random()
    
    # Normalize probabilities
    p_elastic = sigma_elastic / sigma_total
    p_capture = sigma_capture / sigma_total
    
    if xi < p_elastic:
        return "elastic"
    elif xi < p_elastic + p_capture:
        return "capture"
    else:
        return "fission"


def sample_isotropic_direction() -> np.ndarray:
    """
    Sample isotropic direction in 3D using spherical coordinates
    
    Returns:
        Unit direction vector [dx, dy, dz]
    """
    phi = 2 * np.pi * np.random.random()
    cos_theta = 2 * np.random.random() - 1
    sin_theta = np.sqrt(1 - cos_theta**2)
    
    dx = sin_theta * np.cos(phi)
    dy = sin_theta * np.sin(phi)
    dz = cos_theta
    
    return np.array([dx, dy, dz])


def sample_fission_multiplicity(mean_nu: float = 2.5) -> int:
    """
    Sample number of fission neutrons from Poisson distribution
    
    Args:
        mean_nu: Mean neutron multiplicity
        
    Returns:
        Number of fission neutrons
    """
    return np.random.poisson(mean_nu)


def sample_fission_spectrum_energy(scale: float = 1.0e6, minimum: float = 0.5e6) -> float:
    """
    Sample fission neutron energy from simplified spectrum
    
    Args:
        scale: Exponential scale parameter (eV)
        minimum: Minimum fission energy (eV)
        
    Returns:
        Fission neutron energy (eV)
    """
    return np.random.exponential(scale) + minimum


def compute_velocity_from_energy(energy: float, mass_energy_factor: float = 5.227e-9) -> float:
    """
    Compute neutron velocity from kinetic energy
    
    Args:
        energy: Kinetic energy in eV
        mass_energy_factor: Conversion factor E = factor * v^2
        
    Returns:
        Velocity in cm/s
    """
    return np.sqrt(energy / mass_energy_factor)


def normalize_direction(direction: np.ndarray) -> np.ndarray:
    """
    Normalize a direction vector to unit length
    
    Args:
        direction: Direction vector
        
    Returns:
        Normalized unit direction vector
    """
    norm = np.linalg.norm(direction)
    if norm > 0:
        return direction / norm
    return direction
