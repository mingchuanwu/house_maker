"""Placement rules: what the configuration accepts and rejects, and automatic placement quality."""

import itertools

import pytest

from house_maker import PlacementError, WindowType
from house_maker.svgpath import path_bbox
from .conftest import make_house
from .geom import outline, holes, point_in_polygon


def test_features_cannot_overlap_or_leave_panel():
    house = make_house(length=160, width=120, height=90)
    house.add_chimney('roof_panel_left', 30, 30)
    with pytest.raises(PlacementError):
        house.add_chimney('roof_panel_left', 33, 33)               # overlaps first chimney
    with pytest.raises(PlacementError):
        house.add_additional_gable('roof_panel_left', 30, 30, 30)  # overlaps chimney
    with pytest.raises(PlacementError):
        house.add_chimney('roof_panel_left', 0, 0)                 # outside margin
    with pytest.raises(PlacementError):
        house.add_chimney('side_wall_left', 30, 30)                # not a roof panel
    with pytest.raises(PlacementError):
        house.add_chimney('roof_panel_left', 8, 38)                # on top of a gable tab slot
    house.add_additional_gable('roof_panel_left', 90, 30, 30)      # elsewhere is fine
    house.add_chimney('roof_panel_right', 30, 30)                  # the other panel is independent
    assert len(house.architectural_config.chimneys) == 2


CASES = [dict(gable_angle=a, length=l, width=w, height=h)
         for a, (l, w, h) in itertools.product((30, 45, 60), [(100, 80, 70), (160, 120, 140)])]


@pytest.mark.parametrize('window_type', list(WindowType))
@pytest.mark.parametrize('case', CASES, ids=lambda c: f"a{c['gable_angle']}-{c['length']}x{c['width']}x{c['height']}")
def test_automatic_cutouts_inside_walls_and_clear_of_each_other(case, window_type):
    house = make_house(auto_add_components=True, window_type=window_type, **case)
    for panel in house.build_panels():
        if 'wall' not in panel.name or 'casing' in panel.name:
            continue
        outer = outline(panel)
        for hole in holes(panel):
            assert all(point_in_polygon((p.x, p.y), outer) for p in hole), f"{panel.name}: cutout leaves the wall"
        boxes = [path_bbox(d) for d in panel.cut[1:]]
        for a, b in itertools.combinations(boxes, 2):
            assert not a.intersects(b), f"{panel.name}: cutouts overlap"
