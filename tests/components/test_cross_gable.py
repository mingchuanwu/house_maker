"""
Cross gables: a side wall rising into a gable, with its own small roof running back into the main roof. Checked
against the independent 3D construction (tests/assembly3d.py): placement, fit (no penetration, valleys and ridge on
the main roof, the wall through the eave notch, rake tabs in their slots), window; then placement rules and the CLI.
"""

import math
import pathlib
import subprocess
import sys
import warnings

import numpy as np
import pytest

from house_maker import HouseMaker, PlacementError
from house_maker.builders.dormer import face_window
from house_maker.model3d import house_frames
from house_maker.svgpath import parse_path
from ..assembly3d import PanelSolid, box_frames, cross_gable_frames
from .test_assembly_3d import STEP, tol_depth

T = 3.0
L, WD, Z = 200, 140, 100
PKG = pathlib.Path(__file__).resolve().parents[2]
SCENES = [
    # theta, side, x, width, kerf, pitch
    (45, 'left', 80, 40, 0.1, None),
    (35, 'right', 60, 30, 0.0, None),
    (60, 'left', 50, 50, 0.1, None),
    (45, 'right', 100, 40, 0.1, 30.0),
    (30, 'left', 120, 60, 0.15, None),
]


@pytest.fixture(params=SCENES, ids=lambda s: f"a{s[0]}-{s[1]}-x{s[2]}-W{s[3]}-k{s[4]}-p{s[5] or 45}", scope='module')
def scene(request):
    theta, side, x, W, k, pitch = request.param
    house = HouseMaker(length=L, width=WD, height=Z, gable_angle=theta, material_thickness=T, kerf=k, finger_length=10)
    roof, wall = f'roof_panel_{side}', f'side_wall_{side}'
    house.architectural_config.add_cross_gable(roof, x, W, pitch=pitch)
    panels = {p.name: p for p in house.build_panels()}
    ref = box_frames(L, WD, Z, theta, T, k)
    frames, pts = cross_gable_frames(ref[roof], ref[wall], x, W, theta, pitch or 45.0, T, k, Z)
    frames.update({roof: ref[roof], wall: ref[wall]})
    solids = {n: PanelSolid(panels[n], f) for n, f in frames.items()}
    return dict(theta=theta, phi=pitch or 45.0, k=k, roof=roof, wall=wall, house=house, panels=panels, ref=ref,
                frames=frames, pts=pts, solids=solids, samples={n: s.sample(step=STEP) for n, s in solids.items()})


def _top_plane(roof):
    return roof.to_world(np.array([0.0]), np.array([0.0]), np.array([T]))[0], np.asarray(roof.n)


def test_placement_agrees_with_the_independent_model(scene):
    s = scene
    mine = house_frames(s['house'].geometry, s['house'].architectural_config, s['panels'])
    for name in ('cross_gable_roof_left_0', 'cross_gable_roof_right_0'):
        f = s['frames'][name]
        for a, b in ((mine[name].origin, f.O), (mine[name].eu, f.eu), (mine[name].ev, f.ev)):
            assert a == pytest.approx(tuple(b), abs=1e-9), name


def test_sill_and_ridge_end_lie_on_the_main_roof(scene):
    origin, n = _top_plane(scene['ref'][scene['roof']])
    for name in ('A', 'B', 'Q'):
        assert abs((scene['pts'][name] - origin) @ n) < 1e-9, name


def test_valleys_lie_on_the_main_roof(scene):
    s, (origin, n) = scene, _top_plane(scene['ref'][scene['roof']])
    for side in ('left', 'right'):
        name = f'cross_gable_roof_{side}_0'
        panel = s['panels'][name]
        i = panel.edge_names.index('valley')
        a, b = panel.corners[i], panel.corners[(i + 1) % len(panel.corners)]
        us, vs = np.linspace(a.x, b.x, 20), np.linspace(a.y, b.y, 20)
        gaps = [np.abs((s['frames'][name].to_world(us, vs, np.full(20, w)) - origin) @ n).max() for w in (0.0, T)]
        assert min(gaps) <= s['k'] + 0.05, f"{side} valley is {min(gaps):.3f} mm off the main roof"


def test_nothing_interpenetrates(scene):
    """Main roof (with its eave notch), side wall (with its gable) and the two cross roof panels."""
    s = scene
    names = list(s['solids'])
    pair = {'cross_gable_roof_left_0', 'cross_gable_roof_right_0'}
    for a in names:
        for b in names:
            if a == b:
                continue
            d = s['solids'][b].depth(s['samples'][a][0])
            d = d[~np.isnan(d)]
            if not len(d):
                continue
            limit = tol_depth(s['k'])
            if {a, b} == pair and s['phi'] < 45:                         # the ridge's square-cut limitation
                limit += T * abs(math.cos(math.radians(2 * s['phi'])))
            assert d.max() <= limit, f"{a} penetrates {b} by {d.max():.3f} mm (limit {limit:.3f})"


