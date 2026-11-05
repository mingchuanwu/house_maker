"""
HouseMaker - Professional Laser-Cut House Box Generator

A standalone Python library for generating precise laser-cut house boxes
with sophisticated finger joint coordination.
"""

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

__version__ = "1.0.0"
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
