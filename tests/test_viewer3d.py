"""The built-in 3D viewer (`--3d view`): its payload (Python), its maths core and its page (node + jsdom)."""

import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

from house_maker import HouseMaker
from house_maker.viewer3d import build_page, build_payload, part_group
from house_maker.viewer3d.payload import DECIMALS, GROUPS

HERE = pathlib.Path(__file__).resolve().parent
PKG = HERE.parent
CORE = PKG / 'viewer3d' / 'viewer_core.js'


def full_house():
    h = HouseMaker(length=150, width=120, height=90, material_thickness=3, gable_angle=35)
    h.add_chimney('roof_panel_left', 25, 30, 10, 12, 30)
    h.add_additional_gable('roof_panel_right', 20, 20, 40)
    return h


@pytest.fixture(scope='module')
def house():
    return full_house()


@pytest.fixture(scope='module')
def payload(house):
    return build_payload(house.geometry, house.architectural_config, house.build_panels(), 'test')


def _page_data(page: str) -> dict:
    m = re.search(r'<script id="model-data" type="application/json">(.*?)</script>', page, re.S)
    return json.loads(m.group(1))


# ------------------------------------------------------------------ payload
def test_payload_has_every_part_of_the_model(house, payload):
    model = {p.name: p for p in house.build_model()}
    assert [p['name'] for p in payload['parts']] == list(model)
    for p in payload['parts']:
        mesh = model[p['name']].mesh
        assert len(p['vertices']) == 3 * len(mesh.vertices) and len(p['triangles']) == 3 * len(mesh.triangles)
        assert max(p['triangles']) < len(mesh.vertices) and min(p['triangles']) >= 0
        assert p['group'] in GROUPS and p['color'] == list(model[p['name']].color)
        # the very vertices and triangles of the model, in mm (only rounded for the page)
        assert p['vertices'] == pytest.approx([c for v in mesh.vertices for c in v], abs=10 ** -DECIMALS)
        assert p['triangles'] == [i for t in mesh.triangles for i in t]


def test_groups_cover_every_kind_of_part(payload):
    groups = {p['name']: p['group'] for p in payload['parts']}
    assert groups['floor'] == 'floor' and groups['side_wall_left'] == 'walls' and groups['roof_panel_left'] == 'roof'
    assert groups['gable_wall_front_d0_door_casing'] == 'casings' and groups['chimney_casing_0'] == 'chimney'
    assert groups['additional_gable_roof_left_0'] == 'dormer'
    assert part_group('gable_wall_back_w1_window_casing') == 'casings'


def _centre(vertices):
    xs, ys, zs = vertices[0::3], vertices[1::3], vertices[2::3]
    return [(min(c) + max(c)) / 2 for c in (xs, ys, zs)]


def test_explode_moves_every_part_away_from_what_it_belongs_to(payload):
    parts = {p['name']: p for p in payload['parts']}
    box = [p for p in payload['parts'] if p['group'] in ('floor', 'walls', 'roof')]
    house_c = _centre([c for p in box for c in _centre(p['vertices'])])
    for p in box:
        e = p['explode']
        assert math.isclose(math.hypot(*e), 1, abs_tol=1e-3), p['name']
        out = [a - b for a, b in zip(_centre(p['vertices']), house_c)]
        assert sum(a * b for a, b in zip(e, out)) > 0, f"{p['name']} explodes inward"
    assert parts['floor']['explode'] == [0, 0, -1]
    for name, p in parts.items():
        if p['group'] == 'casings':
            wall = re.sub(r'_[wd]\d+_(window|door)_casing$', '', name)
            assert p['explode'] == pytest.approx([1.5 * c for c in parts[wall]['explode']], abs=1e-3), name
    # chimney sides move apart from each other (and all of them along with their roof panel)
    left, right = parts['chimney_left_0']['explode'], parts['chimney_right_0']['explode']
    roof = parts['roof_panel_left']['explode']
    apart = [a - b for a, b in zip(left, right)]
    assert math.hypot(*apart) > 1.5
    for n in ('chimney_left_0', 'chimney_right_0', 'chimney_front_0', 'chimney_back_0', 'chimney_casing_0'):
        assert sum(a * b for a, b in zip(parts[n]['explode'], roof)) > 0.25, n


# ------------------------------------------------------------------ page
def test_page_is_one_self_contained_file(payload):
    page = build_page(payload)
    assert page.count('<script') == 3 and 'src=' not in page and 'http://' not in page and 'https://' not in page
    assert '/*__' not in page
    assert _page_data(page) == json.loads(json.dumps(payload))


def test_page_data_cannot_close_its_script_tag():
    page = build_page({'title': 'x</script><b>', 'units': 'mm', 'parts': []})
    assert page.count('</script>') == 3
    assert _page_data(page)['title'] == 'x</script><b>'
    assert '<title>x&lt;/script&gt;&lt;b&gt; - 3D view</title>' in page


def test_generate_view_returns_or_writes_the_page(tmp_path, house):
    page = house.generate_view()
    assert isinstance(page, str) and _page_data(page)['title'] == 'house'
    out = tmp_path / 'my_house.view.html'
    house.generate_view(str(out))
    assert _page_data(out.read_text(encoding='utf-8'))['title'] == 'my_house'


@pytest.mark.parametrize('mode,expected', [('view', {'.svg', '.view.html'}),
                                           ('all', {'.svg', '.3mf', '.stl', '.glb', '.view.html'})])
def test_cli_writes_the_viewer(tmp_path, mode, expected):
    out = tmp_path / 'h.svg'
    r = subprocess.run([sys.executable, '-m', 'house_maker.generate_house', '-o', str(out), '--3d', mode],
                       capture_output=True, text=True, cwd=PKG.parent)
    assert r.returncode == 0, r.stdout + r.stderr
    assert {p.name[1:] for p in tmp_path.iterdir()} == expected


# ------------------------------------------------------------------ node
@pytest.mark.skipif(shutil.which('node') is None, reason='node not installed')
def test_viewer_core_in_node():
    r = subprocess.run(['node', str(HERE / 'viewer3d_core_test.js'), str(CORE)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert 'ok: viewer3d core' in r.stdout


def _jsdom():
    for cand in (os.environ.get('JSDOM_PATH'), str(PKG / 'node_modules' / 'jsdom')):
        if cand and pathlib.Path(cand).exists():
            return cand
    return None


@pytest.mark.skipif(shutil.which('node') is None or _jsdom() is None,
                    reason='needs node + jsdom (set JSDOM_PATH=<.../node_modules/jsdom>)')
def test_viewer_page_in_jsdom(tmp_path, house):
    page = tmp_path / 'h.view.html'
    house.generate_view(str(page))
    r = subprocess.run(['node', str(HERE / 'viewer3d_dom_smoke.js'), str(page)], capture_output=True, text=True,
                       env=dict(os.environ, JSDOM_PATH=_jsdom()))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert 'dom smoke test passed' in r.stdout
