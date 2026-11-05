"""Regression tests for issues found by the independent review (each was reproduced first)."""

import itertools
import re

import pytest

from house_maker import HouseMaker, HouseStyle, PlacementError
from house_maker.builders.box import BoxPanelBuilder
from house_maker.exceptions import GeometryError
from house_maker.geometry import HouseGeometry
from house_maker.joints import FingerJointEngine
from house_maker.layout import pack
from house_maker.render import CHAR_WIDTH, FONT_SIZE
from .conftest import make_house
from .svgdoc import parse_svg


def test_pack_always_finds_a_place():
    pos = pack([('p0', 30, 60), ('p3', 100, 60), ('p5', 30, 100), ('p6', 150, 30)], 160, 2)
    assert len(pos) == 4


def test_house_that_used_to_crash_the_packer():
    assert HouseMaker(200, 120, 90, 30, 6, 20).generate_svg()


@pytest.mark.parametrize('mw', [457.2, 300.0])
def test_document_stays_within_material_width(mw):
    house = make_house(auto_add_components=True, material_width=mw,
                       chimneys=[('roof_panel_left', 20, 20)], dormers=[('roof_panel_right', 40, 25, 30)])
    assert parse_svg(house.generate_svg()).width <= mw + 1e-6


def test_labels_do_not_collide_with_panels_or_each_other():
    house = make_house(auto_add_components=True, length=160, width=120, height=90,
                       chimneys=[('roof_panel_left', 20, 20)],
                       dormers=[('roof_panel_right', 40, 25, 30), ('roof_panel_right', 100, 25, 30)])
    svg = house.generate_svg()
    doc = parse_svg(svg)
    labels = []
    for m in re.finditer(r'<g id="(?!house_box_panels)([^"]+)" transform="translate\(([-\d.]+),([-\d.]+)\)">.*?'
                         r'<text[^>]* x="([-\d.]+)" y="([-\d.]+)">([^<]*)</text>', svg, re.S):
        _, tx, ty, x, y, text = m.groups()
        cx, top = float(tx) + float(x) + 10, float(ty) + float(y) + 10      # + outer group translate
        half = len(text) * CHAR_WIDTH / 2
        labels.append((text, (cx - half, top, cx + half, top + FONT_SIZE)))
    assert len(labels) == len(doc.panels)
    boxes = [(n, (p.bbox.min_x, p.bbox.min_y, p.bbox.max_x, p.bbox.max_y)) for n, p in doc.panels.items()]

    def hit(a, b):
        return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
    for (t1, r1), (t2, r2) in itertools.combinations(labels, 2):
        assert not hit(r1, r2), f"labels {t1!r} and {t2!r} overlap"
    for t, r in labels:
        for n, b in boxes:
            assert not hit(r, b), f"label {t!r} runs into panel {n}"


def test_gable_window_must_stay_inside_the_gable_outline():
    house = make_house()
    g = house.geometry
    with pytest.raises(PlacementError, match='sloped'):
        house.add_window('gable_wall_front', 3, g.total_gable_height - 20, 10, 10)
    house.add_window('gable_wall_front', 30, 20, 12, 12)
    with pytest.raises(PlacementError, match='overlaps'):
        house.add_window('gable_wall_front', 33, 22, 12, 12)
    with pytest.raises(PlacementError, match='overlaps'):
        house.add_door('gable_wall_front', 36, 20, 15, 30)
    assert house.validate_components() == []


@pytest.mark.parametrize('style', [HouseStyle.HOUSE_NO_ROOF, HouseStyle.WALLS_ONLY])
def test_roof_features_without_roof_are_rejected(style):
    house = make_house(house_style=style, chimneys=[('roof_panel_left', 30, 30)])
    with pytest.raises(PlacementError, match='roof'):
        house.generate_svg()


@pytest.mark.parametrize('panel', ['roof_panel_left', 'roof_panel_right'])
def test_chimney_casing_stays_on_the_panel_and_clear_of_neighbours(panel):
    house = make_house(length=160, width=120, height=90)
    t = house.geometry.thickness
    with pytest.raises(PlacementError):
        house.add_chimney(panel, t, t)                      # casing would hang over the edge
    house.add_chimney(panel, 40, 30, 10, 12, 20)
    c = house.architectural_config.chimneys[0]
    x, y, w, d = c.footprint()
    with pytest.raises(PlacementError):
        house.add_chimney(panel, x + w + 2 * t, y, 10, 12, 20)       # casing frames would touch
    house.add_chimney(panel, x + w + 2 * c.casing_margin + 0.5, y, 10, 12, 20)
    for p in house.build_panels():
        if p.name.startswith('chimney_casing'):
            assert p.nominal_size[0] >= w + 2 * t


def test_joint_plan_is_judged_on_the_length_fingers_occupy():
    e = FingerJointEngine(thickness=2, finger_length=15, kerf=0)
    assert e.plan_edge(32, 'female', inset=2) is not None    # 28 usable >= 22.5
    assert e.plan_edge(26, 'female', inset=2) is None        # 22 usable < 22.5 -> no fingers
    # floor edge and gable bottom edge therefore agree on having fingers or not
    e2 = FingerJointEngine(2, 15, 0)
    floor = e2.plan_edge(22, 'male')
    gable = e2.plan_edge(22 + 4, 'female', inset=2)
    assert (floor is None) == (gable is None)


def test_builder_refuses_invalid_geometry():
    bad = HouseGeometry(100, 20, 20, 45, 2, 15, 0)             # finger_length > min edge / 3
    with pytest.raises(GeometryError):
        BoxPanelBuilder(bad, FingerJointEngine(2, 15, 0))
