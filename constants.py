"""
Constants and enums for HouseMaker project
Based on the detailed specification diagrams provided
"""

from enum import Enum, IntEnum
import math


class HouseStyle(IntEnum):
    """House assembly styles"""
    BASIC_HOUSE = 1          # Floor + 4 walls + 2 roof panels
    HOUSE_NO_ROOF = 2        # Floor + 4 walls only
    WALLS_ONLY = 3           # 4 walls only (no floor or roof)


class RoofType(Enum):
    """Roof panel types"""
    STANDARD = "standard"     # Basic angled roof panels
    EXTENDED = "extended"     # Roof panels with overhangs


class WindowStyle(Enum):
    """Window cutting styles"""
    NONE = "none"
    RECTANGULAR = "rectangular"
    ARCHED = "arched"
    CIRCULAR = "circular"


class EdgeType(Enum):
    """Edge/joint types for finger joints"""
    FINGER_JOINT = "finger"   # Standard interlocking finger joints
    PLAIN = "plain"           # Straight edges (no joints)


# Default dimensions (mm)
DEFAULT_LENGTH = 100.0        # x dimension
DEFAULT_WIDTH = 100.0         # y dimension  
DEFAULT_HEIGHT = 80.0         # z dimension (wall height)
DEFAULT_GABLE_ANGLE = 45.0    # θ (theta) in degrees
DEFAULT_MATERIAL_THICKNESS = 3.0  # w (material thickness)

# Finger joint parameters
DEFAULT_FINGER_LENGTH = 15.0   # l (finger joint length)
DEFAULT_KERF = 0.1            # Laser kerf compensation
DEFAULT_SPACING = 20.0        # Layout spacing between parts

# Validation constraints
MIN_DIMENSION = 30.0          # Minimum practical size
MAX_DIMENSION = 1000.0        # Maximum reasonable size  
MIN_GABLE_ANGLE = 20.0        # Minimum roof angle (degrees)
MAX_GABLE_ANGLE = 70.0        # Maximum roof angle (degrees)
MIN_THICKNESS = 0.5           # Minimum material thickness
MAX_THICKNESS = 20.0          # Maximum material thickness

# Geometric constants
DEGREES_TO_RADIANS = math.pi / 180.0
RADIANS_TO_DEGREES = 180.0 / math.pi

# Layout and spacing
PANEL_SPACING_MULTIPLIER = 1.2  # Extra space for angled panels
GABLE_EXTRA_SPACING = 1.5       # Additional spacing for gable walls

# Precision settings
COORDINATE_PRECISION = 3      # Decimal places for SVG coordinates
ANGLE_PRECISION = 2          # Decimal places for angle calculations