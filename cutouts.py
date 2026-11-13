"""
Cutout outlines for windows and doors, as SVG path strings in panel-local coordinates.

Extension point: add a WindowType/DoorType by writing a `(x, y, width, height) -> path`
function and registering it in WINDOW_CUTOUTS / DOOR_CUTOUTS. Nothing else needs to change.
"""

from typing import Optional, Tuple

from .components import Door, DoorType, Window, WindowType
from .constants import COORDINATE_PRECISION

PANE_SPLIT = 30.0                 # mm: an opening at least this wide (tall) gets 3 columns (rows) of panes, else 2
MIN_PANE_IN_THICKNESSES = 2.0     # a pane must be at least this many material thicknesses in both directions


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


def pane_grid(width: float, height: float, bar: float) -> Tuple[int, int]:
    """
    (columns, rows) of panes for a rectangular window opening with glazing bars `bar` wide: 3 along a side at least
    PANE_SPLIT long, else 2, as long as every pane stays MIN_PANE_IN_THICKNESSES bars wide (3 falls back to 2); a window
    too small even for 2 x 2 stays a single pane, (1, 1).
    """
    def count(size: float) -> int:
        for n in ((3, 2) if size >= PANE_SPLIT else (2,)):
            if (size - (n - 1) * bar) / n >= MIN_PANE_IN_THICKNESSES * bar:
                return n
        return 1
    cols, rows = count(width), count(height)
    return (1, 1) if 1 in (cols, rows) else (cols, rows)


def paned_cutout(x: float, y: float, width: float, height: float, bar: float,
                 grid: Optional[Tuple[int, int]] = None) -> str:
    """The window opening as equal panes, separated by glazing bars of wall material `bar` wide: `grid` (columns, rows),
    or by default as chosen by `pane_grid`."""
    cols, rows = grid or pane_grid(width, height, bar)
    pw, ph = (width - (cols - 1) * bar) / cols, (height - (rows - 1) * bar) / rows
    return " ".join(_generate_rectangular_cutout(x + i * (pw + bar), y + j * (ph + bar), pw, ph)
                    for j in range(rows) for i in range(cols))


# Windows with a fixed pane grid (columns, rows); the glazing bars between the panes are left standing as wall material
FIXED_PANE_GRIDS = {
    WindowType.CROSS_PANE: (2, 2),       # a cross of bars
    WindowType.MULTI_PANE: (3, 2),
    WindowType.DOUBLE_HUNG: (1, 2),      # upper and lower sash
}
DEFAULT_BAR = 1.0                        # mm, glazing bar width when the material thickness is not known


def fixed_grid_cutout(x: float, y: float, width: float, height: float, grid: Tuple[int, int], bar: float) -> str:
    """The opening as the panes of `grid`, separated by bars `bar` wide. A direction whose panes would come out
    narrower than one bar gets fewer divisions (down to a single pane)."""
    cols, rows = grid
    while cols > 1 and (width - (cols - 1) * bar) / cols < bar:
        cols -= 1
    while rows > 1 and (height - (rows - 1) * bar) / rows < bar:
        rows -= 1
    return paned_cutout(x, y, width, height, bar, (cols, rows))


_RECT = _generate_rectangular_cutout

WINDOW_CUTOUTS = {
    WindowType.RECTANGULAR: _RECT,
    WindowType.ARCHED: _generate_arched_cutout,
    WindowType.CIRCULAR: _generate_circular_cutout,
    WindowType.ATTIC: _RECT,
    WindowType.COLONIAL_SET: _generate_colonial_set_cutout,
    WindowType.PALLADIAN: _generate_palladian_cutout,
    WindowType.GOTHIC_PAIR: _generate_gothic_pair_cutout,
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


def window_cutout(window: Window, thickness: Optional[float] = None) -> str:
    """Cutout path for a window at its panel-local position. Given the material `thickness`, a rectangular window is
    cut as a grid of panes with glazing bars one thickness wide (see `pane_grid`); cross-pane, multi-pane and
    double-hung windows are cut as their fixed pane grid (`FIXED_PANE_GRIDS`) with bars one thickness wide."""
    p = window.position
    if window.type == WindowType.RECTANGULAR and thickness:
        return paned_cutout(p.x, p.y, p.width, p.height, thickness)
    if window.type in FIXED_PANE_GRIDS:
        return fixed_grid_cutout(p.x, p.y, p.width, p.height, FIXED_PANE_GRIDS[window.type], thickness or DEFAULT_BAR)
    return WINDOW_CUTOUTS.get(window.type, _RECT)(p.x, p.y, p.width, p.height)


def door_cutout(door: Door) -> str:
    """Cutout path for a door at its panel-local position."""
    p = door.position
    return DOOR_CUTOUTS.get(door.type, _RECT)(p.x, p.y, p.width, p.height)
