"""Black-box invariants of the generated cut file (public API only)."""

import itertools
import os
import subprocess
import sys

import pytest

from house_maker import (ArchitecturalStyle, DoorType, ShingleType, WindowType)
from .conftest import make_house
from .svgdoc import parse_svg

MIN_GAP = 1.0   # mm between cut outlines of different panels

SCENARIOS = {
    'plain': dict(),
    'components': dict(auto_add_components=True),
    'chimney': dict(chimneys=[('roof_panel_left', 20, 20)]),
    'two_chimneys': dict(chimneys=[('roof_panel_left', 20, 20), ('roof_panel_right', 40, 20)]),
    'dormer': dict(dormers=[('roof_panel_left', 50, 30)]),
    'two_dormers': dict(dormers=[('roof_panel_left', 20, 30), ('roof_panel_left', 70, 30)]),
    'everything_a30': dict(auto_add_components=True, gable_angle=30,
                           chimneys=[('roof_panel_right', 40, 20)],
                           dormers=[('roof_panel_left', 30, 20)]),
}


def build(name):
    return make_house(**SCENARIOS[name])


@pytest.mark.parametrize('scenario', SCENARIOS)
def test_every_panel_inside_viewbox(scenario):
    doc = parse_svg(build(scenario).generate_svg())
    vb = doc.viewbox
    for pid, panel in doc.panels.items():
        b = panel.bbox
        assert (b.min_x >= vb.min_x - 1e-6 and b.min_y >= vb.min_y - 1e-6 and
                b.max_x <= vb.max_x + 1e-6 and b.max_y <= vb.max_y + 1e-6), \
            f"{pid} {b} outside viewBox {vb}"


@pytest.mark.parametrize('scenario', SCENARIOS)
def test_panels_do_not_overlap(scenario):
    doc = parse_svg(build(scenario).generate_svg())
    items = list(doc.panels.items())
    for (ida, a), (idb, b) in itertools.combinations(items, 2):
        assert not a.bbox.inflated(MIN_GAP / 2).intersects(b.bbox.inflated(MIN_GAP / 2)), \
            f"{ida} and {idb} are closer than {MIN_GAP}mm: {a.bbox} vs {b.bbox}"


@pytest.mark.parametrize('scenario', SCENARIOS)
def test_panel_ids_unique_and_complete(scenario):
    svg = build(scenario).generate_svg()
    doc = parse_svg(svg)
    ids = list(doc.panels)
    assert len(ids) == len(set(ids))
    for required in ('floor', 'side_wall_left', 'side_wall_right', 'gable_wall_front',
                     'gable_wall_back', 'roof_panel_left', 'roof_panel_right'):
        assert required in doc.panels
    # every svg <g id=...> with geometry must be parsed (no duplicate ids hiding panels)
    assert svg.count('<g id=') - 1 == len(ids)


def test_generation_is_deterministic_across_processes():
    code = ("from house_maker import HouseMaker, ArchitecturalStyle;"
            "print(HouseMaker(architectural_style=ArchitecturalStyle.STONE).generate_svg())")
    parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    outs = []
    for seed in ('1', '2'):
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=parent)
        outs.append(subprocess.run([sys.executable, '-c', code], env=env, capture_output=True,
                                   text=True, check=True).stdout)
    assert outs[0] == outs[1]


def test_generation_does_not_touch_global_random_state():
    import random
    random.seed(1234)
    expected = random.random()
    random.seed(1234)
    make_house(architectural_style=ArchitecturalStyle.STONE).generate_svg()
    assert random.random() == expected


_COMBOS = ([dict(window_type=w) for w in WindowType] +
           [dict(door_type=d) for d in DoorType] +
           [dict(architectural_style=s) for s in ArchitecturalStyle] +
           [dict(shingle_type=s) for s in ShingleType])


@pytest.mark.parametrize('kw', _COMBOS, ids=lambda kw: '-'.join(f'{v.name}' for v in kw.values()))
def test_every_option_generates_valid_closed_outlines(kw):
    """With every window, door, wall-style and roof-tile option: every cut sub-path in the file is closed (ends in Z)
    and every panel passes the full set of panel invariants (simple CCW outline, planned fingers, area, slots and
    cut-outs inside the outline without touching it or each other)."""
    import re
    from . import invariants
    house = make_house(auto_add_components=True, **kw)
    svg = house.generate_svg()
    cut_paths = re.findall(r'<path[^>]*class="cut-line"[^>]*\sd="([^"]+)"|<path[^>]*\sd="([^"]+)"[^>]*class="cut-line"', svg)
    subpaths = [chunk for pair in cut_paths for d in pair if d for chunk in re.split(r'(?=M)', d) if chunk.strip()]
    assert subpaths
    assert all(chunk.rstrip().endswith('Z') for chunk in subpaths), [c for c in subpaths if not c.rstrip().endswith('Z')][:2]
    assert len(parse_svg(svg).panels) == len(house.build_panels())
    for check in invariants.ALL_CHECKS:
        check(house, house.build_panels())


def test_cut_lines_are_a_0_001_inch_hairline_on_the_sheet():
    """The viewBox maps one user unit to one mm, so the cut stroke must be 0.0254 user units. In SVG CSS `px` is one
    user unit while `mm` is 3.78, so a width written in mm would cut (or engrave) with a 3.78x thicker line."""
    import re
    svg = make_house().generate_svg()
    w, h = (float(v) for v in re.search(r'width="([\d.]+)mm"\s+height="([\d.]+)mm"', svg).groups())
    vb = parse_svg(svg).viewbox
    assert abs(vb.max_x - vb.min_x - w) < 1e-6 and abs(vb.max_y - vb.min_y - h) < 1e-6   # 1 user unit = 1 mm
    rule = re.search(r'\.cut-line \{[^}]*stroke-width:\s*([\d.]+)(px|mm)?;', svg)
    user_units = float(rule.group(1)) * (96 / 25.4 if rule.group(2) == 'mm' else 1)
    assert abs(user_units - 0.0254) < 1e-9, rule.group(0)
