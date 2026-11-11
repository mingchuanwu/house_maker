"""
Dormer side walls (cheeks): when a dormer gets them, their shape, and how the face, cheeks and roofs are wired.
The 3D fit (no penetration, tabs through their roofs, cheeks on the roof) is in test_dormer_3d.py.
"""

import math
import re
import subprocess
import sys
import pathlib

import pytest

from house_maker import PlacementError, WindowType
from house_maker.svgpath import parse_path
from house_maker.mates import EDGE, TAB_SLOT, declared_mates
from ..conftest import make_house

T = 3.0
PKG = pathlib.Path(__file__).resolve().parents[2]


def dormer(theta, width=30, **kw):
    house = make_house(length=200, width=160, height=90, gable_angle=theta, material_thickness=T, kerf=0.0)
    d = house.add_additional_gable('roof_panel_left', 30, 20, width, **kw)
    return house, d


@pytest.mark.parametrize('theta,kw,wall,pitch', [
    (60, {}, 15.0, 45.0),                                # steep: walls as tall as the gable (W/2 at 45 degrees)
    (50, {}, 15.0, 45.0),
    (45, {}, 0.0, 45.0),                                 # not steeper than 45: no walls
    (35, {}, 0.0, 45.0),
    (60, dict(wall_height=0), 0.0, 45.0),                # walls off: still a 90 degree apex
    (35, dict(wall_height=12), 12.0, 45.0),              # walls on request on a shallow roof
    (60, dict(pitch=50), 15 * math.tan(math.radians(50)), 50.0),   # auto walls follow the gable at that pitch
])
def test_when_a_dormer_gets_walls(theta, kw, wall, pitch):
    _, d = dormer(theta, **kw)
    assert d.geometry.wall_height == pytest.approx(wall)
    assert d.geometry.phi_deg == pytest.approx(pitch)


def test_walls_make_a_steep_dormer_deeper():
    _, plain = dormer(60, wall_height=0, pitch=45)
    _, walled = dormer(60)
    th = math.radians(60)
    assert plain.position.height == pytest.approx(15 / math.tan(th) / math.cos(th))
    assert walled.position.height == pytest.approx((15 + 15) / math.tan(th) / math.cos(th))   # wall + gable


def test_shapes_of_the_face_and_the_cheeks():
    house, d = dormer(60)
    p = {q.name: q for q in house.build_panels()}
    lift = T * math.tan(math.radians(60))
    face = p['additional_gable_front_0']
    assert face.edge_names == ['base', 'side_right', 'rake_right', 'rake_left', 'side_left']
    assert face.nominal_size == pytest.approx((30, 15 + 15 - lift), abs=0.01)
    for side in ('left', 'right'):
        cheek = p[f'additional_gable_cheek_{side}_0']
        assert sorted(cheek.edge_names) == ['bottom', 'front', 'top']
        # right triangle: level top (y_w - t long), vertical front (wall - lift), bottom on the roof
        assert cheek.nominal_size == pytest.approx((15 / math.tan(math.radians(60)) - T, 15 - lift), abs=0.01)
    roof = p['additional_gable_roof_left_0']
    assert 'side' in roof.edge_names
    (score,) = [s for s in p['roof_panel_left'].score]
    assert score.count('L') == 4                                     # pentagon footprint


def test_walls_must_be_tall_enough():
    with pytest.raises(PlacementError, match='side walls too low'):
        dormer(60, wall_height=5)                                    # below the face's lift + t
    with pytest.raises(PlacementError):
        dormer(35, wall_height=-1)


def test_mates_wire_the_cheeks():
    house, _ = dormer(55, width=50, wall_height=22)
    mates = declared_mates({q.name: q for q in house.build_panels()})
    edges = {(m.a, m.b) for m in mates if m.kind == EDGE}
    slots = {(m.a, m.b[0]) for m in mates if m.kind == TAB_SLOT}
    for side in ('left', 'right'):
        assert (('additional_gable_front_0', f'side_{side}'), (f'additional_gable_cheek_{side}_0', 'front')) in edges
        assert ((f'additional_gable_roof_{side}_0', 'side'), (f'additional_gable_cheek_{side}_0', 'top')) in edges
        assert ((f'additional_gable_cheek_{side}_0', 'bottom'), 'roof_panel_left') in slots
    assert (('additional_gable_front_0', 'base'), 'roof_panel_left') in slots


@pytest.mark.parametrize('angle,extra,cheeks', [
    ('60', [], True),                                                    # steep: walls by default
    ('60', ['--additional-gable-wall-height', '0'], False),
    ('35', ['--additional-gable-wall-height', '8', '--additional-gable-y', '4'], True),   # deeper: placed higher up
])
def test_cli_wall_height(tmp_path, angle, extra, cheeks):
    out = tmp_path / 'h.svg'
    args = ['--angle', angle, '--add-additional-gable'] + extra
    r = subprocess.run([sys.executable, '-m', 'house_maker.generate_house', '-o', str(out), '--3d', 'none'] + args,
                       capture_output=True, text=True, cwd=PKG.parent)
    assert r.returncode == 0, r.stdout + r.stderr
    assert ('additional_gable_cheek_left_0' in out.read_text()) == cheeks


