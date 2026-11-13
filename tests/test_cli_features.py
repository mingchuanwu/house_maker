"""Repeatable --dormer / --chimney CLI flags: 'SIDE[:key=value]...' specs, several features on one roof panel."""

import argparse
import pathlib
import subprocess
import sys

import pytest

from house_maker.generate_house import FEATURE_KEYS, feature_spec

PKG = pathlib.Path(__file__).resolve().parent.parent


def test_spec_fills_defaults_and_accepts_both_side_names():
    text, panel, v = feature_spec('dormer')('left:x=25:y=30:width=35:wall=12')
    assert (text, panel) == ('left:x=25:y=30:width=35:wall=12', 'roof_panel_left')
    assert v == {**FEATURE_KEYS['dormer'], 'x': 25.0, 'y': 30.0, 'width': 35.0, 'wall': 12.0}
    assert feature_spec('chimney')('roof_panel_right')[1:] == ('roof_panel_right', FEATURE_KEYS['chimney'])
    assert feature_spec('chimney')('right:height=30')[2]['height'] == 30.0


@pytest.mark.parametrize('kind,text,why', [
    ('dormer', 'top:x=1', 'roof side'),
    ('dormer', 'left:depth=5', 'key from'),               # depth is a chimney key
    ('chimney', 'left:wall=5', 'key from'),
    ('dormer', 'left:x', 'key=value'),
    ('dormer', 'left:x=abc', 'not a number'),
    ('dormer', 'left:x=1:x=2', 'twice'),
])
def test_bad_specs_are_rejected_with_the_reason(kind, text, why):
    with pytest.raises(argparse.ArgumentTypeError, match=why):
        feature_spec(kind)(text)


def run(tmp_path, *args):
    out = tmp_path / 'h.svg'
    r = subprocess.run([sys.executable, '-m', 'house_maker.generate_house', '-o', str(out), '--3d', 'none', *args],
                       capture_output=True, text=True, cwd=PKG.parent)
    return r, (out.read_text() if out.exists() else '')


def test_several_dormers_and_a_chimney_on_one_roof(tmp_path):
    r, svg = run(tmp_path, '--length', '200', '--width', '140', '--height', '100', '--angle', '45',
                 '--chimney', 'left:x=90:y=20:width=12', '--dormer', 'left:x=25:y=30:width=35',
                 '--dormer', 'left:x=140:y=30:width=35:wall=12', '--dormer', 'right:x=80:y=25:width=40')
    assert r.returncode == 0, r.stdout + r.stderr
    for name in ('chimney_front_0', 'additional_gable_front_0', 'additional_gable_front_1', 'additional_gable_front_2',
                 'additional_gable_cheek_left_1'):
        assert f'id="{name}"' in svg, name
    assert 'additional_gable_cheek_left_0' not in svg               # walls only on the dormer that asked for them


def test_an_overlapping_feature_names_its_flag_and_proposes_a_fit(tmp_path):
    r, _ = run(tmp_path, '--length', '200', '--width', '140', '--height', '100',
               '--chimney', 'left:x=90:y=20', '--dormer', 'left:x=85:y=20:width=30')
    assert r.returncode == 1
    assert '--dormer left:x=85:y=20:width=30' in r.stdout and 'overlaps another roof feature' in r.stdout
    assert 'It would fit with' in r.stdout


def test_a_typo_stops_before_anything_is_built(tmp_path):
    r, svg = run(tmp_path, '--dormer', 'left:widht=30')
    assert r.returncode == 2 and 'widht' in r.stderr and not svg


@pytest.mark.parametrize('name,model', [('h.stl', 'stl'), ('h.3mf', '3mf'), ('h.glb', 'all')])
def test_a_3d_model_never_overwrites_the_svg(tmp_path, name, model):
    out = tmp_path / name
    r = subprocess.run([sys.executable, '-m', 'house_maker.generate_house', '-o', str(out), '--3d', model],
                       capture_output=True, text=True, cwd=PKG.parent)
    assert r.returncode != 0 and 'would be overwritten' in r.stderr, r.stdout + r.stderr
    assert not out.exists()


def test_the_3d_model_is_written_next_to_the_svg(tmp_path):
    out = tmp_path / 'h.svg'
    r = subprocess.run([sys.executable, '-m', 'house_maker.generate_house', '-o', str(out), '--3d', 'stl'],
                       capture_output=True, text=True, cwd=PKG.parent)
    assert r.returncode == 0, r.stdout + r.stderr
    assert out.read_text().lstrip().startswith('<?xml') and (tmp_path / 'h.stl').stat().st_size > 84
