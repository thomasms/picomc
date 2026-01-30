#!/usr/bin/env python
"""
Bootstrap script to download and setup JEFF 4.0 PENDF nuclear data library

This script downloads PENDF files from the OECD-NEA JEFF 4.0 library
and provides utilities for loading multiple isotopes at once.

Usage:
    python bootstrap_jeff.py --download-all    # Download entire library
    python bootstrap_jeff.py --download H1 U235 Pu239  # Download specific isotopes
    python bootstrap_jeff.py --list            # List available isotopes

JEFF 4.0 library: https://data.oecd-nea.org/records/wgw94-qcx30
"""

import os
import sys
import argparse
import urllib.request
from pathlib import Path
from typing import List, Optional
import json

# Base URL for JEFF 4.0 PENDF library
JEFF40_BASE_URL = "https://www.oecd-nea.org/jcms/pl_38066/jeff-3.3"  # Note: JEFF 4.0 may not be directly downloadable
# Alternative: Users may need to manually download from https://data.oecd-nea.org/records/wgw94-qcx30

# Common isotopes and their filenames
COMMON_ISOTOPES = {
    # Light elements
    "H1": "n-001_H_001.pendf",
    "H2": "n-001_H_002.pendf",
    "H3": "n-001_H_003.pendf",
    "He3": "n-002_He_003.pendf",
    "He4": "n-002_He_004.pendf",
    # Structural materials
    "C": "n-006_C_000.pendf",
    "N14": "n-007_N_014.pendf",
    "O16": "n-008_O_016.pendf",
    "Fe56": "n-026_Fe_056.pendf",
    "Cr52": "n-024_Cr_052.pendf",
    "Ni58": "n-028_Ni_058.pendf",
    # Fissile materials
    "U233": "n-092_U_233.pendf",
    "U235": "n-092_U_235.pendf",
    "U238": "n-092_U_238.pendf",
    "Pu239": "n-094_Pu_239.pendf",
    "Pu240": "n-094_Pu_240.pendf",
    "Pu241": "n-094_Pu_241.pendf",
    # Moderators/Coolants
    "Be9": "n-004_Be_009.pendf",
    "C12": "n-006_C_012.pendf",
    "Na23": "n-011_Na_023.pendf",
    # Control/Absorbers
    "B10": "n-005_B_010.pendf",
    "B11": "n-005_B_011.pendf",
    "Cd113": "n-048_Cd_113.pendf",
    "Gd155": "n-064_Gd_155.pendf",
    "Gd157": "n-064_Gd_157.pendf",
}


def get_data_dir() -> Path:
    """
    Get the directory for storing nuclear data files

    Creates ~/.picomc/data/ if it doesn't exist

    Returns:
        Path to data directory
    """
    data_dir = Path.home() / ".picomc" / "data" / "jeff40"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def download_file(url: str, destination: Path, progress: bool = True):
    """
    Download a file with progress indication

    Args:
        url: URL to download from
        destination: Local file path to save to
        progress: Show progress indicator
    """
    if destination.exists():
        print(f"  Already exists: {destination.name}")
        return

    try:
        if progress:
            print(f"  Downloading: {destination.name}...")

        urllib.request.urlretrieve(url, destination)

        if progress:
            print(f"  ✓ Downloaded: {destination.name}")

    except Exception as e:
        print(f"  ✗ Failed to download {destination.name}: {e}")
        if destination.exists():
            destination.unlink()


def download_isotope(isotope: str, data_dir: Path):
    """
    Download PENDF file for a specific isotope

    Args:
        isotope: Isotope name (e.g., 'U235', 'H1')
        data_dir: Directory to save file in
    """
    if isotope not in COMMON_ISOTOPES:
        print(f"Unknown isotope: {isotope}")
        print(f"Available isotopes: {', '.join(sorted(COMMON_ISOTOPES.keys()))}")
        return False

    filename = COMMON_ISOTOPES[isotope]
    destination = data_dir / filename

    # Note: Direct JEFF 4.0 downloads may not be available
    # Users should download manually from https://data.oecd-nea.org/records/wgw94-qcx30
    print(f"\nIsotope: {isotope}")
    print(f"  Filename: {filename}")
    print(f"  Destination: {destination}")
    print(f"  NOTE: JEFF 4.0 files may need to be downloaded manually from:")
    print(f"        https://data.oecd-nea.org/records/wgw94-qcx30")
    print(f"  Place the file in: {data_dir}")

    return True


