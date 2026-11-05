"""
Chimney component: a roof panel at the roof angle, the chimney's footprint on it (trigonometry of the
roof angle and chimney size), and the chimney parts (four walls + casing) with their corner joints.

Every case writes an SVG containing just those panels (see --svg-dir) for visual inspection.
"""

import math

import pytest

from house_maker.svgpath import parse_path
from ..conftest import make_house
from ..geom import bounds, nominal_corners, nominal_extent, outline
from ..profiles import edge_profile, physical

T, K = 3.0, 0.1
TOL = 5e-3
SCENES = [
    # theta, roof panel, interior width W, plan depth D, exposure h
    (20, 'roof_panel_left', 10, 12, 30),
    (35, 'roof_panel_left', 10, 12, 30),
    (35, 'roof_panel_right', 14, 20, 24),
    (45, 'roof_panel_left', 12, 16, 40),
    (60, 'roof_panel_right', 10, 12, 36),
    (60, 'roof_panel_left', 20, 25, 30),
]


def scene_id(s):
    return f"a{s[0]}-{s[1].replace('roof_panel_', '')}-W{s[2]}D{s[3]}h{s[4]}"


@pytest.fixture(params=SCENES, ids=scene_id)
def scene(request, inspect):
    theta, panel, W, D, h = request.param
    house = make_house(gable_angle=theta, material_thickness=T, kerf=K, length=150, width=120, height=90,
                       chimneys=[(panel, 25, 30, W, D, h)])
    panels = inspect('chimney', scene_id(request.param), house,
                     [panel, lambda n: n.startswith('chimney_')],
                     title=f'{theta}° roof, chimney interior width {W}, plan depth {D}, exposure {h}')
    return dict(theta=theta, panel=panel, W=W, D=D, h=h, house=house,
                p={q.name: q for q in panels}, tan=math.tan(math.radians(theta)))


# ------------------------------------------------------------------ roof panel and footprint
def test_roof_panel_has_the_requested_slope(scene):
    """Roof panel width and gable half-width are related by the roof angle."""
    g, panel = scene['house'].geometry, scene['p'][scene['panel']]
    overhang = (4 if scene['panel'].endswith('left') else 3) * T + K
    rafter = panel.nominal_size[1] - overhang
    assert rafter * math.cos(math.radians(scene['theta'])) == pytest.approx(g.gable_wall_width / 2, abs=TOL)


def test_footprint_is_scored_and_follows_the_trigonometry(scene):
    roof = scene['p'][scene['panel']]
    chimney = scene['house'].architectural_config.chimneys[0]
    D, tan = scene['D'], scene['tan']
    (score,) = roof.score
    x0, y0, x1, y1 = bounds(parse_path(score)[0])
    assert (x0, y0) == pytest.approx((25, 30), abs=TOL)
    assert x1 - x0 == pytest.approx(scene['W'] + 2 * T, abs=TOL)          # outer width
    assert y1 - y0 == pytest.approx(math.hypot(D, D * tan), abs=TOL)      # plan depth stretched along the slope
    assert y1 - y0 == pytest.approx(D / math.cos(math.radians(scene['theta'])), abs=TOL)
    assert chimney.footprint()[2:] == pytest.approx((x1 - x0, y1 - y0), abs=TOL)
    # inside the panel, clear of the gable-tab slots
    w, h = roof.nominal_size
    assert x0 >= T and y0 >= T and x1 <= w - T and y1 <= h - T
    for slot in roof.slots:
        sx, sy = slot.cx, slot.cy
        assert not (x0 - T < sx < x1 + T and y0 - T < sy < y1 + T)


