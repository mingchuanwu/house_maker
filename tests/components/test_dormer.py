"""
Dormer component: a roof panel at the roof angle plus the dormer parts (front face, two roof panels),
checked against an independent 3D construction (plain vector maths, none of the library's formulas).
"""

import math

import pytest

from house_maker.svgpath import parse_path
from ..conftest import make_house
from ..geom import centre_from_drawn_start, cross, dot, norm, nominal_edge_length, nominal_extent, outline, sub
from ..profiles import edge_length, edge_profile, mirrored, physical

TOL = 5e-3
ANGLES = (20, 35, 45, 60)


def dormer_3d(theta, W, phi):
    """Vertices of the dormer. Main roof plane: z = y*tan(theta); the sill lies on the roof at y = 0."""
    th, ph = math.radians(theta), math.radians(phi)
    H = (W / 2) * math.tan(ph)
    A, B, P = (0, 0, 0), (W, 0, 0), (W / 2, 0, H)
    y_e = H / math.tan(th)                       # where the horizontal ridge at height H meets the roof
    Q = (W / 2, y_e, H)
    assert Q[2] == pytest.approx(y_e * math.tan(th))        # Q really lies on the main roof plane
    return A, B, P, Q


@pytest.fixture(params=[(a, p) for a in ANGLES for p in (None, 30.0)],
                ids=lambda p: f"a{p[0]}-pitch{p[1] or 'match'}")
def scene(request, inspect):
    theta, phi = request.param
    W, o = 30.0, 3.0
    house = make_house(gable_angle=theta, material_thickness=3.0, length=160, width=140, height=90, kerf=0.0)
    dormer = house.add_additional_gable('roof_panel_left', 30, 20, W, roof_overhang=o, pitch=phi)
    panels = inspect('dormer', f"a{theta}_pitch{phi or 'match'}", house,
                     ['roof_panel_left', lambda n: n.startswith('additional_gable')],
                     title=f'{theta}° main roof, dormer pitch {phi or "= main roof"}, width {W}')
    return dict(theta=theta, phi=phi or theta, W=W, o=o, dormer=dormer, p={q.name: q for q in panels})


def test_roof_plane_has_the_right_pitch_and_a_horizontal_ridge(scene):
    A, B, P, Q = dormer_3d(scene['theta'], scene['W'], scene['phi'])
    n = cross(sub(P, A), sub(Q, A))
    assert math.degrees(math.acos(abs(n[2]) / norm(n))) == pytest.approx(scene['phi'], abs=1e-6)
    assert dot(sub(A, P), sub(Q, P)) == pytest.approx(0, abs=1e-9)         # ridge ⟂ rafter
    assert Q[2] == P[2]                                                   # horizontal ridge
    # front face apex angle follows from the pitch
    assert scene['dormer'].geometry.apex_angle_deg == pytest.approx(180 - 2 * scene['phi'])


def test_front_face_is_triangle_ABP_lifted_clear_of_the_rising_roof(scene):
    A, B, P, Q = dormer_3d(scene['theta'], scene['W'], scene['phi'])
    face = scene['p']['additional_gable_front_0']
    # A vertical slab cannot start at the sill: on a rising roof it would dig in. Its base is cut level at the
    # highest roof point under it, t*tan(theta) above the sill; the sloped edges stay on the roof planes, so
    # the face is a smaller similar triangle.
    lift = 3.0 * math.tan(math.radians(scene['theta']))
    cot = 1 / math.tan(math.radians(scene['phi']))
    assert face.nominal_size == pytest.approx((scene['W'] - 2 * lift * cot, P[2] - lift), abs=TOL)
    xs = [c.x for c in face.corners]                          # nominal corners (the outline may also carry tabs)
    assert max(xs) - min(xs) == pytest.approx(scene['W'] - 2 * lift * cot, abs=TOL)


def test_roof_panel_edges_are_the_true_3d_lengths(scene):
    A, B, P, Q = dormer_3d(scene['theta'], scene['W'], scene['phi'])
    roof, right = scene['p']['additional_gable_roof_left_0'], scene['p']['additional_gable_roof_right_0']
    lengths = {n: edge_length(roof, n) for n in roof.edge_names}
    assert lengths['front'] == pytest.approx(norm(sub(P, A)), abs=TOL)                 # rafter
    assert lengths['ridge'] == pytest.approx(norm(sub(Q, P)) + scene['o'], abs=TOL)    # ridge + overhang
    assert lengths['valley'] == pytest.approx(norm(sub(Q, A)), abs=TOL)
    assert lengths['side'] == pytest.approx(scene['o'], abs=TOL)
    assert sorted(edge_length(right, n) for n in right.edge_names) == \
        pytest.approx(sorted(lengths.values()), abs=TOL)                              # congruent panels


def test_footprint_on_the_main_roof_panel(scene):
    A, B, P, Q = dormer_3d(scene['theta'], scene['W'], scene['phi'])
    d = scene['dormer']
    assert d.position.width == pytest.approx(scene['W'])
    assert d.position.height == pytest.approx(math.hypot(Q[1], Q[2]), abs=TOL)   # sill -> Q measured on the roof
    (score,) = scene['p']['roof_panel_left'].score
    pts = parse_path(score)[0]
    assert len(pts) == 3
    assert max(q.y for q in pts) - min(q.y for q in pts) == pytest.approx(d.position.height, abs=TOL)


def test_no_orphan_tabs_or_slots(scene):
    """A face tab exists exactly when both roof panels have a slot for it (they would not mate otherwise)."""
    p = scene['p']
    has_tabs = bool(p['additional_gable_front_0'].joints)
    assert has_tabs == bool(p['additional_gable_roof_left_0'].slots) == bool(p['additional_gable_roof_right_0'].slots)


