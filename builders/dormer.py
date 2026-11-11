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

Window: the front face gets a slim double-hung window (opening + panes, no frame), sized to the face and kept clear of
its edges and notches; see `face_window`. A face too small for one keeps none.

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
from ..cutouts import paned_cutout
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
DORMER_WINDOW_WIDTH = 0.65   # of the face's width: a slim double-hung window ... (model dormers: ~2/3)
DORMER_WINDOW_ASPECT = 2.0   # ... this many times as tall as wide (model dormer and 6-over-6 windows: ~2:1)
DORMER_GRIDS = ((2, 3), (2, 2), (1, 2), (1, 1))   # (columns, rows), the first whose panes fit
DORMER_BAR = 0.5             # in thicknesses: glazing bars (finer than the house's: dormer windows are small)


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
    edges = [rake, _ridge_span(dormer, engine.kerf)] + ([] if dormer.cross else [face_w - 2 * dormer.thickness])
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


def face_window(dormer: AdditionalGable):
    """
    The dormer's window in front-face coordinates (nominal, y up from the base): (x, y, width, height, grid, bar), or
    None. A slim double-hung window: DORMER_WINDOW_WIDTH of the face wide (at most), DORMER_WINDOW_ASPECT times as
    tall as wide, centred; on a walled face its top sits on the eave line (where the slopes start) if it can, otherwise
    it stands as low as the margins allow. It keeps WINDOW_MARGIN thicknesses of material to the base and the sloped
    edges and WINDOW_SIDE_MARGIN to a walled face's notched sides, shrinking (same proportions) until it does. Panes:
    the first of DORMER_GRIDS whose panes are at least one thickness, with bars DORMER_BAR thicknesses wide.
    """
    g, t = dormer.geometry, dormer.thickness
    outline = [Point(*q) for _, q in g.face_edges(dormer.face_lift)]
    try:
        inner = offset_polygon(outline, -WINDOW_MARGIN * t)
    except GeometryError:
        return None
    ring = list(zip(inner, inner[1:] + inner[:1]))
    if len(inner) < 3 or sum(a.x * b.y - b.x * a.y for a, b in ring) <= 0:
        return None                                          # the inset collapsed (or turned inside out)
    inside = lambda x, y: all((b.x - a.x) * (y - a.y) - (b.y - a.y) * (x - a.x) >= -1e-9 for a, b in ring)
    face_w = g.face_triangle(dormer.face_lift)[0]
    cx, base = face_w / 2, min(q.y for q in inner)
    eave = g.wall_height - dormer.face_lift if g.walls else None
    side = face_w / 2 - WINDOW_SIDE_MARGIN * t if g.walls else math.inf
    bar = DORMER_BAR * t

    def place(width):
        height = DORMER_WINDOW_ASPECT * width
        bottom = max(base, eave - height) if eave is not None else base
        x0, x1, y1 = cx - width / 2, cx + width / 2, bottom + height
        if width / 2 > side or not all(inside(x, y) for x in (x0, x1) for y in (bottom, y1)):
            return None
        return x0, bottom, width, height

    width = DORMER_WINDOW_WIDTH * face_w
    while width >= t:
        spot = place(width)
        if spot is not None:
            x, y, w, h = spot
            for cols, rows in DORMER_GRIDS:
                if (w - (cols - 1) * bar) / cols >= t and (h - (rows - 1) * bar) / rows >= t:
                    return x, y, w, h, (cols, rows), bar
            return None
        width *= 0.98
    return None


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
    holes = []
    if window is not None:
        x, y, w, h, grid, bar = window
        holes = [compensate_void(paned_cutout(x, y, w, h, bar, grid), engine.kerf)]
    panels.append(Panel(
        name=f'additional_gable_front_{index}', label=f'Additional Gable Front {index + 1}',
        cut=[engine.trace_outline(corners, specs)] + holes, nominal_size=_extent(corners), corners=corners,
        edge_names=names, joints={n: sp for n, sp in zip(names, specs) if sp}))

    panels += _roof_panels(dormer, engine, slot, cheek.get('top'), f'additional_gable_roof_{{side}}_{index}',
                           f'Additional Gable Roof {{side}} {index + 1}')

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


def _roof_panels(dormer: AdditionalGable, engine: FingerJointEngine, slot: Optional[SlotSpec], top,
                 name: str, label: str) -> List[Panel]:
    """The two roof panels of a dormer or cross gable: ridge fingers (the right panel lapping t past the ridge), the
    rake-tab slots, and with side walls the notches for the cheek tops. `name`/`label` take {side}."""
    g, t = dormer.geometry, dormer.thickness
    panels: List[Panel] = []
    ridge = _ridge_joint(dormer, engine)
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
            name=name.format(side=side), label=label.format(side=side.title()),
            cut=cut, pattern=polygon_shingles_pattern(nominal), pattern_class=PATTERN_ROOF,
            nominal_size=_extent(pts), corners=pts, edge_names=names,
            joints={n: sp for n, sp in zip(names, specs) if sp}, slots=slots))
    return panels


