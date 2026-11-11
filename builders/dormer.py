"""
Dormer panels: a front face, two roof panels and (with side walls) two cheeks, from `dormer_geometry`.

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
* Side walls (cheeks), when the dormer has them:
  - face <-> cheek: corner fingers along the vertical edge; the face (full width) is female, notched t deep, and
    the cheek, standing behind it, is male, so the corner finishes flush;
  - cheek bottom -> main roof: the bottom lies on the roof, so its one tab goes in square to it, t deep, through a
    plain slot in the main roof panel;
  - cheek top -> dormer roof: the cheek stands flush with the roof panel's side edge, so its tab (t / cos(phi)
    tall, ending flush with the roof's top face at the outside) goes into a notch in that edge, t (cos(phi) +
    tan(phi)) deep - the tab's shadow through the sloped slab.
* Valley edges rest on the main roof and are glued; the footprint is scored on the roof panel.

Window: the front face gets a window opening (no frame), the largest rectangle centred on the face that keeps
WINDOW_MARGIN thicknesses of material to its base and sloped edges (and to the side notches of a walled face), cut as
panes like the house's windows; a face too small for a window of at least 2t keeps none.

Finger size: the dormer uses its own finger length, at most half its shortest joint edge (so small dormers still
get joints) and at least two material thicknesses. An edge too short for a regular finger (1.5 finger lengths) gets
one narrower tab instead, down to one thickness wide, keeping t/2 of material at its ends; only an edge too short
even for that is left plain (glued).
"""

import dataclasses
import math
from typing import Dict, List, Optional, Tuple

from ..components import AdditionalGable
from ..constants import COORDINATE_PRECISION
from ..cutouts import MIN_PANE_IN_THICKNESSES, pane_grid, paned_cutout
from ..exceptions import GeometryError
from ..geometry import Point, offset_polygon
from ..joints import FEMALE, MALE, FingerJointEngine, SlotSpec
from ..kerf import compensate_void
from ..panel import Panel, PATTERN_ROOF
from ..patterns import polygon_shingles_pattern

_P = COORDINATE_PRECISION
_SLOT_EDGE_MARGIN = 0.5      # in thicknesses: slot must keep this much material to the panel edge
MIN_FINGER_IN_THICKNESSES = 2.0
RAKE_TAB_MIN = 1.5           # in thicknesses: narrowest face tab into a dormer roof panel
SINGLE_TAB_MIN = 1.0         # in thicknesses: narrowest single tab where a regular finger does not fit
WINDOW_MARGIN = 1.0          # in thicknesses: material kept around the dormer window
WINDOW_SIDE_MARGIN = 2.0     # in thicknesses: from a walled face's notched sides (notches are t deep)


def _polygon(points) -> str:
    return "M " + " L ".join(f"{p.x:.{_P}f},{p.y:.{_P}f}" for p in points) + " Z"


def footprint_score(dormer: AdditionalGable) -> str:
    """Score line on the main roof panel marking where the dormer sits (a triangle, a pentagon with walls)."""
    x, y, _, _ = dormer.footprint()
    pts = [Point(x + px, y + py) for px, py in dormer.geometry.footprint_polygon()]
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
    e = g.eave_depth                                                    # the valley starts at (0, e)
    valley_u = max(0.0, (top - e) / (g.ridge - e)) * g.rafter           # it leans over as v grows
    lo = max(valley_u + margin, g.rafter - rake)
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


def _single_tab(engine: FingerJointEngine, length: float, t: float, lo: float = 0.0, hi: Optional[float] = None):
    """One tab centred on [lo, hi] of an edge (default: all of it), as wide as a finger but leaving t/2 at each end of
    that span - small dormers and cheeks are too short for a regular finger (1.5 finger lengths); None if that leaves
    less than SINGLE_TAB_MIN thicknesses."""
    hi = length if hi is None else hi
    width = min(engine.finger_length, hi - lo - t)
    if width < SINGLE_TAB_MIN * t:
        return None
    mid = (lo + hi) / 2
    return engine.spec(MALE, length, [(mid - width / 2, mid + width / 2)])


