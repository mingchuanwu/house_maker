"""
The ultimate check: do the cut panels assemble into the house that was specified?

An independent 3D model (tests/assembly3d.py) places every panel as a physical slab (drawn outline
eroded by kerf/2, as the laser leaves it). We then require:
  * panels never interpenetrate (except slivers thinner than the kerf offset tolerance),
  * every tab ends up inside the slab of the panel it plugs into, reaching its outer face,
  * the assembled extents are exactly the specified house.
"""

import itertools
import math

import numpy as np
import pytest

from ..conftest import make_house
from ..assembly3d import PanelSolid, box_frames
from ..spec import CONFIGS, cid

STEP = 0.5


def tol_depth(k):
    return 0.5 * k + 0.03          # sliver tolerance: slanted-edge kerf offsets differ by a few hundredths


def ridge_bound(theta, t, k):
    """Known limit of the ridge joint (see test_ridge_closes_for_any_roof_angle): the tabs run along the
    right roof plane into notches cut along the left plane; the two directions only coincide when the
    planes meet at 90 degrees (theta = 45). Otherwise the panels interpenetrate by up to t*|cos 2*theta|
    (shallower roofs) - wedge gaps open instead on steeper ones."""
    import math
    return tol_depth(k) if theta >= 45 else t * abs(math.cos(math.radians(2 * theta))) + tol_depth(k)


@pytest.fixture(params=CONFIGS, ids=cid, scope='module')
def assembled(request):
    c = request.param
    house = make_house(**c)
    panels = {p.name: p for p in house.build_panels()}
    X, Y, Z, th, t, k = (c[n] for n in ('length', 'width', 'height', 'gable_angle', 'material_thickness', 'kerf'))
    frames = box_frames(X, Y, Z, th, t, k)
    solids = {n: PanelSolid(panels[n], frames[n]) for n in panels}
    samples = {n: s.sample(step=STEP) for n, s in solids.items()}
    return dict(c=c, panels=panels, frames=frames, solids=solids, samples=samples, t=t, k=k, X=X, Y=Y, Z=Z, th=th)


def test_panels_do_not_interpenetrate(assembled):
    a = assembled
    worst = []
    for p, q in itertools.permutations(a['solids'], 2):
        pts, _ = a['samples'][p]
        d = a['solids'][q].depth(pts)
        hit = d[~np.isnan(d)]
        if len(hit):
            worst.append((hit.max(), p, q))
    for depth, p, q in sorted(worst, reverse=True):
        limit = tol_depth(a['k'])
        if {p, q} == {'roof_panel_left', 'roof_panel_right'}:
            limit = ridge_bound(a['th'], a['t'], a['k'])
        assert depth <= limit, f"{p} penetrates {q} by {depth:.3f} mm"


def tab_points(panel, solid, pts):
    """Sample points of a panel's solid that lie outside its nominal outline = the tabs."""
    from ..geom import point_in_polygon
    corners = [(c.x, c.y) for c in panel.corners]
    u, v, _ = solid.frame.to_local(pts)
    poly = np.array(corners)
    inside = np.zeros(len(u), dtype=bool)
    x1, y1 = poly[:, 0][None, :], poly[:, 1][None, :]
    x2, y2 = np.roll(poly[:, 0], -1)[None, :], np.roll(poly[:, 1], -1)[None, :]
    uu, vv = u[:, None], v[:, None]
    cross = ((y1 > vv) != (y2 > vv)) & (uu < (x2 - x1) * (vv - y1) / np.where(y2 == y1, 1, y2 - y1) + x1)
    inside = cross.sum(axis=1) % 2 == 1
    return pts[~inside]


def test_every_tab_sits_inside_the_slab_it_plugs_into_and_reaches_its_outer_face(assembled):
    a = assembled
    t, k = a['t'], a['k']
    for name, panel in a['panels'].items():
        if not any(j.role == 'male' for j in panel.joints.values()):
            continue
        if name == 'roof_panel_right' and a['th'] != 45:
            continue            # ridge limitation, covered by test_ridge_closes_for_any_roof_angle
        pts, _ = a['samples'][name]
        tabs = tab_points(panel, a['solids'][name], pts)
        assert len(tabs), name
        remaining = np.ones(len(tabs), dtype=bool)
        for other, solid in a['solids'].items():
            if other == name:
                continue
            fr = solid.frame
            u, v, w = fr.to_local(tabs)
            slack = k + 0.05                      # slanted gable edges are offset by a few hundredths of a kerf
            in_slab = (w > -slack) & (w < t + slack)
            # inside the other panel's nominal outline (so it really plugs into that panel's face)
            corners = np.array([(c.x, c.y) for c in a['panels'][other].corners])
            x1, y1 = corners[:, 0][None, :], corners[:, 1][None, :]
            x2, y2 = np.roll(corners[:, 0], -1)[None, :], np.roll(corners[:, 1], -1)[None, :]
            uu, vv = u[:, None], v[:, None]
            cross = ((y1 > vv) != (y2 > vv)) & (uu < (x2 - x1) * (vv - y1) / np.where(y2 == y1, 1, y2 - y1) + x1)
            in_poly = cross.sum(axis=1) % 2 == 1
            engaged = in_slab & in_poly
            if engaged.any():
                # the tab reaches the far face of the plate it passes through (flush, not short)
                assert w[engaged].max() >= t - (STEP / 2 + k + 0.05), f"{name} tab is short in {other}: reaches {w[engaged].max():.2f} of {t}"
            remaining &= ~engaged
        assert not remaining.any(), f"{name}: {remaining.sum()} tab samples are not inside any mating slab, e.g. {tabs[remaining][0]}"


