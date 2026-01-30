"""
Nuclear data management using ENDF and PENDF files
"""

import numpy as np
from typing import Dict
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
        self.inelastic = np.array([])
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
            return {
                "total": 0.0,
                "elastic": 0.0,
                "inelastic": 0.0,
                "capture": 0.0,
                "fission": 0.0,
            }

        # Linear interpolation
        # Note: log-log interpolation could be added for better accuracy
        xs = {}
        if len(self.energies) > 1:
            xs["total"] = np.interp(energy, self.energies, self.total)
            xs["elastic"] = np.interp(energy, self.energies, self.elastic)
            xs["inelastic"] = np.interp(energy, self.energies, self.inelastic)
            xs["capture"] = np.interp(energy, self.energies, self.capture)
            xs["fission"] = np.interp(energy, self.energies, self.fission)
        else:
            xs["total"] = self.total[0] if len(self.total) > 0 else 0.0
            xs["elastic"] = self.elastic[0] if len(self.elastic) > 0 else 0.0
            xs["inelastic"] = self.inelastic[0] if len(self.inelastic) > 0 else 0.0
            xs["capture"] = self.capture[0] if len(self.capture) > 0 else 0.0
            xs["fission"] = self.fission[0] if len(self.fission) > 0 else 0.0

        return xs


class NubarData:
    """Container for nubar (neutrons per fission) data"""

    def __init__(self):
        self.energies = np.array([])
        self.total = np.array([])  # Total nubar (prompt + delayed)
        self.prompt = np.array([])  # Prompt nubar
        self.delayed = np.array([])  # Delayed nubar

    def get_nubar_at_energy(self, energy: float) -> float:
        """
        Get nubar at given energy using linear interpolation

        Args:
            energy: Incident neutron energy in eV

        Returns:
            Average number of neutrons per fission
        """
        if len(self.energies) == 0 or len(self.total) == 0:
            # Default for U-235
            return 2.5

        if len(self.energies) == 1:
            return float(self.total[0])

        # Linear interpolation in energy
        return float(np.interp(energy, self.energies, self.total))


