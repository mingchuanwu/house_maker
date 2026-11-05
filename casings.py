"""
Casing (trim frame) pieces for windows and doors, as SVG path strings in piece-local coordinates.
"""

from typing import Dict, Tuple

from .components import Door, DoorType, Window, WindowType
from .constants import COORDINATE_PRECISION


def _generate_rectangular_window_casing(inner_width: float, inner_height: float,
                                       casing_width: float, extension: float, panel_name: str) -> Dict[str, Tuple[float, float, str]]:
    """Generate rectangular window casing matching test.svg pattern exactly"""
    # Frame body dimensions (the narrow vertical part)
    tab_height = casing_width * 1.5
    frame_width = inner_width + 2 * casing_width
    frame_height = inner_height + 2 * tab_height

    # Tab dimensions (horizontal extensions at top and bottom ONLY)
    # Total width at tabs is wider than frame body
    tab_width_total = frame_width + 2 * extension

    # Total bounding box dimensions
    outer_width = tab_width_total
    outer_height = frame_height

    # Inner cutout position (centered in frame body)
    inner_x = extension + casing_width
    inner_y = tab_height

    # Create path matching screenshot exactly
    # The frame has a narrower body with wider tabs at top and bottom
    # frame_height = inner_height + 2*casing_width (total height including casings)
    # tab_height = casing_width (height of top and bottom tabs)
    # Frame body spans from Y=tab_height to Y=(frame_height - tab_height)

    svg_path = (
        # Start at bottom-left of bottom tab
        f"M 0.000,{outer_height:.{COORDINATE_PRECISION}f} "
        # Across bottom tab to the right
        f"L {outer_width:.{COORDINATE_PRECISION}f},{outer_height:.{COORDINATE_PRECISION}f} "
        # Up to top of bottom tab (bottom of frame body sides)
        f"L {outer_width:.{COORDINATE_PRECISION}f},{outer_height - tab_height:.{COORDINATE_PRECISION}f} "
        # Step LEFT (inward) to right edge of frame body
        f"L {outer_width - extension:.{COORDINATE_PRECISION}f},{outer_height - tab_height:.{COORDINATE_PRECISION}f} "
        # Up right side of frame body
        f"L {outer_width - extension:.{COORDINATE_PRECISION}f},{tab_height:.{COORDINATE_PRECISION}f} "
        # Step RIGHT (outward) to right edge of top tab
        f"L {outer_width:.{COORDINATE_PRECISION}f},{tab_height:.{COORDINATE_PRECISION}f} "
        # Up to top of top tab
        f"L {outer_width:.{COORDINATE_PRECISION}f},0.000 "
        # Across top tab to the left
        f"L 0.000,0.000 "
        # Down to bottom of top tab (top of frame body sides)
        f"L 0.000,{tab_height:.{COORDINATE_PRECISION}f} "
        # Step RIGHT (inward) to left edge of frame body
        f"L {extension:.{COORDINATE_PRECISION}f},{tab_height:.{COORDINATE_PRECISION}f} "
        # Down left side of frame body
        f"L {extension:.{COORDINATE_PRECISION}f},{outer_height - tab_height:.{COORDINATE_PRECISION}f} "
        # Step LEFT (outward) to left edge of bottom tab
        f"L 0.000,{outer_height - tab_height:.{COORDINATE_PRECISION}f} "
        # Close path back to start
        f"Z "
        # Inner cutout (counter-clockwise)
        f"M {inner_x:.{COORDINATE_PRECISION}f},{inner_y:.{COORDINATE_PRECISION}f} "
        f"L {inner_x:.{COORDINATE_PRECISION}f},{inner_y + inner_height:.{COORDINATE_PRECISION}f} "
        f"L {inner_x + inner_width:.{COORDINATE_PRECISION}f},{inner_y + inner_height:.{COORDINATE_PRECISION}f} "
        f"L {inner_x + inner_width:.{COORDINATE_PRECISION}f},{inner_y:.{COORDINATE_PRECISION}f} Z"
    )

    # Score lines create border region, COMPLETELY INSIDE red cut line
    # Two rectangles: outer inset from frame body, inner at window cutout position
    # The area between them represents the frame border to be folded

    score_inset = 0.2 * casing_width  # Small inset from frame edges

    # Outer score rectangle - inset from frame body edges (not tabs)
    # Frame body area is from Y=tab_height to Y=(outer_height - tab_height)
    score_outer_x = extension + score_inset
    score_outer_y = score_inset
    score_outer_width = frame_width - 2 * score_inset
    score_outer_height = outer_height - 2 * score_inset

    # Inner score rectangle - matches the window cutout position (not inset from it)
    # This defines where the window opening will be after folding
    score_inner_x = inner_x - score_inset
    score_inner_y = inner_y - score_inset
    score_inner_width = inner_width + 2 * score_inset
    score_inner_height = inner_height + 2 * score_inset

    # Two separate rectangle paths
    score_lines = (
        # Outer rectangle (inset from frame body) From top-left corner, counterclock-wise
        f"M {score_outer_x - extension:.{COORDINATE_PRECISION}f},{score_outer_y:.{COORDINATE_PRECISION}f} "
        f"L {score_outer_x - extension:.{COORDINATE_PRECISION}f},{score_outer_y + tab_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "
        f"L {score_outer_x:.{COORDINATE_PRECISION}f},{score_outer_y + tab_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "
        f"L {score_outer_x:.{COORDINATE_PRECISION}f},{score_inner_y + score_inner_height:.{COORDINATE_PRECISION}f} "
        f"L {score_outer_x - extension:.{COORDINATE_PRECISION}f},{score_inner_y + score_inner_height:.{COORDINATE_PRECISION}f} " # LEFT
        f"L {score_outer_x - extension:.{COORDINATE_PRECISION}f},{score_inner_y + score_inner_height + tab_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "

        # bottom line
        f"L {score_outer_x + score_outer_width + extension:.{COORDINATE_PRECISION}f},{score_inner_y + score_inner_height + tab_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "
        f"L {score_outer_x + score_outer_width + extension:.{COORDINATE_PRECISION}f},{score_outer_y + tab_height + score_inner_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "
        f"L {score_outer_x + score_outer_width:.{COORDINATE_PRECISION}f},{score_outer_y + tab_height + score_inner_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "
        f"L {score_outer_x + score_outer_width:.{COORDINATE_PRECISION}f},{score_inner_y:.{COORDINATE_PRECISION}f} " # UP 
        f"L {score_outer_x + score_outer_width + extension:.{COORDINATE_PRECISION}f},{score_inner_y:.{COORDINATE_PRECISION}f} " # RIGHT
        f"L {score_outer_x + score_outer_width + extension:.{COORDINATE_PRECISION}f},{score_outer_y:.{COORDINATE_PRECISION}f} Z" # UP

        # Inner rectangle (outset from window cutout)
        f"M {score_inner_x:.{COORDINATE_PRECISION}f},{score_inner_y:.{COORDINATE_PRECISION}f} "
        f"L {score_inner_x + score_inner_width:.{COORDINATE_PRECISION}f},{score_inner_y:.{COORDINATE_PRECISION}f} "
        f"L {score_inner_x + score_inner_width:.{COORDINATE_PRECISION}f},{score_inner_y + score_inner_height:.{COORDINATE_PRECISION}f} "
        f"L {score_inner_x:.{COORDINATE_PRECISION}f},{score_inner_y + score_inner_height:.{COORDINATE_PRECISION}f} Z"
    )

    return {
        f'{panel_name}_window_casing': (outer_width, outer_height, svg_path),
        f'{panel_name}_window_casing_scores': (outer_width, outer_height, score_lines)
    }

