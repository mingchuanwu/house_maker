"""
Where every panel sits in the assembled house: a `Frame` per panel (position of its nominal local origin, the
directions of its local u / v axes and its outward normal), derived from the house geometry and the
placement of its components. Used to turn the flat cut panels into a 3D model.

World axes: X along the length, Y along the width, Z up. The floor occupies x in [0, X], y in [0, Y],
z in [0, t]; the side walls stand at y in [-t, 0] and [Y, Y+t], the gable walls at x in [-t, 0] and [X, X+t],
and the roof panels lie on the gable slopes. Every frame is right-handed (u x v = n) with n pointing away from
the house interior, so a panel drawn as seen from outside appears the same way in 3D.

Panel outlines are drawn `shift` further out than the nominal parts (main box: the drawn outline's lower left
corner is at (kerf/2, kerf/2); chimney, dormer and casing pieces are drawn around their nominal origin), which
is the `shift` of the frame.
"""

import math
from dataclasses import dataclass
from typing import Dict, Tuple

from .casings import casing_margins
from .components import DoorType
from .geometry import HouseGeometry

Vec = Tuple[float, float, float]
_Z: Vec = (0.0, 0.0, 1.0)


def _add(a: Vec, b: Vec) -> Vec: return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def _sub(a: Vec, b: Vec) -> Vec: return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _mul(a: Vec, s: float) -> Vec: return (a[0] * s, a[1] * s, a[2] * s)
def _dot(a: Vec, b: Vec) -> float: return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def _neg(a: Vec) -> Vec: return (-a[0], -a[1], -a[2])


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a: Vec) -> Vec:
    n = math.sqrt(_dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n)


@dataclass(frozen=True)
class Frame:
    origin: Vec          # world position of the panel's NOMINAL local origin
    eu: Vec
    ev: Vec
    n: Vec
    thickness: float
    shift: float         # drawn coordinates = nominal coordinates + shift (see module docstring)

    def to_world(self, u: float, v: float, w: float) -> Vec:
        """World point at DRAWN panel coordinates (u, v) and height w above the panel's back face."""
        du, dv = u - self.shift, v - self.shift
        return (self.origin[0] + du * self.eu[0] + dv * self.ev[0] + w * self.n[0],
                self.origin[1] + du * self.eu[1] + dv * self.ev[1] + w * self.n[1],
                self.origin[2] + du * self.eu[2] + dv * self.ev[2] + w * self.n[2])


def _frame(origin, eu, ev, n, t, shift) -> Frame:
    return Frame(tuple(map(float, origin)), tuple(map(float, eu)), tuple(map(float, ev)),
                 tuple(map(float, n)), t, shift)


def _slab(p00: Vec, eu: Vec, ev: Vec, t: float) -> Frame:
    """Frame of a slab whose mid-plane passes through `p00` (the world position of its local origin)."""
    eu, ev = _unit(eu), _unit(ev)
    n = _cross(eu, ev)
    return Frame(_sub(p00, _mul(n, t / 2)), eu, ev, n, t, 0.0)


def _plane_slab(p00: Vec, eu: Vec, ev: Vec, t: float, outward: Vec) -> Frame:
    """Frame of a slab lying on the OUTER side of the plane through `p00` spanned by eu, ev."""
    eu, ev = _unit(eu), _unit(ev)
    n = _cross(eu, ev)
    origin = _sub(p00, _mul(n, t)) if _dot(n, outward) < 0 else p00
    return Frame(origin, eu, ev, n, t, 0.0)


# ------------------------------------------------------------------------------------------------ main box
def box_frames(g: HouseGeometry) -> Dict[str, Frame]:
    """Frames of the floor, the four walls and the two roof panels."""
    X, Y, Z, t, k = g.x, g.y, g.z, g.thickness, g.kerf
    c, s = math.cos(math.radians(g.theta)), math.sin(math.radians(g.theta))
    peak = Z + (Y + 2 * t) / 2 * math.tan(math.radians(g.theta))
    h = k / 2
    F = lambda o, eu, ev, n: _frame(o, eu, ev, n, t, h)
    return {
        'floor': F((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)),
        'side_wall_left': F((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0)),
        'side_wall_right': F((X, Y, 0), (-1, 0, 0), (0, 0, 1), (0, 1, 0)),
        'gable_wall_front': F((X, -t, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0)),
        'gable_wall_back': F((0, Y + t, 0), (0, -1, 0), (0, 0, 1), (-1, 0, 0)),
        # the left roof panel's ridge edge lies t beyond the peak: its notched edge overlaps the right panel
        'roof_panel_left': F((X + 3 * t, Y / 2 + t * c, peak + t * s), (-1, 0, 0), (0, -c, -s), (0, -s, c)),
        'roof_panel_right': F((-3 * t, Y / 2, peak), (1, 0, 0), (0, c, -s), (0, s, c)),
    }


