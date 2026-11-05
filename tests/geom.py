"""Small vector helpers and panel-reading utilities shared by the component tests."""

import math

from house_maker.svgpath import parse_path


def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def norm(a): return math.sqrt(dot(a, a))


def outline(panel):
    """The panel's outer cut outline as a list of Points."""
    return parse_path(panel.cut[0])[0]


def holes(panel):
    """Closed sub-paths of the cut layer other than the outline (cutouts, slots)."""
    return [sub_ for d in panel.cut[1:] for sub_ in parse_path(d)]


def bounds(points):
    xs, ys = [p.x for p in points], [p.y for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def point_in_polygon(pt, poly):
    x, y, inside = pt[0], pt[1], False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (a.y > y) != (b.y > y) and x < (b.x - a.x) * (y - a.y) / (b.y - a.y) + a.x:
            inside = not inside
    return inside


def dedupe(points):
    """Drop consecutive duplicates (and a repeated closing point)."""
    out = []
    for p in points:
        if not out or abs(p.x - out[-1].x) > 1e-9 or abs(p.y - out[-1].y) > 1e-9:
            out.append(p)
    if len(out) > 1 and abs(out[0].x - out[-1].x) < 1e-9 and abs(out[0].y - out[-1].y) < 1e-9:
        out.pop()
    return out


def signed_area(points):
    return sum(a.x * b.y - b.x * a.y for a, b in zip(points, points[1:] + points[:1])) / 2


def _ccw(a, b, c):
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def segments_cross(p1, p2, p3, p4, eps=1e-9):
    """Proper crossing of segments p1p2 and p3p4 (touching at endpoints is not a crossing)."""
    d1, d2 = _ccw(p3, p4, p1), _ccw(p3, p4, p2)
    d3, d4 = _ccw(p1, p2, p3), _ccw(p1, p2, p4)
    return ((d1 > eps and d2 < -eps) or (d1 < -eps and d2 > eps)) and ((d3 > eps and d4 < -eps) or (d3 < -eps and d4 > eps))


def is_simple(points):
    """No two non-adjacent edges of the closed polygon cross."""
    pts = dedupe(points)
    n = len(pts)
    edges = [(pts[i], pts[(i + 1) % n]) for i in range(n)]
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            if segments_cross(*edges[i], *edges[j]):
                return False
    return True


def flat(pairs):
    """[(a, b), ...] -> [a, b, ...] (pytest.approx does not accept nested sequences)."""
    return [v for pair in pairs for v in pair]


def segment_distance(p, a, b):
    """Distance from point p to segment a-b."""
    dx, dy = b.x - a.x, b.y - a.y
    L2 = dx * dx + dy * dy
    s = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p.x - a.x) * dx + (p.y - a.y) * dy) / L2))
    return ((p.x - a.x - s * dx) ** 2 + (p.y - a.y - s * dy) ** 2) ** 0.5


def nominal_corners(panel, kerf):
    """A kerf-compensated panel's nominal (as-cut) corners: the drawn outline moved inward by kerf/2."""
    from house_maker.geometry import offset_polygon
    return offset_polygon(panel.corners, -kerf / 2)


def nominal_edge_length(panel, edge, kerf):
    pts = nominal_corners(panel, kerf)
    i = panel.edge_names.index(edge)
    a, b = pts[i], pts[(i + 1) % len(pts)]
    return ((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5


def nominal_extent(panel, kerf):
    pts = nominal_corners(panel, kerf)
    xs, ys = [p.x for p in pts], [p.y for p in pts]
    return max(xs) - min(xs), max(ys) - min(ys)


def centre_from_drawn_start(panel, edge, kerf):
    """Distance from the DRAWN start of an edge to the middle of the NOMINAL edge (where a centred tab sits)."""
    from house_maker.geometry import offset_polygon
    nom = offset_polygon(panel.corners, -kerf / 2)
    i = panel.edge_names.index(edge)
    n0, n1, d0 = nom[i], nom[(i + 1) % len(nom)], panel.corners[i]
    length = ((n1.x - n0.x) ** 2 + (n1.y - n0.y) ** 2) ** 0.5
    ux, uy = (n1.x - n0.x) / length, (n1.y - n0.y) / length
    shift = (d0.x - n0.x) * ux + (d0.y - n0.y) * uy               # drawn start vs nominal start along the edge
    return length / 2 - shift