def _generate_arched_window_casing(inner_width: float, inner_height: float,
                                  casing_width: float, extension: float, panel_name: str) -> Dict[str, Tuple[float, float, str]]:
    """Generate arched window casing (arched on both inner and outer edges)"""
    # Outer frame dimensions
    outer_width = inner_width + 2 * casing_width + 2 * extension
    # Inner cutout position
    inner_x = extension + casing_width
    inner_y = casing_width

    # Calculate arch dimensions (top 30% of window is arched)
    inner_arch_start = inner_height * 0.7

    # Outer arch starts at same relative position but with casing offset
    outer_arch_start = inner_arch_start + casing_width

    # A quadratic curve's apex is halfway between its end points and its control point. The control points are
    # chosen so the outer apex sits exactly casing_width above the inner apex (uniform frame at the top).
    outer_control = inner_height + 3 * casing_width
    outer_height = (outer_arch_start + outer_control) / 2

    # Create path with ARCHED outer perimeter and ARCHED inner cutout
    svg_path = (
        # Outer perimeter with arched top (clockwise)
        f"M 0.000,0.000 "  # Bottom-left
        f"L 0.000,{outer_arch_start:.{COORDINATE_PRECISION}f} "  # Up left side to arch start
        # Outer arch using quadratic bezier
        f"Q {outer_width/2:.{COORDINATE_PRECISION}f},{outer_control:.{COORDINATE_PRECISION}f} "
        f"{outer_width:.{COORDINATE_PRECISION}f},{outer_arch_start:.{COORDINATE_PRECISION}f} "  # Arch across top
        f"L {outer_width:.{COORDINATE_PRECISION}f},0.000 "  # Down right side
        f"L 0.000,0.000 Z "  # Close bottom
        # Inner arched cutout (counter-clockwise)
        f"M {inner_x:.{COORDINATE_PRECISION}f},{inner_y:.{COORDINATE_PRECISION}f} "  # Bottom-left of opening
        f"L {inner_x + inner_width:.{COORDINATE_PRECISION}f},{inner_y:.{COORDINATE_PRECISION}f} "  # Bottom edge
        f"L {inner_x + inner_width:.{COORDINATE_PRECISION}f},{inner_y + inner_arch_start:.{COORDINATE_PRECISION}f} "  # Up right side
        # Inner arch using quadratic bezier (counter-clockwise)
        f"Q {inner_x + inner_width/2:.{COORDINATE_PRECISION}f},{inner_y + inner_height:.{COORDINATE_PRECISION}f} "
        f"{inner_x:.{COORDINATE_PRECISION}f},{inner_y + inner_arch_start:.{COORDINATE_PRECISION}f} "  # Arch back
        f"Z"  # Close
    )

    return {
        f'{panel_name}_window_casing': (outer_width, outer_height, svg_path)
    }

