"""
Absolute dimensions of every panel against the closed-form specification in tests/spec.py.

The seam tests only compare panels with each other; these tests pin the numbers themselves, so a
house of the requested size really comes out at the requested size.
"""

import math

import pytest

from ..conftest import make_house
from ..geom import bounds, outline
from ..spec import CONFIGS, box_panel_sizes, cid, gable_peak

TOL = 5e-3


@pytest.fixture(params=CONFIGS, ids=cid)
def box(request):
    c = request.param
    house = make_house(**c)
    return c, house, {p.name: p for p in house.build_panels()}


def test_nominal_panel_sizes(box):
    c, _, p = box
    expected = box_panel_sizes(c['length'], c['width'], c['height'], c['gable_angle'],
                               c['material_thickness'], c['kerf'])
    assert set(p) == set(expected)
    for name, (w, h) in expected.items():
        assert p[name].nominal_size == pytest.approx((w, h), abs=TOL), name


def test_nominal_corners_are_the_spec_rectangles_and_gable_pentagon(box):
    c, _, p = box
    X, Y, Z, t, k = c['length'], c['width'], c['height'], c['material_thickness'], c['kerf']
    sizes = box_panel_sizes(X, Y, Z, c['gable_angle'], t, k)
    for name in ('floor', 'side_wall_left', 'side_wall_right', 'roof_panel_left', 'roof_panel_right'):
        w, h = sizes[name]
        got = [(q.x, q.y) for q in p[name].corners]
        assert [v for pt in got for v in pt] == pytest.approx([0, 0, w, 0, w, h, 0, h], abs=TOL), name
    for name in ('gable_wall_front', 'gable_wall_back'):
        w, h = sizes[name]
        wall_top = Z + k
        got = [(q.x, q.y) for q in p[name].corners]
        assert [v for pt in got for v in pt] == pytest.approx(
            [0, 0, w, 0, w, wall_top, w / 2, h, 0, wall_top], abs=TOL), name
        assert h - wall_top == pytest.approx(gable_peak(Y, c['gable_angle'], t, k), abs=TOL)


def test_outline_extents_include_exactly_the_protruding_tabs(box):
    """Cut extent = nominal size + one thickness for every side that carries tabs."""
    c, _, p = box
    t = c['material_thickness']
    sizes = box_panel_sizes(c['length'], c['width'], c['height'], c['gable_angle'], t, c['kerf'])

    def extent(name):
        x0, y0, x1, y1 = bounds(outline(p[name]))
        return x1 - x0, y1 - y0

    w, h = sizes['floor']
    assert extent('floor') == pytest.approx((w + 2 * t, h + 2 * t), abs=TOL)            # tabs on all four sides
    for name in ('side_wall_left', 'side_wall_right'):
        w, h = sizes[name]
        assert extent(name) == pytest.approx((w + 2 * t, h), abs=TOL)                    # tabs on the two vertical sides
    w, h = sizes['roof_panel_left']
    assert extent('roof_panel_left') == pytest.approx((w, h), abs=TOL)                   # notches only
    w, h = sizes['roof_panel_right']
    assert extent('roof_panel_right') == pytest.approx((w, h + t), abs=TOL)              # tabs along the ridge
    w, _ = sizes['gable_wall_front']
    assert extent('gable_wall_front')[0] == pytest.approx(w, abs=TOL)


def test_assembled_house_dimensions(box):
    """What the given specification means once assembled (physical, kerf-free numbers)."""
    c, _, p = box
    X, Y, Z, t, k, theta = (c[n] for n in ('length', 'width', 'height', 'material_thickness', 'kerf', 'gable_angle'))
    phys = lambda v: v - k                                       # drawn size -> cut size
    # floor is X x Y; walls stand around it: outer footprint (X + 2t) x (Y + 2t)
    assert phys(p['floor'].nominal_size[0]) == pytest.approx(X, abs=TOL)
    assert phys(p['floor'].nominal_size[1]) == pytest.approx(Y, abs=TOL)
    assert phys(p['gable_wall_front'].nominal_size[0] - 2 * t) == pytest.approx(Y, abs=TOL)   # spans the side walls
    assert phys(p['side_wall_left'].nominal_size[1]) == pytest.approx(Z, abs=TOL)             # wall height
    # roof overhangs the gable walls by 2t at each end (6t over the floor length, 2t beyond each gable)
    assert phys(p['roof_panel_left'].nominal_size[0] - 6 * t) == pytest.approx(X, abs=TOL)
    # the gable slope is the requested roof angle
    g = p['gable_wall_front']
    rise = g.nominal_size[1] - (Z + k)
    assert math.degrees(math.atan2(rise, g.nominal_size[0] / 2)) == pytest.approx(theta, abs=1e-6)


def test_cut_length_and_area_follow_the_outline(box):
    """get_cutting_summary numbers: perimeter = nominal perimeter + 2t per finger, area likewise."""
    c, house, p = box
    t = c['material_thickness']
    summary = house.get_cutting_summary()['panel_details']
    for name, panel in p.items():
        w, h = panel.nominal_size
        if name.startswith('gable_wall'):
            continue                                          # pentagon: covered by the outline checks
        fingers = [f for j in panel.joints.values() for f in j.fingers]
        nominal_perimeter = 2 * (w + h)
        slots = sum(2 * (s.length + s.thickness) for s in panel.slots)
        assert summary[name]['perimeter'] == pytest.approx(nominal_perimeter + 2 * t * len(fingers) + slots, abs=0.02), name
        male = sum(sum(b - a for a, b in j.fingers) for j in panel.joints.values() if j.role == 'male')
        female = sum(sum(b - a for a, b in j.fingers) for j in panel.joints.values() if j.role == 'female')
        slot_area = sum(s.length * s.thickness for s in panel.slots)
        assert summary[name]['area'] == pytest.approx(w * h + t * (male - female) - slot_area, abs=0.05), name


def test_total_cut_length_is_the_sum_of_panels(box):
    _, house, p = box
    summary = house.get_cutting_summary()
    assert summary['total_cut_length_mm'] == pytest.approx(sum(q.cut_length for q in p.values()))
    assert summary['total_panels'] == len(p)
