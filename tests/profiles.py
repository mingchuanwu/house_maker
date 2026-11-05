"""Extract finger profiles from a Panel's actual outline path (not from its plan)."""

from dataclasses import dataclass
from typing import List

from house_maker.geometry import Point
from house_maker.svgpath import parse_path

EPS = 0.01      # path coordinates are rounded to 0.001mm


@dataclass(frozen=True)
class Finger:
    start: float      # along the edge from its start corner
    end: float
    depth: float      # >0 protrudes outward (male), <0 notched inward (female)


def _near(a: Point, b: Point, tol=2e-3) -> bool:
    return abs(a.x - b.x) <= tol and abs(a.y - b.y) <= tol


def edge_profile(panel, edge: str) -> List[Finger]:
    """Fingers on one nominal edge, measured from the outline path (counter-clockwise outline)."""
    outline = parse_path(panel.cut[0])[0]
    corners = panel.corners
    i = panel.edge_names.index(edge)
    a, b = corners[i], corners[(i + 1) % len(corners)]
    # indices of the corner vertices in the outline polyline
    idx = [next(k for k, p in enumerate(outline) if _near(p, c)) for c in corners]
    lo, hi = idx[i], idx[(i + 1) % len(corners)]
    pts = outline[lo:hi + 1] if hi > lo else outline[lo:] + outline[:hi + 1]
    length = ((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5
    ux, uy = (b.x - a.x) / length, (b.y - a.y) / length
    prof = [((p.x - a.x) * ux + (p.y - a.y) * uy, (p.x - a.x) * uy - (p.y - a.y) * ux) for p in pts]
    fingers, run = [], []
    for s, d in prof:
        if abs(d) > EPS:
            run.append((s, d))
        elif run:
            fingers.append(Finger(min(r[0] for r in run), max(r[0] for r in run),
                                  max(run, key=lambda r: abs(r[1]))[1]))
            run = []
    return fingers


def physical(f: Finger, kerf: float) -> Finger:
    """The finger the cut part actually has. The laser removes kerf/2 either side of every drawn line,
    so a drawn tab (depth > 0) is `kerf` narrower than drawn and a drawn notch `kerf` wider; depths
    are unchanged (the edge they are measured from moves by the same kerf/2)."""
    h = kerf / 2
    return Finger(f.start + h, f.end - h, f.depth) if f.depth > 0 else Finger(f.start - h, f.end + h, f.depth)


def edge_length(panel, edge: str) -> float:
    i = panel.edge_names.index(edge)
    a, b = panel.corners[i], panel.corners[(i + 1) % len(panel.corners)]
    return ((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5


def mirrored(fingers: List[Finger], length: float) -> List[Finger]:
    """The same edge seen from the mating panel (travelling the other way)."""
    return sorted((Finger(length - f.end, length - f.start, f.depth) for f in fingers),
                  key=lambda f: f.start)
