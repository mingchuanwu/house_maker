"""
Independent 3D model of the assembled house, derived by hand from the specification (not from the
library): where every flat panel sits in space, and a physical-solid membership test.

World axes: X along the length, Y along the width, Z up. The floor occupies x in [0, X], y in [0, Y],
z in [0, t]; side walls stand at y in [-t, 0] and [Y, Y+t]; gable walls at x in [-t, 0] and [X, X+t];
the roof panels lie on the gable slopes, overhanging each gable wall by 2t.

A panel is a slab: local (u, v) in the drawn outline, w in [0, t] along the normal. The cut part is the
drawn outline eroded by kerf/2 (the laser removes kerf/2 on each side of every drawn line).
"""

import math
from dataclasses import dataclass

import numpy as np

from house_maker.svgpath import parse_path


@dataclass
class Frame:
    O: np.ndarray       # world position of the panel's NOMINAL local origin
    eu: np.ndarray
    ev: np.ndarray
    n: np.ndarray
    t: float
    k: float
    shift: float = None     # drawn outline = nominal outline + shift on each side; None -> kerf/2 (main box)

    @property
    def h(self):
        return self.k / 2 if self.shift is None else self.shift

    def to_local(self, pts):
        """World points (N,3) -> drawn-outline coordinates (u, v) and slab coordinate w."""
        rel = pts - self.O
        return rel @ self.eu + self.h, rel @ self.ev + self.h, rel @ self.n

    def to_world(self, u, v, w):
        return self.O + np.outer(u - self.h, self.eu) + np.outer(v - self.h, self.ev) + np.outer(w, self.n)


def box_frames(X, Y, Z, theta, t, k):
    c, s = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    zp = Z + (Y + 2 * t) / 2 * math.tan(math.radians(theta))          # peak height
    V = lambda *a: np.array(a, dtype=float)
    F = lambda O, eu, ev, n: Frame(V(*O), V(*eu), V(*ev), V(*n), t, k)
    return {
        'floor': F((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)),
        'side_wall_left': F((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0)),
        'side_wall_right': F((X, Y, 0), (-1, 0, 0), (0, 0, 1), (0, 1, 0)),
        # the gable walls are mirror-symmetric parts, so either orientation is a valid way to mount them
        'gable_wall_front': F((X, -t, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0)),
        'gable_wall_back': F((0, -t, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0)),
        # left roof: ridge edge lies t beyond the peak (its notched edge overlaps the right panel)
        'roof_panel_left': F((X + 3 * t, Y / 2 + t * c, zp + t * s), (-1, 0, 0), (0, -c, -s), (0, -s, c)),
        'roof_panel_right': F((-3 * t, Y / 2, zp), (1, 0, 0), (0, c, -s), (0, s, c)),
    }


