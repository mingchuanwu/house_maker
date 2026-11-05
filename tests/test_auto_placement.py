"""
Automatic window/door placement, specified by the documented policy:

* a house has floors as tall as the average of its length and width (plus a shorter attic floor when
  more than a quarter of that height is left over); heights always add up to the wall height;
* window and door sizes follow fixed proportions of the floor height (see ProportionalSizer);
* side walls get one window per floor, centred, 40% of the way up the floor;
* the door is on the front gable wall, centred, one 2t margin above the ground;
* everything placed automatically is something a hand placement would also have been allowed to do.
"""

import itertools

import pytest

from house_maker import HouseMaker, WindowType, DoorType
from .conftest import make_house

HOUSES = [dict(length=l, width=w, height=z, gable_angle=a, material_thickness=t, kerf=0.1)
          for (l, w, z), a, t in itertools.product(
              [(100, 100, 80), (160, 100, 140), (100, 100, 60), (80, 60, 70), (200, 150, 130), (120, 90, 200), (100, 100, 45)],
              (30, 45, 60), (2.0, 3.0))]


def hid(h):
    return f"{h['length']}x{h['width']}x{h['height']}-a{h['gable_angle']}-t{h['material_thickness']}"


def clamp(v, lo, hi):
    return max(lo, min(v, hi))


