"""
Kerf compensation of cut-outs and trim frames: the laser removes kerf/2 either side of the drawn line, so a hole
must be drawn kerf/2 smaller on every side and a part kerf/2 larger. Checked geometrically for every window and
door type (curves included) against the uncompensated nominal shapes.
"""

import pytest

from house_maker import DoorType, WindowType
from house_maker.casings import door_casing_pieces, window_casing_pieces
from house_maker.cutouts import door_cutout, window_cutout
from house_maker.kerf import CURVE_SAMPLES, compensate_part, compensate_void
from house_maker.svgpath import parse_path
from .conftest import make_house
from .geom import dedupe, point_in_polygon, segment_distance

K = 0.1
H = K / 2
TOL = 6e-3          # 32-sample flattening of a 15 mm radius: sagitta ~ 0.005 mm


def polys(d):
    return [dedupe(sub) for sub in parse_path(d, CURVE_SAMPLES)]


def boundary_distance(p, poly):
    return min(segment_distance(p, a, b) for a, b in zip(poly, poly[1:] + poly[:1]))


def midpoints(poly):
    return [type(poly[0])((a.x + b.x) / 2, (a.y + b.y) / 2) for a, b in zip(poly, poly[1:] + poly[:1])]


def assert_offset(nominal, compensated, inward):
    """Every edge of `compensated` lies exactly H from `nominal`'s boundary, on the inner/outer side."""
    assert len(nominal) == len(compensated)
    for nom, comp in zip(nominal, compensated):
        for v in comp:
            assert point_in_polygon((v.x, v.y), nom) == inward, "vertex on the wrong side of the nominal outline"
            assert boundary_distance(v, nom) >= H - TOL                  # never closer than kerf/2
        for m in midpoints(comp):
            assert boundary_distance(m, nom) == pytest.approx(H, abs=TOL)


@pytest.mark.parametrize('wtype', list(WindowType), ids=lambda t: t.name.lower())
def test_window_cutouts_are_drawn_kerf_smaller(wtype):
    house = make_house(length=160, width=120, height=100, kerf=K)
    w = house.add_window('side_wall_left', 50, 30, window_type=wtype)
    nominal = window_cutout(w)
    drawn = [d for d in house.build_panels() if d.name == 'side_wall_left'][0].cut[1:]
    assert_offset(polys(nominal), [dedupe(sub) for d in drawn for sub in parse_path(d, CURVE_SAMPLES)], inward=True)


@pytest.mark.parametrize('dtype', list(DoorType), ids=lambda t: t.name.lower())
def test_door_cutouts_are_drawn_kerf_smaller(dtype):
    house = make_house(length=160, width=120, height=100, kerf=K)
    d = house.add_door('gable_wall_front', 40, 4, 16, 40, door_type=dtype)
    drawn = [p for p in house.build_panels() if p.name == 'gable_wall_front'][0].cut[1:]
    assert_offset(polys(door_cutout(d)), [dedupe(sub) for dd in drawn for sub in parse_path(dd, CURVE_SAMPLES)], inward=True)


@pytest.mark.parametrize('wtype', [t for t in WindowType if t != WindowType.ATTIC], ids=lambda t: t.name.lower())
def test_window_casings_grow_and_their_openings_shrink(wtype):
    house = make_house(length=160, width=120, height=100, kerf=K)
    w = house.add_window('side_wall_left', 50, 30, window_type=wtype)
    nominal = window_casing_pieces(w, 'x', house.geometry.thickness)
    (_, (_, _, path)), = [(n, v) for n, v in nominal.items() if not n.endswith('scores')]
    (casing,) = [p for p in house.build_panels() if p.name.endswith('window_casing')]
    drawn = [dedupe(s) for s in parse_path(casing.cut[0], CURVE_SAMPLES)]
    nom = polys(path)
    assert_offset(nom[:1], drawn[:1], inward=False)           # outline: outside the nominal one
    assert_offset(nom[1:], drawn[1:], inward=True)            # opening: inside the nominal one


