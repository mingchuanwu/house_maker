"""
Dormer in 3D (face + two roof panels on the main roof): built from the independent model, the parts must
assemble without penetration, the horizontal ridge must end exactly on the main roof, and the face tabs must
sit flush in the roof panels. Measured numerically; known limits are asserted as analytic bounds.
"""

import math

import numpy as np
import pytest

from ..assembly3d import PanelSolid, box_frames, dormer_frames, roof_point
from house_maker.dormer_geometry import DEFAULT_PITCH
from ..conftest import make_house
from .test_assembly_3d import STEP, tab_points, tol_depth

T = 3.0
SCENES = [
    # theta, phi (None = default pitch), roof panel, width, overhang, kerf, wall height (None = default rule)
    (45, None, 'roof_panel_left', 30, 3.0, 0.1, 0),
    (35, None, 'roof_panel_left', 30, 3.0, 0.1, 0),
    (60, None, 'roof_panel_right', 40, 3.0, 0.0, 0),        # steep roof, walls switched off
    (45, None, 'roof_panel_left', 70, 3.0, 0.1, 0),         # large: ridge fingers and face tabs/slots
    (35, None, 'roof_panel_right', 70, 3.0, 0.1, 0),
    (45, 30.0, 'roof_panel_left', 50, 0.0, 0.1, 0),
    # side walls (cheeks)
    (60, None, 'roof_panel_right', 30, 3.0, 0.1, None),     # steep roof: walls by default (as tall as the gable)
    (65, None, 'roof_panel_left', 40, 3.0, 0.1, None),
    (55, None, 'roof_panel_right', 50, 3.0, 0.0, 22.0),     # explicit, tall enough for a cheek top tab
    (35, None, 'roof_panel_left', 40, 3.0, 0.1, 15.0),      # walls on a shallow roof, on request
]
POS = (40.0, 20.0)


def sid(s):
    wall = 'auto' if s[6] is None else s[6]
    return f"a{s[0]}-phi{s[1] or 'default'}-{s[2].replace('roof_panel_', '')}-W{s[3]}-o{s[4]}-k{s[5]}-wall{wall}"


def expected_wall(theta, phi, W, wall):
    """The documented default: on roofs steeper than 45 degrees walls as tall as the gable (at the 45 degree default
    pitch), otherwise none; an explicit height wins."""
    if wall is not None:
        return wall
    return (W / 2) * math.tan(math.radians(phi or 45.0)) if theta > 45 else 0.0


WALL_SCENES = [sc for sc in SCENES if expected_wall(sc[0], sc[1], sc[3], sc[6])]
TALL_WALL_SCENES = [sc for sc in WALL_SCENES if expected_wall(sc[0], sc[1], sc[3], sc[6]) >= 20]


@pytest.fixture(params=SCENES, ids=sid, scope='module')
def scene(request):
    return _build_scene(request.param)


@pytest.fixture(params=WALL_SCENES, ids=sid, scope='module')
def walled(request):
    """The scenes whose dormer has side walls (cheeks)."""
    return _build_scene(request.param)


_SCENE_CACHE = {}


def _build_scene(params):
    if params not in _SCENE_CACHE:
        _SCENE_CACHE[params] = _make_scene(*params)
    return _SCENE_CACHE[params]


def _make_scene(theta, phi, panel, W, o, k, wall):
    house = make_house(length=220, width=170, height=90, gable_angle=theta, material_thickness=T, kerf=k)
    dormer = house.add_additional_gable(panel, POS[0], POS[1], W, roof_overhang=o, pitch=phi, wall_height=wall)
    panels = {p.name: p for p in house.build_panels()}
    frames = box_frames(220, 170, 90, theta, T, k)
    roof = frames[panel]
    wall = expected_wall(theta, phi, W, wall)
    phi = phi or DEFAULT_PITCH
    df, pts = dormer_frames(roof, POS[0], POS[1], W, theta, phi, T, k, wall=wall)
    solids = {n: PanelSolid(panels[n], df[n]) for n in df}
    solids[panel] = PanelSolid(panels[panel], roof)
    samples = {n: s.sample(step=STEP) for n, s in solids.items()}
    return dict(theta=theta, phi=phi, panel=panel, W=W, o=o, k=k, wall=wall, panels=panels, frames=df, roof=roof,
                solids=solids, samples=samples, pts=pts, dormer=dormer)