class PanelSolid:
    """Physical membership test for one panel."""

    def __init__(self, panel, frame):
        self.panel, self.frame = panel, frame
        polys = [sub for d in panel.cut for sub in parse_path(d)]
        self.polys = [np.array([(p.x, p.y) for p in poly]) for poly in polys]
        a, b = [], []
        for poly in self.polys:
            a.append(poly)
            b.append(np.roll(poly, -1, axis=0))
        self.A, self.B = np.vstack(a), np.vstack(b)

    def _inside_2d(self, u, v):
        inside = np.zeros(len(u), dtype=bool)
        for poly in self.polys:                       # even-odd across outline, holes and slots
            x1, y1 = poly[:, 0][None, :], poly[:, 1][None, :]
            x2, y2 = np.roll(poly[:, 0], -1)[None, :], np.roll(poly[:, 1], -1)[None, :]
            uu, vv = u[:, None], v[:, None]
            cross = ((y1 > vv) != (y2 > vv)) & (uu < (x2 - x1) * (vv - y1) / np.where(y2 == y1, 1, y2 - y1) + x1)
            inside ^= (cross.sum(axis=1) % 2 == 1)
        return inside

    def _edge_distance(self, u, v):
        d = self.B - self.A
        L2 = (d ** 2).sum(axis=1)
        L2 = np.where(L2 == 0, 1, L2)
        out = np.full(len(u), np.inf)
        for i in range(0, len(self.A), 64):          # chunk to bound memory
            a, dd, ll = self.A[i:i + 64], d[i:i + 64], L2[i:i + 64]
            t = np.clip(((u[:, None] - a[:, 0]) * dd[:, 0] + (v[:, None] - a[:, 1]) * dd[:, 1]) / ll, 0, 1)
            dx = u[:, None] - (a[:, 0] + t * dd[:, 0])
            dy = v[:, None] - (a[:, 1] + t * dd[:, 1])
            out = np.minimum(out, np.sqrt(dx * dx + dy * dy).min(axis=1))
        return out

    def contains(self, pts):
        """Is each world point inside the physical (kerf-eroded) solid?"""
        u, v, w = self.frame.to_local(pts)
        ok = (w > 0) & (w < self.frame.t)
        res = np.zeros(len(pts), dtype=bool)
        idx = np.where(ok)[0]
        if len(idx):
            uu, vv = u[idx], v[idx]
            inside = self._inside_2d(uu, vv)
            if self.frame.k > 0:
                inside &= self._edge_distance(uu, vv) >= self.frame.k / 2
            res[idx] = inside
        return res

    def sample(self, step=0.5, layers=3):
        """Interior sample points of the physical solid, as world coordinates."""
        us = [p[:, 0] for p in self.polys]
        u0, u1 = min(x.min() for x in us), max(x.max() for x in us)
        vs = [p[:, 1] for p in self.polys]
        v0, v1 = min(x.min() for x in vs), max(x.max() for x in vs)
        gu, gv = np.meshgrid(np.arange(u0 + step / 2, u1, step), np.arange(v0 + step / 2, v1, step))
        u, v = gu.ravel(), gv.ravel()
        inside = self._inside_2d(u, v)
        if self.frame.k > 0:
            inside &= self._edge_distance(u, v) >= self.frame.k / 2
        u, v = u[inside], v[inside]
        pts = [self.frame.to_world(u, v, np.full(len(u), self.frame.t * (i + 0.5) / layers)) for i in range(layers)]
        return np.vstack(pts), step * step * self.frame.t / layers          # points, volume per point

    def depth(self, pts):
        """Penetration depth of points into the physical solid: distance to its nearest surface
        (slab faces or any cut edge, which sits kerf/2 inside the drawn line). NaN if outside."""
        u, v, w = self.frame.to_local(pts)
        t = self.frame.t
        out = np.full(len(pts), np.nan)
        inside = self.contains(pts)
        idx = np.where(inside)[0]
        if len(idx):
            d_edge = self._edge_distance(u[idx], v[idx]) - self.frame.k / 2
            out[idx] = np.minimum(np.minimum(w[idx], t - w[idx]), d_edge)
        return out


def worst_penetrations(panels, frames, step=1.0):
    """{(a, b): deepest penetration of a's solid into b's solid} for all overlapping ordered pairs."""
    import itertools
    solids = {n: PanelSolid(panels[n], frames[n]) for n in frames if n in panels}
    samples = {n: s.sample(step=step) for n, s in solids.items()}
    out = {}
    for a, b in itertools.permutations(solids, 2):
        d = solids[b].depth(samples[a][0])
        d = d[~np.isnan(d)]
        if len(d):
            out[(a, b)] = float(d.max())
    return out


# ------------------------------------------------------------------------------------------------
# Chimney
# ------------------------------------------------------------------------------------------------
def _unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def _slab(P00, eu, ev, t, k, shift=None):
    """Frame of a slab whose mid-plane passes through P00 (the world position of local origin)."""
    eu, ev = _unit(eu), _unit(ev)
    n = np.cross(eu, ev)
    return Frame(P00 - (t / 2) * n, eu, ev, n, t, k, shift)


def roof_point(roof: Frame, u, v, w):
    """World point at drawn roof coordinates (u, v) and height w above the roof's underside."""
    return roof.to_world(np.array([u], float), np.array([v], float), np.array([w], float))[0]