def test_requested_depth_is_ignored_with_a_warning():
    house = make_house()
    with pytest.warns(UserWarning, match='ignored'):
        d = house.add_additional_gable('roof_panel_left', 30, 20, 25, 99.0)
    assert d.position.height != 99.0


@pytest.fixture
def large(inspect):
    t, k = 3.0, 0.1
    house = make_house(length=200, width=160, height=90, gable_angle=35, kerf=k, material_thickness=t)
    house.add_additional_gable('roof_panel_right', 40, 20, 70)
    panels = inspect('dormer', 'large_with_fingers', house,
                     ['roof_panel_right', lambda n: n.startswith('additional_gable')],
                     title='Dormer wide enough for ridge fingers and face tabs/slots')
    return t, k, {p.name: p for p in panels}


def test_large_dormer_ridge_fingers_mate(large):
    t, k, p = large
    left, right = p['additional_gable_roof_left_0'], p['additional_gable_roof_right_0']
    lf, rf = edge_profile(left, 'ridge'), edge_profile(right, 'ridge')
    assert len(lf) == len(rf) > 0
    length = edge_length(left, 'ridge')
    assert edge_length(right, 'ridge') == pytest.approx(length, abs=TOL)
    for male, female in zip(lf, mirrored(rf, length)):                     # left = male, right = female
        pm, pf = physical(male, k), physical(female, k)
        assert (pm.start, pm.end) == pytest.approx((pf.start, pf.end), abs=TOL)
        assert pm.depth == pytest.approx(t, abs=TOL) and -pf.depth == pytest.approx(t, abs=TOL)


def test_large_dormer_face_tabs_line_up_with_roof_slots(large):
    t, k, p = large
    face = p['additional_gable_front_0']
    rafter = nominal_extent(p['additional_gable_roof_left_0'], k)[0]
    rake = nominal_edge_length(face, 'rake_left', k)
    for edge in ('rake_left', 'rake_right'):
        (drawn,) = edge_profile(face, edge)
        tab = physical(drawn, k)
        # the tab is centred on the NOMINAL rake edge (the drawn edge is mitred kerf/2 outwards at both ends)
        assert (tab.start + tab.end) / 2 == pytest.approx(centre_from_drawn_start(face, edge, k), abs=TOL)
        assert tab.depth == pytest.approx(t, abs=TOL)
    for name, expect in (('additional_gable_roof_left_0', rafter - rake / 2),      # left panel: u runs from the eave
                         ('additional_gable_roof_right_0', rake / 2)):             # right panel: u runs from the ridge
        roof = p[name]
        (slot,) = roof.slots
        assert slot.orientation == 'horizontal'
        assert slot.cx == pytest.approx(expect, abs=TOL)                        # under the middle of the face's rake edge
        assert slot.cy == pytest.approx(t / 2, abs=TOL)                       # centre of the face's thickness
        assert slot.length + k == pytest.approx(tab.end - tab.start, abs=TOL)
        assert slot.thickness + k == pytest.approx(t, abs=TOL)
        xs = [q.x for q in outline(roof)]
        assert min(xs) < slot.cx - slot.length / 2 and slot.cx + slot.length / 2 < max(xs)


def test_two_dormers_each_get_their_own_panels(inspect):
    house = make_house(length=200, width=140, height=90)
    house.add_additional_gable('roof_panel_left', 20, 25, 30)
    house.add_additional_gable('roof_panel_left', 100, 25, 40)
    panels = inspect('dormer', 'two_dormers', house, ['roof_panel_left', lambda n: n.startswith('additional_gable')],
                     title='Two dormers on one roof panel')
    names = [p.name for p in panels if p.name.startswith('additional_gable')]
    assert len(names) == 6 and len(set(names)) == 6


@pytest.mark.parametrize('t', [2.0, 3.0, 5.0])
@pytest.mark.parametrize('theta', [25, 35, 45, 60])
@pytest.mark.parametrize('width', [30, 45, 60, 80, 110])
def test_ridge_notches_never_reach_the_valley(width, theta, t):
    """The right roof panel tapers to a point; its female notches (t deep) must leave material next to
    the valley edge and the outline must stay a simple polygon, for every dormer size."""
    from ..geom import dedupe, is_simple, segment_distance
    house = make_house(length=400, width=300, height=100, gable_angle=theta, material_thickness=t, kerf=0.1)
    try:
        house.add_additional_gable('roof_panel_left', 40, 20, width)
    except Exception:
        pytest.skip('does not fit on the roof')
    p = {q.name: q for q in house.build_panels()}
    right, left = p['additional_gable_roof_right_0'], p['additional_gable_roof_left_0']
    outline_pts = dedupe(outline(right))
    assert is_simple(outline_pts) and is_simple(dedupe(outline(left)))
    g = house.architectural_config.additional_gables[0].geometry
    valley = [c for n, c in zip(right.edge_names, right.corners) if n == 'valley'][0]
    valley_end = right.corners[(right.corners.index(valley) + 1) % len(right.corners)]
    # every notch-bottom vertex stays at least t from the valley line (the right panel's ridge is its x = 0 edge)
    if right.joints.get('ridge'):
        bottoms = [q for q in outline_pts if abs(q.x - (t - 0.05)) < 1e-2]      # ridge edge is drawn kerf/2 out
        assert bottoms
        for q in bottoms:
            assert segment_distance(q, valley, valley_end) >= t - 0.02, f"notch bottom {q} too close to the valley"
    # mating: the left panel's fingers sit at the mirrored positions
    lf, rf = edge_profile(left, 'ridge'), edge_profile(right, 'ridge')
    assert len(lf) == len(rf)