# ------------------------------------------------------------------------------------------------ cross gables
def build_cross_gable_panels(gable: AdditionalGable, index: int, engine: FingerJointEngine) -> List[Panel]:
    """The cross gable's two roof panels (its face is the side wall: see `cross_gable_wall`)."""
    engine = joint_engine(gable, engine)
    return _roof_panels(gable, engine, _tab_slot(gable, engine), None, f'cross_gable_roof_{{side}}_{index}',
                        f'Cross Gable Roof {{side}} {index + 1}')


def cross_gable_wall(gable: AdditionalGable, engine: FingerJointEngine, wall_top: float, kerf: float):
    """
    The side wall's rise into a cross gable, in the wall's DRAWN coordinates (nominal + kerf/2): (fragment, holes).
    `fragment` replaces the wall's straight top edge over the gable, traversed right to left like the top edge: up
    through the main roof (t / cos(theta), to its top surface at the wall's outer face), the two rakes with their tabs
    into the cross roof, and down again; drawn kerf/2 outside the nominal shape. `holes` is the window, as panes.
    `wall_top` is the wall's nominal top (the house's wall height).
    """
    eng = joint_engine(gable, engine)
    slot = _tab_slot(gable, eng)
    g, t, h = gable.geometry, gable.thickness, kerf / 2
    base = wall_top + t / math.cos(math.radians(gable.roof_angle))
    x0, W = gable.wall_x - h, g.width                        # nominal
    nominal = [Point(x0, wall_top), Point(x0 + W, wall_top), Point(x0 + W, base),
               Point(x0 + W / 2, base + g.gable_height), Point(x0, base)]
    rakes = _rake_joints(gable, eng, slot) if slot is not None else (None, None)
    corners, specs = eng.kerf_outline(nominal, [None, None, rakes[0], rakes[1], None])
    c = [Point(q.x + h, q.y + h) for q in corners]          # drawn coordinates
    top = wall_top + 2 * h                                   # the wall's drawn top edge
    start, end = Point(c[2].x, top), Point(c[4].x, top)
    fragment = " ".join([f"L {start.x:.{_P}f},{start.y:.{_P}f}", eng.trace_edge(start, c[2], None),
                         eng.trace_edge(c[2], c[3], specs[2]), eng.trace_edge(c[3], c[4], specs[3]),
                         eng.trace_edge(c[4], end, None)])
    holes = []
    window = face_window(gable)
    if window is not None:
        x, y, w, wh, grid, bar = window                      # face coordinates: from the gable's base, centred
        holes.append(compensate_void(paned_cutout(x0 + x + h, base + y + h, w, wh, bar, grid), kerf))
    return fragment, holes


def cross_gable_score(gable: AdditionalGable, notch_v: float, inset: float = 0.5) -> str:
    """Score line on the main roof for a cross gable: its two valleys, from just above the eave notch (at roof y
    `notch_v`; the sill itself lies in the notch) up to the ridge end - an open V, not the dormer's closed triangle."""
    x, y, _, _ = gable.footprint()
    (ax, ay), (bx, by), (qx, qy) = [(x + px, y + py) for px, py in gable.geometry.footprint_polygon()]
    cut = notch_v - inset
    on = lambda px, py: (qx + (px - qx) * (cut - qy) / (py - qy), cut)      # the valley at roof y = cut
    a, b = on(ax, ay), on(bx, by)
    return f"M {a[0]:.{_P}f},{a[1]:.{_P}f} L {qx:.{_P}f},{qy:.{_P}f} L {b[0]:.{_P}f},{b[1]:.{_P}f}"


def cross_gable_eave_notches(gables: List[AdditionalGable], roof_width: float, roof_height: float,
                             inner_v: float, engine: FingerJointEngine):
    """
    JointSpec for the main roof panel's eave edge (drawn from (roof_width, roof_height) to (0, roof_height)) with a
    notch under each cross gable: across its width, from the eave up to `inner_v` - where the side wall's inner face
    passes through the roof's top surface - so the wall can rise through it. None without cross gables. A void: drawn
    kerf/2 smaller on each side (FEMALE), so after cutting it is exactly the gable's width.
    """
    if not gables:
        return None
    k = engine.kerf
    fingers = sorted((roof_width - (gl.position.x + gl.position.width), roof_width - gl.position.x) for gl in gables)
    spec = engine.spec(FEMALE, roof_width, fingers)
    return dataclasses.replace(spec, depth=(roof_height - k / 2) - inner_v)
