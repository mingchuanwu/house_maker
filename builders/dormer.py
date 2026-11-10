"""
Dormer panels: a triangular front face and two roof panels, from `dormer_geometry`.

Joints
------
* Ridge: the left roof panel carries male fingers, the right one female; both ridge edges have the same
  length so the fingers mate. The two panels' undersides meet on the ridge line, so the left panel's end
  face rests against the right panel's underside; the right panel laps t beyond the ridge line (its notches
  are cut in that strip) to reach the outer corner, where the left panel's fingers arrive - as the main
  roof's female panel reaches t beyond the peak. Edges too short for a finger are left plain (glued).
* Front face <-> roof panels: each sloped edge of the face carries one tab that passes through a
  slot in the roof panel. The slot centre is `overhang + t/2` behind the roof panel's front edge
  (the face is `t` thick, standing at the front), centred along the rafter. Tabs and slots are only
  created when the sloped edge is long enough AND the slot lies inside the panel.
* Front face <-> main roof: the face's base edge carries one tab that goes straight down through a slot in the
  main roof panel. The tab is t / cos(theta) deep, so its bottom ends flush with the roof's underside along the
  face's rear surface; because it passes through the sloped roof at an angle, the slot is longer than t along the
  slope (see `roof_slots`).
* Valley edges rest on the main roof and are glued; the footprint is scored on the roof panel.

Finger size: the dormer uses its own finger length, at most half its shortest joint edge (so small dormers still
get joints) and at least two material thicknesses; an edge too short for that is left plain (glued).
"""

import dataclasses
import math
from typing import List, Optional, Tuple

from ..components import AdditionalGable
from ..constants import COORDINATE_PRECISION
from ..geometry import Point
from ..joints import FEMALE, MALE, FingerJointEngine, SlotSpec
from ..panel import Panel, PATTERN_ROOF
from ..patterns import polygon_shingles_pattern

_P = COORDINATE_PRECISION
_SLOT_EDGE_MARGIN = 0.5      # in thicknesses: slot must keep this much material to the panel edge
MIN_FINGER_IN_THICKNESSES = 2.0
RAKE_TAB_MIN = 1.5           # in thicknesses: narrowest face tab into a dormer roof panel


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
    """
    Slot (in left-panel coordinates) for the front-face tab, or None if tabs aren't used.

    The tab is centred on the face's rake edge, which ends at the apex: measured from the eave that is
    (rafter - rake / 2) along the roof panel. The slot must stay right of the valley line and clear of the right
    panel's ridge notches (t deep); on a small dormer the centred tab does not fit between the two, so it moves
    towards the eave and narrows to the room there (but not below RAKE_TAB_MIN thicknesses).
    """
    g, t, k = dormer.geometry, dormer.thickness, engine.kerf
    _, _, rake = g.face_triangle(dormer.face_lift)
    margin = _SLOT_EDGE_MARGIN * t
    cy, thickness = t / 2, engine.slot_thickness
    bottom, top = cy - thickness / 2, cy + thickness / 2
    if bottom < -g.overhang + margin:
        return None
    lo = max((top / g.ridge) * g.rafter + margin, g.rafter - rake)      # the valley edge leans over as v grows
    hi = g.rafter - t - margin
    width = min(engine.finger_length, hi - lo + k)                      # nominal tab width (the slot is kerf less)
    if width < RAKE_TAB_MIN * t:
        return None
    cx = min(max(g.rafter - rake / 2, lo + (width - k) / 2), hi - (width - k) / 2)
    return SlotSpec(cx, cy, width - k, thickness, 'horizontal')


def _rake_joints(dormer: AdditionalGable, engine: FingerJointEngine, slot: SlotSpec):
    """Face tabs over the slot: (rake_right, rake_left) specs. rake_right runs from the base up to the apex,
    rake_left from the apex down; both tabs sit (rafter - slot.cx) from the apex."""
    _, _, rake = dormer.geometry.face_triangle(dormer.face_lift)
    d, half = dormer.geometry.rafter - slot.cx, (slot.length + engine.kerf) / 2
    return (engine.spec(MALE, rake, [(rake - d - half, rake - d + half)]),
            engine.spec(MALE, rake, [(d - half, d + half)]))


def _ridge_span(dormer: AdditionalGable, kerf: float) -> float:
    """
    Length of the ridge edge (from the front) that may carry fingers: the right panel tapers to a point at Q, so
    near Q there is no material behind a notch. The notches are cut in the lap strip, so their bottoms lie on the
    ridge line, R (1 - v / L) * L / valley (perpendicular) from the valley line at ridge position v; keeping t of
    material there ends the fingers at v = L - t * valley / R.
    """
    g, t = dormer.geometry, dormer.thickness
    v_max = g.ridge - t * g.valley / g.rafter
    if v_max <= 0:
        return 0.0
    return min(g.roof_panel_ridge_length, v_max + g.overhang - kerf)


