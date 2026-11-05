"""
Minimal SVG path reader for the commands HouseMaker emits (absolute M, L, C, Q, Z).

Used to measure the *actual* cut extent of a panel (finger tabs protrude beyond the nominal
panel rectangle) and by tests to inspect generated output. Curves are flattened by sampling,
which is exact enough for bounding boxes and containment checks.
"""

import re
from typing import List, NamedTuple, Tuple

from .geometry import Point

_TOKEN = re.compile(r'([MLCQZ])|([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)')
_ARITY = {'M': 2, 'L': 2, 'C': 6, 'Q': 4}
_CURVE_SAMPLES = 12


class BBox(NamedTuple):
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    def inflated(self, margin: float) -> 'BBox':
        return BBox(self.min_x - margin, self.min_y - margin, self.max_x + margin, self.max_y + margin)

    def intersects(self, other: 'BBox') -> bool:
        return not (self.max_x <= other.min_x or other.max_x <= self.min_x or
                    self.max_y <= other.min_y or other.max_y <= self.min_y)


def _bezier(points: List[Point], samples: int = _CURVE_SAMPLES) -> List[Point]:
    """Sample a quadratic/cubic Bezier given [p0, c1, (c2,) p1]; p0 is excluded from the result."""
    out = []
    for i in range(1, samples + 1):
        t = i / samples
        pts = list(points)
        while len(pts) > 1:
            pts = [Point(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)
                   for a, b in zip(pts, pts[1:])]
        out.append(pts[0])
    return out


def parse_path(d: str, curve_samples: int = _CURVE_SAMPLES) -> List[List[Point]]:
    """Return one polyline per sub-path (closed sub-paths are *not* repeated at the end)."""
    subpaths: List[List[Point]] = []
    current: List[Point] = []
    cmd = None
    nums: List[float] = []

    def flush():
        nonlocal nums
        if cmd in _ARITY and len(nums) == _ARITY[cmd]:
            pts = [Point(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
            if cmd == 'M':
                if current:
                    subpaths.append(list(current))
                    current.clear()
                current.append(pts[0])
            elif cmd == 'L':
                current.append(pts[0])
            else:  # C / Q
                current.extend(_bezier([current[-1]] + pts, curve_samples))
            nums = []

    for m in _TOKEN.finditer(d):
        letter, number = m.groups()
        if letter:
            flush()
            nums = []
            cmd = letter
            if letter == 'Z' and current:
                subpaths.append(list(current))
                current.clear()
        else:
            nums.append(float(number))
            if cmd in _ARITY and len(nums) == _ARITY[cmd]:
                flush()
                if cmd == 'M':      # implicit lineto after moveto
                    cmd = 'L'
    if current:
        subpaths.append(list(current))
    return subpaths


def path_bbox(d: str) -> BBox:
    points = [p for sub in parse_path(d) for p in sub]
    if not points:
        raise ValueError("empty path")
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return BBox(min(xs), min(ys), max(xs), max(ys))


def union_bbox(boxes: List[BBox]) -> BBox:
    return BBox(min(b.min_x for b in boxes), min(b.min_y for b in boxes),
                max(b.max_x for b in boxes), max(b.max_y for b in boxes))
