"""
Dormer in 3D (face + two roof panels on the main roof): built from the independent model, the parts must
assemble without penetration, the horizontal ridge must end exactly on the main roof, and the face tabs must
sit flush in the roof panels. Measured numerically; known limits are asserted as analytic bounds.
"""

import math

import numpy as np
import pytest

from ..assembly3d import PanelSolid, box_frames, dormer_frames, roof_point
from ..conftest import make_house
from .test_assembly_3d import STEP, tab_points, tol_depth

T = 3.0
SCENES = [
    # theta, phi (None = match), roof panel, width, overhang, kerf
    (45, None, 'roof_panel_left', 30, 3.0, 0.1),
    (35, None, 'roof_panel_left', 30, 3.0, 0.1),
    (60, None, 'roof_panel_right', 40, 3.0, 0.0),
    (45, None, 'roof_panel_left', 70, 3.0, 0.1),         # large: ridge fingers and face tabs/slots
    (35, None, 'roof_panel_right', 70, 3.0, 0.1),
    (45, 30.0, 'roof_panel_left', 50, 0.0, 0.1),
]
POS = (40.0, 20.0)


def sid(s):
    return f"a{s[0]}-phi{s[1] or 'match'}-{s[2].replace('roof_panel_', '')}-W{s[3]}-o{s[4]}-k{s[5]}"


@pytest.fixture(params=SCENES, ids=sid, scope='module')
def scene(request):
    theta, phi, panel, W, o, k = request.param
    house = make_house(length=220, width=170, height=90, gable_angle=theta, material_thickness=T, kerf=k)
    dormer = house.add_additional_gable(panel, POS[0], POS[1], W, roof_overhang=o, pitch=phi)
    panels = {p.name: p for p in house.build_panels()}
    frames = box_frames(220, 170, 90, theta, T, k)
    roof = frames[panel]
    df, pts = dormer_frames(roof, POS[0], POS[1], W, theta, phi or theta, T, k)
    solids = {n: PanelSolid(panels[n], df[n]) for n in df}
    solids[panel] = PanelSolid(panels[panel], roof)
    samples = {n: s.sample(step=STEP) for n, s in solids.items()}
    return dict(theta=theta, phi=phi or theta, panel=panel, W=W, o=o, k=k, panels=panels, frames=df, roof=roof,
                solids=solids, samples=samples, pts=pts, dormer=dormer)


def _top_plane(roof):
    origin = roof.to_world(np.array([0.0]), np.array([0.0]), np.array([T]))[0]
    return origin, roof.n


def test_independent_ridge_ends_exactly_on_the_main_roof(scene):
    """The horizontal ridge at the apex height meets the roof at Q: Q lies on the main roof's top surface."""
    origin, n = _top_plane(scene['roof'])
    for name in ('A', 'B', 'Q'):
        assert abs((scene['pts'][name] - origin) @ n) < 1e-9, name
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


def test_face_tabs_sit_flush_in_the_roof_panels_when_there_are_tabs(scene):
    s = scene
    face = s['panels']['additional_gable_front_0']
    if not face.joints:
        pytest.skip('no tabs on this dormer')
    k = s['k']
    pts, _ = s['samples']['additional_gable_front_0']
    tabs = tab_points(face, s['solids']['additional_gable_front_0'], pts)
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
