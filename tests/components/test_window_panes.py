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


def _subpath_polys(panel):
    from ..geom import dedupe
    return [dedupe(s) for d in panel.cut[1:] for s in parse_path(d, 32)]


@pytest.mark.parametrize('wtype', list(WindowType), ids=lambda t: t.name.lower())
def test_no_hole_lies_inside_or_overlaps_another(wtype):
    """A hole drawn inside another hole is cut out of the piece that falls away, so it adds nothing to the part: a
    window whose bars are drawn as rectangles inside the opening comes out as one plain hole. Every window type's
    holes must be disjoint (bars between panes stay as wall material)."""
    from ..geom import point_in_polygon, segments_cross
    house = make_house(length=160, width=120, height=100, auto_add_components=False)
    house.add_window('side_wall_left', 50, 30, 40, 30, window_type=wtype)
    wall = next(p for p in house.build_panels() if p.name == 'side_wall_left')
    polys = _subpath_polys(wall)
    assert polys
    for i, a in enumerate(polys):
        for b in polys[i + 1:]:
            assert not any(point_in_polygon(p, b) for p in a) and not any(point_in_polygon(p, a) for p in b)
            assert not any(segments_cross(a[k - 1], a[k], b[m - 1], b[m])
                           for k in range(len(a)) for m in range(len(b)))


@pytest.mark.parametrize('wtype,panes', [(WindowType.CROSS_PANE, 4), (WindowType.MULTI_PANE, 6),
                                         (WindowType.DOUBLE_HUNG, 2)])
def test_barred_windows_leave_their_bars_standing(wtype, panes):
    """Cross-pane, multi-pane and double-hung windows are cut as separate panes with bars one thickness wide."""
    from ..geom import bounds
    house = make_house(length=160, width=120, height=100, material_thickness=T, kerf=0, auto_add_components=False)
    house.add_window('side_wall_left', 50, 30, 40, 30, window_type=wtype)
    polys = _subpath_polys(next(p for p in house.build_panels() if p.name == 'side_wall_left'))
    assert len(polys) == panes
    boxes = [bounds(p) for p in polys]
    for lo, hi, start, end in ((0, 2, 50, 90), (1, 3, 30, 60)):          # x then y: opening 50..90 x 30..60
        starts, ends = sorted({round(b[lo], 6) for b in boxes}), sorted({round(b[hi], 6) for b in boxes})
        assert starts[0] == pytest.approx(start) and ends[-1] == pytest.approx(end)
        assert all(s - e == pytest.approx(T) for s, e in zip(starts[1:], ends[:-1]))   # bars one thickness wide
    assert len({(round(b[0], 6), round(b[1], 6)) for b in boxes}) == panes            # a full grid, no duplicates
