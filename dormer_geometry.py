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

Side walls (cheeks)
-------------------
With walls of height Hw the eave line runs level at z = Hw instead of along the sill: the two roof planes start
there, the apex is at Hw + H and the ridge reaches y_Q = (Hw + H) / tan(theta). Each cheek is a vertical right
triangle under an eave: front edge Hw tall, level top meeting the roof at y_w = Hw / tan(theta), bottom on the roof.
A roof panel's side edge rests on the cheek top from the front to E = (0, y_w), and its valley runs from E to Q.
The front face becomes a pentagon (vertical sides up to the eave line, then the gable). Hw = 0 is the plain dormer.
"""

import math
from dataclasses import dataclass
from typing import Tuple

DEFAULT_PITCH = 45.0       # degrees: a 90 degree apex, the classic dormer; deeper than matching a shallower main roof
AUTO_WALL_ANGLE = 45.0     # degrees: dormers on steeper main roofs get side walls unless told otherwise


@dataclass(frozen=True)
class DormerGeometry:
    width: float                # W: sill length
    theta_deg: float            # main roof angle
    phi_deg: float              # dormer roof pitch
    overhang: float             # front overhang of the dormer roof planes
    gable_height: float         # Hg: height of the gable (eave line to apex)
    rafter: float               # R
    ridge: float                # L: ridge length from the front face to the main roof
    valley: float               # valley edge of a roof panel (eave end E to Q)
    footprint_depth: float      # depth of the footprint measured on the main roof surface
    apex_angle_deg: float       # apex angle of the front face = 180 - 2*phi
    wall_height: float = 0.0    # H: side wall (cheek) height = eave line above the sill; 0 = no walls

    @property
    def walls(self) -> bool:
        return self.wall_height > 0

    @property
    def eave_depth(self) -> float:
        """y_w: how far (horizontally, up-slope) the eave line runs before it meets the roof - the cheek's length."""
        return self.wall_height / math.tan(math.radians(self.theta_deg))

    @property
    def roof_panel_ridge_length(self) -> float:
        """Ridge edge of a roof panel, including the front overhang."""
        return self.ridge + self.overhang

    def roof_panel_edges(self, mirrored: bool = False, lap: float = 0.0) -> Tuple[Tuple[str, Tuple[float, float]], ...]:
        """
        Counter-clockwise outline (x right, y up) of a roof panel as (name of the edge that starts at
        this point, point); x runs along the rafter from the eave line and y along the ridge from the front face.

        The left panel runs front, ridge, valley, side: the valley goes from the ridge end Q back to the eave end E
        (y = eave_depth, where the eave line meets the roof; the sill corner A without walls) and the side edge from
        E to the front (it rests on the cheek top). `mirrored` gives the right panel (mirror image, traversed to stay
        counter-clockwise). Without walls and overhang the side edge has no length and is left out.

        `lap` (right panel only) carries its ridge edge that far beyond the ridge line (to x = -lap) over the
        whole ridge, ending in a short `ridge_end` edge at Q: the female half of a corner joint must reach the
        outer corner, where the male panel's fingers arrive.
        """
        R, L, o, e = self.rafter, self.ridge, self.overhang, self.eave_depth
        side = o > 0 or e > 0
        if not mirrored:
            out = (('front', (0.0, -o)), ('ridge', (R, -o)), ('valley', (R, L)))
            return out + ((('side', (0.0, e)),) if side else ())
        end = (('ridge_end', (0.0, L)), ('ridge', (-lap, L))) if lap > 0 else (('ridge', (0.0, L)),)
        start = (('side', (R, -o)), ('valley', (R, e))) if side else (('valley', (R, e)),)
        return start + end + (('front', (-lap, -o)),)

    def roof_panel_outline(self, mirrored: bool = False) -> Tuple[Tuple[float, float], ...]:
        """The corner points of `roof_panel_edges`."""
        return tuple(p for _, p in self.roof_panel_edges(mirrored))

    def face_triangle(self, lift: float) -> Tuple[float, float, float]:
        """
        The front face when its level base is raised by `lift`. Returns (width, height, rake edge length).

        A vertical slab standing on a rising roof would dig into it by its thickness times tan(theta); the
        caller lifts the base by exactly that (the face is cut level at the highest roof point under it). Without
        walls the face is a similar, smaller triangle whose sloped edges still lie on the roof planes; with walls it
        keeps its full width (the lift only shortens its vertical sides) and its rakes run the full rafter.
        """
        if self.walls:
            return (self.width, self.wall_height + self.gable_height - lift, self.rafter)
        cot = 1 / math.tan(math.radians(self.phi_deg))
        return (self.width - 2 * lift * cot, self.gable_height - lift, self.rafter - lift / math.sin(math.radians(self.phi_deg)))

    def face_edges(self, lift: float) -> Tuple[Tuple[str, Tuple[float, float]], ...]:
        """Counter-clockwise outline of the front face (x along the sill from its left end, y up from the lifted
        base): a triangle (base, rake_right, rake_left), or with walls a pentagon with vertical sides up to the eave
        line (base, side_right, rake_right, rake_left, side_left)."""
        w, h, _ = self.face_triangle(lift)
        if not self.walls:
            return (('base', (0.0, 0.0)), ('rake_right', (w, 0.0)), ('rake_left', (w / 2, h)))
        s = self.wall_height - lift
        return (('base', (0.0, 0.0)), ('side_right', (w, 0.0)), ('rake_right', (w, s)),
                ('rake_left', (w / 2, h)), ('side_left', (0.0, s)))

    def face_offset(self, lift: float) -> float:
        """Where the face's base starts along the sill (from the sill's left end)."""
        return 0.0 if self.walls else lift / math.tan(math.radians(self.phi_deg))

    def cheek_edges(self, side: str, t: float) -> Tuple[Tuple[str, Tuple[float, float]], ...]:
        """
        Counter-clockwise outline of a side wall (cheek), a right triangle: vertical front edge (against the face's
        rear surface, y = t), level top edge (z = wall height, under the eave), bottom edge on the roof. y up = z;
        x runs horizontally: for the left cheek from its back end E towards the front, for the right one from the
        face towards E, so that both are seen from outside. The front edge starts at the roof, t * tan(theta) above
        the sill.
        """
        H, lift = self.wall_height, t * math.tan(math.radians(self.theta_deg))
        d = self.eave_depth - t
        if side == 'left':
            return (('front', (d, lift)), ('top', (d, H)), ('bottom', (0.0, H)))
        return (('bottom', (0.0, lift)), ('top', (d, H)), ('front', (0.0, H)))

    def footprint_polygon(self) -> Tuple[Tuple[float, float], ...]:
        """Footprint on the main roof panel relative to its top-left, y growing downslope: the sill A-B at the
        bottom, Q the up-slope apex, and with walls the cheeks' back ends between them."""
        W, D = self.width, self.footprint_depth
        if not self.walls:
            return ((0.0, D), (W, D), (W / 2, 0.0))
        e = D - self.eave_depth / math.cos(math.radians(self.theta_deg))
        return ((0.0, D), (W, D), (W, e), (W / 2, 0.0), (0.0, e))


