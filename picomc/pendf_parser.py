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
                'nubar_energies': np.array,
                'nubar_total': np.array,
                'nubar_prompt': np.array,
                'nubar_delayed': np.array,
                'fission_spectrum_type': str,
                'fission_spectrum_params': dict
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
            # Include MF=1 (nubar), MF=3 (cross sections), MF=5 (fission spectrum)
            logger.info(f"Parsing PENDF file: {filepath}")
            endf_dict = parser.parsefile(filepath, include=(1, 3, 5))

            # Extract cross section data
            data = self._extract_cross_sections(endf_dict)

            # Extract nubar data (MF=1)
            nubar_data = self._extract_nubar(endf_dict)
            data.update(nubar_data)

            # Extract fission spectrum data (MF=5, MT=18)
            fission_spectrum = self._extract_fission_spectrum(endf_dict)
            data.update(fission_spectrum)

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

    def _extract_nubar(self, endf_dict: Dict) -> Dict:
        """
        Extract nubar (average neutrons per fission) from MF=1

        Args:
            endf_dict: Parsed ENDF data from endf-parserpy

        Returns:
            Dictionary with nubar data:
            {
                'nubar_energies': np.array,
                'nubar_total': np.array,  # MT=452
                'nubar_prompt': np.array,  # MT=456
                'nubar_delayed': np.array  # MT=455
            }
        """
        nubar_data = {
            "nubar_energies": np.array([]),
            "nubar_total": np.array([]),
            "nubar_prompt": np.array([]),
            "nubar_delayed": np.array([]),
        }

        # MF=1 contains multiplicities (nubar)
        if 1 not in endf_dict:
            logger.debug("No MF=1 (nubar) found in file")
            return nubar_data

        mf1 = endf_dict[1]

        # MT=452: Total nubar (prompt + delayed)
        if 452 in mf1:
            energies, nubar = self._extract_tab1_data(mf1[452])
            nubar_data["nubar_energies"] = energies
            nubar_data["nubar_total"] = nubar
            logger.debug(f"Extracted MT=452 (total nubar): {len(nubar)} points")

        # MT=456: Prompt nubar
        if 456 in mf1:
            _, nubar = self._extract_tab1_data(mf1[456])
            nubar_data["nubar_prompt"] = nubar
            logger.debug(f"Extracted MT=456 (prompt nubar): {len(nubar)} points")

        # MT=455: Delayed nubar
        if 455 in mf1:
            _, nubar = self._extract_tab1_data(mf1[455])
            nubar_data["nubar_delayed"] = nubar
            logger.debug(f"Extracted MT=455 (delayed nubar): {len(nubar)} points")

        # If only prompt or only total is available, use that
        if len(nubar_data["nubar_total"]) == 0 and len(nubar_data["nubar_prompt"]) > 0:
            nubar_data["nubar_total"] = nubar_data["nubar_prompt"]
            logger.debug("Using prompt nubar as total nubar")

        return nubar_data

    def _extract_fission_spectrum(self, endf_dict: Dict) -> Dict:
        """
        Extract fission neutron energy spectrum from MF=5, MT=18

        The fission spectrum can be:
        - Watt spectrum (LF=11): chi(E) = C * exp(-E/a) * sinh(sqrt(b*E))
        - Tabulated spectrum (LF=1): chi(E) as tabulated function
        - Other representations

        Args:
            endf_dict: Parsed ENDF data from endf-parserpy

        Returns:
            Dictionary with fission spectrum data:
            {
                'fission_spectrum_type': 'watt' or 'tabulated' or 'none',
                'fission_spectrum_params': dict with parameters or tabulated data
            }
        """
        spectrum_data = {
            "fission_spectrum_type": "none",
            "fission_spectrum_params": {},
        }

        # MF=5 contains energy distributions
        if 5 not in endf_dict:
            logger.debug("No MF=5 (energy distributions) found in file")
            return spectrum_data

        mf5 = endf_dict[5]

        # MT=18: Fission
        if 18 not in mf5:
            logger.debug("No MT=18 in MF=5 (fission spectrum)")
            return spectrum_data

        mt18 = mf5[18]

        # Check the format (LF flag)
        # LF=1: Tabulated spectrum
        # LF=11: Watt spectrum
        # LF=12: Madland-Nix spectrum

        # Try to extract based on structure
        # This depends on how endf-parserpy stores this data
        try:
            # Look for Watt spectrum parameters
            if "NK" in mt18:  # Number of subsections
                nk = mt18["NK"]
                if nk > 0:
                    # Try to find Watt parameters
                    # Typically stored in subsections
                    for key in mt18.keys():
                        if "subsection" in str(key).lower() or isinstance(mt18[key], dict):
                            subsec = mt18[key]
                            if isinstance(subsec, dict):
                                # Check for LF flag
                                lf = subsec.get("LF", 0)

                                if lf == 11:  # Watt spectrum
                                    # Extract a and b parameters
                                    # Format: a and b may be given as TAB1 (energy-dependent)
                                    # or as constants
                                    spectrum_data["fission_spectrum_type"] = "watt"

                                    # Try to extract parameters
                                    if "U" in subsec:  # U parameter (typically = a)
                                        spectrum_data["fission_spectrum_params"]["a"] = subsec["U"]
                                    if "theta" in subsec:  # theta parameter
                                        spectrum_data["fission_spectrum_params"]["theta"] = subsec[
                                            "theta"
                                        ]

                                    # For Watt: a and b parameters
                                    # Sometimes given as CONT record
                                    # Default Watt for U-235: a ≈ 0.988 MeV, b ≈ 2.249 MeV^-1

                                    logger.info("Found Watt spectrum parameters")
                                    break

                                elif lf == 1:  # Tabulated
                                    spectrum_data["fission_spectrum_type"] = "tabulated"
                                    # Extract tabulated data
                                    energies, chi = self._extract_tab1_data(subsec)
                                    spectrum_data["fission_spectrum_params"] = {
                                        "energies": energies,
                                        "chi": chi,
                                    }
                                    logger.info(
                                        f"Found tabulated fission spectrum with {len(energies)} points"
                                    )
                                    break

            # If we didn't find anything, log available keys
            if spectrum_data["fission_spectrum_type"] == "none":
                logger.debug(
                    f"Could not extract fission spectrum. Available keys in MT=18: {list(mt18.keys())}"
                )

        except Exception as e:
            logger.warning(f"Error extracting fission spectrum: {e}")

        return spectrum_data

    def _create_empty_data(self) -> Dict:
        """Create empty data structure"""
        return {
            "energies": np.array([]),
            "total": np.array([]),
            "elastic": np.array([]),
            "inelastic": np.array([]),
            "capture": np.array([]),
            "fission": np.array([]),
            "nubar_energies": np.array([]),
            "nubar_total": np.array([]),
            "nubar_prompt": np.array([]),
            "nubar_delayed": np.array([]),
            "fission_spectrum_type": "none",
            "fission_spectrum_params": {},
        }