def _top_plane(roof):
    origin = roof.to_world(np.array([0.0]), np.array([0.0]), np.array([T]))[0]
    return origin, roof.n


def test_independent_ridge_ends_exactly_on_the_main_roof(scene):
    """The horizontal ridge at the apex height meets the roof at Q: Q lies on the main roof's top surface."""
    origin, n = _top_plane(scene['roof'])
    for name in ('A', 'B', 'Q') + (('Ea', 'Eb') if scene['wall'] else ()):
        assert abs((scene['pts'][name] - origin) @ n) < 1e-9, name
    assert scene['dormer'].geometry.wall_height == pytest.approx(scene['wall'])            # the default rule
    # and the library's footprint depth is the distance from the sill to Q along the roof surface
    assert scene['dormer'].position.height == pytest.approx(scene['pts']['l'], abs=5e-3)


def test_valley_edges_lie_on_the_main_roof_and_the_face_stands_on_it(scene):
    s, (origin, n) = scene, _top_plane(scene['roof'])
    k = s['k']
    for side in ('left', 'right'):
        panel = s['panels'][f"additional_gable_roof_{side}_0"]
        names = panel.edge_names
        i = names.index('valley')
        a, b = panel.corners[i], panel.corners[(i + 1) % len(panel.corners)]
        us, vs = np.linspace(a.x, b.x, 20), np.linspace(a.y, b.y, 20)
        # the valley lies on the plane's underside (slab spans w in [0, t] on the outer side, or [-t, 0]); one of the
        # two faces of the slab touches the main roof along the valley
        gaps = []
        for w in (0.0, T):
            pts = s['frames'][f"additional_gable_roof_{side}_0"].to_world(us, vs, np.full(20, w))
            gaps.append(np.abs((pts - origin) @ n).max())
        assert min(gaps) <= k + 0.05, f"{side} valley is {min(gaps):.3f} mm off the main roof"
    # face: its sill edge is on the roof at the front line, and lifted by the usual wedge at its rear face
    fr, face = s['frames']['additional_gable_front_0'], s['panels']['additional_gable_front_0']
    us = np.linspace(0, face.nominal_size[0], 15)
    wedge = T * math.sin(math.radians(s['theta']))
    gaps = sorted(float(np.mean((fr.to_world(us, np.zeros(15), np.full(15, w)) - origin) @ n)) for w in (0.0, T))
    assert gaps[0] == pytest.approx(0.0, abs=k + 0.05) and gaps[1] == pytest.approx(wedge, abs=k + 0.05)


def test_dormer_parts_do_not_interpenetrate(scene):
    s = scene
    names = list(s['solids'])
    ridge_pair = {'additional_gable_roof_left_0', 'additional_gable_roof_right_0'}
    for a in names:
        for b in names:
            if a == b:
                continue
            d = s['solids'][b].depth(s['samples'][a][0])
            d = d[~np.isnan(d)]
            if not len(d):
                continue
            limit = tol_depth(s['k'])
            if {a, b} == ridge_pair and s['phi'] < 45:               # same ridge limitation as the main roof
                limit += T * abs(math.cos(math.radians(2 * s['phi'])))
            assert d.max() <= limit, f"{a} penetrates {b} by {d.max():.3f} mm (limit {limit:.3f})"


