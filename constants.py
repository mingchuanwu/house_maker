"""Shared constants and enums for HouseMaker."""

import math
from enum import IntEnum


class HouseStyle(IntEnum):
    """Which main panels make up the house"""
    BASIC_HOUSE = 1          # Floor + 4 walls + 2 roof panels
    HOUSE_NO_ROOF = 2        # Floor + 4 walls only
    WALLS_ONLY = 3           # 4 walls only (no floor or roof)


# Laser kerf compensation (mm) used unless the caller says otherwise
DEFAULT_KERF = 0.1

DEGREES_TO_RADIANS = math.pi / 180.0

# Decimal places for SVG coordinates (0.001mm)
COORDINATE_PRECISION = 3
