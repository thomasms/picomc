# Migration to endf-parserpy

## Summary

Successfully replaced the custom PENDF parser implementation with the `endf-parserpy` library as requested. This provides robust, standards-compliant parsing of ENDF-6 format files.

## Changes Made

### 1. `picomc/pendf_parser.py`

**Before:**
- Custom implementation attempting to parse ENDF-6 format
- Manual line-by-line parsing with regex
- Limited TAB1 record support
- ~210 lines of custom parsing code

**After:**
- Uses `endf_parserpy.EndfParserPy()` for all parsing
- Extracts data from parsed EndfDict structures
- Proper handling of ENDF-6 format specifications
- ~260 lines with better error handling and logging
- Removed unused ACEParser class

**Key Implementation Details:**
```python
# Parse file using endf-parserpy
parser = endf.EndfParserPy()
endf_dict = parser.parsefile(filepath, include=(3,))

# Extract cross sections from MF=3 (cross section data)
mf3 = endf_dict[3]
mt1 = mf3[1]  # Total cross section
mt2 = mf3[2]  # Elastic scattering
mt18 = mf3[18]  # Fission
mt102 = mf3[102]  # Radiative capture
```

### 2. `setup.py`

**Before:**
```python
install_requires=[
    "numpy>=1.20.0",
    "matplotlib>=3.3.0",
],
extras_require={
    "endf": ["endf-parserpy>=0.7.0"],
    ...
}
```

**After:**
```python
install_requires=[
    "numpy>=1.20.0",
    "matplotlib>=3.3.0",
    "endf-parserpy>=0.7.0",
],
extras_require={
    "dev": [...],
}
```

### 3. Documentation Updates

- **ENDF_GUIDE.md**: Updated to mention endf-parserpy is used for parsing
- **README.md**: Clarified that endf-parserpy is now a required dependency

## Benefits

1. **Robust Parsing**: Uses well-tested, standards-compliant parser
2. **Maintainable**: Delegates complexity to dedicated library maintained by experts
3. **Feature Complete**: Full ENDF-6 format support including PENDF
4. **Error Handling**: Better error messages and parsing diagnostics
5. **Library Agnostic**: Works with JEFF, ENDF/B, JENDL, and other ENDF-based libraries

## Testing

All existing tests pass without modification:
```
✓ 71 tests passing
✓ 12 CSG geometry tests
✓ 3 integration tests
✓ 10 nuclear data tests
✓ 10 particle tests
✓ 14 physics tests
✓ 22 random sampling tests
```

## Compatibility

- **Backward Compatible**: Same API for users
- **Return Format**: Unchanged dictionary structure
- **Error Handling**: Improved with better warnings and logging

## Usage Example

```python
from picomc.pendf_parser import PENDFParser

# Initialize parser (automatically checks for endf-parserpy)
parser = PENDFParser()

# Parse PENDF file from any library (JEFF, ENDF/B, JENDL, etc.)
data = parser.parse_file('path/to/n-092_U_235.pendf', temperature=293.6)

# Returns dictionary with cross section data
# data = {
#     'energies': np.array([...]),
#     'total': np.array([...]),
#     'elastic': np.array([...]),
#     'capture': np.array([...]),
#     'fission': np.array([...]),
#     'inelastic': np.array([...]),
#     'nu': np.array([...])
# }
```

## Migration Notes for Users

Users who previously installed with `pip install -e ".[endf]"` can now simply use:
```bash
pip install -e .
```

The endf-parserpy dependency is now included automatically.

## Future Enhancements

Now that we're using endf-parserpy, we can easily add support for:
- Additional MF/MT sections (angular distributions, energy distributions, etc.)
- Temperature-dependent data extraction
- Multi-group cross section generation
- Resonance reconstruction (if needed)

## References

- endf-parserpy: https://github.com/IAEA-NDS/endf-parserpy
- ENDF-6 Format: https://www.oecd-nea.org/dbdata/data/manual-endf/
- JEFF 4.0: https://data.oecd-nea.org/records/wgw94-qcx30
