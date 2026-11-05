"""Defaults, error messages and small behaviours that callers rely on (each pinned so a change is deliberate)."""

import dataclasses
import math

import pytest

from house_maker import HouseMaker, PlacementError, WindowType, DoorType
from house_maker.components import AdditionalGable, Chimney, ComponentPosition, Door, Window
from house_maker.dormer_geometry import solve_dormer
from house_maker.exceptions import GeometryError
from house_maker.layout import pack
from .conftest import make_house


# ---------------------------------------------------------------- messages distinguish the reason
@pytest.mark.parametrize('cls,kind,args', [(Window, WindowType.RECTANGULAR, ()), (Door, DoorType.RECTANGULAR, ())])
def test_zero_and_negative_sizes_are_reported_as_non_positive_and_small_ones_as_too_small(cls, kind, args):
    pos = lambda w, h: ComponentPosition(10, 10, w, h, 'side_wall_left')
    for w, h in ((0, 20), (20, 0), (-1, 20), (20, -1)):
        with pytest.raises(GeometryError, match='positive'):
            cls(kind, pos(w, h))
    with pytest.raises(GeometryError, match='too small'):
        cls(kind, pos(1, 1))


def test_chimney_and_dormer_report_non_positive_sizes_distinctly():
    with pytest.raises(GeometryError, match='positive'):
        Chimney(ComponentPosition(0, 0, 0, 12, 'roof_panel_left'), 35, 3.0)
    with pytest.raises(GeometryError, match='positive'):
        Chimney(ComponentPosition(0, 0, 10, -2, 'roof_panel_left'), 35, 3.0)
    with pytest.raises(GeometryError, match='too small'):
        Chimney(ComponentPosition(0, 0, 4, 12, 'roof_panel_left'), 35, 3.0)
    with pytest.raises(GeometryError, match='too small'):
        AdditionalGable(ComponentPosition(0, 0, 10, 0, 'roof_panel_left'), 35, 3.0)


def test_dormer_angle_ranges_are_checked_independently():
    with pytest.raises(ValueError):
        solve_dormer(120, 20, phi_deg=45)          # the main roof angle alone is invalid
    with pytest.raises(ValueError):
        solve_dormer(35, 20, phi_deg=120)          # the dormer pitch alone is invalid
    solve_dormer(89.9, 20, phi_deg=45)


# ---------------------------------------------------------------- defaults
def test_documented_defaults():
    house = HouseMaker()
    g = house.geometry
    assert (g.x, g.y, g.z, g.theta, g.thickness, g.finger_length, g.kerf) == (100, 100, 80, 45, 3, 15, 0.1)
    cfg = house.architectural_config
    assert cfg.architectural_style.value == 'basic' and cfg.shingle_type.value == 'shingles' and cfg.stone_jitter is True
    assert cfg.windows and cfg.doors                                        # auto components are on by default
    assert not cfg.chimneys and not cfg.additional_gables


def test_default_chimney_and_dormer_sizes():
    h = make_house(length=200, width=140, height=90)
    c = h.add_chimney('roof_panel_left', 60, 70)
    assert (c.position.width, c.position.height, c.chimney_height) == (8.0, 12.0, 20.0)
    d = h.add_additional_gable('roof_panel_left', 120, 30)
    assert d.position.width == 25.0 and d.roof_overhang == 3.0


def test_set_style_defaults_to_jittered_stone_and_can_turn_it_off():
    cfg = make_house().architectural_config
    cfg.set_style(cfg.architectural_style)
    assert cfg.stone_jitter is True
    cfg.set_style(cfg.architectural_style, stone_jitter=False)
    assert cfg.stone_jitter is False


def test_automatic_components_flags():
    cfg = make_house().architectural_config
    cfg.add_automatic_components()
    assert cfg.doors and cfg.windows
    cfg.clear_components()
    cfg.add_automatic_components(add_doors=False)
    assert not cfg.doors and cfg.windows
    cfg.clear_components()
    cfg.add_automatic_components(add_windows=False)
    assert cfg.doors and not cfg.windows
    cfg.clear_components()
    cfg.add_automatic_components(door_panel='no_such_panel')
    assert not cfg.doors                                                    # unknown door panel: no door, no crash


def test_attic_windows_only_on_gable_walls():
    h = HouseMaker(length=100, width=100, height=70, gable_angle=45)
    cfg = h.architectural_config
    attic = [w for w in cfg.windows if w.type == WindowType.ATTIC]
    assert attic and all(w.position.panel.startswith('gable_wall') for w in attic)
    assert not [w for w in cfg.windows if w.type == WindowType.ATTIC and w.position.panel.startswith('side_wall')]


def test_a_size_given_for_only_one_dimension_is_respected():
    h = make_house(length=120, width=100, height=90)
    default_w, default_h = h.architectural_config.get_recommended_window_dimensions('side_wall_left')
    w = h.add_window('side_wall_left', 30, 30, width=14.0)                  # height omitted
    assert w.position.width == 14.0 and w.position.height == pytest.approx(default_h)
    w = h.add_window('side_wall_left', 60, 30, height=11.0)                 # width omitted
    assert w.position.height == 11.0 and w.position.width == pytest.approx(default_w)
    d = h.add_door('gable_wall_front', 40, 3, width=13.0)
    assert d.position.width == 13.0 and d.position.height == pytest.approx(
        h.architectural_config.get_recommended_door_dimensions('gable_wall_front')[1])