def _generate_circular_window_casing(inner_width: float, inner_height: float,
                                    casing_width: float, extension: float, panel_name: str) -> Dict[str, Tuple[float, float, str]]:
    """Generate circular window casing (ring/donut shape - circular outer and inner edges)"""
    # Use the smaller dimension for the circle
    inner_diameter = min(inner_width, inner_height)
    inner_radius = inner_diameter / 2

    # Outer circle has casing width added
    outer_radius = inner_radius + casing_width
    outer_diameter = outer_radius * 2
    outer_size = outer_diameter  # Bounding box

    # Center position
    center_x = outer_size / 2
    center_y = outer_size / 2

    # Magic number for bezier control points to approximate a circle
    inner_control_offset = inner_radius * 0.552284749831
    outer_control_offset = outer_radius * 0.552284749831

    # Create path with CIRCULAR outer perimeter and CIRCULAR inner cutout (ring/donut shape)
    svg_path = (
        # Outer circle using 4 cubic bezier curves (clockwise from top)
        f"M {center_x:.{COORDINATE_PRECISION}f},{center_y - outer_radius:.{COORDINATE_PRECISION}f} "
        f"C {center_x + outer_control_offset:.{COORDINATE_PRECISION}f},{center_y - outer_radius:.{COORDINATE_PRECISION}f} "
        f"{center_x + outer_radius:.{COORDINATE_PRECISION}f},{center_y - outer_control_offset:.{COORDINATE_PRECISION}f} "
        f"{center_x + outer_radius:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
        f"C {center_x + outer_radius:.{COORDINATE_PRECISION}f},{center_y + outer_control_offset:.{COORDINATE_PRECISION}f} "
        f"{center_x + outer_control_offset:.{COORDINATE_PRECISION}f},{center_y + outer_radius:.{COORDINATE_PRECISION}f} "
        f"{center_x:.{COORDINATE_PRECISION}f},{center_y + outer_radius:.{COORDINATE_PRECISION}f} "
        f"C {center_x - outer_control_offset:.{COORDINATE_PRECISION}f},{center_y + outer_radius:.{COORDINATE_PRECISION}f} "
        f"{center_x - outer_radius:.{COORDINATE_PRECISION}f},{center_y + outer_control_offset:.{COORDINATE_PRECISION}f} "
        f"{center_x - outer_radius:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
        f"C {center_x - outer_radius:.{COORDINATE_PRECISION}f},{center_y - outer_control_offset:.{COORDINATE_PRECISION}f} "
        f"{center_x - outer_control_offset:.{COORDINATE_PRECISION}f},{center_y - outer_radius:.{COORDINATE_PRECISION}f} "
        f"{center_x:.{COORDINATE_PRECISION}f},{center_y - outer_radius:.{COORDINATE_PRECISION}f} Z "
        # Inner circle cutout using 4 cubic bezier curves (counter-clockwise from top for hole)
        f"M {center_x:.{COORDINATE_PRECISION}f},{center_y - inner_radius:.{COORDINATE_PRECISION}f} "
        f"C {center_x - inner_control_offset:.{COORDINATE_PRECISION}f},{center_y - inner_radius:.{COORDINATE_PRECISION}f} "
        f"{center_x - inner_radius:.{COORDINATE_PRECISION}f},{center_y - inner_control_offset:.{COORDINATE_PRECISION}f} "
        f"{center_x - inner_radius:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
        f"C {center_x - inner_radius:.{COORDINATE_PRECISION}f},{center_y + inner_control_offset:.{COORDINATE_PRECISION}f} "
        f"{center_x - inner_control_offset:.{COORDINATE_PRECISION}f},{center_y + inner_radius:.{COORDINATE_PRECISION}f} "
        f"{center_x:.{COORDINATE_PRECISION}f},{center_y + inner_radius:.{COORDINATE_PRECISION}f} "
        f"C {center_x + inner_control_offset:.{COORDINATE_PRECISION}f},{center_y + inner_radius:.{COORDINATE_PRECISION}f} "
        f"{center_x + inner_radius:.{COORDINATE_PRECISION}f},{center_y + inner_control_offset:.{COORDINATE_PRECISION}f} "
        f"{center_x + inner_radius:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
        f"C {center_x + inner_radius:.{COORDINATE_PRECISION}f},{center_y - inner_control_offset:.{COORDINATE_PRECISION}f} "
        f"{center_x + inner_control_offset:.{COORDINATE_PRECISION}f},{center_y - inner_radius:.{COORDINATE_PRECISION}f} "
        f"{center_x:.{COORDINATE_PRECISION}f},{center_y - inner_radius:.{COORDINATE_PRECISION}f} Z"
    )

    return {
        f'{panel_name}_window_casing': (outer_size, outer_size, svg_path)
    }


