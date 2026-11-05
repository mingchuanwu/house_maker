"""
Geometry of the house box: base dimensions and every derived panel size.

Pure math, no SVG, no finger-joint policy, no layout.

Kerf policy: laser kerf `k` removes material around the cut line, so every *outer* panel dimension
is enlarged by `k` (and internal holes are shrunk by `k`, see joints.FingerJointEngine). All
derived sizes below are already kerf-compensated and mutually consistent, so two panels that share
an edge always report the same edge length.
"""

import math
from typing import Dict, List, NamedTuple, Tuple

from .constants import COORDINATE_PRECISION, DEFAULT_KERF, DEGREES_TO_RADIANS
from .exceptions import GeometryError


class Point(NamedTuple):
    """2D point with x, y coordinates"""
    x: float
    y: float

    def __str__(self):
        return f"{self.x:.{COORDINATE_PRECISION}f},{self.y:.{COORDINATE_PRECISION}f}"


class HouseGeometry:
    """
    Core geometric calculations for the house box.

    Inputs:
        x: length (side wall width, floor length)
        y: width (floor width; gable wall width is y + 2*thickness)
        z: wall height up to the start of the gable
        theta: gable (roof) angle in degrees
        thickness: material thickness (w)
        finger_length: finger joint length (l)
        kerf: laser kerf compensation

    Derived (kerf compensated):
        x_kerf, y_kerf, z_kerf        outer size of floor/walls
        gable_wall_width              y_kerf + 2*thickness
        gable_peak_height             rise of the gable above the wall top
        total_gable_height            z_kerf + gable_peak_height
        base_roof_width               length of the gable's sloped edge (= rafter length)
        roof_panel_length/left_width/right_width
    """

    def __init__(self, x: float, y: float, z: float, theta: float,
                 thickness: float, finger_length: float, kerf: float = DEFAULT_KERF):
        self.x = x
        self.y = y
        self.z = z
        self.theta = theta
        self.thickness = thickness
        self.finger_length = finger_length
        self.kerf = kerf
        self.theta_rad = theta * DEGREES_TO_RADIANS
        self._calculate_derived_dimensions()

    def _calculate_derived_dimensions(self):
        t, k = self.thickness, self.kerf
        self.x_kerf = self.x + k
        self.y_kerf = self.y + k
        self.z_kerf = self.z + k

        # The gable wall is the widest part of the structure; the roof angle is defined on it, so
        # the peak and the rafter length both derive from this single width.
        self.gable_wall_width = self.y_kerf + 2 * t
        half = self.gable_wall_width / 2
        self.gable_peak_height = half * math.tan(self.theta_rad)
        self.total_gable_height = self.z_kerf + self.gable_peak_height
        self.base_roof_width = half / math.cos(self.theta_rad)

        # Roof panels overhang the gable walls: 3*thickness each end, asymmetric at the ridge
        self.roof_panel_length = self.x_kerf + 6 * t
        self.roof_panel_left_width = self.base_roof_width + 4 * t + k
        self.roof_panel_right_width = self.base_roof_width + 3 * t + k

    # --- raw input aliases -------------------------------------------------
    @property
    def length(self) -> float:
        return self.x

    @property
    def width(self) -> float:
        return self.y

    @property
    def height(self) -> float:
        return self.z

    # --- accessors ---------------------------------------------------------
    def get_gable_peak_height(self) -> float:
        return self.gable_peak_height

    def get_roof_panel_left_width(self) -> float:
        return self.roof_panel_left_width

    def get_roof_panel_right_width(self) -> float:
        return self.roof_panel_right_width

    def get_panel_dimensions(self) -> Dict[str, Tuple[float, float]]:
        """(width, height) of each main panel's nominal rectangle, without protruding tabs."""
        return {
            'floor': (self.x_kerf, self.y_kerf),
            'side_wall_left': (self.x_kerf, self.z_kerf),
            'side_wall_right': (self.x_kerf, self.z_kerf),
            'gable_wall_front': (self.gable_wall_width, self.total_gable_height),
            'gable_wall_back': (self.gable_wall_width, self.total_gable_height),
            'roof_panel_left': (self.roof_panel_length, self.roof_panel_left_width),
            'roof_panel_right': (self.roof_panel_length, self.roof_panel_right_width),
        }

    def roof_slot_rects(self, panel_name: str):
        """
        Where the gable tabs pass through a roof panel: [(x0, y0, x1, y1), ...] in panel coordinates
        (x along the ridge, y from the panel's ridge edge towards the eave).

        The slots are centred on the gable walls' thickness (2.5 thicknesses from each roof end).
        Along the slope they sit half a rafter length from the ridge; the left panel's ridge edge is
        offset by one thickness (its female notches).
        """
        t, k, f = self.thickness, self.kerf, self.finger_length
        cy = self.base_roof_width / 2 + (t if panel_name == 'roof_panel_left' else 0.0)
        half_x, half_y = (t - k) / 2, (f - k) / 2
        return [(cx - half_x, cy - half_y, cx + half_x, cy + half_y)
                for cx in (2.5 * t, self.roof_panel_length - 2.5 * t)]

    def validate_geometry(self):
        """Validate that all geometric calculations are reasonable"""
        if self.gable_peak_height <= 0:
            raise GeometryError("gable_calculation", "Gable peak height must be positive")
        if self.total_gable_height > 5 * max(self.x, self.y, self.z):
            raise GeometryError("proportions", "House geometry is unreasonably tall")
        min_edge = min(self.x, self.y, self.z)
        if self.finger_length > min_edge / 3:
            raise GeometryError("finger_joints",
                                f"Finger joints too large ({self.finger_length}) for smallest edge ({min_edge})")


