"""Door component: a wall with one door cut-out, plus the door casing (3-sided frame)."""

import pytest

from house_maker import DoorType
from house_maker.svgpath import parse_path
from ..conftest import make_house
from ..geom import bounds, holes, outline, point_in_polygon

TOL = 5e-3


@pytest.fixture(params=list(DoorType), ids=lambda t: t.name.lower())
def scene(request, inspect):
    dtype = request.param
    house = make_house(length=120, width=100, height=90)
    wall = 'gable_wall_front'
    width, height = house.architectural_config.get_recommended_door_dimensions(wall)
    x = (house.geometry.get_panel_dimensions()[wall][0] - width) / 2
    door = house.add_door(wall, x, house.geometry.thickness, door_type=dtype)
    panels = inspect('door', f"{dtype.name.lower()}_on_{wall}", house,
                     [wall, lambda n: n.startswith(f'{wall}_d0_door_casing')],
                     title=f'{dtype.name} door: wall with cut-out + casing')
    return dict(type=dtype, door=door, house=house, p={q.name: q for q in panels}, wall=wall,
                k=house.geometry.kerf)


def test_cutout_inside_wall_and_sized_like_the_door(scene):
    wall, d = scene['p'][scene['wall']], scene['door'].position
    cut = holes(wall)
    outer = outline(wall)
    for hole in cut:
        assert all(point_in_polygon((p.x, p.y), outer) for p in hole)
    x0, y0, x1, y1 = bounds([p for hole in cut for p in hole])
    h = scene['k'] / 2                                   # a hole is drawn kerf/2 smaller on each side
    assert (x0, x1) == pytest.approx((d.x + h, d.x + d.width - h), abs=TOL)
    assert y0 == pytest.approx(d.y + h, abs=TOL)
    if scene['type'] in (DoorType.RECTANGULAR, DoorType.DOUBLE, DoorType.DUTCH):
        assert y1 == pytest.approx(d.y + d.height - h, abs=TOL)
    assert len(cut) == {DoorType.DOUBLE: 2, DoorType.DUTCH: 2}.get(scene['type'], 1)


def test_casing_is_a_u_frame_around_the_door_width(scene):
    (name,) = [n for n in scene['p'] if n.endswith('door_casing')]
    casing, d = scene['p'][name], scene['door'].position
    t = scene['house'].geometry.thickness
    # outer width = door + two posts (1.5t) + two tabs (0.6t); open at the bottom so a single outline
    k = scene['k']                                       # the frame is a part: drawn kerf larger than the cut size
    assert casing.nominal_size[0] == pytest.approx(d.width + 2 * 1.5 * t + 2 * 0.6 * t + k, abs=TOL)
    assert len(parse_path(casing.cut[0])) == 1
    if scene['type'] != DoorType.ARCHED:
        assert casing.nominal_size[1] == pytest.approx(d.height + 1.5 * 1.5 * t + k, abs=TOL)