def _generate_rectangular_door_casing(inner_width: float, inner_height: float,
                                     casing_width: float, extension: float, panel_name: str) -> Dict[str, Tuple[float, float, str]]:
    """Generate rectangular door casing matching door_frame_example.svg - U-shape open at bottom with small tabs"""
    # Frame body (U-shaped, no bottom bar)
    top_bar_height = 1.5 * casing_width  # Height of the horizontal top bar
    frame_width = inner_width + 2 * casing_width
    frame_height = inner_height  # Full height for the vertical sides

    # Top section with tab
    tab_width_total = frame_width + 2 * extension

    # Total dimensions
    outer_width = tab_width_total
    outer_height = frame_height + top_bar_height

    # Inner door opening - matches door size exactly
    inner_x = extension + casing_width
    inner_y = top_bar_height

    # U-shaped frame: vertical sides go all the way down, horizontal bar only at top with tab
    svg_path = (
        # Start at bottom-left of left vertical side
        f"M {extension:.{COORDINATE_PRECISION}f},{outer_height:.{COORDINATE_PRECISION}f} "
        # Up left vertical side
        f"L {extension:.{COORDINATE_PRECISION}f},{top_bar_height:.{COORDINATE_PRECISION}f} "
        # Step LEFT to start of top tab
        f"L 0.000,{top_bar_height:.{COORDINATE_PRECISION}f} "
        # Up to top of tab
        f"L 0.000,0.000 "
        # Across top tab
        f"L {outer_width:.{COORDINATE_PRECISION}f},0.000 "
        # Down to top bar level
        f"L {outer_width:.{COORDINATE_PRECISION}f},{top_bar_height:.{COORDINATE_PRECISION}f} "
        # Step RIGHT (inward)
        f"L {outer_width - extension:.{COORDINATE_PRECISION}f},{top_bar_height:.{COORDINATE_PRECISION}f} "
        # Down right vertical side
        f"L {outer_width - extension:.{COORDINATE_PRECISION}f},{outer_height:.{COORDINATE_PRECISION}f} "
        # Step LEFT to inner-right
        f"L {inner_x + inner_width:.{COORDINATE_PRECISION}f},{outer_height:.{COORDINATE_PRECISION}f} "
        # Up inner-right side
        f"L {inner_x + inner_width:.{COORDINATE_PRECISION}f},{inner_y:.{COORDINATE_PRECISION}f} "
        # Across inner top
        f"L {inner_x:.{COORDINATE_PRECISION}f},{inner_y:.{COORDINATE_PRECISION}f} "
        # Down inner-left side
        f"L {inner_x:.{COORDINATE_PRECISION}f},{outer_height:.{COORDINATE_PRECISION}f} "
        # Close
        f"Z"
    )

    # Score lines create U-shaped border region, COMPLETELY INSIDE red cut line
    # Must not overlap or extend beyond cut line boundaries
    # Similar to window frame, but U-shaped (no bottom bar)

    score_inset = extension / 2  # Inset from both outer and inner edges

    # Outer score rectangle - inset from frame body edges (not tabs), forming U-shape
    score_outer_x = extension + score_inset
    score_outer_y = score_inset # top_bar_height + score_inset
    score_outer_width = frame_width - 2 * score_inset
    score_outer_height = frame_height + top_bar_height - 2 * score_inset  # Goes to bottom

    # Inner score rectangle - inset FROM door cutout (smaller than opening), forming U-shape
    score_inner_x = inner_x - score_inset
    score_inner_y = inner_y - score_inset
    score_inner_width = inner_width + 2 * score_inset
    score_inner_height = inner_height - 2 * score_inset  # Inset from bottom
    inner_casing_width = casing_width - 2 * score_inset 

    # Single continuous U-shaped border path (similar to window but U-shaped)
    # This creates the border region between outer and inner edges
    score_lines = (
        # Outer U-shape (clockwise from bottom-left)
        f"M {score_outer_x:.{COORDINATE_PRECISION}f},{score_outer_y + score_outer_height:.{COORDINATE_PRECISION}f} "
        f"L {score_outer_x:.{COORDINATE_PRECISION}f},{score_outer_y + top_bar_height - 2 * score_inset :.{COORDINATE_PRECISION}f} "
        f"L {score_outer_x - extension:.{COORDINATE_PRECISION}f},{score_outer_y + top_bar_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "
        f"L {score_outer_x - extension:.{COORDINATE_PRECISION}f},{score_outer_y:.{COORDINATE_PRECISION}f} "

        f"L {score_outer_x + score_outer_width + extension:.{COORDINATE_PRECISION}f},{score_outer_y:.{COORDINATE_PRECISION}f} "
        f"L {score_outer_x + score_outer_width + extension:.{COORDINATE_PRECISION}f},{score_outer_y + top_bar_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "
        f"L {score_outer_x + score_outer_width:.{COORDINATE_PRECISION}f},{score_outer_y + top_bar_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "

        f"L {score_outer_x + score_outer_width:.{COORDINATE_PRECISION}f},{score_outer_y + score_outer_height:.{COORDINATE_PRECISION}f} "
        # Step inward to inner U-shape
        f"L {score_inner_x + score_inner_width:.{COORDINATE_PRECISION}f},{score_outer_y + score_outer_height:.{COORDINATE_PRECISION}f} "
        # Inner U-shape (counter-clockwise from bottom-right)
        f"L {score_inner_x + score_inner_width:.{COORDINATE_PRECISION}f},{score_inner_y:.{COORDINATE_PRECISION}f} "
        f"L {score_inner_x:.{COORDINATE_PRECISION}f},{score_inner_y:.{COORDINATE_PRECISION}f} "
        f"L {score_inner_x:.{COORDINATE_PRECISION}f},{score_outer_y + score_outer_height:.{COORDINATE_PRECISION}f} "
        f"Z"
    )

    return {
        f'{panel_name}_door_casing': (outer_width, outer_height, svg_path),
        f'{panel_name}_door_casing_scores': (outer_width, outer_height, score_lines)
    }