def test_face_rake_tabs_sit_flush_in_the_roof_panels_when_there_are_tabs(scene):
    s = scene
    face = s['panels']['additional_gable_front_0']
    if not face.joints:
        pytest.skip('no tabs on this dormer')
    k = s['k']
    if 'rake_left' not in face.joints:
        pytest.skip('no rake tabs on this dormer')
    pts, _ = s['samples']['additional_gable_front_0']
    tabs = tab_points(face, s['solids']['additional_gable_front_0'], pts)
    tabs = tabs[s['frames']['additional_gable_front_0'].to_local(tabs)[1] > 0]     # the base tab goes into the main roof
    assert len(tabs)
    left = np.zeros(len(tabs), dtype=bool)
    for side in ('left', 'right'):
        name = f'additional_gable_roof_{side}_0'
        fr = s['frames'][name]
        u, v, w = fr.to_local(tabs)
        corners = np.array([(c.x, c.y) for c in s['panels'][name].corners])
        x1, y1 = corners[:, 0][None, :], corners[:, 1][None, :]
        x2, y2 = np.roll(corners[:, 0], -1)[None, :], np.roll(corners[:, 1], -1)[None, :]
        cross = ((y1 > v[:, None]) != (y2 > v[:, None])) & (
            u[:, None] < (x2 - x1) * (v[:, None] - y1) / np.where(y2 == y1, 1, y2 - y1) + x1)
        engaged = (w > -(k + 0.05)) & (w < T + k + 0.05) & (cross.sum(axis=1) % 2 == 1)
        left |= engaged
        assert engaged.any(), f"no tab reaches the {side} roof panel"
        assert w[engaged].max() >= T - (STEP / 2 + k + 0.05), f"{side}: tab is short"
    assert left.all(), f"{(~left).sum()} tab samples are not inside a roof panel"


def test_face_base_tab_goes_through_the_main_roof(scene):
    """The base tab runs from the lifted base (t * sin(theta) above the roof at the face's front, normal to the roof)
    down through the main roof - its slot keeps it from penetrating, see above - and its bottom reaches the roof's
    underside along the face's rear surface (within a sampling step)."""
    s = scene
    face = s['panels']['additional_gable_front_0']
    if 'base' not in face.joints:
        pytest.skip('face too narrow for a base tab')
    k = s['k']
    pts, _ = s['samples']['additional_gable_front_0']
    tabs = tab_points(face, s['solids']['additional_gable_front_0'], pts)
    tabs = tabs[s['frames']['additional_gable_front_0'].to_local(tabs)[1] < 0]
    assert len(tabs)
    _, _, w = s['roof'].to_local(tabs)
    wedge = T * math.sin(math.radians(s['theta']))
    assert w.min() >= -(k + 0.05) and w.max() <= T + wedge + k + 0.05, "base tab pokes out of the roof"
    # exact: the tab's bottom edge along the face's rear surface lies on the roof's underside
    (a, b), = face.joints['base'].nominal
    fr = s['frames']['additional_gable_front_0']
    bottom = fr.to_world(np.array([a, b]), np.full(2, -face.joints['base'].depth), np.full(2, T))
    under = s['roof'].to_local(bottom)[2]
    assert np.abs(under).max() <= k + 1e-6, f"base tab bottom is {under} mm off the roof's underside"


def test_ridge_fingers_land_in_the_right_panels_lap(scene):
    """The left panel's ridge fingers stick out t past its end face, which rests on the right panel's underside;
    they must land inside the right panel - in the notches of its lap strip beyond the ridge line - not beside it.
    Exact for a square ridge (90 degree apex, pitch 45); other pitches have the main ridge's limitation (a square
    cut cannot follow a different angle): the fingers stand off by at most t * |cos(2 * pitch)|."""
    s = scene
    left = s['panels']['additional_gable_roof_left_0']
    if not left.joints.get('ridge'):
        pytest.skip('no ridge fingers on this dormer')
    k = s['k']
    pts, _ = s['samples']['additional_gable_roof_left_0']
    fingers = tab_points(left, s['solids']['additional_gable_roof_left_0'], pts)
    assert len(fingers)
    right = s['panels']['additional_gable_roof_right_0']
    u, v, w = s['frames']['additional_gable_roof_right_0'].to_local(fingers)
    us = [c.x for c in right.corners]
    tol = k + 0.05 + T * abs(math.cos(math.radians(2 * s['phi'])))
    assert u.min() >= min(us) - tol, f"fingers reach {min(us) - u.min():.3f} mm past the right panel's lap"
    assert u.max() <= 0 + tol, f"fingers reach {u.max():.3f} mm past the lap's notch bottoms"
    assert w.min() >= -tol and w.max() <= T + tol, "fingers outside the right panel's thickness"
    if s['phi'] == 45:                     # square ridge: the fingers fill the lap (to within a sampling step)
        assert w.max() >= T - (STEP + k + 0.05) and u.min() <= min(us) + STEP + k + 0.05