@pytest.mark.parametrize('pitch', [90, 0, -10, 120])
def test_pitch_out_of_range_explains_pitch_vs_apex(pitch):
    with pytest.raises(PlacementError, match='apex angle is 180 - 2 x pitch'):
        dormer(60, pitch=pitch)


def test_placement_error_proposes_settings_that_fit():
    """`--angle 30 --add-additional-gable --additional-gable-wall-height 10 --additional-gable-pitch 30`: too deep for
    the roof at y=15. The error lists a y range, a lower wall and a smaller width - and each of them does fit."""
    kw = dict(length=80, width=60, height=70, gable_angle=30, material_thickness=3, finger_length=10)
    house = make_house(**kw)
    with pytest.raises(PlacementError) as err:
        house.add_additional_gable('roof_panel_right', 30, 15, 25, wall_height=10, pitch=30)
    msg = str(err.value)
    y0, y1 = map(float, re.search(r'y between ([\d.]+) and ([\d.]+)', msg).groups())
    wall = float(re.search(r'wall at most ([\d.]+)', msg).group(1))
    width = float(re.search(r'width at most ([\d.]+)', msg).group(1))
    for change in (dict(y=y0), dict(y=y1), dict(wall_height=wall), dict(width=width)):
        args = {**dict(x=30, y=15, width=25, wall_height=10, pitch=30), **change}
        make_house(**kw).add_additional_gable('roof_panel_right', **args)            # does not raise
    with pytest.raises(PlacementError):                                               # and the ranges are tight
        make_house(**kw).add_additional_gable('roof_panel_right', 30, y1 + 0.2, 25, wall_height=10, pitch=30)


def test_no_proposal_when_nothing_fits():
    house = make_house(length=80, width=60, height=70, gable_angle=30, material_thickness=3)
    with pytest.raises(PlacementError) as err:
        house.add_additional_gable('roof_panel_right', 30, 15, 25, wall_height=60, pitch=60)   # far too deep anywhere
    assert 'It would fit with' not in str(err.value)          # no single change helps: the plain reason only


# ------------------------------------------------------------------ the dormer window
def _segment_distance(p, a, b):
    ax, ay, bx, by = a.x, a.y, b.x, b.y
    L2 = (bx - ax) ** 2 + (by - ay) ** 2
    s = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p.x - ax) * (bx - ax) + (p.y - ay) * (by - ay)) / L2))
    return math.hypot(p.x - (ax + s * (bx - ax)), p.y - (ay + s * (by - ay)))


@pytest.mark.parametrize('theta,width,kw,grid', [
    (60, 40, {}, (2, 2)),                    # walls by default: room for panes
    (60, 50, {}, (3, 2)),
    (45, 70, {}, (2, 2)),                    # large plain dormer
    (60, 25, {}, (1, 1)),                    # small: a single pane
    (60, 30, dict(wall_height=15), (1, 1)),
    (35, 25, {}, None),                      # too small for any window
    (60, 25, dict(wall_height=0), None),
])
def test_dormer_face_window_fits_the_face(theta, width, kw, grid):
    house = make_house(length=200, width=160, height=90, gable_angle=theta, material_thickness=T, kerf=0.0)
    d = house.add_additional_gable('roof_panel_left', 40, 20, width, **kw)
    face = {p.name: p for p in house.build_panels()}['additional_gable_front_0']
    holes = [sub for path in face.cut[1:] for sub in parse_path(path)]
    if grid is None:
        assert not holes
        return
    assert len(holes) == grid[0] * grid[1]
    corners, names = face.corners, face.edge_names
    for hole in holes:
        for q in hole:
            for i, name in enumerate(names):
                a, b = corners[i], corners[(i + 1) % len(corners)]
                need = 2 * T if name.startswith('side') else T          # notched sides: notch t + t of material
                assert _segment_distance(q, a, b) >= need - 1e-3, f"window corner {q} too close to {name}"  # 3-decimal file


def test_attic_windows_are_only_ever_in_gable_triangles():
    from house_maker import HouseMaker
    for dims in ((200, 140, 100), (100, 100, 70)):
        h = HouseMaker(length=dims[0], width=dims[1], height=dims[2], gable_angle=45)
        panels = {p.name for p in h.build_panels()}
        for wall in ('gable_wall_front', 'gable_wall_back'):
            for i, w in enumerate(h.architectural_config.get_windows_for_panel(wall)):
                if w.position.y < h.geometry.z:                      # on a floor: an ordinary, framed window
                    assert w.type != WindowType.ATTIC and f'{wall}_w{i}_window_casing' in panels, (wall, i)


def test_side_windows_beside_the_main_window_are_symmetric():
    from house_maker import HouseMaker
    h = HouseMaker(length=200, width=140, height=100, gable_angle=45, material_thickness=3)
    ws = sorted((w.position for w in h.architectural_config.get_windows_for_panel('gable_wall_back')
                 if w.position.y < h.geometry.z), key=lambda p: p.x)
    assert len(ws) == 3
    left, main, right = ws
    assert main.x - (left.x + left.width) == pytest.approx(right.x - (main.x + main.width), abs=1e-6)