class FissionSpectrumData:
    """Container for fission neutron energy spectrum"""

    def __init__(self):
        self.spectrum_type = "none"  # 'watt', 'tabulated', 'none'
        self.params = {}

    def sample_energy(self, incident_energy: float = None) -> float:
        """
        Sample fission neutron energy from spectrum

        Args:
            incident_energy: Incident neutron energy in eV (may affect spectrum)

        Returns:
            Fission neutron energy in eV
        """
        if self.spectrum_type == "watt":
            # Watt spectrum: chi(E) = C * exp(-E/a) * sinh(sqrt(b*E))
            # Default parameters for U-235 thermal fission
            a = self.params.get("a", 0.988e6)  # eV
            b = self.params.get("b", 2.249e-6)  # 1/eV

            # Sample using rejection method
            # Maximum of Watt spectrum is around E ~ 0.7 MeV
            # Use simplified sampling: sample from maxwellian + rejection
            max_attempts = 1000
            for _ in range(max_attempts):
                # Sample from exponential distribution as proposal
                E = np.random.exponential(a)

                # Compute Watt probability (unnormalized)
                if E > 0 and b * E < 100:  # Avoid overflow
                    prob = np.exp(-E / a) * np.sinh(np.sqrt(b * E))

                    # Rejection sampling
                    # Max value of sinh(sqrt(b*E))/exp(-E/a) is around 1.5 for typical values
                    u = np.random.random()
                    max_val = 1.5
                    if u < prob / (max_val * np.exp(-E / a)):
                        return E

            # Fallback if rejection fails
            return np.random.exponential(a)

        elif self.spectrum_type == "tabulated":
            # Sample from tabulated distribution
            energies = self.params.get("energies", np.array([]))
            chi = self.params.get("chi", np.array([]))

            if len(energies) > 0 and len(chi) > 0:
                # Normalize chi
                chi_norm = chi / np.sum(chi)

                # Sample from discrete distribution
                idx = np.random.choice(len(energies), p=chi_norm)

                # Add some randomization within the bin
                if idx < len(energies) - 1:
                    E_low = energies[idx]
                    E_high = energies[idx + 1]
                    return E_low + np.random.random() * (E_high - E_low)
                else:
                    return energies[idx]

        # Default: use simplified exponential (backward compatibility)
        return np.random.exponential(1.0e6) + 0.5e6


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
                import endf_parserpy  # noqa: F401

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
            xs_data.inelastic = pendf_data.get("inelastic", np.zeros_like(xs_data.energies))
            xs_data.capture = pendf_data.get("capture", np.zeros_like(xs_data.energies))
            xs_data.fission = pendf_data.get("fission", np.zeros_like(xs_data.energies))

            # If total is not available, compute it
            if np.all(xs_data.total == 0):
                xs_data.total = xs_data.elastic + xs_data.capture + xs_data.fission

            # Extract nubar data
            nubar_data = NubarData()
            nubar_data.energies = pendf_data.get("nubar_energies", np.array([]))
            nubar_data.total = pendf_data.get("nubar_total", np.array([]))
            nubar_data.prompt = pendf_data.get("nubar_prompt", np.array([]))
            nubar_data.delayed = pendf_data.get("nubar_delayed", np.array([]))

            # Extract fission spectrum data
            fission_spectrum = FissionSpectrumData()
            fission_spectrum.spectrum_type = pendf_data.get("fission_spectrum_type", "none")
            fission_spectrum.params = pendf_data.get("fission_spectrum_params", {})

            self.materials[material_name] = {
                "xs_data": xs_data,
                "nubar_data": nubar_data,
                "fission_spectrum": fission_spectrum,
                "number_density": number_density,
                "source_format": "pendf",
                "temperature": temperature,
            }

            logger.info(f"Successfully loaded PENDF data for {material_name}")
            logger.info(
                f"  Energy range: {xs_data.energies[0]:.2e} to {xs_data.energies[-1]:.2e} eV"
            )
            logger.info(f"  Number of energy points: {len(xs_data.energies)}")

            if len(nubar_data.energies) > 0:
                logger.info(f"  Nubar data: {len(nubar_data.energies)} points")
                logger.info(
                    f"    Nubar range: {nubar_data.total[0]:.3f} to {nubar_data.total[-1]:.3f}"
                )
            else:
                logger.info("  No nubar data found (will use default)")

            if fission_spectrum.spectrum_type != "none":
                logger.info(f"  Fission spectrum: {fission_spectrum.spectrum_type}")
            else:
                logger.info("  No fission spectrum data (will use default)")

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
        xs_data.inelastic = np.array([0.0, 0.0, 0.0, 0.5, 1.0, 1.5, 2.0])
        xs_data.capture = np.array([1000.0, 10.0, 3.0, 1.0, 0.5, 0.3, 0.2])
        xs_data.fission = np.array([0.0, 0.0, 0.5, 1.0, 1.2, 1.0, 0.8])
        xs_data.total = xs_data.elastic + xs_data.inelastic + xs_data.capture + xs_data.fission

        # Default nubar data (U-235-like)
        nubar_data = NubarData()
        nubar_data.energies = np.array([1e-5, 1e6, 2e7])
        nubar_data.total = np.array([2.43, 2.5, 2.8])

        # Default fission spectrum (Watt parameters for U-235)
        fission_spectrum = FissionSpectrumData()
        fission_spectrum.spectrum_type = "watt"
        fission_spectrum.params = {
            "a": 0.988e6,  # eV
            "b": 2.249e-6,  # 1/eV
        }

        self.materials[material_name] = {
            "xs_data": xs_data,
            "nubar_data": nubar_data,
            "fission_spectrum": fission_spectrum,
            "number_density": number_density,
        }

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

    def get_nubar(self, material: str, energy: float) -> float:
        """
        Get nubar (average neutrons per fission) for a material at given energy

        Args:
            material: Material name
            energy: Incident neutron energy in eV

        Returns:
            Average number of neutrons per fission
        """
        if material not in self.materials:
            logger.warning(f"Material {material} not found, using default nubar")
            return 2.5

        nubar_data = self.materials[material].get("nubar_data")
        if nubar_data is None:
            # Default nubar if not available
            logger.debug(f"No nubar data for {material}, using default")
            return 2.5

        return nubar_data.get_nubar_at_energy(energy)

    def sample_fission_energy(self, material: str, incident_energy: float) -> float:
        """
        Sample fission neutron energy for a material

        Args:
            material: Material name
            incident_energy: Incident neutron energy in eV

        Returns:
            Fission neutron energy in eV
        """
        if material not in self.materials:
            logger.warning(f"Material {material} not found, using default fission spectrum")
            return np.random.exponential(1.0e6) + 0.5e6

        fission_spectrum = self.materials[material].get("fission_spectrum")
        if fission_spectrum is None:
            # Default spectrum if not available
            logger.debug(f"No fission spectrum for {material}, using default")
            return np.random.exponential(1.0e6) + 0.5e6

        return fission_spectrum.sample_energy(incident_energy)

    def load_library_directory(
        self, directory: str, isotopes: list = None, temperature: float = 293.6
    ):
        """
        Load multiple PENDF files from a directory

        Args:
            directory: Path to directory containing PENDF files
            isotopes: List of isotope names to load (e.g., ['U235', 'Pu239']).
                     If None, loads all files in directory.
            temperature: Temperature in Kelvin (default: 293.6K)

        Returns:
            Dictionary mapping isotope names to material names in the manager
        """
        from pathlib import Path
        import re

        data_dir = Path(directory)
        if not data_dir.exists():
            raise ValueError(f"Directory not found: {directory}")

        # Get list of PENDF files
        pendf_files = list(data_dir.glob("*.pendf"))

        if not pendf_files:
            logger.warning(f"No PENDF files found in {directory}")
            return {}

        loaded_materials = {}

        for pendf_file in pendf_files:
            # Parse filename to extract isotope info
            # Format: n-ZZZ_SYMBOL_AAA.pendf
            match = re.match(r"n-(\d+)_([A-Za-z]+)_(\d+)\.pendf", pendf_file.name)
            if not match:
                logger.warning(f"Could not parse filename: {pendf_file.name}")
                continue

            z_str, symbol, a_str = match.groups()
            isotope_name = f"{symbol}{a_str}"

            # Skip if not in requested list
            if isotopes is not None and isotope_name not in isotopes:
                continue

            # Load the file
            try:
                logger.info(f"Loading {isotope_name} from {pendf_file.name}...")

                # Default number density (can be changed later)
                number_density = 0.05  # atoms/barn-cm

                self.load_pendf_file(str(pendf_file), isotope_name, number_density, temperature)
                loaded_materials[isotope_name] = isotope_name

                logger.info(f"  ✓ Loaded {isotope_name}")

            except Exception as e:
                logger.error(f"  ✗ Failed to load {isotope_name}: {e}")

        logger.info(f"\nLoaded {len(loaded_materials)} isotopes from {directory}")
        return loaded_materials

    def load_jeff40_library(self, isotopes: list = None, temperature: float = 293.6):
        """
        Load JEFF 4.0 library from default location

        Looks for JEFF 4.0 files in ~/.picomc/data/jeff40/

        Args:
            isotopes: List of isotope names to load (e.g., ['U235', 'Pu239']).
                     If None, loads all available files.
            temperature: Temperature in Kelvin (default: 293.6K)

        Returns:
            Dictionary mapping isotope names to material names

        Example:
            >>> dm = NuclearDataManager()
            >>> materials = dm.load_jeff40_library(['U235', 'Pu239', 'H1'])
            >>> print(f"Loaded: {list(materials.keys())}")
        """
        from pathlib import Path

        # Default JEFF 4.0 location
        jeff40_dir = Path.home() / ".picomc" / "data" / "jeff40"

        if not jeff40_dir.exists():
            raise FileNotFoundError(
                f"JEFF 4.0 directory not found: {jeff40_dir}\n"
                f"Please download JEFF 4.0 files and place them in this directory.\n"
                f"Use: python bootstrap_jeff.py --help for instructions."
            )

        return self.load_library_directory(str(jeff40_dir), isotopes, temperature)

    def list_loaded_materials(self):
        """
        List all materials currently loaded in the manager

        Returns:
            List of material names
        """
        return list(self.materials.keys())

    def get_material_info(self, material: str) -> dict:
        """
        Get information about a loaded material

        Args:
            material: Material name

        Returns:
            Dictionary with material information
        """
        if material not in self.materials:
            raise ValueError(f"Material not found: {material}")

        mat = self.materials[material]
        xs_data = mat["xs_data"]

        info = {
            "name": material,
            "number_density": mat["number_density"],
            "energy_range": (
                (float(xs_data.energies[0]), float(xs_data.energies[-1]))
                if len(xs_data.energies) > 0
                else (0.0, 0.0)
            ),
            "num_energy_points": len(xs_data.energies),
            "has_fission": len(xs_data.fission) > 0 and np.max(xs_data.fission) > 0,
            "has_nubar": mat.get("nubar_data") is not None,
            "has_fission_spectrum": mat.get("fission_spectrum") is not None,
        }

        return info
