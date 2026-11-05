"""
Architectural component data: enums, positions, windows, doors, chimneys, dormers.

Pure data + each component's own validation/geometry. No SVG, no placement policy.
"""

import math
from enum import Enum
from typing import Dict, List, NamedTuple, Optional, Tuple

from .dormer_geometry import solve_dormer
from .exceptions import GeometryError
from .geometry import Point


class RoofType(Enum):
    """Different roof patterns supported by the system"""
    GABLE = "gable"           # Standard triangular gable roof (default)
    FLAT = "flat"             # Flat roof (no gable)
    HIP = "hip"               # Hip roof (sloped on all four sides)
    GAMBREL = "gambrel"       # Gambrel roof (barn-style with two slopes)
    SHED = "shed"             # Shed roof (single slope)
    MANSARD = "mansard"       # Mansard roof (four-sided gambrel)


class WindowType(Enum):
    """Different window styles"""
    RECTANGULAR = "rectangular"   # Simple rectangular window
    ARCHED = "arched"             # Arched top window
    CIRCULAR = "circular"         # Circular window
    ATTIC = "attic"              # Small attic window for gable walls
    BAY = "bay"                  # Bay window (protruding)
    DORMER = "dormer"            # Dormer window (on roof)
    DOUBLE_HUNG = "double_hung"   # Traditional double-hung sash windows
    CASEMENT = "casement"         # Side-hinged casement windows
    PALLADIAN = "palladian"       # Palladian window (arch with flanking rectangles)
    GOTHIC_PAIR = "gothic_pair"   # Paired Gothic arched windows
    COLONIAL_SET = "colonial_set" # Set of 3 colonial windows with shutters
    CROSS_PANE = "cross_pane"     # Cross-pattern mullioned window (gingerbread style)
    MULTI_PANE = "multi_pane"     # Multi-pane grid window (advent calendar style)


class DoorType(Enum):
    """Different door styles"""
    RECTANGULAR = "rectangular"   # Simple rectangular door
    ARCHED = "arched"             # Arched top door
    DOUBLE = "double"             # Double door
    DUTCH = "dutch"              # Dutch door (split horizontal)


class ArchitecturalStyle(Enum):
    """Architectural styles for decorative patterns"""
    BASIC = "basic"                    # Clean, minimal style
    FACHWERKHAUS = "fachwerkhaus"      # German timber frame style
    FARMHOUSE = "farmhouse"            # American farmhouse style
    COLONIAL = "colonial"              # Colonial style
    BRICK = "brick"                    # Brick pattern style
    STONE = "stone"                    # Stone wall pattern style
    VICTORIAN = "victorian"            # Victorian ornate style
    TUDOR = "tudor"                    # Tudor revival style
    CRAFTSMAN = "craftsman"            # Arts and crafts style
    GINGERBREAD = "gingerbread"        # Festive gingerbread house style with ornate cutouts


class ShingleType(Enum):
    """Different roof shingle/tile patterns"""
    SPANTILE = "spantile"              # Spanish tile with wavy pattern
    SPANISH = "spanish"                # Spanish tile variant
    SHINGLES = "shingles"              # Standard rectangular shingles
    SCALLOPS = "scallops"              # Scalloped/fish-scale shingles
    S_TILE = "s-tile"                  # S-shaped tiles with curves


class ComponentPosition(NamedTuple):
    """Position and size specification for architectural components"""
    x: float          # X position (relative to panel)
    y: float          # Y position (relative to panel)
    width: float      # Component width
    height: float     # Component height
    panel: str        # Target panel name




class Window:
    """Window component with position and styling information"""
    
    def __init__(self, window_type: WindowType, position: ComponentPosition):
        self.type = window_type
        self.position = position
        
        # Validate position
        self._validate_position()
    
    def _validate_position(self):
        """Validate that window position is reasonable"""
        if self.position.width <= 0 or self.position.height <= 0:
            raise GeometryError("window_validation", "Window dimensions must be positive")
        
        # Minimum window sizes for manufacturability
        if self.position.width < 5.0 or self.position.height < 5.0:
            raise GeometryError("window_validation", "Window too small for laser cutting (minimum 5mm)")



