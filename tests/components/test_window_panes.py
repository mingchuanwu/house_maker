"""
Rectangular windows look like windows: the wall opening is cut as a grid of panes, with glazing bars of wall material
one thickness wide. 3 columns (rows) from 30 mm wide (tall), else 2; panes at least 2t; too small for 2 x 2 = one pane.
"""

import pytest

from house_maker import WindowType
from house_maker.cutouts import PANE_SPLIT, pane_grid
from house_maker.svgpath import parse_path
from ..conftest import make_house

T = 3.0


@pytest.mark.parametrize('w,h,grid', [
    (25.2, 21.0, (2, 2)),                 # the 80x60x70 house's windows
    (29.99, 29.99, (2, 2)), (30.0, 21.0, (3, 2)), (21.0, 30.0, (2, 3)), (50.4, 42.0, (3, 3)),
    (14.9, 20, (1, 1)), (15.0, 15.0, (2, 2)),          # 2 panes need 2 * 2t + t = 15 mm
    (30.0, 20, (3, 2)),                   # 3 panes of (30 - 2t) / 3 = 8 mm >= 2t
    (12.8, 7.9, (1, 1)),                  # small gable window: one pane
])
def test_grid_follows_the_size_thresholds(w, h, grid):
    assert PANE_SPLIT == 30.0
    assert pane_grid(w, h, T) == grid


def test_three_falls_back_to_two_when_panes_would_be_too_small():
    # 30 mm with 3 mm bars: 3 panes of 8 mm would be fine (>= 6); with 5 mm bars 3 panes of 6.67 < 10 -> 2 of 12.5
    assert pane_grid(30, 30, 3.0) == (3, 3)
    assert pane_grid(30, 30, 5.0) == (2, 2)


@pytest.mark.parametrize('kerf', [0.0, 0.1])
@pytest.mark.parametrize('size,grid', [((25.2, 21.0), (2, 2)), ((36.0, 21.0), (3, 2)), ((24.0, 33.0), (2, 3)),
                                       ((40.0, 40.0), (3, 3))])
def test_panes_fill_the_opening_with_t_wide_bars(kerf, size, grid):
    house = make_house(length=160, width=120, height=100, material_thickness=T, kerf=kerf)
    win = house.add_window('side_wall_left', 50, 30, *size)
    wall = {p.name: p for p in house.build_panels()}['side_wall_left']
    p = win.position
    holes = [sub for d in wall.cut[1:] for sub in parse_path(d)]
    boxes = sorted((min(q.x for q in s), min(q.y for q in s), max(q.x for q in s), max(q.y for q in s)) for s in holes)
    cols, rows = grid
    assert len(boxes) == cols * rows
    h = kerf / 2                                         # each pane is a hole: drawn kerf/2 smaller on every side
    xs, ys = sorted({b[0] for b in boxes}), sorted({b[1] for b in boxes})
    assert len(xs) == cols and len(ys) == rows
    # the panes span exactly the opening, equal in size, and the bars between them are t wide (after cutting)
    assert min(b[0] for b in boxes) == pytest.approx(p.x + h, abs=1e-3)
    assert max(b[2] for b in boxes) == pytest.approx(p.x + p.width - h, abs=1e-3)
    assert min(b[1] for b in boxes) == pytest.approx(p.y + h, abs=1e-3)
    assert max(b[3] for b in boxes) == pytest.approx(p.y + p.height - h, abs=1e-3)
    widths, heights = [b[2] - b[0] for b in boxes], [b[3] - b[1] for b in boxes]
    assert max(widths) - min(widths) < 2e-3 and max(heights) - min(heights) < 2e-3     # equal (to drawn precision)
    pane_w, pane_h = widths[0] + 2 * h, heights[0] + 2 * h
    assert (p.width - cols * pane_w) / (cols - 1) == pytest.approx(T, abs=2e-3)
    assert (p.height - rows * pane_h) / (rows - 1) == pytest.approx(T, abs=2e-3)


def test_other_window_types_keep_their_shapes():
    house = make_house(length=160, width=120, height=100, material_thickness=T)
    house.add_window('side_wall_left', 20, 30, 30, 30, window_type=WindowType.ARCHED)
    house.add_window('side_wall_left', 80, 30, 30, 30, window_type=WindowType.CIRCULAR)
    wall = {p.name: p for p in house.build_panels()}['side_wall_left']
    assert len(wall.cut) == 3                              # outline + one hole per window


def test_the_casing_opening_frames_the_panes():
    """The casing's inner opening is the full window rectangle: the outer panes' corners are its corners."""
    house = make_house(length=160, width=120, height=100, material_thickness=T)
    win = house.add_window('side_wall_left', 50, 30, 40, 40)
    p = {q.name: q for q in house.build_panels()}
    casing = p['side_wall_left_w0_window_casing']
    (opening,) = parse_path(casing.cut[0])[1:]
    w = max(q.x for q in opening) - min(q.x for q in opening)
    h = max(q.y for q in opening) - min(q.y for q in opening)
    k = house.geometry.kerf                                # the opening is a hole in a cut part: drawn kerf smaller
    assert (w + k, h + k) == pytest.approx((win.position.width, win.position.height), abs=1e-3)