def _generate_arched_door_casing(inner_width: float, inner_height: float,
                                casing_width: float, extension: float, panel_name: str) -> Dict[str, Tuple[float, float, str]]:
    """Generate arched door casing (horseshoe shape with arch at BOTTOM, opening at TOP for upside-down gable walls)"""
    # Outer frame dimensions (3-sided, opening at top)
    outer_width = inner_width + 2 * casing_width + 2 * extension
    outer_height = inner_height + casing_width

    # Inner cutout position
    inner_x = extension + casing_width
    inner_y = 0.0  # No top casing (opening is at top)
    inner_right_x = inner_x + inner_width

    # Calculate arch dimensions (bottom 30% of door is arched)
    inner_arch_start = inner_height * 0.7

    # For outer arch, calculate where rectangular portion ends
    outer_arch_start = inner_arch_start + casing_width

    # Create path with ARCHED outer perimeter (arch at bottom) and ARCHED inner cutout
    # The outer edge follows the arch shape of the door
    svg_path = (
        # Start at top-left
        f"M 0.000,0.000 "
        # Down left side to where arch begins
        f"L 0.000,{outer_arch_start:.{COORDINATE_PRECISION}f} "
        # Outer arch across bottom using quadratic bezier
        f"Q {outer_width/2:.{COORDINATE_PRECISION}f},{outer_height:.{COORDINATE_PRECISION}f} "
        f"{outer_width:.{COORDINATE_PRECISION}f},{outer_arch_start:.{COORDINATE_PRECISION}f} "
        # Up right side
        f"L {outer_width:.{COORDINATE_PRECISION}f},0.000 "
        # Inward to inner-right top
        f"L {inner_right_x:.{COORDINATE_PRECISION}f},0.000 "
        # Down inner-right to arch start
        f"L {inner_right_x:.{COORDINATE_PRECISION}f},{inner_arch_start:.{COORDINATE_PRECISION}f} "
        # Inner arch using quadratic bezier (arch at bottom)
        f"Q {inner_x + inner_width/2:.{COORDINATE_PRECISION}f},{inner_height:.{COORDINATE_PRECISION}f} "
        f"{inner_x:.{COORDINATE_PRECISION}f},{inner_arch_start:.{COORDINATE_PRECISION}f} "
        # Up inner-left
        f"L {inner_x:.{COORDINATE_PRECISION}f},0.000 "
        # Close path
        f"Z"
    )

    return {
        f'{panel_name}_door_casing': (outer_width, outer_height, svg_path)
    }


