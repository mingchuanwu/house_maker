"""
Main-box seams: every finger meets a groove of the same position and width, tab depth equals the
mating material thickness, and shared edges have equal lengths. Run over several roof angles, sizes,
thicknesses and kerf values (positions must match exactly; depths may differ by at most the kerf).

Each seam is also rendered as its own small assembly (see --svg-dir).
"""

import itertools
import math

import pytest

from ..conftest import make_house
from ..profiles import edge_length, edge_profile, mirrored, physical

POS_TOL = 5e-3     # outline coordinates are rounded to 0.001mm
CASES = [dict(length=l, width=w, height=h, gable_angle=a, kerf=k, material_thickness=t)
         for (l, w, h), a, k, t in itertools.product([(100, 80, 70), (160, 90, 120)],
                                                     (30, 45, 60), (0.0, 0.1), (3.0, 2.0))]


def _id(c):
    return f"{c['length']}x{c['width']}x{c['height']}-a{c['gable_angle']}-k{c['kerf']}-t{c['material_thickness']}"


@pytest.fixture(params=CASES, ids=_id)
def box(request):
    c = request.param
    return {p.name: p for p in make_house(**c).build_panels()}, c


def assert_mate(male_f, female_f, length, t, k, offset=0.0):
    """Fingers on two mating edges (each in its own panel's direction), compared as the cut parts will
    be: same place, same width, tab exactly as long as the mating material is thick, notch as deep."""
    assert len(male_f) == len(female_f) > 0
    for m, f in zip(male_f, mirrored(female_f, length + 2 * offset)):
        pm, pf = physical(m, k), physical(f, k)
        assert pm.start == pytest.approx(pf.start - offset, abs=POS_TOL)
        assert pm.end == pytest.approx(pf.end - offset, abs=POS_TOL)
        assert pm.end - pm.start == pytest.approx(15.0, abs=POS_TOL)           # finger_length
        assert pm.depth == pytest.approx(t, abs=POS_TOL) and -pf.depth == pytest.approx(t, abs=POS_TOL)


def test_shared_edge_lengths_agree(box):
    p, c = box
    t = c['material_thickness']
    assert edge_length(p['floor'], 'bottom') == pytest.approx(edge_length(p['side_wall_left'], 'bottom'))
    assert edge_length(p['floor'], 'right') == pytest.approx(edge_length(p['gable_wall_front'], 'bottom') - 2 * t)
    assert edge_length(p['side_wall_left'], 'right') == pytest.approx(edge_length(p['gable_wall_front'], 'right'))
    assert edge_length(p['roof_panel_left'], 'ridge') == pytest.approx(edge_length(p['roof_panel_right'], 'ridge'))
    assert edge_length(p['roof_panel_left'], 'ridge') == pytest.approx(edge_length(p['floor'], 'bottom') + 6 * t)


@pytest.mark.parametrize('side', ['side_wall_left', 'side_wall_right'])
@pytest.mark.parametrize('floor_edge', ['bottom', 'top'])
def test_floor_to_side_walls(box, side, floor_edge):
    p, c = box
    assert_mate(edge_profile(p['floor'], floor_edge), edge_profile(p[side], 'bottom'),
                edge_length(p['floor'], floor_edge), c['material_thickness'], c['kerf'])


@pytest.mark.parametrize('gable', ['gable_wall_front', 'gable_wall_back'])
@pytest.mark.parametrize('floor_edge', ['right', 'left'])
def test_floor_to_gable_walls(box, gable, floor_edge):
    """The gable bottom edge is 2t longer than the floor edge: fingers sit t in from each end."""
    p, c = box
    assert_mate(edge_profile(p['floor'], floor_edge), edge_profile(p[gable], 'bottom'),
                edge_length(p['floor'], floor_edge), c['material_thickness'], c['kerf'],
                offset=c['material_thickness'])


@pytest.mark.parametrize('side', ['side_wall_left', 'side_wall_right'])
@pytest.mark.parametrize('gable', ['gable_wall_front', 'gable_wall_back'])
@pytest.mark.parametrize('edge', ['right', 'left'])
def test_side_walls_to_gable_walls(box, side, gable, edge):
    p, c = box
    assert_mate(edge_profile(p[side], edge), edge_profile(p[gable], edge),
                edge_length(p[side], edge), c['material_thickness'], c['kerf'])