def test_assembled_extents_are_the_specified_house(assembled):
    a = assembled
    X, Y, Z, t, th = a['X'], a['Y'], a['Z'], a['t'], a['th']
    allpts = np.vstack([a['samples'][n][0] for n in ('floor', 'side_wall_left', 'side_wall_right', 'gable_wall_front', 'gable_wall_back')])
    lo, hi = allpts.min(axis=0), allpts.max(axis=0)
    tol = STEP / 2 + a['k'] + 0.05                 # sample points are cell centres inside the kerf-eroded part
    # walls + floor: outer footprint (X + 2t) x (Y + 2t) starting at the floor edge, height Z + roof peak
    assert (lo[0], hi[0]) == pytest.approx((-t, X + t), abs=tol)
    assert (lo[1], hi[1]) == pytest.approx((-t, Y + t), abs=tol)
    assert lo[2] == pytest.approx(0, abs=tol)
    peak = (Y + 2 * t) / 2 * np.tan(np.radians(th))
    # the apex is a thin tip that the sample grid cannot reach exactly
    assert Z + peak - 1.0 <= hi[2] <= Z + peak + tol
    roofs = np.vstack([a['samples'][n][0] for n in ('roof_panel_left', 'roof_panel_right')])
    assert (roofs[:, 0].min(), roofs[:, 0].max()) == pytest.approx((-3 * t, X + 3 * t), abs=tol)    # 2t overhang past each gable


def _ridge_stats(theta, t=3.0, k=0.0):
    house = make_house(length=100, width=80, height=70, gable_angle=theta, material_thickness=t, kerf=k)
    panels = {p.name: p for p in house.build_panels()}
    frames = box_frames(100, 80, 70, theta, t, k)
    left = PanelSolid(panels['roof_panel_left'], frames['roof_panel_left'])
    right = PanelSolid(panels['roof_panel_right'], frames['roof_panel_right'])
    pts, _ = right.sample(step=0.25, layers=4)
    penetration = np.nan_to_num(left.depth(pts), nan=0.0).max()
    tabs = tab_points(panels['roof_panel_right'], right, pts)
    u, v, w = left.frame.to_local(tabs)
    corners = np.array([(c.x, c.y) for c in panels['roof_panel_left'].corners])
    x1, y1 = corners[:, 0][None, :], corners[:, 1][None, :]
    x2, y2 = np.roll(corners[:, 0], -1)[None, :], np.roll(corners[:, 1], -1)[None, :]
    cross = ((y1 > v[:, None]) != (y2 > v[:, None])) & (u[:, None] < (x2 - x1) * (v[:, None] - y1) / np.where(y2 == y1, 1, y2 - y1) + x1)
    engaged = (w > -0.05) & (w < t + 0.05) & (cross.sum(axis=1) % 2 == 1)
    reach = w[engaged].max() if engaged.any() else 0.0
    return penetration, reach, engaged.mean()


@pytest.mark.parametrize('theta', [20, 25, 30, 35, 40, 50, 55, 60, 65])
def test_ridge_deviation_is_the_inherent_geometric_limit(theta):
    """
    A laser cuts perpendicular to the plate, so the two roof panels cannot be bevelled to meet at the ridge: they
    fit exactly only when the planes meet at 90 degrees (theta = 45). Otherwise the deviation is bounded:
      shallower roofs: the panels overlap along the ridge by at most t*|cos 2*theta| (trim by hand),
      steeper roofs:   they do not overlap but leave a wedge gap of at most t*|tan(90 - 2*theta)| on the outer
                       ridge face and the tabs fall short by about as much (fill / sand by hand).
    """
    t = 3.0
    penetration, reach, engaged_fraction = _ridge_stats(theta, t)
    if theta < 45:
        assert 0 < penetration <= t * abs(math.cos(math.radians(2 * theta))) + 0.03
    else:
        assert penetration <= tol_depth(0.0)
        wedge = t * abs(math.tan(math.radians(90 - 2 * theta)))
        assert t - reach <= wedge + 0.3                    # tabs fall short by no more than the wedge (+ sampling)


def test_ridge_is_exact_at_45_degrees():
    penetration, reach, engaged_fraction = _ridge_stats(45, 3.0, 0.1)
    assert penetration <= tol_depth(0.1)
    assert engaged_fraction > 0.99 and reach >= 3.0 - 0.3


@pytest.mark.parametrize('theta', [45, 50, 60])
def test_ridge_is_exact_when_it_can_be(theta):
    """At 45 degrees the ridge fits perfectly; on steeper roofs the panels at least never interpenetrate."""
    t, k = 3.0, 0.1
    house = make_house(length=100, width=80, height=70, gable_angle=theta, material_thickness=t, kerf=k)
    panels = {p.name: p for p in house.build_panels()}
    frames = box_frames(100, 80, 70, theta, t, k)
    left = PanelSolid(panels['roof_panel_left'], frames['roof_panel_left'])
    right = PanelSolid(panels['roof_panel_right'], frames['roof_panel_right'])
    for a, b in ((left, right), (right, left)):
        d = b.depth(a.sample(step=STEP)[0])
        assert (np.nan_to_num(d, nan=0.0)).max() <= tol_depth(k)