# ------------------------------------------------------------------ side walls (cheeks)
def _into_roof(s, side, pts):
    """Depth of points into a dormer roof panel, measured from its underside (the plane through the eave line's end,
    which is w = 0 or w = t of the slab depending on which way its frame normal points)."""
    fr = s['frames'][f'additional_gable_roof_{side}_0']
    w = fr.to_local(pts)[2]
    under = fr.to_local(s['pts']['Ae' if side == 'left' else 'Be'][None, :])[2][0]
    return w - under if under < T / 2 else under - w


def _edge_points(panel, frame, edge, w, n=15):
    i = panel.edge_names.index(edge)
    a, b = panel.corners[i], panel.corners[(i + 1) % len(panel.corners)]
    return frame.to_world(np.linspace(a.x, b.x, n), np.linspace(a.y, b.y, n), np.full(n, w))


def test_cheek_bottoms_lie_on_the_main_roof(walled):
    s = walled
    origin, n = _top_plane(s['roof'])
    for side in ('left', 'right'):
        name = f'additional_gable_cheek_{side}_0'
        for w in (0.0, T):                     # both faces of the cheek: the roof is level across its thickness
            gap = (_edge_points(s['panels'][name], s['frames'][name], 'bottom', w) - origin) @ n
            assert np.abs(gap).max() <= s['k'] + 0.05, f"{side} cheek bottom is {np.abs(gap).max():.3f} mm off the roof"


def test_cheek_tops_carry_the_dormer_roof_on_their_outer_face(walled):
    """The roof panel's underside passes through the cheek top's outer edge; inside, it rises away (a wedge, hidden
    within the dormer) - so the cheek never digs into the roof."""
    s = walled
    k = s['k']
    for side in ('left', 'right'):
        name = f'additional_gable_cheek_{side}_0'
        gaps = [_into_roof(s, side, _edge_points(s['panels'][name], s['frames'][name], 'top', w)) for w in (0.0, T)]
        outer, inner = sorted(gaps, key=lambda g: np.abs(g).max())
        assert np.abs(outer).max() <= k + 0.05, f"{side}: cheek top is {np.abs(outer).max():.3f} mm off the roof"
        wedge = T * math.sin(math.radians(s['phi']))                 # t * tan(phi) vertically, measured normal to the roof
        assert (-inner).min() == pytest.approx(wedge, abs=k + 0.05)


