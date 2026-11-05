"""
Chimney panels: four walls and a casing, generated from `Chimney`'s explicit geometry.

Side walls (left/right) are right trapezoids (plan width D, level top, base following the roof
slope) standing outside; front/back walls are rectangles between them.

Roof panel: the footprint is scored and a through-hole inset by one thickness on every side is cut,
so the walls rest on a lip instead of falling through.

Joints (same convention as the main box): the front and back walls carry male tabs on their two
vertical edges; each side wall has matching female notches on its two vertical end edges, cut as
deep as the wall thickness so the corners finish flush. Notch positions are matched in *height
above the roof*, because the side wall's base is slanted. The chimney uses its own finger length
(at most a third of its shortest wall) so even small chimneys get joints; if that would make
fingers narrower than two material thicknesses the walls are plain (glued) instead.
The casing is a flat frame lying on the roof, and the footprint is scored on the roof panel.
"""

from typing import Dict, List, Optional, Tuple

from ..components import Chimney
from ..constants import COORDINATE_PRECISION
from ..geometry import Point
from ..joints import FEMALE, MALE, FingerJointEngine, JointSpec
from ..panel import Panel, PATTERN_CHIMNEY
from ..patterns import chimney_brick_pattern

_P = COORDINATE_PRECISION
_ORIGIN = Point(0, 0)
MIN_FINGER_IN_THICKNESSES = 2.0


def _polygon(points) -> str:
    return "M " + " L ".join(f"{p.x:.{_P}f},{p.y:.{_P}f}" for p in points) + " Z"


def footprint_score(chimney: Chimney) -> str:
    """Score rectangle on the roof panel marking where the chimney's outer footprint sits."""
    x, y, w, d = chimney.footprint()
    return _polygon([Point(x, y), Point(x + w, y), Point(x + w, y + d), Point(x, y + d)])


def roof_cutout(chimney: Chimney, kerf: float = 0.0) -> str:
    """Through-cut in the roof panel: footprint inset by one thickness on every side (a lip remains
    for the chimney to rest on). A void: drawn kerf/2 smaller on each side, the laser opens it up again."""
    x, y, w, d = chimney.roof_cutout()
    h = kerf / 2
    return _polygon([Point(x + h, y + h), Point(x + w - h, y + h), Point(x + w - h, y + d - h), Point(x + h, y + d - h)])


def _extent(corners) -> Tuple[float, float]:
    xs, ys = [p.x for p in corners], [p.y for p in corners]
    return (max(xs) - min(xs), max(ys) - min(ys))


def wall_corners(chimney: Chimney, wall: str) -> List[Point]:
    """Counter-clockwise outline of a chimney wall (y up, base at y = 0 for rectangles)."""
    w, h = chimney.get_panel_dimensions()[wall]
    if wall in ('chimney_front', 'chimney_back'):
        return [Point(0, 0), Point(w, 0), Point(w, h), Point(0, h)]
    D, rise = chimney.plan_depth, chimney.rise
    tall = chimney.side_wall_heights()[0]
    if wall == 'chimney_left':     # downslope (tall) end on the left
        return [Point(0, 0), Point(D, rise), Point(D, tall), Point(0, tall)]
    return [Point(0, rise), Point(D, 0), Point(D, tall), Point(0, tall)]   # chimney_right: mirrored


def joint_engine(chimney: Chimney, engine: FingerJointEngine) -> Optional[FingerJointEngine]:
    """Engine with the chimney's finger length, or None if the walls are too small for fingers."""
    shortest = min(h for _, h in (chimney.get_panel_dimensions()[n] for n in ('chimney_front', 'chimney_back')))
    f = min(engine.finger_length, shortest / 3)
    if f < MIN_FINGER_IN_THICKNESSES * engine.thickness:
        return None
    return engine.with_finger_length(f)


def _edge_fingers(fingers, base_z: float, start_z: float, going_up: bool):
    """Fingers given as heights above their wall's base -> positions along a side-wall edge that
    starts at height `start_z` and runs up or down."""
    out = []
    for a, b in fingers:
        z0, z1 = base_z + a, base_z + b
        out.append((z0 - start_z, z1 - start_z) if going_up else (start_z - z1, start_z - z0))
    return out