class Chimney:
    """
    A vertical chimney standing on a sloped roof panel.

    Model (all lengths in mm, `t` = material thickness, `theta` = roof angle)
    ----------------------------------------------------------------------
    * `position.width`  (W): interior width, i.e. the width of the front/back walls; the two side
      walls stand outside them, so the outer width is W + 2t.
    * `position.height` (D): *plan* (horizontal) depth of the chimney = width of the side walls.
      On the roof panel the footprint is longer: l = D / cos(theta).
    * The top is LEVEL. The roof rises up-slope, so the exposed wall height is largest on the
      downslope (front) side. `chimney_height` (h) is the minimum exposure, at the up-slope (back)
      wall; the downslope end is taller by D * tan(theta).
    * The roof panel is cut through inside the footprint, inset by one thickness on every side
      (`roof_cutout`), leaving a lip the walls rest on; the footprint itself is scored.
    * The casing frame lies on the roof around the chimney; its opening is longer on the up-slope side
      (`casing_upslope_extra`) because the vertical walls lean across the casing's thickness.
    * Walls are joined with finger joints at the four vertical corners (see builders/chimney.py);
      the casing and the roof contact are glued.
    * Front/back walls are rectangles whose base is cut level at the highest roof point under their
      thickness (so they never intersect the roof); this leaves a t*tan(theta) wedge gap under the
      front wall's outer face.
    """

    CASING_CLEARANCE = 0.1      # casing opening is this many thicknesses larger than the footprint

    def __init__(self, position: ComponentPosition, roof_angle: float, thickness: float,
                 chimney_height: float = 20.0):
        self.position = position
        self.roof_angle = roof_angle
        self.thickness = thickness
        self.chimney_height = chimney_height
        self._validate_position()
        self.wall_panels = self._wall_panel_dimensions()

    def _validate_position(self):
        w, d, t = self.position.width, self.position.height, self.thickness
        if w <= 0 or d <= 0:
            raise GeometryError("chimney_validation", "Chimney dimensions must be positive")
        if w < 5.0 or d < 8.0:
            raise GeometryError("chimney_validation", "Chimney too small (minimum 5x8mm)")
        if d <= 2 * t:
            raise GeometryError("chimney_validation",
                                f"Chimney depth {d} must exceed twice the material thickness ({2 * t})")
        if self.chimney_height <= 0:
            raise GeometryError("chimney_validation", "Chimney height must be positive")

    # --- derived geometry --------------------------------------------------
    @property
    def plan_depth(self) -> float:
        return self.position.height

    @property
    def outer_width(self) -> float:
        return self.position.width + 2 * self.thickness

    @property
    def slope_depth(self) -> float:
        """Footprint depth measured on the roof panel."""
        return self.plan_depth / math.cos(math.radians(self.roof_angle))

    @property
    def rise(self) -> float:
        """Roof rise across the chimney's plan depth."""
        return self.plan_depth * math.tan(math.radians(self.roof_angle))

    def footprint(self) -> Tuple[float, float, float, float]:
        """Outer footprint on the roof panel as (x, y, width, depth). `position.x` is the left
        edge of the footprint's outer face."""
        return (self.position.x, self.position.y, self.outer_width, self.slope_depth)

    def roof_cutout(self) -> Tuple[float, float, float, float]:
        """Hole cut through the roof panel as (x, y, width, depth): the outer footprint minus two
        thicknesses in both directions, centred, so a lip of one thickness all round carries the
        chimney walls."""
        x, y, w, d = self.footprint()
        t = self.thickness
        return (x + t, y + t, w - 2 * t, d - 2 * t)

    def side_wall_heights(self) -> Tuple[float, float]:
        """(downslope end, up-slope end) height of the side walls above the roof."""
        return (self.chimney_height + self.rise, self.chimney_height)

    @property
    def casing_margin(self) -> float:
        """How far the casing frame extends beyond the footprint at the sides and down-slope."""
        return self.thickness + self.CASING_CLEARANCE * self.thickness / 2

    @property
    def casing_upslope_extra(self) -> float:
        """The chimney is vertical but the casing lies on the sloped roof: across the casing's thickness
        the up-slope wall leans away from the roof's surface normal by t*tan(theta), so the opening must
        reach that much further up-slope to clear it."""
        return self.thickness * math.tan(math.radians(self.roof_angle))

    def casing_margins(self) -> Tuple[float, float, float, float]:
        """Casing extent beyond the footprint as (left, up-slope, right, down-slope)."""
        m = self.casing_margin
        return (m, m + self.casing_upslope_extra, m, m)

    def casing_opening(self) -> Tuple[float, float]:
        c = self.CASING_CLEARANCE * self.thickness
        return (self.outer_width + c, self.slope_depth + self.casing_upslope_extra + c)

    def _wall_panel_dimensions(self) -> Dict[str, Tuple[float, float]]:
        t = self.thickness
        tan = math.tan(math.radians(self.roof_angle))
        tall, short = self.side_wall_heights()
        opening_w, opening_h = self.casing_opening()
        return {
            # base cut level at the highest roof point under the wall's thickness
            'chimney_front': (self.position.width, self.chimney_height + (self.plan_depth - t) * tan),
            'chimney_back': (self.position.width, self.chimney_height),
            # bounding box of the trapezoid (plan width x tall end)
            'chimney_left': (self.plan_depth, tall),
            'chimney_right': (self.plan_depth, tall),
            # frame of width t around the opening
            'chimney_casing': (opening_w + 2 * t, opening_h + 2 * t),
        }

    def get_panel_dimensions(self) -> Dict[str, Tuple[float, float]]:
        """Bounding (width, height) of every chimney panel."""
        return self.wall_panels


