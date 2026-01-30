# Testing Guide for PicoMC

This document describes the testing infrastructure and best practices for PicoMC.

## Test Organization

```
tests/
├── conftest.py              # Shared pytest fixtures
├── test_csg.py              # CSG geometry tests (12 tests)
├── test_neutron_box.py      # Integration tests (3 tests)
└── unit/
    ├── test_data.py         # Nuclear data management (10 tests)
    ├── test_particle.py     # Particle and event classes (10 tests)
    ├── test_physics.py      # Physics engine (14 tests)
    └── test_random_sampling.py  # Random sampling utilities (22 tests)
```

**Total: 71 tests** with 70% code coverage

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_data.py

# Run specific test class
pytest tests/unit/test_data.py::TestCrossSectionData

# Run specific test
pytest tests/unit/test_data.py::TestCrossSectionData::test_interpolation_at_grid_point
```

### Coverage Reports

```bash
# Run with coverage
pytest tests/ --cov=picomc

# Generate detailed coverage report
pytest tests/ --cov=picomc --cov-report=term-missing

# Generate HTML coverage report
pytest tests/ --cov=picomc --cov-report=html
# Open htmlcov/index.html in browser
```

### Test Markers

Tests are organized with markers for selective execution:

```bash
# Run only unit tests
pytest tests/ -m unit

# Run only integration tests
pytest tests/ -m integration

# Run fast tests only (exclude slow tests)
pytest tests/ -m "not slow"
```

## Writing Tests

### Unit Test Structure

Unit tests should follow this pattern:

```python
import pytest
from picomc.module import function_to_test

class TestFunctionName:
    """Test description"""
    
    @pytest.fixture
    def test_data(self):
        """Create test data"""
        return {"key": "value"}
    
    def test_normal_case(self, test_data):
        """Test normal operation"""
        result = function_to_test(test_data)
        assert result == expected
    
    def test_edge_case(self):
        """Test edge case"""
        result = function_to_test(edge_case_input)
        assert result is not None
    
    def test_error_handling(self):
        """Test error handling"""
        with pytest.raises(ValueError):
            function_to_test(invalid_input)
```

### Using Fixtures

Common fixtures are defined in `tests/conftest.py`:

```python
def test_with_random_seed(random_seed):
    """Test that uses reproducible random numbers"""
    # random_seed fixture sets np.random.seed(42)
    result = some_random_operation()
    assert result == expected_with_seed_42

def test_with_sample_data(sample_energies, sample_cross_sections):
    """Test using standard energy grid and cross sections"""
    xs_data = CrossSectionData()
    xs_data.energies = sample_energies
    xs_data.elastic = sample_cross_sections["elastic"]
```

### Testing with Mocks

For testing with dependency injection:

```python
from unittest.mock import Mock, MagicMock

def test_with_mock_dependency():
    """Test using mocked dependency"""
    mock_data_manager = Mock()
    mock_data_manager.get_macroscopic_xs.return_value = {
        "total": 0.5,
        "elastic": 0.3,
        "capture": 0.2,
        "fission": 0.0,
    }
    
    engine = PhysicsEngine(mock_data_manager)
    # Test engine behavior with controlled inputs
```

### Parametrized Tests

For testing multiple cases:

```python
@pytest.mark.parametrize("energy,expected_xs", [
    (1.0e5, 5.0),
    (1.0e6, 2.0),
    (1.0e7, 1.0),
])
def test_cross_section_values(energy, expected_xs):
    """Test cross sections at various energies"""
    xs = get_cross_section(energy)
    assert abs(xs - expected_xs) < 0.1
```

## Best Practices

### 1. Test Naming

- Test files: `test_<module>.py`
- Test classes: `Test<FeatureName>`
- Test methods: `test_<what_it_tests>`

### 2. Test Organization

- **Unit tests**: Test single functions/methods in isolation
- **Integration tests**: Test multiple components working together
- **Fixtures**: Use for common setup/teardown

### 3. Assertions

- Use descriptive assertion messages
- Test both success and failure cases
- Check edge cases and boundary conditions

### 4. Random Numbers

- Use `random_seed` fixture for reproducible tests
- Test statistical properties with large samples
- Mock random functions when testing logic

### 5. Test Independence

- Each test should be independent
- Don't rely on test execution order
- Use fixtures to set up test state

## Continuous Integration

The project uses GitHub Actions for CI. Every push triggers:

1. **Linting** (flake8): Checks code style and common errors
2. **Formatting** (black): Verifies code formatting
3. **Tests** (pytest): Runs full test suite
4. **Coverage** (pytest-cov): Measures code coverage

Tests run on Python 3.8, 3.9, 3.10, and 3.11 to ensure compatibility.

See `.github/workflows/ci.yml` for CI configuration.

## Coverage Goals

Current coverage: **70%**

Priority areas for improving coverage:
- `picomc/data.py` (44% → 80%): Add tests for ENDF/PENDF loading
- `picomc/pendf_parser.py` (0% → 70%): Add parser tests
- `picomc/simulator.py` (72% → 90%): Add integration tests
- `picomc/tally.py` (69% → 85%): Add tally tests

## Troubleshooting

### Tests Fail Randomly

If tests fail randomly, they may depend on random numbers:
- Use the `random_seed` fixture
- Or increase sample size for statistical tests

### Import Errors

If you get import errors:
```bash
# Install package in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

### Slow Tests

Mark slow tests with `@pytest.mark.slow`:
```python
@pytest.mark.slow
def test_long_simulation():
    """This test takes a long time"""
    # ...
```

Then skip them during development:
```bash
pytest tests/ -m "not slow"
```

## Adding New Tests

When adding new functionality:

1. **Write tests first** (TDD approach)
2. **Test the interface**, not implementation details
3. **Use dependency injection** for mockability
4. **Keep functions small** for easier testing
5. **Add integration tests** for end-to-end validation

Example workflow:
```bash
# 1. Write test for new feature
vi tests/unit/test_new_feature.py

# 2. Run test (should fail)
pytest tests/unit/test_new_feature.py

# 3. Implement feature
vi picomc/new_feature.py

# 4. Run test (should pass)
pytest tests/unit/test_new_feature.py

# 5. Run all tests
pytest tests/
```
