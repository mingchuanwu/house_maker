"""
Boundary-value tests: every limit is tested exactly at, and just beyond, the allowed value, so a
`<` that becomes `<=` (or an `or` that becomes `and`) changes the outcome of a test.
"""

import math

import pytest

from house_maker import HouseGeometry, PlacementError
from house_maker.components import AdditionalGable, Chimney, ComponentPosition, Door, DoorType, Window, WindowType
from house_maker.dormer_geometry import solve_dormer
from house_maker.exceptions import GeometryError
from house_maker.layout import pack
from house_maker.render import CHAR_WIDTH, FONT_SIZE, LABEL_HEIGHT, LABEL_OFFSET, MARGIN, item_size, render_svg
from house_maker.svgpath import BBox, parse_path, path_bbox, union_bbox
from .conftest import make_house

EPS = 1e-3


def pos(w, h, x=10, y=10, panel='side_wall_left'):
    return ComponentPosition(x, y, w, h, panel)


# ---------------------------------------------------------------- component minimum sizes
@pytest.mark.parametrize('w,h,ok', [
    (5.0, 5.0, True), (4.999, 5.0, False), (5.0, 4.999, False), (4.999, 4.999, False),
    (0, 10, False), (10, 0, False), (-1, 10, False), (10, -1, False),
])
def test_window_minimum_size(w, h, ok):
    if ok:
        Window(WindowType.RECTANGULAR, pos(w, h))
    else:
        with pytest.raises(GeometryError):
            Window(WindowType.RECTANGULAR, pos(w, h))


@pytest.mark.parametrize('w,h,ok', [
    (8.0, 15.0, True), (7.999, 15.0, False), (8.0, 14.999, False), (7.999, 14.999, False),
    (0, 20, False), (10, 0, False),
])
def test_door_minimum_size(w, h, ok):
    if ok:
        Door(DoorType.RECTANGULAR, pos(w, h))
    else:
        with pytest.raises(GeometryError):
            Door(DoorType.RECTANGULAR, pos(w, h))


@pytest.mark.parametrize('w,d,t,h,ok', [
    (5.0, 8.0, 3.0, 20, True), (4.999, 8.0, 3.0, 20, False), (5.0, 7.999, 3.0, 20, False),
    (4.999, 7.999, 3.0, 20, False),
    (10, 8.0, 4.0, 20, False),            # depth must EXCEED twice the thickness (8 == 2*4)
    (10, 8.001, 4.0, 20, True),
    (10, 12, 3.0, 0.001, True), (10, 12, 3.0, 0, False), (10, 12, 3.0, -1, False),
    (0, 12, 3.0, 20, False), (10, 0, 3.0, 20, False), (-5, 12, 3.0, 20, False),
])
def test_chimney_limits(w, d, t, h, ok):
    make = lambda: Chimney(ComponentPosition(0, 0, w, d, 'roof_panel_left'), 35, t, h)
    if ok:
        make()
    else:
        with pytest.raises(GeometryError):
            make()


@pytest.mark.parametrize('width,overhang,ok', [
    (15.0, 3.0, True), (14.999, 3.0, False), (30, 0.0, True), (30, -0.001, False),
])
def test_dormer_limits(width, overhang, ok):
    make = lambda: AdditionalGable(ComponentPosition(0, 0, width, 0, 'roof_panel_left'), 35, 3.0, overhang)
    if ok:
        make()
    else:
        with pytest.raises(GeometryError):
            make()


@pytest.mark.parametrize('theta,phi,width,ok', [
    (35, None, 20, True), (0.001, None, 20, True), (89.999, None, 20, True),
    (0, None, 20, False), (90, None, 20, False), (-5, None, 20, False), (120, None, 20, False),
    (35, 0, 20, False), (35, 90, 20, False), (35, 120, 20, False), (35, 0.001, 20, True),
    (35, None, 0, False), (35, None, -1, False), (35, None, 0.001, True),
])
def test_solve_dormer_input_ranges(theta, phi, width, ok):
    if ok:
        solve_dormer(theta, width, phi)
    else:
        with pytest.raises(ValueError):
            solve_dormer(theta, width, phi)