def test_roof_cutout_is_footprint_minus_two_thicknesses(scene):
    """The hole leaves a lip of one thickness all round, so the chimney rests on the roof."""
    roof = scene['p'][scene['panel']]
    D, theta = scene['D'], scene['theta']
    assert len(roof.cut) == 1 + 2 + 1                  # outline + the two gable slots + the chimney hole
    (hole,) = [parse_path(d)[0] for d in roof.cut[3:]]
    hx0, hy0, hx1, hy1 = bounds(hole)
    fx0, fy0, fx1, fy1 = bounds(parse_path(roof.score[0])[0])
    footprint_w, footprint_l = fx1 - fx0, fy1 - fy0
    # a void: drawn kerf/2 smaller on each side, the laser opens it up to the nominal size
    assert hx1 - hx0 + K == pytest.approx(footprint_w - 2 * T, abs=TOL)
    assert hy1 - hy0 + K == pytest.approx(D / math.cos(math.radians(theta)) - 2 * T, abs=TOL)
    # lip of exactly one thickness on every side (after cutting)
    lip = T + K / 2
    assert (hx0 - fx0, fx1 - hx1, hy0 - fy0, fy1 - hy1) == pytest.approx((lip,) * 4, abs=TOL)
    # nothing else on the roof is cut near the hole
    assert fx0 >= T and fy0 >= T


# ------------------------------------------------------------------ parts
def test_walls_match_independent_3d_construction(scene):
    p, D, h, tan = scene['p'], scene['D'], scene['h'], scene['tan']
    roof_z = lambda s: s * tan          # s: plan distance from the down-slope (front) face
    top = roof_z(D) + h                 # level top: h above the roof at the up-slope face

    left, right = p['chimney_left_0'], p['chimney_right_0']
    flat = lambda pts: [v for p in pts for v in p]
    # the drawn outline is the nominal one offset outward by kerf/2 (checked on its own in test_contracts)
    assert flat((c.x, c.y) for c in nominal_corners(left, K)) == pytest.approx(flat([(0, 0), (D, roof_z(D)), (D, top), (0, top)]), abs=TOL)
    assert flat((c.x, c.y) for c in nominal_corners(right, K)) == pytest.approx(flat([(0, roof_z(D)), (D, 0), (D, top), (0, top)]), abs=TOL)

    front, back = p['chimney_front_0'], p['chimney_back_0']
    (fw, fh), (bw, bh) = nominal_extent(front, K), nominal_extent(back, K)
    assert fw == pytest.approx(scene['W'], abs=TOL) and bw == pytest.approx(scene['W'], abs=TOL)
    # a wall's base is level at the highest roof point under its thickness; its top is the common top
    assert roof_z(T) + fh == pytest.approx(top, abs=TOL)
    assert roof_z(D) + bh == pytest.approx(top, abs=TOL)
    assert fh > bh                                           # the down-slope side stands taller


def test_casing_frames_the_footprint(scene):
    casing = scene['p']['chimney_casing_0']
    chimney = scene['house'].architectural_config.chimneys[0]
    _, _, w, d = chimney.footprint()
    hole = parse_path(casing.cut[1])[0]
    x0, y0, x1, y1 = bounds(hole)
    ow, oh = casing.nominal_size                             # drawn outer size = nominal + kerf
    lean = T * scene['tan']                                  # up-slope walls lean away from the casing's normal
    open_w, open_h = (x1 - x0) + K, (y1 - y0) + K            # the opening as cut: a void, drawn kerf smaller
    assert 0 <= open_w - w <= 0.5 * T                        # snug at the sides
    assert 0 <= open_h - (d + lean) <= 0.5 * T               # longer up-slope by t*tan(theta), snug otherwise
    # frame widths measured from the drawn outer edge (kerf/2 outside the nominal origin)
    left, right, top, bottom = x0 + K / 2, ow - K / 2 - x1, y0 + K / 2, oh - K / 2 - y1
    assert left == pytest.approx(right, abs=TOL) and top == pytest.approx(bottom, abs=TOL)   # frame is centred on the opening
    assert left == pytest.approx(T + K, abs=TOL) and top == pytest.approx(T + K, abs=TOL)    # t as cut (+ kerf as drawn)
    assert chimney.casing_margin == pytest.approx(T * 1.05)
    assert chimney.casing_margins() == pytest.approx((T * 1.05, T * 1.05 + lean, T * 1.05, T * 1.05))


