"""
The assembled house as a 3D model: every panel extruded to its material thickness and placed by `placement3d`.

The model shows the NOMINAL geometry (what the finished house is meant to be), not the drawn laser paths: the
cut outlines carry kerf compensation, so each outline is brought back by kerf/2 (outline in, holes out) before it
is extruded. Decorative mullions inside a window opening (islands in a hole) are not modelled.
"""

from typing import Dict, List, Sequence, Tuple

from .config import ArchitecturalConfiguration
from .constants import HouseStyle
from .exceptions import GeometryError
from .formats3d import Part
from .geometry import HouseGeometry, Point, offset_polygon
from .kerf import CURVE_SAMPLES
from .mesh import extrude, signed_area
from .panel import Panel
from .placement3d import Frame, box_frames, casing_frame, chimney_frames, dormer_frames
from .svgpath import parse_path

Ring = List[Tuple[float, float]]

WOOD = (222, 184, 135)
ROOF = (150, 75, 60)
BRICK = (170, 85, 65)
TRIM = (240, 235, 225)


def part_color(name: str) -> Tuple[int, int, int]:
    if 'casing' in name:
        return TRIM
    if name.startswith('chimney'):
        return BRICK
    if name.startswith(('roof_panel', 'additional_gable_roof')):
        return ROOF
    return WOOD


def _dedupe(points: Sequence[Point]) -> List[Point]:
    out: List[Point] = []
    for p in points:
        if not out or abs(p.x - out[-1].x) > 1e-9 or abs(p.y - out[-1].y) > 1e-9:
            out.append(p)
    if len(out) > 1 and abs(out[0].x - out[-1].x) < 1e-9 and abs(out[0].y - out[-1].y) < 1e-9:
        out.pop()
    return out


def _inside(p: Tuple[float, float], ring: Ring) -> bool:
    x, y, inside = p[0], p[1], False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside


def _nominal(points: Sequence[Point], distance: float) -> Ring:
    """Counter-clockwise ring moved outward by `distance` (negative: inward)."""
    pts = _dedupe(points)
    if signed_area([(p.x, p.y) for p in pts]) < 0:
        pts.reverse()
    try:
        pts = offset_polygon(pts, distance)
    except GeometryError:                    # a feature thinner than the kerf: keep the drawn shape
        pass
    return [(p.x, p.y) for p in pts]


def panel_rings(panel: Panel, kerf: float) -> Tuple[Ring, List[Ring]]:
    """Nominal outline and holes of a panel, in its drawn coordinates (outline CCW, holes CCW)."""
    subpaths = [sub for d in panel.cut for sub in parse_path(d, CURVE_SAMPLES)]
    outer = _nominal(subpaths[0], -kerf / 2)
    holes = [_nominal(sub, kerf / 2) for sub in subpaths[1:]]
    holes = [h for i, h in enumerate(holes)
             if not any(j != i and all(_inside(p, other) for p in h) for j, other in enumerate(holes))]
    return outer, holes


def panel_solid(panel: Panel, frame: Frame, kerf: float) -> Part:
    outer, holes = panel_rings(panel, kerf)
    mesh = extrude(outer, holes, frame.thickness, frame.to_world)
    return Part(panel.name, mesh, part_color(panel.name))


def house_frames(geometry: HouseGeometry, config: ArchitecturalConfiguration,
                 panels: Dict[str, Panel]) -> Dict[str, Frame]:
    """Frame of every panel that exists in `panels`, keyed by panel name."""
    frames = box_frames(geometry)
    frames = {n: f for n, f in frames.items() if n in panels}
    theta = geometry.theta
    for i, c in enumerate(config.chimneys):
        p = c.position
        frames.update(chimney_frames(frames[p.panel], p.x, p.y, p.width, p.height, theta, i))
    for i, d in enumerate(config.additional_gables):
        p = d.position
        frames.update(dormer_frames(frames[p.panel], p.x, p.y, p.width, theta, d.geometry.phi_deg, i))
    for name in [n for n in frames if n in panels and n in box_frames(geometry)]:
        wall = frames[name]
        for kind, items in (('window', config.get_windows_for_panel(name)), ('door', config.get_doors_for_panel(name))):
            for i, comp in enumerate(items):
                tag = 'w' if kind == 'window' else 'd'
                cname = f'{name}_{tag}{i}_{kind}_casing'
                if cname in panels:
                    frames[cname] = casing_frame(wall, kind, comp.type, comp.position)
    return frames


def build_model(geometry: HouseGeometry, style: HouseStyle, config: ArchitecturalConfiguration,
                panels: Sequence[Panel]) -> List[Part]:
    """The solid parts of the assembled house, one per panel."""
    by_name = {p.name: p for p in panels}
    frames = house_frames(geometry, config, by_name)
    return [panel_solid(by_name[n], f, geometry.kerf) for n, f in frames.items()]