# ---------------------------------------------------------------- house geometry validation
def test_finger_length_limit_is_a_third_of_the_smallest_edge():
    HouseGeometry(30, 60, 60, 45, 3, 10, 0).validate_geometry()                       # 10 == 30/3: allowed
    with pytest.raises(GeometryError):
        HouseGeometry(30, 60, 60, 45, 3, 10.001, 0).validate_geometry()


def test_flat_roof_angle_is_rejected_but_any_positive_angle_is_not():
    with pytest.raises(GeometryError):
        HouseGeometry(100, 80, 70, 0, 3, 15, 0).validate_geometry()
    HouseGeometry(100, 80, 70, 0.5, 3, 15, 0).validate_geometry()


def test_absurdly_tall_gable_is_rejected():
    # x=y=z=30, t=3: peak = 18*tan(theta); total = 30 + peak must not exceed 5*30
    limit = math.degrees(math.atan((150 - 30) / 18))
    HouseGeometry(30, 30, 30, limit - 0.01, 3, 5, 0).validate_geometry()
    with pytest.raises(GeometryError):
        HouseGeometry(30, 30, 30, limit + 0.01, 3, 5, 0).validate_geometry()


def test_maker_validates_on_construction():
    from house_maker import HouseMaker
    with pytest.raises(GeometryError):
        HouseMaker(length=30, width=60, height=60, finger_length=10.5)


# ---------------------------------------------------------------- wall component placement (margins)
def wall_house(**kw):
    return make_house(length=120, width=100, height=90, material_thickness=3.0, kerf=0.0, **kw)


def test_window_margins_are_exactly_one_thickness():
    h = wall_house()
    t, (pw, ph) = 3.0, h.geometry.get_panel_dimensions()['side_wall_left']
    h.add_window('side_wall_left', t, t, 10, 10)                                      # touching the margin: ok
    for x, y in ((t - EPS, 30), (30, t - EPS)):
        with pytest.raises(PlacementError):
            h.add_window('side_wall_left', x, y, 10, 10)
    h.add_window('side_wall_left', pw - t - 10, 40, 10, 10)                           # right margin exactly
    with pytest.raises(PlacementError):
        h.add_window('side_wall_left', pw - t - 10 + EPS, 60, 10, 10)
    h.add_window('side_wall_left', 60, ph - t - 10, 10, 10)                           # top margin exactly
    with pytest.raises(PlacementError):
        h.add_window('side_wall_left', 80, ph - t - 10 + EPS, 10, 10)


def test_windows_keep_one_thickness_apart():
    def fresh():
        h = wall_house()
        h.add_window('side_wall_left', 30, 30, 10, 10)
        return h
    fresh().add_window('side_wall_left', 43, 30, 10, 10)                              # gap of exactly t to the right: ok
    fresh().add_window('side_wall_left', 30, 43, 10, 10)                              # ... and above: ok
    fresh().add_window('side_wall_left', 17, 30, 10, 10)                              # ... and to the left: ok
    for x, y in ((43 - EPS, 30), (30, 43 - EPS), (17 + EPS, 30), (30, 17 + EPS)):
        with pytest.raises(PlacementError, match='overlaps'):
            fresh().add_window('side_wall_left', x, y, 10, 10)


def test_door_and_window_also_keep_apart():
    h = wall_house()
    h.add_door('gable_wall_front', 40, 3, 12, 30)
    h.add_window('gable_wall_front', 55, 20, 10, 10)                                  # exactly t right of the door
    with pytest.raises(PlacementError, match='overlaps'):
        wall_house_ = wall_house()
        wall_house_.add_door('gable_wall_front', 40, 3, 12, 30)
        wall_house_.add_window('gable_wall_front', 55 - EPS, 20, 10, 10)


