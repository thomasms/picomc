"""
Shared test fixtures and utilities
"""

import sys
import os
import pytest
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_energies():
    """Standard energy grid for testing"""
    return np.array([1e-5, 1e-2, 1.0, 100.0, 1e4, 1e6, 2e7])


@pytest.fixture
def sample_cross_sections():
    """Sample cross section data for testing"""
    return {
        "elastic": np.array([10.0, 10.0, 8.0, 5.0, 3.0, 2.0, 1.5]),
        "inelastic": np.array([0.0, 0.0, 0.0, 0.5, 1.0, 1.5, 2.0]),
        "capture": np.array([1000.0, 10.0, 3.0, 1.0, 0.5, 0.3, 0.2]),
        "fission": np.array([0.0, 0.0, 0.1, 0.2, 0.3, 0.2, 0.1]),
    }


@pytest.fixture
def random_seed():
    """Set random seed for reproducible tests"""
    np.random.seed(42)
    yield
    # Reset after test
    np.random.seed(None)
