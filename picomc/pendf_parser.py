"""
PENDF (Pointwise ENDF) format parser using endf-parserpy

PENDF is a processed nuclear data format with linearized, unionized cross sections.
This module provides library-agnostic parsing for PENDF files from various sources
like JEFF, ENDF/B, JENDL, etc.

This implementation uses the endf-parserpy package for robust ENDF-6 format parsing.
"""

import numpy as np
from typing import Dict
import warnings
import logging

# Setup logger
logger = logging.getLogger(__name__)


class PENDFParser:
    """
    Parser for PENDF (Pointwise ENDF) format files using endf-parserpy

    PENDF files contain processed nuclear data with:
    - Linearized cross sections (no resonances to process)
    - Unionized energy grids
    - Temperature-dependent data

    This parser is library-agnostic and works with JEFF, ENDF/B, JENDL, etc.
    It uses endf-parserpy for robust parsing of ENDF-6 format files.
    """

    def __init__(self):
        self.data = {}
        self._check_endf_parserpy()

    def _check_endf_parserpy(self):
        """Check if endf-parserpy is available"""
        try:
            import endf_parserpy

            self.endf_parserpy_available = True
            logger.debug(f"endf-parserpy version {endf_parserpy.__version__} available")
        except ImportError:
            self.endf_parserpy_available = False
            warnings.warn(
                "endf-parserpy not available. Install with: pip install endf-parserpy\n"
                "PENDF parsing will not work without it."
            )

    def parse_file(self, filepath: str, temperature: float = 293.6) -> Dict:
        """
        Parse a PENDF file using endf-parserpy

        Args:
            filepath: Path to PENDF file
            temperature: Temperature in Kelvin (default: 293.6K = 20.43°C)
                        Note: This is informational; the file should already
                        contain data for the desired temperature

        Returns:
            Dictionary with parsed cross section data:
            {
                'energies': np.array,
                'total': np.array,
                'elastic': np.array,
                'inelastic': np.array,
                'capture': np.array,
                'fission': np.array,
                'nu': np.array
            }
        """
        if not self.endf_parserpy_available:
            warnings.warn("endf-parserpy not available, returning empty data")
            return self._create_empty_data()

        try:
            import endf_parserpy as endf

            # Use EndfParserPy with PENDF recipe
            parser = endf.EndfParserPy()

            # Parse the file with PENDF flavor
            # Include only MF=3 (cross sections) for efficiency
            logger.info(f"Parsing PENDF file: {filepath}")
            endf_dict = parser.parsefile(filepath, include=(3,))

            # Extract cross section data
            data = self._extract_cross_sections(endf_dict)

            logger.info(
                f"Successfully parsed PENDF file with {len(data['energies'])} energy points"
            )
            return data

        except Exception as e:
            logger.error(f"Failed to parse PENDF file: {e}")
            warnings.warn(f"Failed to parse PENDF file: {e}")
            return self._create_empty_data()

    def _extract_cross_sections(self, endf_dict: Dict) -> Dict:
        """
        Extract cross section data from parsed ENDF dictionary

        Args:
            endf_dict: Parsed ENDF data from endf-parserpy

        Returns:
            Dictionary with cross section arrays
        """
        data = {
            "energies": np.array([]),
            "total": np.array([]),
            "elastic": np.array([]),
            "inelastic": np.array([]),
            "capture": np.array([]),
            "fission": np.array([]),
            "nu": np.array([]),
        }

        # MF=3 contains cross section data
        if 3 not in endf_dict:
            logger.warning("No MF=3 (cross sections) found in PENDF file")
            return data

        mf3 = endf_dict[3]

        # Extract energy grid and cross sections for each MT
        # MT numbers: 1=total, 2=elastic, 18=fission, 102=capture, etc.

        # MT=1: Total cross section - use this for energy grid
        if 1 in mf3:
            mt1 = mf3[1]
            data["energies"], data["total"] = self._extract_tab1_data(mt1)
            logger.debug(f"Extracted MT=1 (total): {len(data['energies'])} points")

        # MT=2: Elastic scattering
        if 2 in mf3:
            mt2 = mf3[2]
            _, data["elastic"] = self._extract_tab1_data(mt2)
            logger.debug(f"Extracted MT=2 (elastic): {len(data['elastic'])} points")

        # MT=18: Fission
        if 18 in mf3:
            mt18 = mf3[18]
            _, data["fission"] = self._extract_tab1_data(mt18)
            logger.debug(f"Extracted MT=18 (fission): {len(data['fission'])} points")

        # MT=102: Radiative capture
        if 102 in mf3:
            mt102 = mf3[102]
            _, data["capture"] = self._extract_tab1_data(mt102)
            logger.debug(f"Extracted MT=102 (capture): {len(data['capture'])} points")

        # Inelastic scattering: MT=51-91
        # Sum all inelastic contributions
        inelastic_sum = None
        for mt in range(51, 92):
            if mt in mf3:
                _, xs = self._extract_tab1_data(mf3[mt])
                if inelastic_sum is None:
                    inelastic_sum = xs
                else:
                    # Add if same length, otherwise skip
                    if len(xs) == len(inelastic_sum):
                        inelastic_sum = inelastic_sum + xs

        if inelastic_sum is not None:
            data["inelastic"] = inelastic_sum
            logger.debug(f"Extracted inelastic (MT=51-91): {len(data['inelastic'])} points")

        # Ensure all arrays are the same length (use energy grid length)
        n_points = len(data["energies"])
        for key in ["total", "elastic", "capture", "fission", "inelastic"]:
            if len(data[key]) == 0:
                data[key] = np.zeros(n_points)
            elif len(data[key]) != n_points:
                logger.warning(
                    f"{key} has {len(data[key])} points, expected {n_points}. Padding with zeros."
                )
                # Interpolate or pad to match energy grid
                if len(data[key]) > 0:
                    data[key] = np.interp(
                        data["energies"],
                        data["energies"][: len(data[key])],
                        data[key],
                        left=0.0,
                        right=0.0,
                    )
                else:
                    data[key] = np.zeros(n_points)

        return data

    def _extract_tab1_data(self, mt_dict: Dict) -> tuple:
        """
        Extract energy and cross section data from TAB1 record

        Args:
            mt_dict: Dictionary for a specific MT section

        Returns:
            Tuple of (energies, cross_sections) as numpy arrays
        """
        try:
            # TAB1 data structure in endf-parserpy
            # Look for 'xstable' or 'sigma' keys (common in PENDF)
            if "xstable" in mt_dict:
                # Format: xstable contains x and y arrays
                table = mt_dict["xstable"]
                if isinstance(table, dict):
                    x = np.array(table.get("x", []))
                    y = np.array(table.get("y", []))
                    return x, y

            # Alternative: look for 'energy' and 'xs' or 'sigma'
            if "energy" in mt_dict and "xs" in mt_dict:
                x = np.array(mt_dict["energy"])
                y = np.array(mt_dict["xs"])
                return x, y

            if "energy" in mt_dict and "sigma" in mt_dict:
                x = np.array(mt_dict["energy"])
                y = np.array(mt_dict["sigma"])
                return x, y

            # Try to find arrays in the dictionary
            # endf-parserpy typically stores data with specific keys
            for key in mt_dict.keys():
                if "table" in str(key).lower() or "data" in str(key).lower():
                    table = mt_dict[key]
                    if isinstance(table, dict):
                        if "x" in table and "y" in table:
                            x = np.array(table["x"])
                            y = np.array(table["y"])
                            return x, y

            # If we reach here, we couldn't find the data
            logger.warning(f"Could not extract TAB1 data. Available keys: {list(mt_dict.keys())}")
            return np.array([]), np.array([])

        except Exception as e:
            logger.error(f"Error extracting TAB1 data: {e}")
            return np.array([]), np.array([])

    def _create_empty_data(self) -> Dict:
        """Create empty data structure"""
        return {
            "energies": np.array([]),
            "total": np.array([]),
            "elastic": np.array([]),
            "inelastic": np.array([]),
            "capture": np.array([]),
            "fission": np.array([]),
            "nu": np.array([]),
        }
