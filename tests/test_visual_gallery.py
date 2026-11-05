"""
Whole-house gallery (component galleries live in tests/components). To LOOK at the output:

    cd /Users/mingchuanwu/src/oss && python3 -m pytest house_maker --svg-dir /tmp/house_gallery \
        && open /tmp/house_gallery/index.html

Each case is a scenario that exercises one interesting area (joints at different angles/kerf,
chimneys on both roof panels, dormers incl. one big enough for fingers, every window/door type...).
"""

import pytest

from .conftest import make_house

CASES = {
    '01_default_house': ('Default house with automatic windows and door', dict(auto_add_components=True)),
    '02_steep_roof_60deg': ('60° roof, kerf 0.1 - check gable tabs vs roof slots', dict(gable_angle=60, auto_add_components=True)),
    '03_shallow_roof_25deg_no_kerf': ('25° roof, kerf 0 - exact fit', dict(gable_angle=25, kerf=0.0, auto_add_components=True)),
    '04_thin_material_2mm': ('2 mm material', dict(material_thickness=2.0, auto_add_components=True)),
    '05_large_house_many_fingers': ('Large house: 5-7 fingers per edge', dict(length=200, width=150, height=130, auto_add_components=True)),
    '06_single_joints': ('single_joints=True', dict(single_joints=True)),
    '07_chimney_left_35deg': ('Chimney on the left roof panel, 35°',
                              dict(gable_angle=35, length=140, width=110, height=90,
                                   chimneys=[('roof_panel_left', 20, 25, 10, 12, 20)])),
    '08_chimneys_both_panels_60deg': ('Chimneys on both roof panels, 60°',
                                      dict(gable_angle=60, length=140, width=110, height=90,
                                           chimneys=[('roof_panel_left', 20, 25, 10, 12, 20),
                                                     ('roof_panel_right', 60, 20, 14, 16, 15)])),
    '09_small_dormer': ('Small dormer (glued: too small for fingers)',
                        dict(length=140, width=110, height=90, dormers=[('roof_panel_left', 40, 25, 25)])),
    '10_large_dormer_fingers': ('Large dormer: ridge fingers and face tabs/slots',
                                dict(length=200, width=160, height=90, gable_angle=35, kerf=0.1,
                                     dormers=[('roof_panel_right', 40, 20, 70)])),
    '11_two_dormers_one_chimney_30deg': ('Two dormers + chimney, 30°',
                                         dict(length=220, width=140, height=90, gable_angle=30,
                                              dormers=[('roof_panel_left', 20, 25, 30), ('roof_panel_left', 110, 25, 40)],
                                              chimneys=[('roof_panel_right', 40, 30, 12, 14, 20)])),
    '12_arched_windows_doors': ('Arched windows and door', dict(auto_add_components=True, window_type='ARCHED', door_type='ARCHED')),
    '13_everything': ('Everything at once, brick style',
                      dict(auto_add_components=True, architectural_style='BRICK', length=220, width=150, height=110,
                           gable_angle=40,
                           chimneys=[('roof_panel_right', 40, 30, 12, 14, 20)],
                           dormers=[('roof_panel_left', 40, 25, 40)])),
}


def _build(kwargs):
    from house_maker import ArchitecturalStyle, DoorType, WindowType
    kw = dict(kwargs)
    if isinstance(kw.get('window_type'), str):
        kw['window_type'] = WindowType[kw['window_type']]
    if isinstance(kw.get('door_type'), str):
        kw['door_type'] = DoorType[kw['door_type']]
    if isinstance(kw.get('architectural_style'), str):
        kw['architectural_style'] = ArchitecturalStyle[kw['architectural_style']]
    return make_house(**kw)


@pytest.mark.parametrize('name', CASES)
def test_gallery_case(name, inspect):
    title, kwargs = CASES[name]
    house = _build(kwargs)
    panels = inspect('whole_house', name, house, [lambda n: True], title=title)
    assert len(panels) >= 7