def _ridge_joint(dormer: AdditionalGable, engine: FingerJointEngine):
    """Male fingers for the left panel's ridge edge (it runs from the front to the apex Q); the right panel
    gets the mirrored female layout."""
    hi = _ridge_span(dormer, engine.kerf)
    if hi <= 0:
        return None
    return engine.plan_edge(dormer.geometry.roof_panel_ridge_length, MALE, span=(0.0, hi))


def joint_engine(dormer: AdditionalGable, engine: FingerJointEngine) -> FingerJointEngine:
    """Engine with the dormer's finger length: at most half its shortest joint edge, at least 2t."""
    face_w, _, rake = dormer.geometry.face_triangle(dormer.face_lift)
    shortest = min(face_w - 2 * dormer.thickness, rake, _ridge_span(dormer, engine.kerf))
    f = max(min(engine.finger_length, shortest / 2), MIN_FINGER_IN_THICKNESSES * dormer.thickness)
    return engine.with_finger_length(f)


def base_tab_depth(dormer: AdditionalGable) -> float:
    """How far the base tab reaches below the face: the vertical thickness of the main roof."""
    return dormer.thickness / math.cos(math.radians(dormer.roof_angle))


def _base_joint(dormer: AdditionalGable, engine: FingerJointEngine):
    """One tab in the middle of the face's base edge (kept t clear of its ends), or None if it is too short."""
    face_w, _, _ = dormer.geometry.face_triangle(dormer.face_lift)
    return engine.plan_edge(face_w, MALE, inset=dormer.thickness, count=1)


def roof_slots(dormer: AdditionalGable, index: int, engine: FingerJointEngine) -> List[SlotSpec]:
    """
    Slot in the main roof panel (its drawn coordinates, v down the slope) for the face's base tab.

    The face stands with its front surface on the sill line (v = sill) and its rear surface t up-slope, where the
    roof's top meets the lifted base. Moving vertically down by h moves along the roof by h * sin(theta) in v,
    so the tab's cross-section (t wide horizontally, from the base down to t / cos(theta) below it) covers
    v in [sill - t / cos(theta), sill + t * sin(theta) * (1 - sin(theta)) / cos(theta)] through the roof.
    A void: drawn kerf/2 smaller on every side.
    """
    eng = joint_engine(dormer, engine)
    tab = _base_joint(dormer, eng)
    if tab is None:
        return []
    t, k = dormer.thickness, engine.kerf
    th = math.radians(dormer.roof_angle)
    s, c = math.sin(th), math.cos(th)
    x, y, _, depth = dormer.footprint()
    sill = y + depth
    u0 = x + dormer.face_lift / math.tan(math.radians(dormer.geometry.phi_deg))   # the face's base starts here
    (a, b), = tab.nominal
    v0, v1 = sill - t / c, sill + t * s * (1 - s) / c
    return [SlotSpec(u0 + (a + b) / 2, (v0 + v1) / 2, (b - a) - k, (v1 - v0) - k, 'horizontal',
                     owner=f'additional_gable_front_{index}')]


def build_dormer_panels(dormer: AdditionalGable, index: int, engine: FingerJointEngine) -> List[Panel]:
    g = dormer.geometry
    engine = joint_engine(dormer, engine)
    slot = _tab_slot(dormer, engine)
    use_tabs = slot is not None
    panels: List[Panel] = []

    # ---- front face: triangle on the roof, tabs on both sloped edges (into the dormer roof panels) and on the
    # base (through the main roof)
    face_w, face_h, _ = g.face_triangle(dormer.face_lift)
    nominal = [Point(0, 0), Point(face_w, 0), Point(face_w / 2, face_h)]
    names = ['base', 'rake_right', 'rake_left']
    rakes = _rake_joints(dormer, engine, slot) if use_tabs else (None, None)
    planned = [_base_joint(dormer, engine), rakes[0], rakes[1]]
    corners, specs = engine.kerf_outline(nominal, planned)             # drawn kerf/2 outside the nominal outline
    if specs[0]:
        specs[0] = dataclasses.replace(specs[0], depth=base_tab_depth(dormer))
    panels.append(Panel(
        name=f'additional_gable_front_{index}', label=f'Additional Gable Front {index + 1}',
        cut=[engine.trace_outline(corners, specs)], nominal_size=_extent(corners), corners=corners,
        edge_names=names, joints={n: sp for n, sp in zip(names, specs) if sp}))

    # ---- roof panels
    ridge = _ridge_joint(dormer, engine)
    for side, mirrored in (('left', False), ('right', True)):
        edges = g.roof_panel_edges(mirrored, lap=dormer.thickness if ridge else 0.0)
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
