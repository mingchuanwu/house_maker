"""
Chimney in 3D: the four walls and the casing, placed on the roof by the independent model in
tests/assembly3d.py, must assemble without interpenetration; the corner tabs must sit flush in the
side-wall notches; the top must be level; the side walls must rest on the roof; the front and back
walls must leave exactly the documented wedge gap under their down-slope faces.
"""

import math

import numpy as np
import pytest

from ..assembly3d import PanelSolid, box_frames, chimney_frames
from ..conftest import make_house
from .test_assembly_3d import STEP, tab_points, tol_depth

SCENES = [
    # theta, roof panel, interior width W, plan depth D, exposure h, kerf
    (30, 'roof_panel_left', 10, 12, 30, 0.0),
    (35, 'roof_panel_left', 10, 12, 30, 0.1),
    (45, 'roof_panel_right', 14, 20, 24, 0.1),
    (60, 'roof_panel_left', 12, 16, 40, 0.2),
    (60, 'roof_panel_right', 20, 25, 30, 0.1),
]
T = 3.0
POS = (40.0, 60.0)          # footprint position on the roof panel (drawn coordinates)


def sid(s):
    return f"a{s[0]}-{s[1].replace('roof_panel_', '')}-W{s[2]}D{s[3]}h{s[4]}-k{s[5]}"


@pytest.fixture(params=SCENES, ids=sid, scope='module')
def scene(request):
    theta, panel, W, D, h, k = request.param
    house = make_house(length=200, width=140, height=90, gable_angle=theta, material_thickness=T, kerf=k,
                       chimneys=[(panel, POS[0], POS[1], W, D, h)])
    panels = {p.name: p for p in house.build_panels()}
    frames = box_frames(200, 140, 90, theta, T, k)
    roof = frames[panel]
    cf = chimney_frames(roof, POS[0], POS[1], W, D, theta, T, k)
    solids = {n: PanelSolid(panels[n], cf[n]) for n in cf}
    solids[panel] = PanelSolid(panels[panel], roof)
    samples = {n: s.sample(step=STEP) for n, s in solids.items()}
    return dict(theta=theta, panel=panel, W=W, D=D, h=h, k=k, panels=panels, frames=cf, roof=roof,
                solids=solids, samples=samples)


def test_chimney_parts_do_not_interpenetrate_each_other_or_the_roof(scene):
    s = scene
    names = list(s['solids'])
    for a in names:
        for b in names:
            if a == b:
                continue
            d = s['solids'][b].depth(s['samples'][a][0])
            d = d[~np.isnan(d)]
            if len(d):
                assert d.max() <= tol_depth(s['k']), f"{a} penetrates {b} by {d.max():.3f} mm"


def test_corner_tabs_sit_flush_in_the_side_wall_notches(scene):
    s = scene
    k = s['k']
    for wall in ('chimney_front_0', 'chimney_back_0'):
        pts, _ = s['samples'][wall]
        tabs = tab_points(s['panels'][wall], s['solids'][wall], pts)
        assert len(tabs), wall
        reached = {}
        left = np.zeros(len(tabs), dtype=bool)
        for side in ('chimney_left_0', 'chimney_right_0'):
            fr = s['frames'][side]
            u, v, w = fr.to_local(tabs)
            corners = np.array([(c.x, c.y) for c in s['panels'][side].corners])
            x1, y1 = corners[:, 0][None, :], corners[:, 1][None, :]
            x2, y2 = np.roll(corners[:, 0], -1)[None, :], np.roll(corners[:, 1], -1)[None, :]
            cross = ((y1 > v[:, None]) != (y2 > v[:, None])) & (
                u[:, None] < (x2 - x1) * (v[:, None] - y1) / np.where(y2 == y1, 1, y2 - y1) + x1)
            engaged = (w > -(k + 0.05)) & (w < T + k + 0.05) & (cross.sum(axis=1) % 2 == 1)
            left |= engaged
            if engaged.any():
                reached[side] = w[engaged].max()
        assert left.all(), f"{wall}: {(~left).sum()} tab samples are not inside a side wall"
        assert len(reached) == 2 and all(r >= T - (STEP / 2 + k + 0.05) for r in reached.values()), (wall, reached)