def test_component_summary_flags_decorative_patterns():
    from house_maker import ArchitecturalStyle
    assert make_house().architectural_config.get_component_summary()['has_decorative_patterns'] is False
    assert make_house(architectural_style=ArchitecturalStyle.BRICK).architectural_config.get_component_summary()['has_decorative_patterns'] is True


def test_non_gable_roofs_warn_with_the_caller_as_the_source():
    from house_maker import RoofType
    with pytest.warns(UserWarning) as rec:
        HouseMaker(roof_type=RoofType.HIP)
    assert rec[0].filename.endswith('test_contracts.py')                    # stacklevel points at the caller


def test_ignored_dormer_depth_warns_at_the_caller():
    h = make_house()
    with pytest.warns(UserWarning) as rec:
        h.add_additional_gable('roof_panel_left', 30, 30, 25, 50.0)
    assert rec[0].filename.endswith('test_contracts.py')


# ---------------------------------------------------------------- immutability of value objects
def test_value_objects_are_frozen():
    geo = solve_dormer(35, 20)
    with pytest.raises(dataclasses.FrozenInstanceError):
        geo.width = 1
    from house_maker.mates import Mate
    with pytest.raises(dataclasses.FrozenInstanceError):
        Mate('edge', ('a', 'b'), ('c', 'd')).shift = 1


def test_dormer_roof_panel_outline_default_is_the_left_panel():
    geo = solve_dormer(35, 30, overhang=3)
    assert geo.roof_panel_outline() == geo.roof_panel_outline(mirrored=False)
    assert geo.roof_panel_outline() != geo.roof_panel_outline(mirrored=True)
    assert geo.roof_panel_ridge_length == pytest.approx(geo.ridge + 3)
    assert solve_dormer(35, 30).overhang == 0.0


# ---------------------------------------------------------------- layout details
def test_equal_height_items_are_placed_largest_area_first():
    pos = pack([('small', 10, 10), ('wide', 30, 10)], 200, 2)
    assert pos['wide'] == (0, 0) and pos['small'][0] == 32


def test_packing_is_tight_gaps_equal_the_spacing():
    items = [('a', 40, 30), ('b', 40, 20), ('c', 20, 50), ('d', 30, 30)]
    pos = pack(items, 120, 2)
    rects = {n: (pos[n][0], pos[n][1], w, h) for n, w, h in items}
    gaps = []
    for n1, (x1, y1, w1, h1) in rects.items():
        for n2, (x2, y2, w2, h2) in rects.items():
            if n1 < n2:
                gx = max(x2 - (x1 + w1), x1 - (x2 + w2))
                gy = max(y2 - (y1 + h1), y1 - (y2 + h2))
                gaps.append(max(gx, gy))
    assert min(gaps) == pytest.approx(2.0)                                  # never closer, and tight somewhere
    assert all(g >= 2.0 - 1e-9 for g in gaps)


# ---------------------------------------------------------------- kerf offset of polygons
def test_offset_polygon_on_known_shapes():
    from house_maker.geometry import Point, edge_shifts, offset_polygon
    rect = [Point(0, 0), Point(10, 0), Point(10, 5), Point(0, 5)]
    out = offset_polygon(rect, 0.5)
    assert [(round(p.x, 9), round(p.y, 9)) for p in out] == [(-0.5, -0.5), (10.5, -0.5), (10.5, 5.5), (-0.5, 5.5)]
    assert [v for p in offset_polygon(out, -0.5) for v in p] == pytest.approx([v for p in rect for v in p])      # inverse
    assert edge_shifts(rect, out) == pytest.approx([-0.5] * 4)
    # right triangle (3-4-5): every edge moves out by d, so the inradius grows by d
    tri = [Point(0, 0), Point(4, 0), Point(0, 3)]
    big = offset_polygon(tri, 1.0)
    area = lambda P: abs(sum(a.x * b.y - b.x * a.y for a, b in zip(P, P[1:] + P[:1]))) / 2
    per = lambda P: sum(((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5 for a, b in zip(P, P[1:] + P[:1]))
    r = area(tri) / (per(tri) / 2)                                  # inradius = 1
    assert per(big) == pytest.approx(per(tri) * (r + 1.0) / r, rel=1e-9)     # similar triangle, inradius r + d
    # a slanted edge moves out PERPENDICULAR to itself
    trap = [Point(0, 0), Point(12, 6), Point(12, 26), Point(0, 26)]
    off = offset_polygon(trap, 0.1)
    nx, ny = 6 / (12 ** 2 + 6 ** 2) ** 0.5, -12 / (12 ** 2 + 6 ** 2) ** 0.5
    d = (off[1].x - trap[1].x) * nx + (off[1].y - trap[1].y) * ny
    assert d == pytest.approx(0.1)


def test_offset_handles_collinear_vertices_but_not_doubling_back():
    from house_maker.geometry import Point, offset_polygon
    out = offset_polygon([Point(0, 0), Point(1, 0), Point(2, 0), Point(2, 1), Point(0, 1)], 0.1)   # (1, 0) is collinear
    assert [(round(p.x, 9), round(p.y, 9)) for p in out] == [(-0.1, -0.1), (1.0, -0.1), (2.1, -0.1), (2.1, 1.1), (-0.1, 1.1)]
    with pytest.raises(GeometryError):
        offset_polygon([Point(0, 0), Point(2, 0), Point(1, 0), Point(1, 1)], 0.1)          # edge doubles back
    with pytest.raises(GeometryError):
        offset_polygon([Point(0, 0), Point(0, 0), Point(1, 0), Point(1, 1)], 0.1)          # zero-length edge