def test_the_wall_rises_through_the_eave_notch(scene):
    """At the gable's middle, just above the main roof, there is wall - and the roof is notched where the wall passes."""
    s = scene
    P, A, B = s['pts']['P'], s['pts']['A'], s['pts']['B']
    mid = (A + B) / 2
    wall = s['ref'][s['wall']]
    into = -np.asarray(wall.n)
    probe = mid + into * (T / 2) + np.array([0.0, 0.0, 1.0])               # mid-thickness, 1 mm above the sill
    assert s['solids'][s['wall']].contains(probe[None, :])[0]
    under = mid + into * (T / 2) - np.array([0.0, 0.0, T / math.cos(math.radians(s['theta'])) / 2])  # inside the roof slab
    assert s['solids'][s['wall']].contains(under[None, :])[0]
    assert not s['solids'][s['roof']].contains(under[None, :])[0]


def test_rake_tabs_fill_their_slots(scene):
    s = scene
    for side in ('left', 'right'):
        name = f'cross_gable_roof_{side}_0'
        (slot,) = s['panels'][name].slots
        centre = s['frames'][name].to_world(np.array([slot.cx]), np.array([slot.cy]), np.array([T / 2]))
        assert s['solids'][s['wall']].contains(centre)[0], f"no wall tab in the {side} cross roof's slot"


def test_the_gable_has_a_window_when_it_has_room(scene):
    """The dormer window rule, with the gable as the face: a low gable (30 degree pitch here) has no room for one."""
    s = scene
    wall = s['panels'][s['wall']]
    top = s['house'].geometry.z_kerf
    up_high = [sub for d in wall.cut[1:] for sub in parse_path(d) if min(q.y for q in sub) > top]
    (gable,) = s['house'].architectural_config.cross_gables
    assert bool(up_high) == (face_window(gable) is not None)
    assert up_high or s['phi'] < 45


# ------------------------------------------------------------------ placement rules
def house(**kw):
    return HouseMaker(length=L, width=WD, height=Z, gable_angle=45, material_thickness=T, finger_length=10, **kw)


def test_clear_of_the_wall_ends_and_other_roof_features():
    h = house()
    cfg = h.architectural_config
    with pytest.raises(PlacementError, match='corner joints'):
        cfg.add_cross_gable('roof_panel_left', 2, 30)
    cfg.add_cross_gable('roof_panel_left', 80, 40)
    with pytest.raises(PlacementError, match=r'overlaps.*It would fit with \(mm\) x between'):
        cfg.add_cross_gable('roof_panel_left', 100, 40)
    with pytest.raises(PlacementError, match='overlaps'):                      # dormers see it too
        h.add_additional_gable('roof_panel_left', h.geometry.roof_u_from_wall_x('roof_panel_left', 100) - 15, 60, 30)
    with pytest.raises(PlacementError, match='roof panel'):
        cfg.add_cross_gable('side_wall_left', 80, 40)


def test_cross_gables_count_toward_the_coverage_warning():
    h = house()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        h.architectural_config.add_cross_gable('roof_panel_right', 20, 60)
        h.architectural_config.add_cross_gable('roof_panel_right', 110, 60)
    assert any('dominate' in str(m.message) for m in w)


def test_cli_cross_gable(tmp_path):
    out = tmp_path / 'h.svg'
    run = lambda *a: subprocess.run([sys.executable, '-m', 'house_maker.generate_house', '-o', str(out), '--3d', 'none',
                                     *a], capture_output=True, text=True, cwd=PKG.parent)
    r = run('--length', '200', '--width', '140', '--height', '100', '--cross-gable', 'left:x=80:width=40',
            '--cross-gable', 'right:x=60:width=30:pitch=50')
    assert r.returncode == 0, r.stdout + r.stderr
    svg = out.read_text()
    assert all(f'id="cross_gable_roof_{s}_{i}"' in svg for s in ('left', 'right') for i in (0, 1))
    r = run('--cross-gable', 'left:width=40')
    assert r.returncode == 2 and 'x=' in r.stderr


def test_a_cross_gable_too_low_to_reach_the_main_roof_is_rejected():
    """A small, shallow cross gable whose ridge would end within the strip of main roof cut away for the wall (its
    valleys would rest on nothing) - random sweep seed 84: 20 mm at 35 degrees on a 60 degree roof, 5 mm stock."""
    h = HouseMaker(length=219, width=166, height=88, gable_angle=60, material_thickness=5, finger_length=15, kerf=0.15)
    with pytest.raises(PlacementError, match='too low'):
        h.add_cross_gable('left', 34, 20, pitch=35, roof_overhang=2)
    h.add_cross_gable('left', 34, 45, pitch=50, roof_overhang=2)         # wider and steeper: fine