def solve_dormer(theta_deg: float, width: float, phi_deg: float = None,
                 overhang: float = 0.0, wall_height: float = None) -> DormerGeometry:
    """
    Args:
        theta_deg: main roof angle (0 < theta < 90)
        width: dormer sill width W
        phi_deg: dormer roof pitch; default DEFAULT_PITCH (45: a right angle at the apex)
        overhang: how far the dormer roof planes project in front of the front face
        wall_height: side wall height (eave line above the sill); 0 = no walls. Default: walls as tall as the
            gable on roofs steeper than AUTO_WALL_ANGLE, none otherwise.
    """
    walls = wall_height > 0 if wall_height is not None else theta_deg > AUTO_WALL_ANGLE
    if phi_deg is None:
        phi_deg = DEFAULT_PITCH
    if not 0 < theta_deg < 90 or not 0 < phi_deg < 90:
        raise ValueError("roof angles must be between 0 and 90 degrees")
    if width <= 0:
        raise ValueError("dormer width must be positive")
    if wall_height is not None and wall_height < 0:
        raise ValueError("dormer wall height cannot be negative")
    theta, phi = math.radians(theta_deg), math.radians(phi_deg)
    half = width / 2
    gable = half * math.tan(phi)
    wall = (wall_height if wall_height is not None else gable) if walls else 0.0
    rafter = half / math.cos(phi)
    plan_depth = (wall + gable) / math.tan(theta)         # y_Q: the ridge at the apex height meets the roof
    eave = wall / math.tan(theta)
    return DormerGeometry(
        width=width, theta_deg=theta_deg, phi_deg=phi_deg, overhang=overhang,
        gable_height=gable, rafter=rafter, ridge=plan_depth,
        valley=math.hypot(rafter, plan_depth - eave),
        footprint_depth=plan_depth / math.cos(theta),
        apex_angle_deg=180.0 - 2 * phi_deg,
        wall_height=wall,
    )