def test_cheek_tabs_go_through_the_roofs_they_plug_into(walled):
    """Bottom tab: through the main roof, square to it, ending flush with its underside. Front fingers: inside the
    face's thickness. Top tab (if any): inside the dormer roof's thickness, flush with its top at the outer face."""
    s = walled
    k = s['k']
    tol = k + 0.05
    for side in ('left', 'right'):
        name = f'additional_gable_cheek_{side}_0'
        cheek, fr = s['panels'][name], s['frames'][name]
        assert 'bottom' in cheek.joints and 'front' in cheek.joints, f"{side} cheek has no bottom tab or corner fingers"
        pts, _ = s['samples'][name]
        tabs = tab_points(cheek, s['solids'][name], pts)
        # which edge a tab belongs to: by its (u, v) position against the nominal triangle
        u, v, _ = fr.to_local(tabs)
        top_v = max(c.y for c in cheek.corners)
        front_u = [c.x for c, nm in zip(cheek.corners, cheek.edge_names) if nm == 'front'][0]
        on_top = v > top_v
        on_front = ~on_top & (np.abs(u - front_u) < np.abs(u - front_u).min() + T + tol) & (
            (u - front_u) * (1 if side == 'left' else -1) > 0)
        on_bottom = ~on_top & ~on_front
        _, _, w = s['roof'].to_local(tabs[on_bottom])
        assert len(w) and w.min() >= -tol and w.max() <= T + tol, f"{side}: bottom tab leaves the main roof"
        face = s['frames']['additional_gable_front_0']
        _, _, wf = face.to_local(tabs[on_front])
        assert len(wf) and wf.min() >= -tol and wf.max() <= T + tol, f"{side}: corner fingers leave the face"
        if 'top' in cheek.joints:
            # from the cheek top (inside: across the hidden wedge) up through the roof, never out of its top
            d = _into_roof(s, side, tabs[on_top])
            wedge = T * math.sin(math.radians(s['phi']))
            assert len(d) and d.min() >= -wedge - tol and d.max() <= T + tol, f"{side}: top tab leaves the dormer roof"
            # exact: the tab's tip on the cheek's outer face (w = t) is flush with the roof's top face
            (a, b), = cheek.joints['top'].nominal
            i = cheek.edge_names.index('top')
            p0, p1 = cheek.corners[i], cheek.corners[(i + 1) % len(cheek.corners)]
            L = math.hypot(p1.x - p0.x, p1.y - p0.y)
            ux = (p1.x - p0.x) / L
            us = np.array([p0.x + ux * q for q in (a, b)])
            a_dir = (s['pts']['B'] - s['pts']['A']) / np.linalg.norm(s['pts']['B'] - s['pts']['A'])
            faces = [fr.to_world(us, np.full(2, p0.y + cheek.joints['top'].depth), np.full(2, w)) for w in (0.0, T)]
            outer = max(faces, key=lambda q: abs((q[0] - s['pts']['P']) @ a_dir))   # farther from the dormer's middle
            assert _into_roof(s, side, outer) == pytest.approx([T, T], abs=k + 0.1), f"{side}: top tab not flush on top"
        # exact: the bottom tab ends on the main roof's underside
        (a, b), = cheek.joints['bottom'].nominal
        i = cheek.edge_names.index('bottom')
        p0, p1 = cheek.corners[i], cheek.corners[(i + 1) % len(cheek.corners)]
        L = math.hypot(p1.x - p0.x, p1.y - p0.y)
        ux, uy = (p1.x - p0.x) / L, (p1.y - p0.y) / L
        nx, ny = uy, -ux                                                 # outward = right of travel
        d = cheek.joints['bottom'].depth
        us = np.array([p0.x + ux * q + nx * d for q in (a, b)])
        vs = np.array([p0.y + uy * q + ny * d for q in (a, b)])
        tip = s['roof'].to_local(fr.to_world(us, vs, np.full(2, T / 2)))[2]
        assert np.abs(tip).max() <= k + 0.15, f"{side}: bottom tab tip is {tip} mm off the roof's underside"


@pytest.mark.parametrize('params', TALL_WALL_SCENES, ids=sid)
def test_tall_walls_get_a_cheek_top_tab(params):
    s = _build_scene(params)
    for side in ('left', 'right'):
        assert 'top' in s['panels'][f'additional_gable_cheek_{side}_0'].joints
        assert 'side' in s['panels'][f'additional_gable_roof_{side}_0'].joints


def test_the_scene_lists_cover_both_kinds_of_dormer():
    assert len(WALL_SCENES) >= 3 and TALL_WALL_SCENES and len(SCENES) - len(WALL_SCENES) >= 3