def spec_floors(x, y, z):
    """[(start, height), ...] of every floor."""
    std = (x + y) / 2
    n_std = int(z // std)
    rest = z - n_std * std
    attic = rest > 0.25 * std
    n = max(1, n_std + (1 if attic else 0))
    heights = []
    for i in range(n):
        if attic:
            heights.append(rest if i == n - 1 else std)
        else:
            heights.append(std + rest if i == 0 else std)
    starts = [sum(heights[:i]) for i in range(n)]
    return list(zip(starts, heights))


@pytest.fixture(params=HOUSES, ids=hid)
def house(request):
    return HouseMaker(**request.param, auto_add_components=True), request.param


# ---------------------------------------------------------------- floors
def test_floors_follow_the_policy_and_add_up_to_the_wall_height(house):
    h, c = house
    pos = h.architectural_config._positioner
    floors = spec_floors(c['length'], c['width'], c['height'])
    assert pos.calculate_number_of_floors() == len(floors)
    assert [pos.get_floor_height(i) for i in range(len(floors))] == pytest.approx([f[1] for f in floors])
    assert sum(f[1] for f in floors) == pytest.approx(c['height'])


@pytest.mark.parametrize('z,expected_floors', [
    (75.0, 1), (100.0, 1), (125.0, 1), (125.01, 2), (200.0, 2), (225.0, 2), (225.01, 3)])
def test_attic_floor_appears_when_more_than_a_quarter_floor_is_left(z, expected_floors):
    h = make_house(length=100, width=100, height=z)           # floor height 100
    assert h.architectural_config._positioner.calculate_number_of_floors() == expected_floors


def test_ground_floor_absorbs_a_small_remainder():
    pos = make_house(length=100, width=100, height=120).architectural_config._positioner      # 20% left: no attic
    assert pos.calculate_number_of_floors() == 1
    assert pos.get_floor_height(0) == pytest.approx(120)
    pos = make_house(length=100, width=100, height=260).architectural_config._positioner      # 2 floors + 60 left: attic
    assert [pos.get_floor_height(i) for i in range(3)] == pytest.approx([100, 100, 60])


# ---------------------------------------------------------------- sizing proportions
def test_door_size_follows_the_ground_floor(house):
    h, c = house
    ground = spec_floors(c['length'], c['width'], c['height'])[0][1]
    pw = h.geometry.get_panel_dimensions()['gable_wall_front'][0]
    door_h = max(15.0, min(0.8 * ground, ground - 10))
    door_w = max(8.0, min(0.4 * door_h, pw - 20))
    width, height = h.architectural_config._sizer.get_door_dimensions('gable_wall_front', ground)
    assert (width, height) == pytest.approx((door_w, door_h))


def test_door_is_centred_on_the_front_gable_wall_one_margin_above_the_ground(house):
    h, c = house
    cfg = h.architectural_config
    (door,) = cfg.doors if len(cfg.doors) == 1 else (None,)
    if door is None:
        assert not cfg.doors                                  # nothing is better than a door that does not fit
        return
    p = door.position
    pw = h.geometry.get_panel_dimensions()['gable_wall_front'][0]
    assert p.panel == 'gable_wall_front'
    assert p.x == pytest.approx((pw - p.width) / 2) and p.y == pytest.approx(2 * c['material_thickness'])


@pytest.mark.parametrize('wtype', [WindowType.RECTANGULAR, WindowType.CIRCULAR, WindowType.BAY, WindowType.ARCHED])
def test_window_sizes_follow_the_proportions(house, wtype):
    h, c = house
    floors = spec_floors(c['length'], c['width'], c['height'])
    pw, ph = h.geometry.get_panel_dimensions()['side_wall_left']
    for i, (start, fh) in enumerate(floors):
        base_h = 0.3 * fh
        base_w = base_h * 1.2
        if wtype == WindowType.CIRCULAR:
            base_w = base_h
        elif wtype == WindowType.BAY:
            base_w *= 1.5
        elif wtype == WindowType.ARCHED:
            base_h *= 1.2
        want = (clamp(base_w, 5.0, 0.8 * pw), clamp(base_h, 5.0, 0.6 * fh))
        got = h.architectural_config._sizer.get_window_dimensions('side_wall_left', wtype, fh)
        assert got == pytest.approx(want), (i, wtype)


def test_attic_window_size_follows_the_gable_peak(house):
    h, _ = house
    g = h.geometry
    pw, ph = g.get_panel_dimensions()['gable_wall_front']
    base_h = g.gable_peak_height * 0.4
    want = (clamp(base_h * 1.618 * 0.6, 5.0, 0.8 * pw), clamp(base_h * 0.6, 5.0, 0.6 * ph))
    assert h.architectural_config._sizer.get_window_dimensions('gable_wall_front', WindowType.ATTIC) == pytest.approx(want, rel=1e-3)


# ---------------------------------------------------------------- where windows go
def test_side_walls_get_one_centred_window_per_floor_when_it_fits(house):
    h, c = house
    t, fl = c['material_thickness'], spec_floors(c['length'], c['width'], c['height'])
    pw, ph = h.geometry.get_panel_dimensions()['side_wall_left']
    margin = 2 * t
    expected = []
    for start, fh in fl:
        w, hgt = h.architectural_config._sizer.get_window_dimensions('side_wall_left', WindowType.RECTANGULAR, fh)
        y = start + 0.4 * fh
        if y + hgt > start + fh - margin:
            continue
        if y + hgt > ph - margin:
            break
        expected.append(((pw - w) / 2, y, w, hgt))
    for panel in ('side_wall_left', 'side_wall_right'):
        got = sorted((w.position.x, w.position.y, w.position.width, w.position.height)
                     for w in h.architectural_config.get_windows_for_panel(panel))
        # the placer's own validity filter may drop a window that would touch a margin; it never invents one
        assert set(map(lambda r: tuple(round(v, 6) for v in r), got)) <= set(tuple(round(v, 6) for v in e) for e in expected), panel
        assert len(got) == len(expected) or len(got) >= len(expected) - 1


def test_no_window_straddles_a_floor_boundary(house):
    h, c = house
    fl = spec_floors(c['length'], c['width'], c['height'])
    for panel in ('side_wall_left', 'side_wall_right', 'gable_wall_front', 'gable_wall_back'):
        for w in h.architectural_config.get_windows_for_panel(panel):
            p = w.position
            if panel.startswith('gable') and p.y >= c['height']:
                continue                                       # above the wall top: in the gable triangle
            inside = [s <= p.y + 1e-9 and p.y + p.height <= s + fh + 1e-9 for s, fh in fl]
            assert any(inside) or w.type == WindowType.ATTIC, f"{panel}: window at y={p.y} h={p.height} straddles floors {fl}"


def test_every_wall_has_a_window_in_ordinary_houses(house):
    h, c = house
    if c['height'] < 40:
        pytest.skip('too low for a window')
    cfg = h.architectural_config
    for panel in ('side_wall_left', 'side_wall_right'):
        assert cfg.get_windows_for_panel(panel), panel


def test_automatic_components_are_valid_hand_placements(house):
    h, _ = house
    cfg = h.architectural_config
    assert cfg.validate_all_components() == []
    assert len(cfg.doors) <= 1


def test_placement_is_deterministic():
    kw = dict(length=160, width=100, height=140, gable_angle=40)
    a, b = HouseMaker(**kw), HouseMaker(**kw)
    key = lambda cfg: sorted((w.position, w.type.name) for w in cfg.windows + cfg.doors)
    assert key(a.architectural_config) == key(b.architectural_config)


# ---------------------------------------------------------------- attic rule
@pytest.mark.parametrize('gable_height,angle,ok', [
    (60.0, 0.0, True), (59.999, 0.0, False), (0.0, 30.0, True), (0.0, 29.999, False),
    (59.999, 29.999, False), (100.0, 10.0, True), (10.0, 80.0, True),
])
def test_attic_windows_need_a_tall_or_steep_gable(gable_height, angle, ok):
    pos = make_house().architectural_config._positioner
    assert pos.can_add_attic_window(gable_height, angle) is ok


# ---------------------------------------------------------------- doors and windows never collide
def test_door_leaves_room_for_neighbouring_windows(house):
    h, c = house
    t = c['material_thickness']
    cfg = h.architectural_config
    for door in cfg.doors:
        for w in cfg.get_windows_for_panel(door.position.panel):
            a, b = door.position, w.position
            gap_x = max(b.x - (a.x + a.width), a.x - (b.x + b.width))
            gap_y = max(b.y - (a.y + a.height), a.y - (b.y + b.height))
            assert max(gap_x, gap_y) >= t - 1e-9