def _ridge_joint(dormer: AdditionalGable, engine: FingerJointEngine):
    """Male fingers for the left panel's ridge edge (it runs from the front to the apex Q); the right panel
    gets the mirrored female layout. A ridge too short for a regular finger gets a single narrower one."""
    hi = _ridge_span(dormer, engine.kerf)
    if hi <= 0:
        return None
    L = dormer.geometry.roof_panel_ridge_length
    return engine.plan_edge(L, MALE, span=(0.0, hi)) or _single_tab(engine, L, dormer.thickness, 0.0, hi)


def _cheek_lengths(dormer: AdditionalGable) -> Tuple[float, float, float]:
    """(front, top, bottom) edge lengths of a cheek."""
    g, t = dormer.geometry, dormer.thickness
    front = g.wall_height - dormer.face_lift
    return front, g.eave_depth - t, front / math.sin(math.radians(dormer.roof_angle))


def joint_engine(dormer: AdditionalGable, engine: FingerJointEngine) -> FingerJointEngine:
    """Engine with the dormer's finger length: at most half its shortest joint edge, at least 2t."""
    face_w, _, rake = dormer.geometry.face_triangle(dormer.face_lift)
    edges = [face_w - 2 * dormer.thickness, rake, _ridge_span(dormer, engine.kerf)]
    if dormer.geometry.walls:
        edges += _cheek_lengths(dormer)
    shortest = min(edges)
    f = max(min(engine.finger_length, shortest / 2), MIN_FINGER_IN_THICKNESSES * dormer.thickness)
    return engine.with_finger_length(f)


def base_tab_depth(dormer: AdditionalGable) -> float:
    """How far the base tab reaches below the face: the vertical thickness of the main roof."""
    return dormer.thickness / math.cos(math.radians(dormer.roof_angle))


def _base_joint(dormer: AdditionalGable, engine: FingerJointEngine):
    """One tab in the middle of the face's base edge (kept t clear of its ends): a regular finger, or a narrower
    single tab on a small face; None if even that does not fit."""
    face_w, _, _ = dormer.geometry.face_triangle(dormer.face_lift)
    t = dormer.thickness
    return engine.plan_edge(face_w, MALE, inset=t, count=1) or _single_tab(engine, face_w, t, t, face_w - t)


def cheek_top_depth(dormer: AdditionalGable) -> float:
    """How far a cheek's top tab reaches above the cheek: the roof slab's vertical thickness at the outer face."""
    return dormer.thickness / math.cos(math.radians(dormer.geometry.phi_deg))


def side_notch_depth(dormer: AdditionalGable) -> float:
    """Depth (across the roof panel, from its side edge) of the notch that takes a cheek's top tab: the tab's
    t-wide, t/cos(phi)-tall cross-section measured along the sloped slab."""
    ph = math.radians(dormer.geometry.phi_deg)
    return dormer.thickness * (math.cos(ph) + math.tan(ph))


def _cheek_joints(dormer: AdditionalGable, engine: FingerJointEngine):
    """Planned (nominal) specs of a cheek: {'front': corner fingers, 'top': tab, 'bottom': tab}; any may be None.
    The plans are the same for both cheeks (every layout is symmetric about the edge's middle)."""
    t = dormer.thickness
    front, top, bottom = _cheek_lengths(dormer)
    return {'front': engine.plan_edge(front, MALE) or _single_tab(engine, front, t),
            'top': _single_tab(engine, top, t),
            'bottom': _single_tab(engine, bottom, t)}


