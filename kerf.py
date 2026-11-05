"""
Kerf compensation of arbitrary closed cut paths (window/door cut-outs, trim frames).

The laser removes `kerf` of material centred on the drawn line, so a cut part ends up kerf/2 smaller on every
edge and a hole kerf/2 larger. Drawn paths are therefore offset by kerf/2: parts outward, holes inward.
Curves are flattened to fine polylines first so the offset is exact (a Bezier has no exact Bezier offset).
"""

from typing import List

from .constants import COORDINATE_PRECISION
from .geometry import Point, offset_polygon
from .svgpath import parse_path

CURVE_SAMPLES = 32          # chord error on a 15 mm radius quarter circle: ~0.001 mm
_P = COORDINATE_PRECISION


def _clean(poly: List[Point]) -> List[Point]:
    out = []
    for p in poly:
        if not out or abs(p.x - out[-1].x) > 1e-9 or abs(p.y - out[-1].y) > 1e-9:
            out.append(p)
    if len(out) > 1 and abs(out[0].x - out[-1].x) < 1e-9 and abs(out[0].y - out[-1].y) < 1e-9:
        out.pop()
    return out


def _signed_area(poly: List[Point]) -> float:
    return sum(a.x * b.y - b.x * a.y for a, b in zip(poly, poly[1:] + poly[:1])) / 2


def _path(polys: List[List[Point]]) -> str:
    return " ".join("M " + " L ".join(f"{p.x:.{_P}f},{p.y:.{_P}f}" for p in poly) + " Z" for poly in polys)


def _offset(poly: List[Point], distance: float) -> List[Point]:
    """Offset a closed polygon of either orientation; positive distance grows it."""
    poly = _clean(poly)
    flipped = _signed_area(poly) < 0
    if flipped:
        poly = poly[::-1]
    out = offset_polygon(poly, distance)
    return out[::-1] if flipped else out


def compensate_void(d: str, kerf: float) -> str:
    """Every closed sub-path of `d` is a hole: draw it kerf/2 smaller on each side."""
    if kerf == 0:
        return d
    return _path([_offset(sub, -kerf / 2) for sub in parse_path(d, CURVE_SAMPLES)])


def compensate_part(d: str, kerf: float) -> str:
    """The first sub-path is a part's outline (draw it kerf/2 larger), the others are holes in it (kerf/2 smaller)."""
    if kerf == 0:
        return d
    subs = parse_path(d, CURVE_SAMPLES)
    return _path([_offset(sub, kerf / 2 if i == 0 else -kerf / 2) for i, sub in enumerate(subs)])
