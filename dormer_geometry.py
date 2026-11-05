"""
3D geometry of a gable dormer on a sloped roof, as pure functions.

Model
-----
The main roof is a plane at angle `theta` (descending with +y, the downslope direction).
The dormer has a vertical triangular front face standing on the roof along a horizontal line
(its sill, length W), and two roof planes of pitch `phi` meeting at a *horizontal* ridge that runs
back towards the main ridge:

        P (apex of front face)  = (W/2, 0, H)            H = (W/2) * tan(phi)
        ridge  P -> Q          horizontal, runs up-slope until it meets the main roof:
        Q                       = (W/2, y_e, H)           y_e = H / tan(theta)
        sill corners A, B       = (0, 0, 0), (W, 0, 0)

Each dormer roof plane is the triangle (A, P, Q). The ridge is perpendicular to the rafter A->P,
so the triangle has a RIGHT ANGLE AT P, with legs
        rafter  R = |AP| = (W/2) / cos(phi)
        ridge   L = |PQ| = y_e = H / tan(theta)
and the hypotenuse |AQ| is the valley where the dormer roof meets the main roof.

Because the ridge is horizontal, the dormer depth is *determined* by the pitches
(it is not a free parameter): measured on the main roof surface
        footprint depth = y_e / cos(theta) = H / sin(theta)

With a front overhang `o` the roof panels extend `o` in front of the front face (hanging over the
main roof), which turns each triangle into the quadrilateral A', P', Q, A in panel coordinates
(u along the rafter from the eave, v along the ridge from the front face):
        A'(0,-o)  P'(R,-o)  Q(R,L)  A(0,0)
"""

import math
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class DormerGeometry:
    width: float                # W: sill length
    theta_deg: float            # main roof angle
    phi_deg: float              # dormer roof pitch
    overhang: float             # front overhang of the dormer roof planes
    gable_height: float         # H: apex height of the front face above the sill
    rafter: float               # R
    ridge: float                # L: ridge length from the front face to the main roof
    valley: float               # |AQ|
    footprint_depth: float      # depth of the footprint measured on the main roof surface
    apex_angle_deg: float       # apex angle of the front face = 180 - 2*phi

    @property
    def roof_panel_ridge_length(self) -> float:
        """Ridge edge of a roof panel, including the front overhang."""
        return self.ridge + self.overhang

    def roof_panel_edges(self, mirrored: bool = False) -> Tuple[Tuple[str, Tuple[float, float]], ...]:
        """
        Counter-clockwise outline (x right, y up) of a roof panel as (name of the edge that starts at
        this point, point); x runs along the rafter and y along the ridge.

        The left panel runs A' P' Q A (front, ridge, valley, side); `mirrored` gives the right panel (mirror
        image, traversed to stay counter-clockwise). Without overhang the short `side` edge has no length
        and the panel is a plain right triangle.
        """
        R, L, o = self.rafter, self.ridge, self.overhang
        if not mirrored:
            if o > 0:
                return (('front', (0.0, -o)), ('ridge', (R, -o)), ('valley', (R, L)), ('side', (0.0, 0.0)))
            return (('front', (0.0, 0.0)), ('ridge', (R, 0.0)), ('valley', (R, L)))
        if o > 0:
            return (('side', (R, -o)), ('valley', (R, 0.0)), ('ridge', (0.0, L)), ('front', (0.0, -o)))
        return (('valley', (R, 0.0)), ('ridge', (0.0, L)), ('front', (0.0, 0.0)))

    def roof_panel_outline(self, mirrored: bool = False) -> Tuple[Tuple[float, float], ...]:
        """The corner points of `roof_panel_edges`."""
        return tuple(p for _, p in self.roof_panel_edges(mirrored))

    def face_triangle(self, lift: float) -> Tuple[float, float, float]:
        """
        The front face when its level base is raised by `lift`: a similar, smaller triangle whose sloped
        edges still lie on the roof planes. Returns (width, height, rake edge length).

        A vertical slab standing on a rising roof would dig into it by its thickness times tan(theta); the
        caller lifts the base by exactly that (the face is cut level at the highest roof point under it).
        """
        cot = 1 / math.tan(math.radians(self.phi_deg))
        return (self.width - 2 * lift * cot, self.gable_height - lift, self.rafter - lift / math.sin(math.radians(self.phi_deg)))

    def footprint_triangle(self) -> Tuple[Tuple[float, float], ...]:
        """Footprint on the main roof panel relative to its top-left: (x,y) of A, B, Q.
        y grows downslope, so the sill (A-B) is the bottom edge and Q the up-slope apex."""
        W, D = self.width, self.footprint_depth
        return ((0.0, D), (W, D), (W / 2, 0.0))


def solve_dormer(theta_deg: float, width: float, phi_deg: float = None,
                 overhang: float = 0.0) -> DormerGeometry:
    """
    Args:
        theta_deg: main roof angle (0 < theta < 90)
        width: dormer sill width W
        phi_deg: dormer roof pitch; default = theta (the dormer matches the main roof pitch)
        overhang: how far the dormer roof planes project in front of the front face
    """
    if phi_deg is None:
        phi_deg = theta_deg
    if not 0 < theta_deg < 90 or not 0 < phi_deg < 90:
        raise ValueError("roof angles must be between 0 and 90 degrees")
    if width <= 0:
        raise ValueError("dormer width must be positive")
    theta, phi = math.radians(theta_deg), math.radians(phi_deg)
    half = width / 2
    height = half * math.tan(phi)
    rafter = half / math.cos(phi)
    plan_depth = height / math.tan(theta)          # y_e
    return DormerGeometry(
        width=width, theta_deg=theta_deg, phi_deg=phi_deg, overhang=overhang,
        gable_height=height, rafter=rafter, ridge=plan_depth,
        valley=math.hypot(rafter, plan_depth),
        footprint_depth=plan_depth / math.cos(theta),
        apex_angle_deg=180.0 - 2 * phi_deg,
    )