def roof_slots(dormer: AdditionalGable, index: int, engine: FingerJointEngine) -> List[SlotSpec]:
    """
    Slots in the main roof panel (its drawn coordinates, v down the slope) for the face's base tab and, with side
    walls, the cheeks' bottom tabs.

    The face stands with its front surface on the sill line (v = sill) and its rear surface t up-slope, where the
    roof's top meets the lifted base. Moving vertically down by h moves along the roof by h * sin(theta) in v,
    so the tab's cross-section (t wide horizontally, from the base down to t / cos(theta) below it) covers
    v in [sill - t / cos(theta), sill + t * sin(theta) * (1 - sin(theta)) / cos(theta)] through the roof.
    A void: drawn kerf/2 smaller on every side.

    A cheek's bottom edge lies on the roof from the face's rear (t / cos(theta) up-slope of the sill) back, so a
    tab d along it from the front sits d further up-slope; it is t wide across the slope (the cheek's thickness).
    """
    eng = joint_engine(dormer, engine)
    t, k = dormer.thickness, engine.kerf
    th = math.radians(dormer.roof_angle)
    s, c = math.sin(th), math.cos(th)
    x, y, _, depth = dormer.footprint()
    sill = y + depth
    out = []
    tab = _base_joint(dormer, eng)
    if tab is not None:
        u0 = x + dormer.geometry.face_offset(dormer.face_lift)          # the face's base starts here
        (a, b), = tab.nominal
        v0, v1 = sill - t / c, sill + t * s * (1 - s) / c
        out.append(SlotSpec(u0 + (a + b) / 2, (v0 + v1) / 2, (b - a) - k, (v1 - v0) - k, 'horizontal',
                            owner=f'additional_gable_front_{index}', owner_edge='base'))
    bottom = _cheek_joints(dormer, eng)['bottom'] if dormer.geometry.walls else None
    if bottom is not None:
        (a, b), = bottom.nominal                                        # laid out symmetrically: same from either end
        W = dormer.geometry.width
        for side, u in (('left', x + t / 2), ('right', x + W - t / 2)):
            out.append(SlotSpec(u, sill - t / c - (a + b) / 2, (b - a) - k, t - k, 'vertical',
                                owner=f'additional_gable_cheek_{side}_{index}', owner_edge='bottom'))
    return out


def face_window(dormer: AdditionalGable) -> Optional[Tuple[float, float, float, float]]:
    """
    (x, y, width, height) of the dormer's window in front-face coordinates (nominal, y up from the base), or None: the
    largest-area rectangle centred on the face, standing on the inset base, inside its outline inset by WINDOW_MARGIN
    thicknesses (with walls also WINDOW_SIDE_MARGIN from the notched sides), at least MIN_PANE_IN_THICKNESSES
    thicknesses each way - preferring the largest that still splits into a grid of panes (see `pane_grid`).
    """
    g, t = dormer.geometry, dormer.thickness
    outline = [Point(*q) for _, q in g.face_edges(dormer.face_lift)]
    try:
        inner = offset_polygon(outline, -WINDOW_MARGIN * t)
    except GeometryError:
        return None
    if len(inner) < 3 or sum(a.x * b.y - b.x * a.y for a, b in zip(inner, inner[1:] + inner[:1])) <= 0:
        return None                                          # the inset collapsed (or turned inside out)
    w = g.face_triangle(dormer.face_lift)[0]
    cx, bottom = w / 2, min(q.y for q in inner)
    half_max = (max(q.x for q in inner) - min(q.x for q in inner)) / 2
    if g.walls:
        half_max = min(half_max, w / 2 - WINDOW_SIDE_MARGIN * t)

    def top_at(x):
        """Highest point of the inset outline above x (it is convex)."""
        ys = []
        for a, b in zip(inner, inner[1:] + inner[:1]):
            if min(a.x, b.x) - 1e-9 <= x <= max(a.x, b.x) + 1e-9:
                ys.append(a.y if abs(b.x - a.x) < 1e-12 else a.y + (x - a.x) * (b.y - a.y) / (b.x - a.x))
        return max(ys) if ys else bottom

    best = {True: None, False: None}                         # largest with panes / as a single pane
    smallest = MIN_PANE_IN_THICKNESSES * t
    for i in range(1, 201):
        half = half_max * i / 200
        top = min(top_at(cx - half), top_at(cx + half)) - bottom
        # every height up to the top fits: try the tallest, and the tallest that still splits into rows of panes
        for height in {top, *(n * smallest + (n - 1) * t for n in (2, 3) if n * smallest + (n - 1) * t <= top)}:
            if 2 * half < smallest or height < smallest:
                continue
            paned = pane_grid(2 * half, height, t) != (1, 1)
            if best[paned] is None or 2 * half * height > best[paned][0]:
                best[paned] = (2 * half * height, half, height)
    chosen = best[True] or best[False]
    if chosen is None:
        return None
    _, half, height = chosen
    return (cx - half, bottom, 2 * half, height)