def test_ridge_fingers_mate(box):
    p, c = box
    left, right = edge_profile(p['roof_panel_left'], 'ridge'), edge_profile(p['roof_panel_right'], 'ridge')
    t, k = c['material_thickness'], c['kerf']
    assert len(left) == len(right) > 0
    for female, male in zip(left, right):               # both run along +x in their own panel
        pf, pm = physical(female, k), physical(male, k)
        assert (pm.start, pm.end) == pytest.approx((pf.start, pf.end), abs=POS_TOL)
        assert pm.depth == pytest.approx(t, abs=POS_TOL) and -pf.depth == pytest.approx(t, abs=POS_TOL)


@pytest.mark.parametrize('gable', ['gable_wall_front', 'gable_wall_back'])
@pytest.mark.parametrize('roof,edge', [('roof_panel_left', 'roof_left'), ('roof_panel_right', 'roof_right')])
def test_gable_tab_passes_through_roof_slot(box, gable, roof, edge):
    p, c = box
    t, k = c['material_thickness'], c['kerf']
    (drawn_tab,) = edge_profile(p[gable], edge)         # exactly one tab on each sloped edge
    tab = physical(drawn_tab, k)
    length = edge_length(p[gable], edge)
    centre = (tab.start + tab.end) / 2
    from_peak = centre if edge == 'roof_left' else length - centre
    assert from_peak == pytest.approx(length / 2, abs=POS_TOL)          # tab is centred on the slope
    assert tab.end - tab.start == pytest.approx(15.0, abs=POS_TOL)
    assert tab.depth == pytest.approx(t, abs=POS_TOL)               # flush with the roof's outer face
    panel = p[roof]
    assert len(panel.slots) == 2
    ridge_offset = t if roof == 'roof_panel_left' else 0.0               # left ridge edge is notched
    roof_len = edge_length(panel, 'ridge')
    for slot, expect_x in zip(panel.slots, (2.5 * t, roof_len - 2.5 * t)):
        assert slot.orientation == 'vertical'
        assert slot.cx == pytest.approx(expect_x, abs=POS_TOL)          # centred on the gable wall's thickness
        assert slot.cy - ridge_offset == pytest.approx(from_peak, abs=POS_TOL)
        assert slot.thickness + k == pytest.approx(t, abs=POS_TOL)      # hole grows by the kerf when cut
        assert slot.length + k == pytest.approx(tab.end - tab.start, abs=POS_TOL)


def test_gable_slope_matches_roof_angle(box):
    p, c = box
    g = p['gable_wall_front']
    (x0, y0), (x1, y1) = ((g.corners[3].x, g.corners[3].y), (g.corners[4].x, g.corners[4].y))
    assert math.degrees(math.atan2(abs(y1 - y0), abs(x1 - x0))) == pytest.approx(c['gable_angle'], abs=1e-6)


# ---------------------------------------------------------------- one SVG per seam (inspection)
ASSEMBLIES = {
    'floor_to_side_wall': ['floor', 'side_wall_left'],
    'floor_to_gable_wall': ['floor', 'gable_wall_front'],
    'side_wall_to_gable_wall': ['side_wall_left', 'gable_wall_front'],
    'gable_wall_to_roof': ['gable_wall_front', 'roof_panel_left', 'roof_panel_right'],
    'roof_ridge': ['roof_panel_left', 'roof_panel_right'],
}


@pytest.mark.parametrize('angle', [30, 60])
@pytest.mark.parametrize('name', ASSEMBLIES)
def test_seam_assembly_svgs(inspect, name, angle):
    house = make_house(gable_angle=angle, length=120, width=90, height=70)
    panels = inspect('box_seams', f'{name}_a{angle}', house, ASSEMBLIES[name],
                     title=f'{name.replace("_", " ")} at {angle}°: the two sides of each seam')
    assert len(panels) == len(ASSEMBLIES[name])
