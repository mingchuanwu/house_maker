"""
Triangle meshes: polygon triangulation (outline with holes) and extrusion into a watertight solid.

Pure Python, no dependencies. A `Mesh` is a list of vertices and CCW triangles (outward normals).
"""

import math
from dataclasses import dataclass, field
from typing import List, Sequence, Tuple

from .exceptions import GeometryError

Vec = Tuple[float, float, float]
Pt = Tuple[float, float]
_EPS = 1e-12


@dataclass
class Mesh:
    vertices: List[Vec] = field(default_factory=list)
    triangles: List[Tuple[int, int, int]] = field(default_factory=list)

    def bounds(self) -> Tuple[Vec, Vec]:
        xs, ys, zs = zip(*self.vertices)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def volume(self) -> float:
        """Signed volume (positive for outward-facing triangles of a closed mesh)."""
        v = self.vertices
        total = 0.0
        for a, b, c in self.triangles:
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = v[a], v[b], v[c]
            total += ax * (by * cz - bz * cy) + ay * (bz * cx - bx * cz) + az * (bx * cy - by * cx)
        return total / 6.0

    def is_watertight(self) -> bool:
        """Every edge is shared by exactly two triangles, once in each direction."""
        edges = {}
        for a, b, c in self.triangles:
            for e in ((a, b), (b, c), (c, a)):
                edges[e] = edges.get(e, 0) + 1
        return all(n == 1 and (e[1], e[0]) in edges for e, n in edges.items())


def signed_area(ring: Sequence[Pt]) -> float:
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, list(ring[1:]) + [ring[0]])) / 2


def _cross(o: Pt, a: Pt, b: Pt) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _in_triangle(a: Pt, b: Pt, c: Pt, p: Pt) -> bool:
    """p inside or on the boundary of CCW triangle abc."""
    return _cross(a, b, p) >= -_EPS and _cross(b, c, p) >= -_EPS and _cross(c, a, p) >= -_EPS