def _traced(engine: FingerJointEngine, nominal: List[Point], planned, depths: Dict[str, float], names: List[str]):
    """Kerf-compensated outline with the planned specs refitted, and special tab/notch depths applied."""
    corners, specs = engine.kerf_outline(nominal, planned)             # drawn kerf/2 outside the nominal outline
    specs = [dataclasses.replace(sp, depth=depths[n]) if sp and n in depths else sp for n, sp in zip(names, specs)]
    return corners, specs


def build_dormer_panels(dormer: AdditionalGable, index: int, engine: FingerJointEngine) -> List[Panel]:
    g, t = dormer.geometry, dormer.thickness
    engine = joint_engine(dormer, engine)
    slot = _tab_slot(dormer, engine)
    use_tabs = slot is not None
    cheek = _cheek_joints(dormer, engine) if g.walls else {}
    panels: List[Panel] = []

    # ---- front face: triangle (pentagon with walls) on the roof; tabs on both sloped edges (into the dormer roof
    # panels) and on the base (through the main roof); with walls, notches on both vertical sides for the cheeks
    edges = g.face_edges(dormer.face_lift)
    names = [n for n, _ in edges]
    nominal = [Point(*q) for _, q in edges]
    rakes = _rake_joints(dormer, engine, slot) if use_tabs else (None, None)
    corner = engine.mirrored(cheek['front'], FEMALE) if cheek.get('front') else None
    plan = {'base': _base_joint(dormer, engine), 'rake_right': rakes[0], 'rake_left': rakes[1],
            'side_right': corner, 'side_left': corner}
    corners, specs = _traced(engine, nominal, [plan[n] for n in names], {'base': base_tab_depth(dormer)}, names)
    window = face_window(dormer)
    holes = [] if window is None else [compensate_void(paned_cutout(*window, t), engine.kerf)]
    panels.append(Panel(
        name=f'additional_gable_front_{index}', label=f'Additional Gable Front {index + 1}',
        cut=[engine.trace_outline(corners, specs)] + holes, nominal_size=_extent(corners), corners=corners,
        edge_names=names, joints={n: sp for n, sp in zip(names, specs) if sp}))

    # ---- roof panels
    ridge = _ridge_joint(dormer, engine)
    top = cheek.get('top')
    e, o = g.eave_depth, g.overhang
    for side, mirrored in (('left', False), ('right', True)):
        edges = g.roof_panel_edges(mirrored, lap=t if ridge else 0.0)
        names = [n for n, _ in edges]
        nominal = [Point(*q) for _, q in edges]
        notch = None
        if top is not None:
            # the cheek top's tab sits at y in [t + a, t + b] (both cheeks: its plan is centred); the left panel's side
            # edge runs from the eave end (v = e) to the front, the right one's from the front (v = -o) back
            (a, b), = top.nominal
            length = e + o
            ys = (t + a, t + b)
            pos = (e - ys[1], e - ys[0]) if not mirrored else (ys[0] + o, ys[1] + o)
            notch = engine.spec(FEMALE, length, [pos])
        plan = {'ridge': (engine.mirrored(ridge, FEMALE) if mirrored else ridge) if ridge else None, 'side': notch}
        pts, specs = _traced(engine, nominal, [plan.get(n) for n in names], {'side': side_notch_depth(dormer)}, names)
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

    # ---- side walls
    if g.walls:
        for side in ('left', 'right'):
            edges = g.cheek_edges(side, t)
            names = [n for n, _ in edges]
            nominal = [Point(*q) for _, q in edges]
            corners, specs = _traced(engine, nominal, [cheek[n] for n in names], {'top': cheek_top_depth(dormer)}, names)
            panels.append(Panel(
                name=f'additional_gable_cheek_{side}_{index}', label=f'Additional Gable Wall {side.title()} {index + 1}',
                cut=[engine.trace_outline(corners, specs)], nominal_size=_extent(corners), corners=corners,
                edge_names=names, joints={n: sp for n, sp in zip(names, specs) if sp}))
    return panels
