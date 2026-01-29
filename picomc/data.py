"""
Nuclear data management using ENDF and PENDF files
"""

import numpy as np
from typing import Dict, Optional, Tuple
import warnings
import logging

# Setup logger
logger = logging.getLogger(__name__)


class CrossSectionData:
    """Container for cross section data"""

    def __init__(self):
        self.energies = np.array([])
        self.total = np.array([])
        self.elastic = np.array([])
        self.capture = np.array([])
        self.fission = np.array([])

    def get_xs_at_energy(self, energy: float) -> Dict[str, float]:
        """
        Get cross sections at given energy using linear interpolation

        Args:
            energy: Energy in eV

        Returns:
            Dictionary with cross section values (barns)
        """
        if len(self.energies) == 0:
            return {"total": 0.0, "elastic": 0.0, "capture": 0.0, "fission": 0.0}

        # Linear interpolation
        # Note: log-log interpolation could be added for better accuracy
        xs = {}
        if len(self.energies) > 1:
            xs["total"] = np.interp(energy, self.energies, self.total)
            xs["elastic"] = np.interp(energy, self.energies, self.elastic)
            xs["capture"] = np.interp(energy, self.energies, self.capture)
            xs["fission"] = np.interp(energy, self.energies, self.fission)
        else:
            xs["total"] = self.total[0] if len(self.total) > 0 else 0.0
            xs["elastic"] = self.elastic[0] if len(self.elastic) > 0 else 0.0
            xs["capture"] = self.capture[0] if len(self.capture) > 0 else 0.0
            xs["fission"] = self.fission[0] if len(self.fission) > 0 else 0.0

        return xs