@pytest.mark.parametrize('dtype', list(DoorType), ids=lambda t: t.name.lower())
def test_door_casings_grow(dtype):
    house = make_house(length=160, width=120, height=100, kerf=K)
    d = house.add_door('gable_wall_front', 40, 4, 16, 40, door_type=dtype)
    nominal = door_casing_pieces(d, 'x', house.geometry.thickness)
    (_, (_, _, path)), = [(n, v) for n, v in nominal.items() if not n.endswith('scores')]
    (casing,) = [p for p in house.build_panels() if p.name.endswith('door_casing')]
    assert_offset(polys(path)[:1], [dedupe(s) for s in parse_path(casing.cut[0], CURVE_SAMPLES)][:1], inward=False)


def test_score_lines_are_not_compensated():
    """Score lines are engraved, not cut: they stay exactly where the design puts them."""
    house = make_house(length=160, width=120, height=100, kerf=0.2)
    w = house.add_window('side_wall_left', 50, 30)
    nominal = window_casing_pieces(w, 'x', house.geometry.thickness)
    (_, (_, _, score)), = [(n, v) for n, v in nominal.items() if n.endswith('scores')]
    (casing,) = [p for p in house.build_panels() if p.name.endswith('window_casing')]
    assert casing.score == [score]


def test_zero_kerf_leaves_the_paths_untouched_curves_included():
    d = "M 0,0 L 10,0 Q 12,5 10,10 L 0,10 Z M 2,2 C 3,3 4,3 5,2 Z"
    assert compensate_void(d, 0) == d and compensate_part(d, 0) == d
    house = make_house(kerf=0.0, length=160, width=120, height=100)
    w = house.add_window('side_wall_left', 50, 30, window_type=WindowType.ARCHED)
    wall = [p for p in house.build_panels() if p.name == 'side_wall_left'][0]
    assert wall.cut[1] == window_cutout(w)                                  # not even re-formatted: still has its curves
    assert ' Q ' in wall.cut[1] or ' C ' in wall.cut[1]


def test_compensated_hole_loses_exactly_the_kerf_strip():
    """Rectangle 20 x 10: shrinking by kerf/2 per side removes kerf*(20+10) - kerf^2 of area."""
    out = compensate_void("M 0,0 L 20,0 L 20,10 L 0,10 Z", 0.2)
    (poly,) = polys(out)
    xs, ys = [p.x for p in poly], [p.y for p in poly]
    assert (min(xs), max(xs), min(ys), max(ys)) == pytest.approx((0.1, 19.9, 0.1, 9.9))
    # a part grows the same way, and holes in it shrink
    part = compensate_part("M 0,0 L 20,0 L 20,10 L 0,10 Z M 5,3 L 8,3 L 8,6 L 5,6 Z", 0.2)
    outer, hole = polys(part)
    assert (min(p.x for p in outer), max(p.x for p in outer)) == pytest.approx((-0.1, 20.1))
    assert (min(p.x for p in hole), max(p.x for p in hole)) == pytest.approx((5.1, 7.9))


def test_opposite_orientations_are_handled():
    cw = "M 0,0 L 0,10 L 20,10 L 20,0 Z"
    ccw = "M 0,0 L 20,0 L 20,10 L 0,10 Z"
    a, b = polys(compensate_void(cw, 0.2))[0], polys(compensate_void(ccw, 0.2))[0]
    assert sorted((round(p.x, 6), round(p.y, 6)) for p in a) == sorted((round(p.x, 6), round(p.y, 6)) for p in b)


@pytest.mark.parametrize('wtype', [WindowType.ARCHED, WindowType.CIRCULAR, WindowType.PALLADIAN, WindowType.GOTHIC_PAIR],
                         ids=lambda t: t.name.lower())
def test_curves_are_flattened_finely_enough_for_a_cut_file(wtype):
    """Against a 256-sample reference of the true curve, the drawn hole stays kerf/2 inside to within 0.01 mm."""
    house = make_house(length=160, width=120, height=100, kerf=K)
    w = house.add_window('side_wall_left', 50, 30, window_type=wtype)
    fine = [dedupe(s) for s in parse_path(window_cutout(w), 256)]
    drawn = [p for p in house.build_panels() if p.name == 'side_wall_left'][0].cut[1:]
    drawn_polys = [dedupe(s) for d in drawn for sub in [parse_path(d, 4)] for s in sub]       # as written: no re-flattening
    for comp, nom in zip(drawn_polys, fine):
        for m in midpoints(comp):
            assert boundary_distance(m, nom) == pytest.approx(H, abs=0.01)