def chimney_frames(roof: Frame, x, y, W, D, theta, t, k, index=0, shift=0.0):
    """
    Frames of the chimney's panels standing on `roof` (the frame of the roof panel that carries it).

    Chimney model: footprint (x, y) .. (x + W + 2t, y + D / cos(theta)) on the roof panel (drawn coordinates,
    v grows down the slope). Side walls stand outside, full plan depth D; front (down-slope) and back
    (up-slope) walls fit between them. Wall bases: side walls follow the roof; front/back are cut level at
    the highest roof point under their thickness.
    """
    th = math.radians(theta)
    down = _unit(np.array([roof.ev[0], roof.ev[1], 0.0]))          # horizontal down-slope direction
    up = -down
    Z = np.array([0.0, 0.0, 1.0])
    a = roof.eu
    Wo, l = W + 2 * t, D / math.cos(th)
    front = lambda u: roof_point(roof, u, y + l, t)                 # roof top surface, front face
    z_front = front(x)[2]
    tan = math.tan(th)
    at = lambda p, z: np.array([p[0], p[1], z])

    frames = {}
    # side walls (left: local u runs up-slope from the front; right: down-slope from the back)
    pl = at(front(x + t / 2), z_front)
    frames[f'chimney_left_{index}'] = _slab(pl, up, Z, t, k, shift)
    pr = at(front(x + Wo - t / 2) + D * up, z_front)
    frames[f'chimney_right_{index}'] = _slab(pr, down, Z, t, k, shift)
    # front / back walls between the side walls
    p0 = front(x + t)
    frames[f'chimney_front_{index}'] = _slab(at(p0 + (t / 2) * up, z_front + t * tan), a, Z, t, k, shift)
    frames[f'chimney_back_{index}'] = _slab(at(p0 + (D - t / 2) * up, z_front + D * tan), a, Z, t, k, shift)
    # casing frame lying on the roof around the footprint
    m = t + 0.05 * t
    up_extra = t * tan                                              # the leaning walls need this much more room up-slope
    c0 = roof_point(roof, x - m, y - m - up_extra, t + t / 2)
    frames[f'chimney_casing_{index}'] = _slab(c0, roof.eu, roof.ev, t, k, shift)
    return frames


# ------------------------------------------------------------------------------------------------
# Dormer
# ------------------------------------------------------------------------------------------------
def dormer_points(roof: Frame, x, y, W, theta, phi, t):
    """Corner points of the dormer in 3D: sill corners A, B on the roof, apex P of the face, ridge end Q.
    Independent construction: the ridge is horizontal at the apex height, so it ends where the main roof
    surface rises to that height (Q is checked to lie on the roof plane by the tests)."""
    th, ph = math.radians(theta), math.radians(phi)
    H = (W / 2) * math.tan(ph)
    plan_depth = H / math.tan(th)                                  # horizontal distance from the sill to Q
    down = _unit(np.array([roof.ev[0], roof.ev[1], 0.0]))
    up = -down
    l = plan_depth / math.cos(th)                                  # the same distance measured on the roof surface
    A = roof_point(roof, x, y + l, t)
    B = roof_point(roof, x + W, y + l, t)
    P = (A + B) / 2 + np.array([0.0, 0.0, H])
    Q = P + plan_depth * up
    return dict(A=A, B=B, P=P, Q=Q, up=up, H=H, plan_depth=plan_depth, l=l)


def _plane_slab(P00, eu, ev, t, k, outward, shift=0.0):
    """Frame of a slab lying on the OUTER side of the plane through P00 spanned by eu, ev."""
    eu, ev = _unit(eu), _unit(ev)
    n = np.cross(eu, ev)
    O = P00 - t * n if np.dot(n, outward) < 0 else P00           # slab spans w in [0, t] along +n
    return Frame(O, eu, ev, n, t, k, shift)


def dormer_frames(roof: Frame, x, y, W, theta, phi, t, k, index=0, shift=0.0):
    d = dormer_points(roof, x, y, W, theta, phi, t)
    A, B, P, up = d['A'], d['B'], d['P'], d['up']
    Z = np.array([0.0, 0.0, 1.0])
    a = _unit(B - A)
    lift = t * math.tan(math.radians(theta))        # the face is cut level at the highest roof point under it
    return {
        # front face: vertical triangle, thickness t BEHIND the front line (up-slope)
        f'additional_gable_front_{index}': _slab(
            A + lift * Z + (lift / math.tan(math.radians(phi))) * a + (t / 2) * up, a, Z, t, k, shift),
        # roof panels: underside plane through the sill corner, the apex and the ridge end
        f'additional_gable_roof_left_{index}': _plane_slab(A, P - A, up, t, k, Z, shift),
        f'additional_gable_roof_right_{index}': _plane_slab(P, B - P, up, t, k, Z, shift),
    }, d