class NuclearDataManager:
    """
    Manager for nuclear data from ENDF and PENDF files

    This class handles loading and accessing nuclear data from:
    - ENDF format files (using endf-parserpy library)
    - PENDF format files (processed, linearized data) - library-agnostic
    - ACE format files (future support)
    """

    def __init__(self, use_endf: bool = False, data_format: str = "auto"):
        """
        Initialize nuclear data manager

        Args:
            use_endf: Whether to use ENDF data (requires endf-parserpy)
            data_format: Format of nuclear data files ('auto', 'endf', 'pendf', 'ace')
        """
        self.use_endf = use_endf
        self.data_format = data_format
        self.materials = {}
        self.endf_parser_available = False

        if use_endf:
            try:
                import endf_parserpy

                self.endf_parser_available = True
            except ImportError:
                warnings.warn(
                    "endf-parserpy not available. Install with: pip install endf-parserpy\n"
                    "Falling back to simple cross section model."
                )
                self.use_endf = False

    def load_endf_file(self, filepath: str, material_name: str, number_density: float = 1.0):
        """
        Load nuclear data from ENDF file

        Args:
            filepath: Path to ENDF file
            material_name: Name to assign to this material
            number_density: Number density in atoms/barn-cm
        """
        if not self.use_endf or not self.endf_parser_available:
            warnings.warn("ENDF parsing not available, using default data")
            self._add_default_material(material_name, number_density)
            return

        try:
            from endf_parserpy import EndfParser

            parser = EndfParser()
            endf_dict = parser.parsefile(filepath)

            xs_data = CrossSectionData()

            # Extract cross section data from ENDF
            # MF=3 contains cross sections
            if 3 in endf_dict.get("sections", {}):
                mf3 = endf_dict["sections"][3]

                # MT=1 is total cross section
                if 1 in mf3:
                    xs_data.energies = np.array(mf3[1].get("energies", []))
                    xs_data.total = np.array(mf3[1].get("xs", []))

                # MT=2 is elastic scattering
                if 2 in mf3:
                    xs_data.elastic = np.array(mf3[2].get("xs", []))

                # MT=18 is fission (if present)
                if 18 in mf3:
                    xs_data.fission = np.array(mf3[18].get("xs", []))

                # MT=102 is radiative capture
                if 102 in mf3:
                    xs_data.capture = np.array(mf3[102].get("xs", []))

            self.materials[material_name] = {"xs_data": xs_data, "number_density": number_density}

        except Exception as e:
            warnings.warn(f"Error loading ENDF file: {e}\nUsing default data")
            self.add_material(material_name, number_density)

    def load_pendf_file(
        self,
        filepath: str,
        material_name: str,
        number_density: float = 1.0,
        temperature: float = 293.6,
    ):
        """
        Load nuclear data from PENDF (Pointwise ENDF) file

        PENDF files contain processed nuclear data with linearized cross sections.
        This is library-agnostic and works with JEFF, ENDF/B, JENDL, etc.

        Args:
            filepath: Path to PENDF file
            material_name: Name to assign to this material
            number_density: Number density in atoms/barn-cm
            temperature: Temperature in Kelvin (default: 293.6K)
        """
        try:
            from picomc.pendf_parser import PENDFParser

            parser = PENDFParser()
            pendf_data = parser.parse_file(filepath, temperature)

            if not pendf_data or len(pendf_data.get("energies", [])) == 0:
                raise ValueError("No data extracted from PENDF file")

            xs_data = CrossSectionData()
            xs_data.energies = pendf_data["energies"]
            xs_data.total = pendf_data.get("total", np.zeros_like(xs_data.energies))
            xs_data.elastic = pendf_data.get("elastic", np.zeros_like(xs_data.energies))
            xs_data.capture = pendf_data.get("capture", np.zeros_like(xs_data.energies))
            xs_data.fission = pendf_data.get("fission", np.zeros_like(xs_data.energies))

            # If total is not available, compute it
            if np.all(xs_data.total == 0):
                xs_data.total = xs_data.elastic + xs_data.capture + xs_data.fission

            self.materials[material_name] = {
                "xs_data": xs_data,
                "number_density": number_density,
                "source_format": "pendf",
                "temperature": temperature,
            }

            logger.info(f"Successfully loaded PENDF data for {material_name}")
            logger.info(
                f"  Energy range: {xs_data.energies[0]:.2e} to {xs_data.energies[-1]:.2e} eV"
            )
            logger.info(f"  Number of energy points: {len(xs_data.energies)}")

        except Exception as e:
            warnings.warn(f"Error loading PENDF file: {e}\nUsing default data")
            self.add_material(material_name, number_density)

    def load_library_file(
        self,
        filepath: str,
        material_name: str,
        number_density: float = 1.0,
        file_format: str = "auto",
        temperature: float = 293.6,
    ):
        """
        Load nuclear data from any supported format (auto-detect or specify)

        Args:
            filepath: Path to nuclear data file
            material_name: Name to assign to this material
            number_density: Number density in atoms/barn-cm
            file_format: Format ('auto', 'endf', 'pendf', 'ace')
            temperature: Temperature in Kelvin for PENDF files
        """
        import os

        # Auto-detect format from file extension
        if file_format == "auto":
            ext = os.path.splitext(filepath)[1].lower()
            basename = os.path.basename(filepath).lower()

            if ext == ".pendf" or "pendf" in basename:
                file_format = "pendf"
            elif ext in [".ace", ".xsd", ".xsdir"]:
                file_format = "ace"
            elif ext in [".endf", ".txt"]:
                # Check if it's JEFF library by path
                if "jeff" in filepath.lower() and "pendf" in filepath.lower():
                    file_format = "pendf"
                else:
                    file_format = "endf"
            else:
                # Default to ENDF for unknown extensions
                file_format = "endf"

        if file_format == "pendf":
            self.load_pendf_file(filepath, material_name, number_density, temperature)
        elif file_format == "endf":
            self.load_endf_file(filepath, material_name, number_density)
        elif file_format == "ace":
            warnings.warn("ACE format not yet implemented, using default data")
            self.add_material(material_name, number_density)
        else:
            warnings.warn(f"Unknown format {file_format}, using default data")
            self.add_material(material_name, number_density)

    def add_material(self, material_name: str, number_density: float = 1.0):
        """
        Add a material with default cross sections (for testing/demo)

        Args:
            material_name: Name for the material
            number_density: Number density in atoms/barn-cm
        """
        xs_data = CrossSectionData()

        # Create simple energy grid (eV)
        xs_data.energies = np.array([1e-5, 1e-2, 1.0, 100.0, 1e4, 1e6, 2e7])

        # Simplified cross sections (barns)
        # These are rough approximations for demonstration
        xs_data.elastic = np.array([10.0, 10.0, 8.0, 5.0, 3.0, 2.0, 1.5])
        xs_data.capture = np.array([1000.0, 10.0, 3.0, 1.0, 0.5, 0.3, 0.2])
        xs_data.fission = np.array([0.0, 0.0, 0.5, 1.0, 1.2, 1.0, 0.8])
        xs_data.total = xs_data.elastic + xs_data.capture + xs_data.fission

        self.materials[material_name] = {"xs_data": xs_data, "number_density": number_density}

    # Keep old name for backwards compatibility
    def _add_default_material(self, material_name: str, number_density: float = 1.0):
        """Deprecated: Use add_material() instead"""
        self.add_material(material_name, number_density)

    def get_material_xs(self, material: str, energy: float) -> Dict[str, float]:
        """
        Get cross sections for a material at given energy

        Args:
            material: Material name
            energy: Energy in eV

        Returns:
            Dictionary with microscopic cross sections (barns)
        """
        if material not in self.materials:
            warnings.warn(f"Material {material} not found, adding default")
            self.add_material(material)

        xs_data = self.materials[material]["xs_data"]
        return xs_data.get_xs_at_energy(energy)

    def get_macroscopic_xs(self, material: str, energy: float) -> Dict[str, float]:
        """
        Get macroscopic cross sections for a material at given energy

        Args:
            material: Material name
            energy: Energy in eV

        Returns:
            Dictionary with macroscopic cross sections (cm^-1)
        """
        micro_xs = self.get_material_xs(material, energy)
        number_density = self.materials[material]["number_density"]

        # Macroscopic XS (cm^-1) = microscopic XS (barn) * N (atoms/barn-cm)
        # Since 1 barn = 1e-24 cm^2 and 1 atom/barn-cm = 1e24 atoms/cm^3,
        # these factors cancel out
        macro_xs = {}
        for key, value in micro_xs.items():
            macro_xs[key] = value * number_density

        return macro_xs
