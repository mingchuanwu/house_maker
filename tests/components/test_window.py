"""
Window component: a wall panel with one window cut-out, plus that window's casing (trim frame).
One case per window type, on a side wall and on a gable wall.
"""

import pytest

from house_maker import WindowType
from house_maker.svgpath import parse_path
from ..conftest import make_house
from ..geom import bounds, holes, outline, point_in_polygon

TOL = 5e-3
# Types whose cut-out and casing opening are plain rectangles of the window's size
RECTANGULAR_TYPES = {WindowType.RECTANGULAR, WindowType.CASEMENT, WindowType.BAY, WindowType.ATTIC}
WALLS = [('side_wall_left', 40, 25), ('gable_wall_front', 30, 30)]


@pytest.fixture(params=[(t, w) for t in WindowType for w in WALLS],
                ids=lambda p: f"{p[0].name.lower()}-{p[1][0]}")
def scene(request, inspect):
    wtype, (wall, x, y) = request.param
    house = make_house(length=120, width=100, height=90)
    window = house.add_window(wall, x, y, window_type=wtype)
    panels = inspect('window', f"{wtype.name.lower()}_on_{wall}", house,
                     [wall, lambda n: n.startswith(f'{wall}_w0_window_casing')],
                     title=f'{wtype.name} window on {wall}: wall with cut-out + casing')
    return dict(type=wtype, wall=wall, window=window, house=house, p={q.name: q for q in panels},
                k=house.geometry.kerf)


def test_cutout_lies_inside_the_wall_and_inside_the_window_rectangle(scene):
    wall, w = scene['p'][scene['wall']], scene['window'].position
    cut = holes(wall)
    assert cut
    outer = outline(wall)
    for hole in cut:
        assert all(point_in_polygon((p.x, p.y), outer) for p in hole)
    x0, y0, x1, y1 = bounds([p for hole in cut for p in hole])
    h = scene['k'] / 2                         # a hole is drawn kerf/2 smaller on each side; the laser opens it up
    assert x0 >= w.x + h - TOL and y0 >= w.y + h - TOL and x1 <= w.x + w.width - h + TOL and y1 <= w.y + w.height - h + TOL
    if scene['type'] in RECTANGULAR_TYPES:
        assert (x0, y0, x1, y1) == pytest.approx((w.x + h, w.y + h, w.x + w.width - h, w.y + w.height - h), abs=TOL)


def test_casing_opening_matches_the_window(scene):
    casings = [n for n in scene['p'] if n.endswith('window_casing')]
    if scene['type'] == WindowType.ATTIC:
        assert not casings                      # attic windows are too small for a casing
        return
    (name,) = casings
    casing, w = scene['p'][name], scene['window'].position
    subpaths = parse_path(casing.cut[0])
    assert len(subpaths) == 2                   # frame outline + opening
    x0, y0, x1, y1 = bounds(subpaths[1])
    t, k = scene['house'].geometry.thickness, scene['k']
    ow, oh = (x1 - x0) + k, (y1 - y0) + k      # the opening as cut: drawn kerf smaller (a hole)
    if scene['type'] == WindowType.CIRCULAR:
        assert (ow, oh) == pytest.approx((min(w.width, w.height),) * 2, abs=TOL)
    elif scene['type'] == WindowType.ARCHED:
        assert ow == pytest.approx(w.width, abs=TOL)
        assert 0.7 * w.height <= oh <= w.height + TOL
    else:
        assert (ow, oh) == pytest.approx((w.width, w.height), abs=TOL)
    # the frame is at least one material thickness wide at the sides ...
    ox0, oy0, ox1, oy1 = bounds(subpaths[0])
    assert (x0 - ox0) >= t - TOL and (ox1 - x1) >= t - TOL
    # ... and across the top/bottom (for an arched casing this includes the apex)
    assert (oy1 - y1) >= t - TOL and (y0 - oy0) >= t - TOL


def test_casing_score_lines_stay_inside_the_frame(scene):
    for name, casing in scene['p'].items():
        if name.endswith('window_casing') and casing.score:
            fx0, fy0, fx1, fy1 = bounds(outline(casing))
            sx0, sy0, sx1, sy1 = bounds([p for d in casing.score for sub in parse_path(d) for p in sub])
            assert sx0 >= fx0 - TOL and sy0 >= fy0 - TOL and sx1 <= fx1 + TOL and sy1 <= fy1 + TOL
