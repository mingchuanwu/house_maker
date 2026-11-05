"""
Cutout outlines for windows and doors, as SVG path strings in panel-local coordinates.

Extension point: add a WindowType/DoorType by writing a `(x, y, width, height) -> path`
function and registering it in WINDOW_CUTOUTS / DOOR_CUTOUTS. Nothing else needs to change.
"""

from .components import Door, DoorType, Window, WindowType
from .constants import COORDINATE_PRECISION


def _generate_rectangular_cutout(x: float, y: float, width: float, height: float) -> str:
    """Generate a rectangular cutout"""
    return (f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
            f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
            f"L {x + width:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
            f"L {x:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} Z")

def _generate_arched_cutout(x: float, y: float, width: float, height: float) -> str:
    """Generate an arched cutout (rectangular with arched top)"""
    arch_height = height * 0.3  # Top 30% is the arch
    rect_height = height - arch_height

    # Start at bottom left
    path = f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
    # Bottom edge
    path += f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
    # Right edge up to arch
    path += f"L {x + width:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
    # Arch at top (using quadratic bezier curve)
    path += f"Q {x + width/2:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
    path += f"{x:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
    # Close path
    path += "Z"

    return path

def _generate_circular_cutout(x: float, y: float, width: float, height: float) -> str:
    """Generate a circular cutout"""
    # Use the smaller dimension to ensure it fits
    diameter = min(width, height)
    radius = diameter / 2
    center_x = x + width / 2
    center_y = y + height / 2

    # Generate circle using 4 cubic bezier curves (standard SVG technique)
    # Magic number for bezier control points to approximate a circle
    control_offset = radius * 0.552284749831

    path = f"M {center_x:.{COORDINATE_PRECISION}f},{center_y - radius:.{COORDINATE_PRECISION}f} "
    path += f"C {center_x + control_offset:.{COORDINATE_PRECISION}f},{center_y - radius:.{COORDINATE_PRECISION}f} "
    path += f"{center_x + radius:.{COORDINATE_PRECISION}f},{center_y - control_offset:.{COORDINATE_PRECISION}f} "
    path += f"{center_x + radius:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
    path += f"C {center_x + radius:.{COORDINATE_PRECISION}f},{center_y + control_offset:.{COORDINATE_PRECISION}f} "
    path += f"{center_x + control_offset:.{COORDINATE_PRECISION}f},{center_y + radius:.{COORDINATE_PRECISION}f} "
    path += f"{center_x:.{COORDINATE_PRECISION}f},{center_y + radius:.{COORDINATE_PRECISION}f} "
    path += f"C {center_x - control_offset:.{COORDINATE_PRECISION}f},{center_y + radius:.{COORDINATE_PRECISION}f} "
    path += f"{center_x - radius:.{COORDINATE_PRECISION}f},{center_y + control_offset:.{COORDINATE_PRECISION}f} "
    path += f"{center_x - radius:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
    path += f"C {center_x - radius:.{COORDINATE_PRECISION}f},{center_y - control_offset:.{COORDINATE_PRECISION}f} "
    path += f"{center_x - control_offset:.{COORDINATE_PRECISION}f},{center_y - radius:.{COORDINATE_PRECISION}f} "
    path += f"{center_x:.{COORDINATE_PRECISION}f},{center_y - radius:.{COORDINATE_PRECISION}f} Z"

    return path

def _generate_cross_pane_cutout(x: float, y: float, width: float, height: float) -> str:
    """Generate a cross-pane window cutout with cross mullions"""
    center_x = x + width / 2
    center_y = y + height / 2
    mullion_width = 1.0  # 1mm mullion width

    # Main window opening
    main = _generate_rectangular_cutout(x, y, width, height)

    # Vertical mullion (center)
    vert_mullion = _generate_rectangular_cutout(
        center_x - mullion_width/2, y, mullion_width, height)

    # Horizontal mullion (center)
    horiz_mullion = _generate_rectangular_cutout(
        x, center_y - mullion_width/2, width, mullion_width)

    return main + " " + vert_mullion + " " + horiz_mullion

def _generate_multi_pane_cutout(x: float, y: float, width: float, height: float) -> str:
    """Generate a multi-pane window cutout (3x2 grid with internal mullions)"""
    mullion_width = 1.0  # 1mm mullion width
    pane_width = width / 3
    pane_height = height / 2

    # Main window opening
    main = _generate_rectangular_cutout(x, y, width, height)

    # Vertical mullions (2 internal divisions for 3 columns)
    mullions = []
    for i in range(1, 3):
        mullion_x = x + i * pane_width - mullion_width/2
        mullions.append(_generate_rectangular_cutout(
            mullion_x, y, mullion_width, height))

    # Horizontal mullion (1 internal division for 2 rows)
    mullion_y = y + pane_height - mullion_width/2
    mullions.append(_generate_rectangular_cutout(
        x, mullion_y, width, mullion_width))

    return main + " " + " ".join(mullions)

def _generate_colonial_set_cutout(x: float, y: float, width: float, height: float) -> str:
    """Generate a colonial set window cutout (3 separate windows)"""
    window_width = width / 3
    spacing = window_width * 0.1
    actual_window_width = window_width - spacing

    cutouts = []
    for i in range(3):
        window_x = x + i * window_width + spacing/2
        cutouts.append(_generate_rectangular_cutout(
            window_x, y, actual_window_width, height))

    return " ".join(cutouts)

