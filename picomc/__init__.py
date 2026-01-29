"""
PicoMC - A simple Monte Carlo simulator for neutron transport

A modular, pythonic Monte Carlo code for neutron transport with ENDF/PENDF data support.
Includes CSG geometry support similar to Serpent and OpenMC.
"""

from picomc.simulator import Simulator
from picomc.geometry import Geometry, BoxGeometry, CSGGeometryWrapper
from picomc.particle import Particle
from picomc.data import NuclearDataManager
from picomc.tally import FluxTally

__version__ = "0.3.0"
__all__ = [
    "Simulator",
    "Geometry",
    "BoxGeometry",
    "CSGGeometryWrapper",
    "Particle",
    "NuclearDataManager",
    "FluxTally",
]
