"""Public API behaviour: HouseMaker facade, configuration errors, presets, CLI."""

import os
import subprocess
import sys
import warnings

import pytest

from house_maker import HouseMaker, PlacementError, RoofType
from .conftest import make_house
from .svgdoc import parse_svg

PARENT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_changes_after_first_generation_are_reflected():
    house = make_house()
    before = parse_svg(house.generate_svg()).panels
    house.add_chimney('roof_panel_left', 30, 30)
    after = parse_svg(house.generate_svg()).panels
    assert 'chimney_front_0' not in before and 'chimney_front_0' in after
    house.clear_components()
    assert 'chimney_front_0' not in parse_svg(house.generate_svg()).panels


def test_failed_placement_raises_with_reason_and_changes_nothing():
    house = make_house()
    with pytest.raises(PlacementError, match='roof panel'):
        house.add_chimney('floor', 10, 10)
    with pytest.raises(PlacementError, match='does not fit'):
        house.add_window('side_wall_left', 500, 500)
    assert not house.architectural_config.chimneys and not house.architectural_config.windows


@pytest.mark.parametrize('preset', ['basic', 'farmhouse', 'tudor', 'german', 'stone'])
def test_presets_generate(preset):
    house = HouseMaker(architectural_preset=preset)
    assert len(parse_svg(house.generate_svg()).panels) >= 7


def test_unimplemented_roof_types_warn_instead_of_silently_ignoring():
    with pytest.warns(UserWarning, match='not implemented'):
        HouseMaker(roof_type=RoofType.HIP)
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        HouseMaker(roof_type=RoofType.GABLE)


def test_cutting_summary_counts_every_panel():
    house = make_house(chimneys=[('roof_panel_left', 30, 30)])
    summary = house.get_cutting_summary()
    assert summary['total_panels'] == len(house.build_panels())
    assert summary['total_cut_length_mm'] > 0
    assert all(d['area'] > 0 for d in summary['panel_details'].values())


def _cli(*args):
    env = dict(os.environ, PYTHONPATH=PARENT)
    return subprocess.run([sys.executable, os.path.join(PARENT, 'house_maker', 'generate_house.py'), *args],
                          env=env, capture_output=True, text=True)


def test_cli_generates_with_chimney_and_dormer(tmp_path):
    out = tmp_path / 'h.svg'
    r = _cli('-o', str(out), '--length', '160', '--width', '120', '--height', '90',
             '--add-chimney', '--chimney-x', '30', '--add-additional-gable',
             '--additional-gable-x', '90', '--additional-gable-panel', 'roof_panel_left')
    assert r.returncode == 0, r.stdout + r.stderr
    panels = parse_svg(out.read_text()).panels
    assert 'chimney_casing_0' in panels and 'additional_gable_front_0' in panels


def test_cli_reports_placement_problem_cleanly(tmp_path):
    r = _cli('-o', str(tmp_path / 'x.svg'), '--add-chimney', '--chimney-x', '500')
    assert r.returncode == 1 and 'Cannot place chimney' in r.stdout


def test_kerf_defaults_to_0_1_everywhere(tmp_path):
    from house_maker import HouseGeometry
    assert HouseGeometry(100, 80, 70, 45, 3, 15).kerf == 0.1
    assert HouseMaker().geometry.kerf == 0.1
    r = _cli('-o', str(tmp_path / 'k.svg'), '--verbose')
    assert 'Kerf compensation: 0.1mm' in r.stdout


def test_assembly_instructions_say_how_much_ridge_finishing_is_needed():
    exact = HouseMaker(gable_angle=45).get_assembly_instructions()
    assert not any('ridge' in line for line in exact)
    shallow = ' '.join(HouseMaker(gable_angle=30, material_thickness=3.0).get_assembly_instructions())
    assert 'overlap' in shallow and '1.5 mm' in shallow                       # 3 * cos(60 deg)
    steep = ' '.join(HouseMaker(gable_angle=60, material_thickness=3.0).get_assembly_instructions())
    assert 'wedge gap' in steep and '1.7 mm' in steep                         # 3 * tan(30 deg)