# ------------------------------------------------------------------------------------------------ chimney
def chimney_frames(roof: Frame, x: float, y: float, W: float, D: float, theta: float, index: int
                   ) -> Dict[str, Frame]:
    """
    Frames of a chimney standing on `roof` (the frame of the roof panel that carries it). (x, y) is the top left
    of the outer footprint in the roof's drawn coordinates (v grows down the slope), W the interior width and D
    the plan depth. Side walls stand outside, over the full plan depth; the front (down-slope) and back (up-slope)
    walls fit between them and are cut level at the highest roof point under their thickness.
    """
    t = roof.thickness
    th = math.radians(theta)
    down = _unit((roof.ev[0], roof.ev[1], 0.0))
    up = _neg(down)
    Wo, slope = W + 2 * t, D / math.cos(th)
    front = lambda u: roof.to_world(u, y + slope, t)                # roof top surface, at the front face
    z_front = front(x)[2]
    tan = math.tan(th)
    at = lambda p, z: (p[0], p[1], z)

    frames = {}
    frames[f'chimney_left_{index}'] = _slab(at(front(x + t / 2), z_front), up, _Z, t)
    frames[f'chimney_right_{index}'] = _slab(at(_add(front(x + Wo - t / 2), _mul(up, D)), z_front), down, _Z, t)
    p0 = front(x + t)
    frames[f'chimney_front_{index}'] = _slab(at(_add(p0, _mul(up, t / 2)), z_front + t * tan), roof.eu, _Z, t)
    frames[f'chimney_back_{index}'] = _slab(at(_add(p0, _mul(up, D - t / 2)), z_front + D * tan), roof.eu, _Z, t)
    m = t + 0.05 * t                                                # casing margin
    c0 = roof.to_world(x - m, y - m - t * tan, t + t / 2)           # longer up-slope: the walls lean
    frames[f'chimney_casing_{index}'] = _slab(c0, roof.eu, roof.ev, t)
    return frames


# ------------------------------------------------------------------------------------------------ dormer
def dormer_frames(roof: Frame, x: float, y: float, W: float, theta: float, phi: float, index: int
                  ) -> Dict[str, Frame]:
    """
    Frames of a gable dormer on `roof`: the front face (a vertical triangle) and the two roof panels. The ridge is
    horizontal at the apex height, so the dormer ends where the main roof rises to that height.
    """
    t = roof.thickness
    th, ph = math.radians(theta), math.radians(phi)
    height = (W / 2) * math.tan(ph)
    plan_depth = height / math.tan(th)
    down = _unit((roof.ev[0], roof.ev[1], 0.0))
    up = _neg(down)
    slope = plan_depth / math.cos(th)
    A = roof.to_world(x, y + slope, t)
    B = roof.to_world(x + W, y + slope, t)
    P = _add(_mul(_add(A, B), 0.5), (0.0, 0.0, height))
    a = _unit(_sub(B, A))
    lift = t * math.tan(th)
    face0 = _add(_add(_add(A, _mul(_Z, lift)), _mul(a, lift / math.tan(ph))), _mul(up, t / 2))
    return {
        f'additional_gable_front_{index}': _slab(face0, a, _Z, t),
        f'additional_gable_roof_left_{index}': _plane_slab(A, _sub(P, A), up, t, _Z),
        f'additional_gable_roof_right_{index}': _plane_slab(P, _sub(B, P), up, t, _Z),
    }


# ------------------------------------------------------------------------------------------------ casings
def casing_frame(wall: Frame, kind: str, ctype, pos) -> Frame:
    """
    Frame of the trim piece around a window ('window') or door ('door') on `wall`; the piece lies on the outside
    face of the wall. `pos` is the component position (drawn wall coordinates). The opening is centred on the
    component. Window casings and the arched door casing are drawn upright (opening at their foot); the
    rectangular door casing is drawn upside down (its top bar at v = 0), so it is mounted turned half a revolution.
    """
    t = wall.thickness
    left, bottom, right, top = casing_margins(kind, ctype, pos.width, pos.height, t)
    u0, v0 = pos.x - left, pos.y - bottom
    if kind == 'door' and ctype != DoorType.ARCHED:
        far = pos.x + pos.width + right, pos.y + pos.height + top        # the piece's far corner becomes its origin
        return Frame(wall.to_world(far[0], far[1], t), _neg(wall.eu), _neg(wall.ev), wall.n, t, 0.0)
    return Frame(wall.to_world(u0, v0, t), wall.eu, wall.ev, wall.n, t, 0.0)