def test_gable_window_must_stay_t_below_the_slope():
    g, t, width = wall_house().geometry, 3.0, 10
    x = 20.0
    # both top corners must lie at least t/cos(theta) (measured vertically) below the sloped edge
    below = lambda cx: g.z_kerf + min(cx, g.gable_wall_width - cx) * math.tan(g.theta_rad) - t / math.cos(g.theta_rad)
    top = min(below(x), below(x + width))
    wall_house().add_window('gable_wall_front', x, top - 10, width, 10)               # touching the limit: ok
    with pytest.raises(PlacementError, match='sloped'):
        wall_house().add_window('gable_wall_front', x, top - 10 + EPS, width, 10)
    # mirror image on the other slope
    xr = g.gable_wall_width - x - width
    wall_house().add_window('gable_wall_front', xr, top - 10, width, 10)
    with pytest.raises(PlacementError, match='sloped'):
        wall_house().add_window('gable_wall_front', xr, top - 10 + EPS, width, 10)


# ---------------------------------------------------------------- roof feature placement (margins, keep-outs)
def roof_house(**kw):
    return make_house(length=200, width=140, height=90, material_thickness=3.0, kerf=0.0, **kw)


def test_chimney_edge_margin_includes_the_casing_frame():
    m = 3.0 * 1.05                                            # casing frame = t + clearance/2
    h = roof_house()
    w, hgt = h.geometry.get_panel_dimensions()['roof_panel_left']
    probe = Chimney(ComponentPosition(0, 0, 10, 12, 'roof_panel_left'), h.geometry.theta, 3.0, 20)
    _, _, fw, fd = probe.footprint()
    Y = 75                                                    # below the gable-tab slots, so only the edge margin matters
    top = m + T * math.tan(h.geometry.theta_rad)              # the casing reaches t*tan(theta) further up-slope
    cases = [  # (x, y) of the footprint's top-left at the limit
        (m, Y), (w - m - fw, Y), (60, top), (60, hgt - m - fd),
    ]
    for x, y in cases:
        roof_house().add_chimney('roof_panel_left', x, y, 10, 12, 20)                  # exactly at the limit: ok
    for x, y in ((m - EPS, Y), (w - m - fw + EPS, Y), (60, top - EPS), (60, hgt - m - fd + EPS)):
        with pytest.raises(PlacementError, match='minus a'):
            roof_house().add_chimney('roof_panel_left', x, y, 10, 12, 20)


def test_two_chimneys_may_touch_but_not_overlap_their_casings():
    def pair(second):
        h = roof_house()
        c1 = h.add_chimney('roof_panel_left', 60, 45, 10, 12, 20)
        return h, c1, second(c1)

    def beside(dx):
        return lambda c: (c.footprint()[0] + c.footprint()[2] + 2 * c.casing_margin + dx, c.footprint()[1])

    def below(dy):
        # next chimney's up-slope margin also includes the lean
        return lambda c: (c.footprint()[0], c.footprint()[1] + c.footprint()[3] + 2 * c.casing_margin
                          + c.casing_upslope_extra + dy)

    for place in (beside(0), below(0)):                       # casing frames exactly touching: ok
        h, _, (x, y) = pair(place)
        h.add_chimney('roof_panel_left', x, y, 10, 12, 20)
    for place in (beside(-EPS), below(-EPS)):                 # a hair closer: rejected
        h, _, (x, y) = pair(place)
        with pytest.raises(PlacementError, match='overlaps'):
            h.add_chimney('roof_panel_left', x, y, 10, 12, 20)


def test_dormer_keepout_includes_its_overhang_downslope():
    h = roof_house()
    d1 = h.add_additional_gable('roof_panel_left', 60, 20, 30)
    x, y, w, depth = d1.footprint()
    t, o = 3.0, d1.roof_overhang
    below = y + depth + o + 2 * t                         # footprint + overhang + t (own) + t (next)
    h.add_additional_gable('roof_panel_left', 60, below, 30)                          # exactly touching keep-outs
    with pytest.raises(PlacementError):
        d2 = roof_house()
        d2.add_additional_gable('roof_panel_left', 60, 20, 30)
        d2.add_additional_gable('roof_panel_left', 60, below - EPS, 30)
    h.add_additional_gable('roof_panel_left', 60 + w + 2 * t, 20, 30)                  # beside it, touching
    with pytest.raises(PlacementError):
        d3 = roof_house()
        d3.add_additional_gable('roof_panel_left', 60, 20, 30)
        d3.add_additional_gable('roof_panel_left', 60 + w + 2 * t - EPS, 20, 30)


