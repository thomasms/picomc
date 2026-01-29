"""
PENDF (Pointwise ENDF) format parser

PENDF is a processed nuclear data format with linearized, unionized cross sections.
This module provides library-agnostic parsing for PENDF files from various sources
like JEFF, ENDF/B, JENDL, etc.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
import struct

# Parser configuration
MAX_TAB1_LOOKAHEAD_LINES = 100  # Maximum lines to search for TAB1 data


class PENDFParser:
    """
    Parser for PENDF (Pointwise ENDF) format files
    
    PENDF files contain processed nuclear data with:
    - Linearized cross sections (no resonances to process)
    - Unionized energy grids
    - Temperature-dependent data
    
    This parser is library-agnostic and works with JEFF, ENDF/B, JENDL, etc.
    """
    
    def __init__(self):
        self.data = {}
        
    def parse_file(self, filepath: str, temperature: float = 293.6) -> Dict:
        """
        Parse a PENDF file
        
        Args:
            filepath: Path to PENDF file
            temperature: Temperature in Kelvin (default: 293.6K = 20.43°C)
            
        Returns:
            Dictionary with parsed cross section data
        """
        try:
            # PENDF files can be ASCII or binary
            # Try ASCII first (most common for JEFF 4.0)
            return self._parse_ascii_pendf(filepath, temperature)
        except Exception as e:
            warnings.warn(f"Failed to parse PENDF file: {e}")
            return {}
    
    def _parse_ascii_pendf(self, filepath: str, temperature: float) -> Dict:
        """
        Parse ASCII PENDF file
        
        PENDF files use ENDF-6 format structure but with processed data
        """
        data = {
            'energies': [],
            'total': [],
            'elastic': [],
            'inelastic': [],
            'capture': [],
            'fission': [],
            'nu': [],  # Neutrons per fission
        }
        
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        # PENDF files use ENDF-6 format with TAB1/TAB2 records
        # MF=3 contains cross sections
        current_mf = 0
        current_mt = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # ENDF-6 format: columns 71-75 contain MF, 76-80 contain MT
            if len(line) >= 80:
                try:
                    mf = int(line[70:72].strip())
                    mt = int(line[72:75].strip())
                    
                    if mf == 3:  # Cross section data
                        # Parse TAB1 record for this MT
                        energies, xs = self._parse_tab1_record(lines, i)
                        
                        # Map MT numbers to reaction types
                        if mt == 1:  # Total
                            data['total'] = xs
                            if len(data['energies']) == 0:
                                data['energies'] = energies
                        elif mt == 2:  # Elastic
                            data['elastic'] = xs
                        elif mt >= 51 and mt <= 91:  # Inelastic
                            if len(data['inelastic']) == 0:
                                data['inelastic'] = xs
                            else:
                                data['inelastic'] = [a + b for a, b in zip(data['inelastic'], xs)]
                        elif mt == 18:  # Fission
                            data['fission'] = xs
                        elif mt == 102:  # Capture
                            data['capture'] = xs
                        
                except (ValueError, IndexError) as e:
                    # Ignore parsing errors for individual lines
                    pass
            
            i += 1
        
        # Convert to numpy arrays
        for key in data:
            if data[key]:
                data[key] = np.array(data[key])
        
        # If we didn't find energies, create empty arrays
        if len(data['energies']) == 0:
            return self._create_empty_data()
        
        return data
    
    def _parse_tab1_record(self, lines: List[str], start_idx: int) -> Tuple[List[float], List[float]]:
        """
        Parse a TAB1 record from ENDF-6 format
        
        TAB1 contains tabulated data (x, y pairs)
        """
        energies = []
        values = []
        
        # This is a simplified parser - full ENDF-6 TAB1 parsing is complex
        # For now, we'll extract what we can
        
        # Look for data pairs in the following lines
        i = start_idx + 1
        max_lines = min(start_idx + MAX_TAB1_LOOKAHEAD_LINES, len(lines))
        
        while i < max_lines:
            line = lines[i]
            if len(line) < 66:
                i += 1
                continue
                
            # Try to extract number pairs from the line
            try:
                # ENDF format: 6 fields of 11 characters each
                for j in range(0, 66, 11):
                    val_str = line[j:j+11].strip()
                    if val_str:  # Accept all values including zero
                        try:
                            val = float(val_str)
                            if len(energies) <= len(values):
                                energies.append(val)
                            else:
                                values.append(val)
                        except ValueError:
                            pass
            except Exception:
                pass
            
            i += 1
            
            # Stop if we have enough data or see a new section
            if len(energies) > 10 and len(values) > 10:
                break
        
        # Make sure we have pairs
        min_len = min(len(energies), len(values))
        return energies[:min_len], values[:min_len]
    
    def _create_empty_data(self) -> Dict:
        """Create empty data structure"""
        return {
            'energies': np.array([]),
            'total': np.array([]),
            'elastic': np.array([]),
            'inelastic': np.array([]),
            'capture': np.array([]),
            'fission': np.array([]),
            'nu': np.array([]),
        }


class ACEParser:
    """
    Parser for ACE (A Compact ENDF) format files
    
    ACE is another common format, especially for MCNP.
    This provides an alternative to PENDF.
    """
    
    def __init__(self):
        self.data = {}
    
    def parse_file(self, filepath: str) -> Dict:
        """
        Parse an ACE format file
        
        Args:
            filepath: Path to ACE file
            
        Returns:
            Dictionary with parsed cross section data
        """
        # ACE format parsing - placeholder for future implementation
        warnings.warn("ACE format parsing not yet implemented")
        return {}
