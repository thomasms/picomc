# Flaky Test Fix Summary

## Problem
The test `test_fission_process_creates_secondaries` was failing intermittently in CI with:
```
FAILED tests/unit/test_fission_physics.py::TestFissionPhysicsIntegration::test_fission_process_creates_secondaries
assert 0 > 0
  where 0 = len([])
  where [] = Event(fission at [0. 0. 0.], secondaries=0).secondary_particles
```

## Root Cause Analysis

### The Physics
When a fission event occurs, the code samples the number of fission neutrons using a Poisson distribution:
```python
def sample_fission_neutrons(self, incident_energy: float, material: str) -> int:
    nubar = self.data_manager.get_nubar(material, incident_energy)
    return np.random.poisson(nubar)
```

### The Statistics
For U-235 at 2 MeV:
- nubar ≈ 2.5
- P(k neutrons) = (nubar^k * e^(-nubar)) / k!
- **P(0 neutrons) = e^(-2.5) ≈ 0.082 (8.2%)**

This means approximately **1 in 12 test runs would fail** because the Poisson sampling returned 0 neutrons, resulting in no secondary particles.

### Verification of Flakiness
Before the fix, running the test 10 times showed:
```
Run 1-5: PASSED
Run 6: FAILED ❌
Run 7-10: PASSED
```

## Solution

### Approach
Set a fixed random seed at the start of the test to ensure reproducible results:
```python
def test_fission_process_creates_secondaries(self, setup):
    """Test that fission event creates secondary particles"""
    from picomc.particle import Particle

    engine, dm = setup

    # Set random seed for reproducible results
    # Without this, Poisson sampling can occasionally return 0
    np.random.seed(42)

    # ... rest of test
```

### Why This Works
1. **Deterministic**: The same seed produces the same sequence of random numbers
2. **Realistic**: Still uses actual Poisson sampling (not mocked)
3. **CI-Friendly**: CI will always get the same results
4. **Minimal Change**: Only one line added

### Alternative Solutions Considered

❌ **Mock the Poisson function**: Too heavy-handed, doesn't test real code
❌ **Change assertion to allow 0**: Defeats the purpose of the test
❌ **Run multiple times and check average**: Makes test slower
✅ **Set random seed**: Simple, effective, maintains test integrity

## Verification

### Before Fix
```bash
# Run test 10 times
for i in {1..10}; do pytest test_fission_process_creates_secondaries -x; done

Result: 9 PASSED, 1 FAILED (90% success rate)
```

### After Fix
```bash
# Run test 150 times
for i in {1..150}; do pytest test_fission_process_creates_secondaries -x; done

Result: 150 PASSED, 0 FAILED (100% success rate) ✅
```

## Test Results

✅ **Target Test**: 150/150 passes
✅ **All Fission Physics Tests**: 17/17 passing
✅ **Full Test Suite**: 86/86 passing
✅ **Black Formatting**: Pass
✅ **Flake8 Linting**: Pass

## Impact

- **No functional code changes**: Only test improvement
- **No API changes**: Backward compatible
- **CI stability**: Test will no longer fail randomly
- **Reproducibility**: Same results every run

## Files Modified

1. `tests/unit/test_fission_physics.py` (line 218)
   - Added `np.random.seed(42)`
   - Added explanatory comment

## Conclusion

The test was failing because the physics simulation correctly uses Poisson sampling for fission neutron multiplicity, which can occasionally (8% of the time) return 0. This is **physically correct behavior** but makes the test flaky.

The fix ensures the test is deterministic by using a fixed random seed, maintaining the test's ability to verify the code works correctly while eliminating random failures.

**Status: FIXED** ✅
**CI Status: Should now pass consistently** 🚀