def _generate_palladian_cutout(x: float, y: float, width: float, height: float) -> str:
    """Generate a Palladian window cutout (arched center + 2 rectangular sides)"""
    central_width = width * 0.6
    side_width = width * 0.2

    # Central arched window
    center_x = x + side_width
    center = _generate_arched_cutout(center_x, y, central_width, height)

    # Left rectangular window
    left = _generate_rectangular_cutout(x, y, side_width, height)

    # Right rectangular window
    right_x = x + side_width + central_width
    right = _generate_rectangular_cutout(right_x, y, side_width, height)

    return left + " " + center + " " + right

def _generate_gothic_pair_cutout(x: float, y: float, width: float, height: float) -> str:
    """Generate a Gothic pair window cutout (2 gothic arched windows)"""
    window_width = (width - 3) / 2  # Account for central mullion
    spacing = 3.0

    # Left gothic window
    left = _generate_gothic_arch_cutout(x, y, window_width, height)

    # Right gothic window
    right_x = x + window_width + spacing
    right = _generate_gothic_arch_cutout(right_x, y, window_width, height)

    return left + " " + right

def _generate_gothic_arch_cutout(x: float, y: float, width: float, height: float) -> str:
    """Generate a single Gothic arched window cutout"""
    # Gothic arch is a pointed arch created with two curves meeting at the top
    rect_height = height * 0.7  # Lower 70% is rectangular
    arch_height = height * 0.3  # Upper 30% is the pointed arch

    path = f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
    # Right edge up to arch
    path += f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
    path += f"L {x + width:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
    # Right side of pointed arch
    path += f"Q {x + width * 0.75:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
    path += f"{x + width/2:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
    # Left side of pointed arch
    path += f"Q {x + width * 0.25:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
    path += f"{x:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
    # Left edge
    path += "Z"

    return path

def _generate_double_hung_cutout(x: float, y: float, width: float, height: float) -> str:
    """Generate a double-hung window cutout with horizontal division"""
    divider_height = 1.0  # 1mm divider height
    mid_y = y + height / 2

    # Main window opening
    main = _generate_rectangular_cutout(x, y, width, height)

    # Horizontal divider in the middle
    divider = _generate_rectangular_cutout(
        x, mid_y - divider_height/2, width, divider_height)

    return main + " " + divider

def _generate_dormer_cutout(x: float, y: float, width: float, height: float) -> str:
    """Generate a dormer window cutout (rectangular with peaked roof top)"""
    peak_height = height * 0.2  # Top 20% is peaked
    rect_height = height - peak_height

    # Start at bottom left
    path = f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
    # Right edge up to peak
    path += f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
    path += f"L {x + width:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
    # Right slope to peak
    path += f"L {x + width/2:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
    # Left slope from peak
    path += f"L {x:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
    # Close path
    path += "Z"

    return path


def _generate_double_door_cutout(x: float, y: float, width: float, height: float) -> str:
    """Double door is two rectangular sections"""
    half_width = width / 2
    left = _generate_rectangular_cutout(x, y, half_width - 0.5, height)
    right = _generate_rectangular_cutout(x + half_width + 0.5, y, half_width - 0.5, height)
    return left + " " + right


def _generate_dutch_door_cutout(x: float, y: float, width: float, height: float) -> str:
    """Dutch door is split horizontally"""
    half_height = height / 2
    top = _generate_rectangular_cutout(x, y + half_height + 0.5, width, half_height - 0.5)
    bottom = _generate_rectangular_cutout(x, y, width, half_height - 0.5)
    return top + " " + bottom


_RECT = _generate_rectangular_cutout

WINDOW_CUTOUTS = {
    WindowType.RECTANGULAR: _RECT,
    WindowType.ARCHED: _generate_arched_cutout,
    WindowType.CIRCULAR: _generate_circular_cutout,
    WindowType.ATTIC: _RECT,
    WindowType.CROSS_PANE: _generate_cross_pane_cutout,
    WindowType.MULTI_PANE: _generate_multi_pane_cutout,
    WindowType.COLONIAL_SET: _generate_colonial_set_cutout,
    WindowType.PALLADIAN: _generate_palladian_cutout,
    WindowType.GOTHIC_PAIR: _generate_gothic_pair_cutout,
    WindowType.DOUBLE_HUNG: _generate_double_hung_cutout,
    WindowType.CASEMENT: _RECT,
    WindowType.BAY: _RECT,
    WindowType.DORMER: _generate_dormer_cutout,
}

DOOR_CUTOUTS = {
    DoorType.RECTANGULAR: _RECT,
    DoorType.ARCHED: _generate_arched_cutout,
    DoorType.DOUBLE: _generate_double_door_cutout,
    DoorType.DUTCH: _generate_dutch_door_cutout,
}


def window_cutout(window: Window) -> str:
    """Cutout path for a window at its panel-local position."""
    p = window.position
    return WINDOW_CUTOUTS.get(window.type, _RECT)(p.x, p.y, p.width, p.height)


def door_cutout(door: Door) -> str:
    """Cutout path for a door at its panel-local position."""
    p = door.position
    return DOOR_CUTOUTS.get(door.type, _RECT)(p.x, p.y, p.width, p.height)