class AdditionalGable:
    """
    A gable dormer on a roof panel. All dimensions come from `dormer_geometry.solve_dormer`:
    the dormer's pitch defaults to the main roof's pitch and its depth follows from the horizontal
    ridge constraint, so `position.height` is *derived* (the footprint depth on the roof panel).
    """

    def __init__(self, position: ComponentPosition, roof_angle: float, thickness: float,
                 roof_overhang: float = 3.0, pitch: Optional[float] = None):
        self.roof_overhang = roof_overhang
        self.roof_angle = roof_angle
        self.thickness = thickness
        self.geometry = solve_dormer(roof_angle, position.width, pitch, roof_overhang)
        # The requested depth is ignored: it is fixed by geometry (see dormer_geometry).
        self.position = position._replace(height=self.geometry.footprint_depth)
        self._validate_position()

    @property
    def face_lift(self) -> float:
        """Height the face's level base is raised above the sill line so it never digs into the rising roof:
        its thickness times tan(roof angle)."""
        return self.thickness * math.tan(math.radians(self.roof_angle))

    def face_size(self) -> Tuple[float, float]:
        w, h, _ = self.geometry.face_triangle(self.face_lift)
        return (w, h)

    def _validate_position(self):
        if self.position.width < 15.0:
            raise GeometryError("additional_gable_validation", "Gable too small (minimum width 15mm)")
        if self.roof_overhang < 0:
            raise GeometryError("additional_gable_validation", "Roof overhang cannot be negative")
        w, h, _ = self.geometry.face_triangle(self.face_lift)
        if w <= 0 or h <= 0:
            raise GeometryError("additional_gable_validation",
                                "Gable too low for its roof angle: the front face would vanish once lifted clear of the roof")

    def footprint(self) -> Tuple[float, float, float, float]:
        """Bounding box on the roof panel as (x, y, width, depth)."""
        p = self.position
        return (p.x, p.y, p.width, p.height)

    def get_wall_panel_dimensions(self) -> Dict[str, Tuple[float, float]]:
        return {'additional_gable_front': self.face_size()}

    def get_roof_panel_dimensions(self) -> Dict[str, Tuple[float, float]]:
        g = self.geometry
        size = (g.rafter, g.roof_panel_ridge_length)
        return {'additional_gable_roof_left': size, 'additional_gable_roof_right': size}


class Door:
    """Door component with position and styling information"""
    
    def __init__(self, door_type: DoorType, position: ComponentPosition):
        self.type = door_type
        self.position = position
        
        # Validate position
        self._validate_position()
    
    def _validate_position(self):
        """Validate that door position is reasonable"""
        if self.position.width <= 0 or self.position.height <= 0:
            raise GeometryError("door_validation", "Door dimensions must be positive")
        
        # Minimum door sizes
        if self.position.width < 8.0 or self.position.height < 15.0:
            raise GeometryError("door_validation", "Door too small (minimum 8×15mm)")
