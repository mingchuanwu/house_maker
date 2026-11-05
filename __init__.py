"""
HouseMaker - Professional Laser-Cut House Box Generator

A standalone Python library for generating precise laser-cut house boxes
with sophisticated finger joint coordination.
"""

from importlib.metadata import PackageNotFoundError, version as _dist_version

from .components import (
    RoofType, WindowType, DoorType, ArchitecturalStyle, ShingleType, Chimney, AdditionalGable
)
from .config import ArchitecturalConfiguration, create_preset_configuration
from .constants import HouseStyle
from .exceptions import (
    HouseMakerError,
    ValidationError,
    GeometryError,
    DimensionError,
    FingerJointError,
    SVGGenerationError,
    PlacementError
)
from .geometry import HouseGeometry
from .maker import HouseMaker
from .svg_generator import SVGGenerator

try:
    __version__ = _dist_version("house-maker")      # derived from the git tag at build time
except PackageNotFoundError:                         # running from a source tree that is not installed
    __version__ = "0+unknown"
__author__ = "HouseMaker Project"

__all__ = [
    'HouseMaker',
    'HouseGeometry',
    'SVGGenerator',
    'HouseStyle',
    'RoofType',
    'WindowType',
    'DoorType',
    'ArchitecturalStyle',
    'ShingleType',
    'Chimney',
    'AdditionalGable',
    'ArchitecturalConfiguration',
    'create_preset_configuration',
    'HouseMakerError',
    'ValidationError',
    'GeometryError',
    'DimensionError',
    'FingerJointError',
    'SVGGenerationError',
    'PlacementError'
]
