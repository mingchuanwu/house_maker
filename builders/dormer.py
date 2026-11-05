"""
Dormer panels: a triangular front face and two roof panels, from `dormer_geometry`.

Joints
------
* Ridge: the left roof panel carries male fingers, the right one female (same convention as the
  main ridge); both ridge edges have the same length so the fingers mate. Edges shorter than 1.5
  finger lengths are left plain (glued).
* Front face <-> roof panels: each sloped edge of the face carries one tab that passes through a
  slot in the roof panel. The slot centre is `overhang + t/2` behind the roof panel's front edge
  (the face is `t` thick, standing at the front), centred along the rafter. Tabs and slots are only
  created when the sloped edge is long enough AND the slot lies inside the panel.
* Valley edges rest on the main roof and are glued; the footprint is scored on the roof panel.
"""

from typing import List, Optional, Tuple

from ..components import AdditionalGable
from ..constants import COORDINATE_PRECISION
from ..geometry import Point
from ..joints import FEMALE, MALE, FingerJointEngine, SlotSpec
from ..panel import Panel, PATTERN_ROOF
from ..patterns import polygon_shingles_pattern

_P = COORDINATE_PRECISION
_SLOT_EDGE_MARGIN = 0.5      # in thicknesses: slot must keep this much material to the panel edge


def _polygon(points) -> str:
    return "M " + " L ".join(f"{p.x:.{_P}f},{p.y:.{_P}f}" for p in points) + " Z"


def footprint_score(dormer: AdditionalGable) -> str:
    """Score triangle on the main roof panel marking where the dormer sits."""
    x, y, _, _ = dormer.footprint()
    pts = [Point(x + px, y + py) for px, py in dormer.geometry.footprint_triangle()]
    return _polygon(pts)


def _length(a: Point, b: Point) -> float:
    return ((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5


def _extent(corners) -> Tuple[float, float]:
    xs, ys = [p.x for p in corners], [p.y for p in corners]
    return (max(xs) - min(xs), max(ys) - min(ys))


def _tab_slot(dormer: AdditionalGable, engine: FingerJointEngine) -> Optional[SlotSpec]:
    """Slot (in left-panel coordinates) for the front-face tab, or None if tabs aren't used."""
    g = dormer.geometry
    _, _, rake = g.face_triangle(dormer.face_lift)
    if rake < 1.5 * engine.finger_length:
        return None
    # the face's tab is centred on its rake edge, which ends at the apex: measured from the eave that is
    # (rafter - rake / 2) along the roof panel
    slot = engine.make_slot(g.rafter - rake / 2, dormer.thickness / 2, 'horizontal')
    margin = _SLOT_EDGE_MARGIN * dormer.thickness
    # slot corners must be inside the panel: right of the valley line, above the front edge
    left, right = slot.cx - slot.length / 2, slot.cx + slot.length / 2
    bottom, top = slot.cy - slot.thickness / 2, slot.cy + slot.thickness / 2
    valley_u_at_top = (top / g.ridge) * g.rafter       # the valley edge leans over as v grows
    # toward the ridge the right panel carries female notches t deep: keep the slot clear of them
    if bottom < -g.overhang + margin or left < valley_u_at_top + margin or right > g.rafter - dormer.thickness - margin:
        return None
    return slot


def _ridge_joint(dormer: AdditionalGable, engine: FingerJointEngine):
    """
    Male fingers for the left panel's ridge edge (it runs from the front to the apex Q); the right panel
    gets the mirrored female layout. The roof panel tapers to a point at Q, so a notch (t deep) would cut
    through the valley edge there: fingers are confined to where the panel is at least 2t wide.
    """
    g, t = dormer.geometry, dormer.thickness
    length = g.roof_panel_ridge_length
    if g.rafter <= 2 * t:
        return None
    v_max = g.ridge * (1 - 2 * t / g.rafter)              # last ridge position with >= 2t of material
    hi = min(length, v_max + g.overhang - engine.kerf)
    return engine.plan_edge(length, MALE, span=(0.0, hi))


def build_dormer_panels(dormer: AdditionalGable, index: int, engine: FingerJointEngine) -> List[Panel]:
    g = dormer.geometry
    slot = _tab_slot(dormer, engine)
    use_tabs = slot is not None
    panels: List[Panel] = []

    # ---- front face: triangle on the roof, tabs on both sloped edges
    face_w, face_h, _ = g.face_triangle(dormer.face_lift)
    nominal = [Point(0, 0), Point(face_w, 0), Point(face_w / 2, face_h)]
    names = ['base', 'rake_right', 'rake_left']
    planned = [engine.plan_edge(_length(nominal[i], nominal[(i + 1) % 3]), MALE, count=1)
               if use_tabs and names[i] != 'base' else None for i in range(3)]
    corners, specs = engine.kerf_outline(nominal, planned)             # drawn kerf/2 outside the nominal outline
    panels.append(Panel(
        name=f'additional_gable_front_{index}', label=f'Additional Gable Front {index + 1}',
        cut=[engine.trace_outline(corners, specs)], nominal_size=_extent(corners), corners=corners,
        edge_names=names, joints={n: sp for n, sp in zip(names, specs) if sp}))

    # ---- roof panels
    ridge = _ridge_joint(dormer, engine)
    for side, mirrored in (('left', False), ('right', True)):
        edges = g.roof_panel_edges(mirrored)
        names = [n for n, _ in edges]
        nominal = [Point(*p) for _, p in edges]
        planned = [(engine.mirrored(ridge, FEMALE) if mirrored else ridge) if (n == 'ridge' and ridge) else None
                   for n in names]
        pts, specs = engine.kerf_outline(nominal, planned)
        # the slot is planned in the left panel's coordinates (u from the eave); the right panel measures u from
        # the ridge, so its slot is the mirror image
        slots = [] if slot is None else [slot if not mirrored else engine.make_slot(
            g.rafter - slot.cx, slot.cy, slot.orientation)]
        cut = [engine.trace_outline(pts, specs)] + [engine.slot_path(sl) for sl in slots]
        panels.append(Panel(
            name=f'additional_gable_roof_{side}_{index}',
            label=f'Additional Gable Roof {side.title()} {index + 1}',
            cut=cut, pattern=polygon_shingles_pattern(nominal), pattern_class=PATTERN_ROOF,
            nominal_size=_extent(pts), corners=pts, edge_names=names,
            joints={n: sp for n, sp in zip(names, specs) if sp}, slots=slots))
    return panels