# ------------------------------------------------------------------ joints
def heights(panel, edge, base_offset=0.0):
    """Fingers on a vertical edge as (z0, z1) heights above the roof reference (3D, independent of the
    edge's travel direction). `base_offset` is the height of the panel's y=0 line."""
    i = panel.edge_names.index(edge)
    a, b = panel.corners[i], panel.corners[(i + 1) % len(panel.corners)]
    sign = 1 if b.y > a.y else -1
    out = []
    for f in (physical(g, K) for g in edge_profile(panel, edge)):         # the finger the cut part has
        z0, z1 = base_offset + a.y + sign * f.start, base_offset + a.y + sign * f.end
        out.append((min(z0, z1), max(z0, z1), f.depth))
    return sorted(out)


def test_corner_joints_mate(scene):
    p, D, h, tan = scene['p'], scene['D'], scene['h'], scene['tan']
    base = {'chimney_front_0': T * tan, 'chimney_back_0': D * tan}      # height of each wall's base
    end = {'chimney_front_0': 'front_end', 'chimney_back_0': 'back_end'}
    for wall in base:
        tabs_l, tabs_r = heights(p[wall], 'left', base[wall]), heights(p[wall], 'right', base[wall])
        assert tabs_l
        assert [v for t in tabs_l for v in t[:2]] == pytest.approx([v for t in tabs_r for v in t[:2]])
        for side in ('chimney_left_0', 'chimney_right_0'):
            notches = heights(p[side], end[wall])
            assert len(notches) == len(tabs_l)
            for (a0, a1, depth), (n0, n1, ndepth) in zip(tabs_l, notches):
                assert (n0, n1) == pytest.approx((a0, a1), abs=TOL)                 # same place, same width
                assert depth == pytest.approx(T, abs=TOL)                           # tab = side-wall thickness
                assert -ndepth == pytest.approx(T, abs=TOL)                         # notch = front/back thickness
                roof_under_notch = D * tan if wall == 'chimney_back_0' else 0.0
                assert n0 > roof_under_notch and n1 < D * tan + h                   # notch stays inside the wall


def test_finger_length_is_scaled_to_the_chimney(scene):
    p = scene['p']
    shortest = min(nominal_extent(p['chimney_front_0'], K)[1], nominal_extent(p['chimney_back_0'], K)[1])
    expected = min(15.0, shortest / 3)
    for wall in ('chimney_front_0', 'chimney_back_0'):
        for edge in ('left', 'right'):
            f = [physical(x, K) for x in edge_profile(p[wall], edge)]
            assert all(x.end - x.start == pytest.approx(expected, abs=TOL) for x in f)


def test_notches_are_cut_into_the_side_walls_end_edges(scene):
    """Female notches open onto the end edges (flush corner), so the outline has no internal slot."""
    for side in ('chimney_left_0', 'chimney_right_0'):
        panel = scene['p'][side]
        assert panel.joints.keys() == {'front_end', 'back_end'}
        assert all(j.role == 'female' for j in panel.joints.values())
        assert len(panel.cut) == 1


def test_tiny_chimney_is_glued_not_jointed(inspect):
    """Fingers narrower than two thicknesses would be fragile: no joints anywhere, consistently."""
    house = make_house(chimneys=[('roof_panel_left', 25, 30, 6, 8, 10)])
    panels = inspect('chimney', 'tiny_glued', house, [lambda n: n.startswith('chimney_') and 'casing' not in n],
                     title='Too small for fingers: walls are plain rectangles/trapezoids')
    assert all(not p.joints for p in panels)
    assert all(len({(round(q.x, 3), round(q.y, 3)) for q in outline(p)}) == 4 for p in panels)
