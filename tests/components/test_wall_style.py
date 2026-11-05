"""
Decoration components: a wall (or roof) panel with its engraved pattern. The engraving must stay
within the panel's outline, for every architectural style and every roof-tile type.
"""

import pytest

from house_maker import ArchitecturalStyle, ShingleType
from house_maker.svgpath import parse_path
from ..conftest import make_house
from ..geom import bounds, outline

TOL = 0.2          # engraving is jittered/hand-drawn; allow a hair of overshoot


def engraving_bounds(panel):
    pts = [p for sub in parse_path(panel.pattern) for p in sub]
    return bounds(pts) if pts else None


@pytest.mark.parametrize('wall', ['side_wall_left', 'gable_wall_front'])
@pytest.mark.parametrize('style', [s for s in ArchitecturalStyle if s != ArchitecturalStyle.BASIC],
                         ids=lambda s: s.name.lower())
def test_wall_pattern_stays_inside_the_wall(inspect, style, wall):
    house = make_house(architectural_style=style, length=120, width=100, height=90)
    (panel,) = inspect('wall_style', f'{style.name.lower()}_on_{wall}', house, [wall],
                       title=f'{style.name} pattern on {wall}')
    box = engraving_bounds(panel)
    assert box is not None
    ox0, oy0, ox1, oy1 = bounds(outline(panel))
    assert box[0] >= -TOL and box[1] >= -TOL                     # nominal origin is (0, 0)
    assert box[2] <= panel.nominal_size[0] + TOL and box[3] <= panel.nominal_size[1] + TOL


def test_basic_style_has_no_wall_engraving():
    house = make_house()
    assert all(not p.pattern for p in house.build_panels() if 'wall' in p.name)


@pytest.mark.parametrize('shingle', list(ShingleType), ids=lambda s: s.name.lower())
def test_roof_tiles_stay_inside_the_roof_panel(inspect, shingle):
    house = make_house(shingle_type=shingle)
    (panel,) = inspect('roof_tiles', shingle.name.lower(), house, ['roof_panel_left'],
                       title=f'{shingle.name} tiles on the left roof panel')
    box = engraving_bounds(panel)
    assert box is not None
    assert box[0] >= -TOL and box[1] >= -TOL
    assert box[2] <= panel.nominal_size[0] + TOL and box[3] <= panel.nominal_size[1] + TOL


def test_chimney_brick_stays_inside_each_chimney_wall(inspect):
    house = make_house(chimneys=[('roof_panel_left', 25, 30, 14, 20, 30)])
    walls = inspect('chimney', 'brick_pattern', house, [lambda n: n.startswith('chimney_') and 'casing' not in n],
                    title='Brick engraving on the four chimney walls')
    for wall in walls:
        box = engraving_bounds(wall)
        assert box is not None
        x0, y0, x1, y1 = bounds(wall.corners)
        assert box[0] >= x0 - TOL and box[1] >= y0 - TOL and box[2] <= x1 + TOL and box[3] <= y1 + TOL