def chimney_wall_joints(chimney: Chimney, engine: FingerJointEngine
                        ) -> Optional[Dict[str, Dict[str, JointSpec]]]:
    """
    Joint specs per wall: {'chimney_front': {'left':..., 'right':...}, 'chimney_back': {...},
    'chimney_left': {'front_end':..., 'back_end':...}, 'chimney_right': {...}}, or None for glued walls.
    """
    eng = joint_engine(chimney, engine)
    if eng is None:
        return None
    dims = chimney.get_panel_dimensions()
    tan_t = chimney.thickness * (chimney.rise / chimney.plan_depth)          # t * tan(theta)
    top = chimney.side_wall_heights()[0]                                     # level top height
    plans = {}
    for wall, base_z in (('chimney_front', tan_t), ('chimney_back', chimney.rise)):
        plans[wall] = (eng.plan_edge(dims[wall][1], MALE), base_z, dims[wall][1])
    out = {w: {'left': plans[w][0], 'right': plans[w][0]} for w in plans}

    front_fingers = plans['chimney_front'][0].nominal
    back_fingers = plans['chimney_back'][0].nominal
    for side in ('chimney_left', 'chimney_right'):
        # front end (down-slope, full height): left wall runs it top->bottom, right wall bottom->top
        front_up = side == 'chimney_right'
        front = eng.spec(FEMALE, top, _edge_fingers(front_fingers, tan_t, 0.0 if front_up else top, front_up))
        # back end (up-slope, height h): left wall runs it bottom->top, right wall top->bottom
        back_up = side == 'chimney_left'
        back = eng.spec(FEMALE, top - chimney.rise,
                        _edge_fingers(back_fingers, chimney.rise, chimney.rise if back_up else top, back_up))
        out[side] = {'front_end': front, 'back_end': back}
    return out


def build_chimney_panels(chimney: Chimney, index: int, engine: FingerJointEngine) -> List[Panel]:
    panels = []
    dims = chimney.get_panel_dimensions()
    joints = chimney_wall_joints(chimney, engine)
    eng = joint_engine(chimney, engine) or engine
    edge_names = {
        'chimney_front': ['bottom', 'right', 'top', 'left'],
        'chimney_back': ['bottom', 'right', 'top', 'left'],
        'chimney_left': ['base', 'back_end', 'top', 'front_end'],
        'chimney_right': ['base', 'front_end', 'top', 'back_end'],
    }
    for wall in ('chimney_front', 'chimney_back', 'chimney_left', 'chimney_right'):
        nominal = wall_corners(chimney, wall)
        names = edge_names[wall]
        wall_joints = (joints or {}).get(wall, {})
        # fingers were planned on the nominal edges; the outline is drawn kerf/2 outside the nominal one
        corners, specs = eng.kerf_outline(nominal, [wall_joints.get(n) for n in names])
        path = eng.trace_outline(corners, specs)
        w, h = dims[wall]
        panels.append(Panel(
            name=f'{wall}_{index}', label=f'{wall.replace("_", " ").title()} {index + 1}',
            cut=[path], pattern=chimney_brick_pattern(wall, _ORIGIN, w, h, nominal),
            pattern_class=PATTERN_CHIMNEY, nominal_size=_extent(corners), corners=corners,
            edge_names=names, joints={n: s for n, s in zip(names, specs) if s}))

    outer_w, outer_h = dims['chimney_casing']
    in_w, in_h = chimney.casing_opening()
    x0, y0 = (outer_w - in_w) / 2, (outer_h - in_h) / 2
    h = engine.kerf / 2                  # the frame grows by kerf/2 on every edge, its opening shrinks by the same
    outer = [Point(-h, -h), Point(outer_w + h, -h), Point(outer_w + h, outer_h + h), Point(-h, outer_h + h)]
    hole = [Point(x0 + h, y0 + h), Point(x0 + h, y0 + in_h - h), Point(x0 + in_w - h, y0 + in_h - h),
            Point(x0 + in_w - h, y0 + h)]
    panels.append(Panel(
        name=f'chimney_casing_{index}', label=f'Chimney Casing {index + 1}',
        cut=[_polygon(outer), _polygon(hole)], nominal_size=_extent(outer),
        corners=outer, edge_names=['bottom', 'right', 'top', 'left']))
    return panels