def list_isotopes():
    """List all available isotopes"""
    print("\nAvailable isotopes in JEFF 4.0 library:")
    print("=" * 60)

    categories = {
        "Light Elements": ["H1", "H2", "H3", "He3", "He4"],
        "Structural Materials": ["C", "N14", "O16", "Fe56", "Cr52", "Ni58"],
        "Fissile Materials": ["U233", "U235", "U238", "Pu239", "Pu240", "Pu241"],
        "Moderators/Coolants": ["Be9", "C12", "Na23"],
        "Control/Absorbers": ["B10", "B11", "Cd113", "Gd155", "Gd157"],
    }

    for category, isotopes in categories.items():
        print(f"\n{category}:")
        for iso in isotopes:
            if iso in COMMON_ISOTOPES:
                print(f"  {iso:10s} -> {COMMON_ISOTOPES[iso]}")


def create_library_index(data_dir: Path):
    """
    Create an index of available PENDF files

    Args:
        data_dir: Directory containing PENDF files
    """
    index_file = data_dir / "library_index.json"

    # Scan for PENDF files
    pendf_files = list(data_dir.glob("*.pendf"))

    index = {"library": "JEFF 4.0", "files": [], "isotopes": {}}

    for pendf_file in pendf_files:
        # Parse filename to extract isotope info
        # Format: n-ZZZ_SYMBOL_AAA.pendf
        parts = pendf_file.stem.split("_")
        if len(parts) >= 3:
            z_str = parts[0].split("-")[1]  # Extract ZZZ
            symbol = parts[1]
            a_str = parts[2]

            isotope_key = f"{symbol}{a_str}"

            index["files"].append(str(pendf_file.name))
            index["isotopes"][isotope_key] = {
                "filename": str(pendf_file.name),
                "element": symbol,
                "mass_number": a_str,
                "atomic_number": z_str,
            }

    # Write index
    with open(index_file, "w") as f:
        json.dump(index, f, indent=2)

    print(f"\nCreated library index: {index_file}")
    print(f"Found {len(index['files'])} PENDF files")
    print(f"Indexed {len(index['isotopes'])} isotopes")


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap JEFF 4.0 PENDF nuclear data library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available isotopes
  python bootstrap_jeff.py --list
  
  # Get info about downloading specific isotopes
  python bootstrap_jeff.py --download H1 U235 Pu239
  
  # Create index of downloaded files
  python bootstrap_jeff.py --index
  
Note: JEFF 4.0 files must be downloaded manually from:
  https://data.oecd-nea.org/records/wgw94-qcx30
  
Place downloaded files in: ~/.picomc/data/jeff40/
        """,
    )

    parser.add_argument("--list", action="store_true", help="List available isotopes")

    parser.add_argument(
        "--download",
        nargs="+",
        metavar="ISOTOPE",
        help="Download specific isotopes (e.g., H1 U235 Pu239)",
    )

    parser.add_argument(
        "--index", action="store_true", help="Create index of downloaded PENDF files"
    )

    parser.add_argument(
        "--data-dir", type=str, help="Custom data directory (default: ~/.picomc/data/jeff40/)"
    )

    args = parser.parse_args()

    # Get data directory
    if args.data_dir:
        data_dir = Path(args.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
    else:
        data_dir = get_data_dir()

    print(f"Data directory: {data_dir}")

    # Handle commands
    if args.list:
        list_isotopes()

    elif args.download:
        print("\nDownload Information:")
        print("=" * 60)
        for isotope in args.download:
            download_isotope(isotope, data_dir)

    elif args.index:
        create_library_index(data_dir)

    else:
        parser.print_help()
        print("\nQuick start:")
        print("  1. List available isotopes:")
        print("     python bootstrap_jeff.py --list")
        print("\n  2. Download JEFF 4.0 files manually from:")
        print("     https://data.oecd-nea.org/records/wgw94-qcx30")
        print(f"\n  3. Place files in: {data_dir}")
        print("\n  4. Create index:")
        print("     python bootstrap_jeff.py --index")


if __name__ == "__main__":
    main()