def test_roof_feature_keepout_clears_the_gable_tab_slots():
    h = roof_house()
    t = 3.0
    (sx0, sy0, sx1, sy1), _ = h.geometry.roof_slot_rects('roof_panel_left')
    probe = Chimney(ComponentPosition(0, 0, 10, 12, 'roof_panel_left'), h.geometry.theta, t, 20)
    _, _, fw, fd = probe.footprint()
    m = probe.casing_margin
    x_ok = sx1 + t + m                                    # slot + its keep-out + casing frame
    y = (sy0 + sy1) / 2 - fd / 2
    h.add_chimney('roof_panel_left', x_ok, y, 10, 12, 20)
    with pytest.raises(PlacementError):
        roof_house().add_chimney('roof_panel_left', x_ok - EPS, y, 10, 12, 20)
    # and from the other side of the slot
    roof_house().add_chimney('roof_panel_left', sx0 - t - m - fw, y, 10, 12, 20) if sx0 - t - m - fw >= m else None


def test_roof_features_need_a_roof_panel():
    h = roof_house()
    for panel in ('floor', 'side_wall_left', 'gable_wall_front'):
        with pytest.raises(PlacementError, match='roof panel'):
            h.add_chimney(panel, 30, 30)
        with pytest.raises(PlacementError, match='roof panel'):
            h.add_additional_gable(panel, 30, 30, 30)


# ---------------------------------------------------------------- layout and path helpers
def test_pack_touching_at_exactly_the_spacing_is_allowed():
    pos = pack([('a', 40, 30), ('b', 40, 30)], sheet_width=82, spacing=2)
    assert pos['b'][1] == pos['a'][1] and abs(pos['b'][0] - pos['a'][0]) == 42      # side by side, exactly 2 apart
    stacked = pack([('a', 40, 30), ('b', 40, 30)], sheet_width=81.999, spacing=2)
    assert stacked['a'][0] == stacked['b'][0] == 0
    assert abs(stacked['b'][1] - stacked['a'][1]) == 32


def test_pack_item_as_wide_as_the_sheet_fits_and_wider_is_an_error():
    assert pack([('a', 100, 10)], 100, 2)['a'] == (0, 0)
    with pytest.raises(GeometryError):
        pack([('a', 100.001, 10)], 100, 2)


def test_pack_orders_tallest_first_then_largest_area_then_input_order():
    pos = pack([('small', 10, 10), ('tall', 10, 50), ('wide', 30, 10), ('twin', 10, 10)], 200, 2)
    assert pos['tall'] == (0, 0)                                   # tallest placed first
    order = sorted(pos, key=lambda n: (pos[n][1], pos[n][0]))
    assert order[0] == 'tall'
    assert pos['wide'][0] < pos['small'][0] < pos['twin'][0] or pos['wide'][1] < pos['small'][1]   # wide before equal-height squares, small before twin


def test_bbox_semantics():
    a, b = BBox(0, 0, 10, 10), BBox(10, 0, 20, 10)
    assert not a.intersects(b) and not b.intersects(a)               # touching is not intersecting
    assert a.intersects(BBox(9.999, 0, 20, 10))
    assert a.inflated(1) == BBox(-1, -1, 11, 11)
    gap = BBox(11, 0, 21, 10)                                          # 1 mm apart
    assert not a.inflated(0.5).intersects(gap.inflated(0.5)) and a.inflated(0.6).intersects(gap.inflated(0.6))
    assert (a.width, a.height) == (10, 10)
    assert union_bbox([a, b]) == BBox(0, 0, 20, 10)