def _bridge(outer: List[int], hole: List[int], pts: List[Pt]) -> List[int]:
    """Merge a hole (CW indices) into the outline (CCW indices) through a cut to a visible vertex."""
    m_pos = max(range(len(hole)), key=lambda i: (pts[hole[i]][0], -pts[hole[i]][1]))
    mi = hole[m_pos]
    mx, my = pts[mi]
    # nearest outline edge hit by the ray from M towards +x
    best, best_x = None, math.inf
    n = len(outer)
    for i in range(n):
        a, b = pts[outer[i]], pts[outer[(i + 1) % n]]
        if (a[1] - my) * (b[1] - my) > 0 or a[1] == b[1]:
            continue
        x = a[0] + (my - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
        if x >= mx - _EPS and x < best_x:
            best_x, best = x, i
    if best is None:
        raise GeometryError("triangulate", "hole is not inside the outline")
    i0, i1 = best, (best + 1) % n
    cand = i0 if pts[outer[i0]][0] > pts[outer[i1]][0] else i1
    if pts[outer[i0]][1] == my and pts[outer[i0]][0] >= mx - _EPS:
        cand = i0
    elif pts[outer[i1]][1] == my and pts[outer[i1]][0] >= mx - _EPS:
        cand = i1
    else:
        # any outline vertex inside triangle (M, hit, candidate) blocks the view; take the one closest in angle
        hit = (best_x, my)
        p = pts[outer[cand]]
        tri = (mx, my), hit, p
        if _cross(*tri) < 0:
            tri = (tri[0], tri[2], tri[1])
        best_ang = None
        for j in range(n):
            q = pts[outer[j]]
            if j == cand or q[0] < mx - _EPS:
                continue
            if _in_triangle(*tri, q) and q != (mx, my):
                ang = abs(math.atan2(q[1] - my, q[0] - mx))
                if best_ang is None or ang < best_ang or (ang == best_ang and q[0] < pts[outer[cand]][0]):
                    best_ang, cand = ang, j
    # splice: outer[..cand], M, hole around, M, outer[cand..]
    rotated = hole[m_pos:] + hole[:m_pos]
    return outer[:cand + 1] + rotated + [rotated[0]] + outer[cand:]


def triangulate(outer: Sequence[Pt], holes: Sequence[Sequence[Pt]] = ()) -> Tuple[List[Pt], List[Tuple[int, int, int]]]:
    """
    Triangulate a simple polygon with holes. Returns (points, triangles): `points` is the outline followed by
    the holes in order (so indices map directly to the input rings); triangles are CCW index triples that use
    only those points, so extruded side walls always match the caps.
    """
    pts: List[Pt] = []
    rings: List[List[int]] = []
    for k, ring in enumerate([outer] + list(holes)):
        ring = list(ring)
        want_ccw = k == 0
        start = len(pts)
        idx = list(range(start, start + len(ring)))
        if (signed_area(ring) > 0) != want_ccw:
            idx.reverse()
        pts.extend(ring)
        rings.append(idx)
    poly = rings[0]
    for hole in sorted(rings[1:], key=lambda r: -max(pts[i][0] for i in r)):
        poly = _bridge(poly, hole, pts)
    return pts, _ear_clip(poly, pts)


def _ear_clip(poly: List[int], pts: List[Pt]) -> List[Tuple[int, int, int]]:
    poly = list(poly)
    tris: List[Tuple[int, int, int]] = []
    guard = 0
    while len(poly) > 3:
        n = len(poly)
        clipped = False
        for strict in (True, False):
            for i in range(n):
                ia, ib, ic = poly[i - 1], poly[i], poly[(i + 1) % n]
                a, b, c = pts[ia], pts[ib], pts[ic]
                area = _cross(a, b, c)
                if area <= _EPS:
                    if strict:
                        continue
                    if area < -_EPS:
                        continue
                    # zero-area spike/collinear vertex: drop it without emitting a triangle
                    poly.pop(i)
                    clipped = True
                    break
                if any(pts[j] not in (a, b, c) and _in_triangle(a, b, c, pts[j]) for j in poly
                       if j not in (ia, ib, ic)):
                    continue
                tris.append((ia, ib, ic))
                poly.pop(i)
                clipped = True
                break
            if clipped:
                break
        if not clipped:
            # numerically stuck: clip the sharpest convex vertex so we still terminate
            i = max(range(n), key=lambda k: _cross(pts[poly[k - 1]], pts[poly[k]], pts[poly[(k + 1) % n]]))
            tris.append((poly[i - 1], poly[i], poly[(i + 1) % n]))
            poly.pop(i)
        guard += 1
        if guard > 10 * len(pts) + 100:
            raise GeometryError("triangulate", "polygon could not be triangulated")
    if len(poly) == 3 and _cross(pts[poly[0]], pts[poly[1]], pts[poly[2]]) > _EPS:
        tris.append((poly[0], poly[1], poly[2]))
    return tris


def extrude(outer: Sequence[Pt], holes: Sequence[Sequence[Pt]], thickness: float, to_world) -> Mesh:
    """
    Prism of the polygon (outline minus holes) between w = 0 and w = thickness. `to_world(u, v, w)` maps panel
    coordinates to world space and must preserve handedness (u x v = +w), so CCW stays outward.
    """
    pts, tris = triangulate(outer, holes)
    n = len(pts)
    mesh = Mesh()
    mesh.vertices = [to_world(u, v, 0.0) for u, v in pts] + [to_world(u, v, thickness) for u, v in pts]
    for a, b, c in tris:
        mesh.triangles.append((a + n, b + n, c + n))            # top cap, normal +w
        mesh.triangles.append((a, c, b))                        # bottom cap, normal -w
    # side walls follow each ring (outline CCW, holes CW => outward from the solid)
    start = 0
    for k, ring in enumerate([outer] + list(holes)):
        m = len(ring)
        ccw = signed_area(ring) > 0
        want_ccw = k == 0
        order = list(range(start, start + m))
        if ccw != want_ccw:
            order.reverse()
        for i in range(m):
            a, b = order[i], order[(i + 1) % m]
            mesh.triangles.append((a, b, b + n))
            mesh.triangles.append((a, b + n, a + n))
        start += m
    return mesh