def test_chimney_top_is_level_and_the_exposure_is_as_requested(scene):
    s = scene
    k, tol = s['k'], STEP / 2 + s['k'] + 0.05
    tops = {n: s['samples'][n][0][:, 2].max() for n in s['solids'] if n.startswith('chimney') and 'casing' not in n}
    assert len(tops) == 4
    assert max(tops.values()) - min(tops.values()) <= tol, tops        # all four walls end at the same height
    roof = s['roof']
    # roof top surface height at the up-slope (back) face; the chimney stands h above it
    down = np.array([roof.ev[0], roof.ev[1], 0.0]); down /= np.linalg.norm(down)
    th = math.radians(s['theta'])
    l = s['D'] / math.cos(th)
    back = roof.to_world(np.array([POS[0] + T]), np.array([POS[1]]), np.array([T]))[0]
    assert np.mean(list(tops.values())) == pytest.approx(back[2] + s['h'], abs=tol)


def _roof_gap(s, points):
    """Distance of world points above the roof's top surface (negative = below it)."""
    roof = s['roof']
    origin = roof.to_world(np.array([0.0]), np.array([0.0]), np.array([T]))[0]
    return (points - origin) @ roof.n


def test_side_walls_rest_exactly_on_the_roof(scene):
    s = scene
    for side in ('chimney_left_0', 'chimney_right_0'):
        panel, fr = s['panels'][side], s['frames'][side]
        c0, c1 = panel.corners[0], panel.corners[1]                    # the slanted base edge
        us = np.linspace(c0.x, c1.x, 25)
        vs = np.linspace(c0.y, c1.y, 25)
        for w in (0.0, T / 2, T):
            pts = fr.to_world(us, vs, np.full(25, w))
            gap = _roof_gap(s, pts)
            assert np.abs(gap).max() <= s['k'] + 0.05, f"{side}: base is {gap.min():.3f}..{gap.max():.3f} from the roof"


def test_front_and_back_walls_never_dig_into_the_roof_and_leave_the_documented_wedge(scene):
    s = scene
    wedge = T * math.sin(math.radians(s['theta']))                     # t*tan(theta) vertical = t*sin(theta) normal
    tol = s['k'] + 0.05
    for wall in ('chimney_front_0', 'chimney_back_0'):
        panel, fr = s['panels'][wall], s['frames'][wall]
        us = np.linspace(0, panel.nominal_size[0], 15)
        gaps = []
        for w in (0.0, T):                                              # the two faces of the wall
            pts = fr.to_world(us, np.zeros_like(us), np.full(15, w))
            g = _roof_gap(s, pts)
            assert g.min() >= -tol, f"{wall} digs {g.min():.3f} mm into the roof"
            gaps.append(float(np.mean(g)))
        gaps.sort()
        assert gaps[0] == pytest.approx(0.0, abs=tol)                   # the up-slope face touches the roof
        assert gaps[1] == pytest.approx(wedge, abs=tol)                 # the down-slope face is lifted by the wedge


def test_casing_lies_on_the_roof_around_the_chimney(scene):
    s = scene
    pts, _ = s['samples']['chimney_casing_0']
    gap = _roof_gap(s, pts)
    # samples sit at 1/6, 1/2, 5/6 of the thickness: the slab starts on the roof surface and is t thick
    assert gap.min() == pytest.approx(T / 6, abs=0.05 + s['k'])
    assert gap.max() == pytest.approx(5 * T / 6, abs=0.05 + s['k'])
    # clear of the chimney walls: the opening is larger than the footprint
    for wall in ('chimney_front_0', 'chimney_back_0', 'chimney_left_0', 'chimney_right_0'):
        d = s['solids'][wall].depth(pts)
        assert np.isnan(d).all(), f"casing touches {wall}"