def test_path_parser_handles_every_command():
    sub = parse_path("M 0,0 L 10,0 L 10,5 Z M 20,0 L 30,0")
    assert [len(s) for s in sub] == [3, 2]
    assert parse_path("M 0,0 10,0 10,5")[0][-1].x == 10                # implicit lineto after moveto
    q = parse_path("M 0,0 Q 5,10 10,0")[0]
    assert len(q) == 13 and q[-1].x == pytest.approx(10) and max(p.y for p in q) == pytest.approx(5, abs=0.05)
    c = parse_path("M 0,0 C 0,10 10,10 10,0")[0]
    assert len(c) == 13 and max(p.y for p in c) == pytest.approx(7.5, abs=0.05)
    assert path_bbox("M -2,1 L 8,-3 L 4,9 Z") == BBox(-2, -3, 8, 9)
    with pytest.raises(ValueError):
        path_bbox("")


# ---------------------------------------------------------------- render sizing
def test_item_size_makes_room_for_the_label():
    from house_maker.panel import Panel
    wide_label = Panel('p', 'A very long label here', ['M 0,0 L 10,0 L 10,10 L 0,10 Z'])
    assert item_size(wide_label, False) == (10, 10)
    w, h = item_size(wide_label, True)
    assert w == pytest.approx(len('A very long label here') * CHAR_WIDTH) and h == pytest.approx(10 + LABEL_OFFSET + LABEL_HEIGHT)
    short = Panel('q', 'X', ['M 0,0 L 50,0 L 50,10 L 0,10 Z'])
    assert item_size(short, True)[0] == 50                                   # panel wider than its label


def test_rendered_document_encloses_every_item_plus_the_margin():
    from house_maker.panel import Panel
    a = Panel('a', 'A', ['M 5,5 L 25,5 L 25,15 L 5,15 Z'])
    b = Panel('b', 'B', ['M 0,0 L 10,0 L 10,40 L 0,40 Z'])
    svg, w, h = render_svg([a, b], {'a': (0, 0), 'b': (30, 0)}, include_labels=True)
    assert w == pytest.approx(30 + 10 + 2 * MARGIN)
    assert h == pytest.approx(40 + LABEL_OFFSET + LABEL_HEIGHT + 2 * MARGIN)
    assert f'width="{w:.3f}mm"' in svg and f'height="{h:.3f}mm"' in svg
    _, w0, h0 = render_svg([a, b], {'a': (0, 0), 'b': (30, 0)}, include_labels=False)
    assert (w0, h0) == pytest.approx((40 + 2 * MARGIN, 40 + 2 * MARGIN))


# ---------------------------------------------------------------- keep-outs on every side, every pairing
T = 3.0


def keepout(feature):
    """Independent statement of each feature's keep-out: chimney = footprint + casing frame all round;
    dormer = footprint + t all round, and its roof overhang extends further down the slope."""
    x, y, w, d = feature.footprint()
    if isinstance(feature, Chimney):
        left, up, right, down = feature.casing_margins()
        return (x - left, y - up, x + w + right, y + d + down)
    return (x - T, y - T, x + w + T, y + d + feature.roof_overhang + T)


def reach(kind):
    """(side margin, up-slope margin, down-slope margin, extra reach down-slope) around the footprint."""
    lean = T * math.tan(math.radians(45))                     # roof_house() has the default 45 degree roof
    return {'chimney': (T * 1.05, T * 1.05 + lean, T * 1.05, 0.0), 'dormer': (T, T, T, 3.0)}[kind]


def add(house, kind, x, y):
    if kind == 'chimney':
        return house.add_chimney('roof_panel_left', x, y, 10, 12, 20)
    return house.add_additional_gable('roof_panel_left', x, y, 30)


def footprint_size(kind):
    probe = roof_house()
    c = add(probe, kind, 100, 50)
    _, _, w, d = c.footprint()
    return w, d