def offset_polygon(corners: List[Point], distance: float) -> List[Point]:
    """
    Counter-clockwise polygon with every edge moved outward by `distance` (negative: inward), mitred at the
    corners. Used for kerf compensation: the laser leaves a part `kerf/2` smaller on each edge, so the drawn
    outline is the nominal one offset outward by `kerf/2`.
    """
    n = len(corners)
    lines = []                                        # (outward unit normal, offset of the moved edge line)
    for i in range(n):
        a, b = corners[i], corners[(i + 1) % n]
        length = math.hypot(b.x - a.x, b.y - a.y)
        if length == 0:
            raise GeometryError("offset_polygon", "zero-length edge")
        nx, ny = (b.y - a.y) / length, -(b.x - a.x) / length            # right of travel = outward for CCW
        lines.append((nx, ny, nx * a.x + ny * a.y + distance))
    out = []
    for i in range(n):
        (n1x, n1y, c1), (n2x, n2y, c2) = lines[i - 1], lines[i]
        det = n1x * n2y - n1y * n2x
        if abs(det) < 1e-12:
            if n1x * n2x + n1y * n2y > 0:             # collinear, same direction: just move the vertex sideways
                out.append(Point(corners[i].x + n1x * distance, corners[i].y + n1y * distance))
                continue
            raise GeometryError("offset_polygon", "edge doubles back on itself")
        out.append(Point((c1 * n2y - c2 * n1y) / det, (n1x * c2 - n2x * c1) / det))
    return out


def edge_shifts(nominal: List[Point], drawn: List[Point]) -> List[float]:
    """For each edge i (corner i -> i+1): how far along the edge the drawn start lies from the nominal start
    (negative = earlier). Lets features planned on the nominal edge be placed on the drawn one."""
    n = len(nominal)
    out = []
    for i in range(n):
        a, b = nominal[i], nominal[(i + 1) % n]
        length = math.hypot(b.x - a.x, b.y - a.y)
        ux, uy = (b.x - a.x) / length, (b.y - a.y) / length
        out.append((drawn[i].x - a.x) * ux + (drawn[i].y - a.y) * uy)
    return out
