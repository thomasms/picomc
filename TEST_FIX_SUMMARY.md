# Test Fix Summary: test_material_not_found_creates_default

## Problem
The test `tests/unit/test_data.py::TestNuclearDataManager::test_material_not_found_creates_default` was failing in CI due to an uncaught UserWarning.

## Root Cause
```
UserWarning: Material unknown_material not found, adding default
  warnings.warn(f"Material {material} not found, adding default")
```

The test was checking that requesting an unknown material creates it with defaults. The code intentionally generates a warning when this happens (at `data.py:428`), but the test didn't explicitly expect/catch this warning using pytest's warning handling mechanism.

## Solution
Added `pytest.warns()` context manager to explicitly expect the UserWarning:

```python
def test_material_not_found_creates_default(self):
    """Test that requesting unknown material creates it with defaults"""
    dm = NuclearDataManager()

    # This should create the material automatically with a warning
    with pytest.warns(UserWarning, match="Material unknown_material not found"):
        xs = dm.get_material_xs("unknown_material", 2.0e6)

    assert "unknown_material" in dm.materials
    assert all(v >= 0 for v in xs.values())
```

## Benefits
1. **Test is more explicit**: Now clearly documents that a warning is expected
2. **CI compatible**: Works with strict warning policies
3. **Better test quality**: Validates that the warning is actually generated
4. **No functional changes**: Only improved test handling

## Verification
- ✅ Specific test passes without warnings
- ✅ All 10 tests in test_data.py pass
- ✅ Full test suite passes (86/86 tests)
- ✅ Black formatting maintained
- ✅ Flake8 linting passes

## Files Changed
- `tests/unit/test_data.py` (lines 130-139)

## Status
**FIXED** - Test now passes cleanly in CI