@pytest.mark.parametrize('a_kind', ['chimney', 'dormer'])
@pytest.mark.parametrize('b_kind', ['chimney', 'dormer'])
@pytest.mark.parametrize('side', ['right', 'left', 'below', 'above'])
def test_keepouts_touch_but_do_not_overlap_on_every_side(a_kind, b_kind, side):
    wb, db = footprint_size(b_kind)
    mb, mb_up, mb_down, rb = reach(b_kind)

    def place(gap):
        h = roof_house()
        a = add(h, a_kind, 100, 50)
        k = keepout(a)
        x, y = a.footprint()[0], a.footprint()[1]
        if side == 'right':
            x, y = k[2] + mb + gap, a.footprint()[1]
        elif side == 'left':
            x, y = k[0] - mb - wb - gap, a.footprint()[1]
        elif side == 'below':
            x, y = a.footprint()[0], k[3] + mb_up + gap
        else:
            x, y = a.footprint()[0], k[1] - mb_down - db - rb - gap
        return h, x, y

    h, x, y = place(0.0)                                     # keep-outs exactly touching: allowed
    add(h, b_kind, x, y)
    h, x, y = place(-EPS)                                    # a hair closer: refused
    with pytest.raises(PlacementError, match='overlaps'):
        add(h, b_kind, x, y)
    h, x, y = place(1.0)                                     # comfortably apart: allowed
    add(h, b_kind, x, y)


@pytest.mark.parametrize('kind', ['chimney', 'dormer'])
@pytest.mark.parametrize('slot', [0, 1])
def test_keepout_clears_each_gable_slot_on_both_sides(kind, slot):
    """Slot keep-out = the drawn slot grown by one thickness; the feature's own margin comes on top."""
    wb, db = footprint_size(kind)
    mb, mb_up, mb_down, rb = reach(kind)
    h = roof_house()
    sx0, sy0, sx1, sy1 = h.geometry.roof_slot_rects('roof_panel_left')[slot]
    yc = (sy0 + sy1) / 2 - db / 2
    right_of = sx1 + T + mb
    left_of = sx0 - T - mb - wb
    for x, ok in ((right_of, True), (right_of - EPS, False), (left_of, True), (left_of + EPS, False)):
        if x < mb or x + wb > h.geometry.get_panel_dimensions()['roof_panel_left'][0] - mb:
            continue                                         # that side is outside the panel anyway
        if ok:
            add(roof_house(), kind, x, yc)
        else:
            with pytest.raises(PlacementError, match='overlaps'):
                add(roof_house(), kind, x, yc)
    # above and below the slot (slots are tall: use the keep-out in y)
    below = sy1 + T + mb_up
    above = sy0 - T - mb_down - db - rb
    pw = h.geometry.get_panel_dimensions()['roof_panel_left'][0]
    x = max(mb, min(sx0 - wb / 2, pw - mb - wb))          # as close to the slot as the panel allows
    for y, ok in ((below, True), (below - EPS, False), (above, True), (above + EPS, False)):
        if y < mb_up:
            continue
        if ok:
            add(roof_house(), kind, x, y)
        else:
            with pytest.raises(PlacementError, match='overlaps'):
                add(roof_house(), kind, x, y)


@pytest.mark.parametrize('theta', [30, 45, 60])
def test_gable_slope_rule_at_any_angle(theta):
    """Both top corners stay t/cos(theta) below the slope - for steep and shallow roofs alike."""
    def house():
        return make_house(length=120, width=100, height=90, material_thickness=3.0, kerf=0.0, gable_angle=theta)
    g = house().geometry
    width = 10
    below = lambda cx: g.z_kerf + min(cx, g.gable_wall_width - cx) * math.tan(g.theta_rad) - 3.0 / math.cos(g.theta_rad)
    for x in (15.0, g.gable_wall_width - 15.0 - width):
        top = min(below(x), below(x + width))
        house().add_window('gable_wall_front', x, top - 10, width, 10)
        with pytest.raises(PlacementError, match='sloped'):
            house().add_window('gable_wall_front', x, top - 10 + EPS, width, 10)