def window_casing_pieces(window: Window, panel_name: str, thickness: float) -> Dict[str, Tuple[float, float, str]]:
    """
    Window casing as a single frame piece with an inner cutout; the shape follows the window type.
    Returns {piece name: (width, height, svg_path)}; a `<name>_scores` entry holds the score lines.
    Attic windows get no casing (too small).
    """
    if window.type == WindowType.ATTIC:
        return {}
    inner_width = window.position.width
    inner_height = window.position.height
    casing_width = thickness                # frame width = 1 * thickness
    extension = 0.4 * thickness             # horizontal extension per side
    if window.type == WindowType.ARCHED:
        return _generate_arched_window_casing(inner_width, inner_height, casing_width, extension, panel_name)
    if window.type == WindowType.CIRCULAR:
        return _generate_circular_window_casing(inner_width, inner_height, casing_width, extension, panel_name)
    return _generate_rectangular_window_casing(inner_width, inner_height, casing_width, extension, panel_name)


def door_casing_pieces(door: Door, panel_name: str, thickness: float) -> Dict[str, Tuple[float, float, str]]:
    """Door casing: a 3-sided frame (no bottom) with an inner cutout; arched for arched doors."""
    inner_width = door.position.width
    inner_height = door.position.height
    casing_width = 1.5 * thickness
    extension = 0.6 * thickness
    if door.type == DoorType.ARCHED:
        return _generate_arched_door_casing(inner_width, inner_height, casing_width, extension, panel_name)
    return _generate_rectangular_door_casing(inner_width, inner_height, casing_width, extension, panel_name)
