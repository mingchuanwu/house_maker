"""The review page's data (Python side) and its geometry core (node)."""

import json
import os
import pathlib
import shutil
import subprocess

import pytest

from house_maker.review import __main__ as review_cli
from house_maker.review.builder import build_review
from house_maker.review.metadata import case_record
from .conftest import make_house
from .components.test_box_seams import ASSEMBLIES

HERE = pathlib.Path(__file__).resolve().parent
CORE = HERE.parent / 'review' / 'viewer_core.js'


def _rec(group, case, house, panels):
    panels = list(panels)
    rec = case_record(group, case, '', house, panels)
    rec['svg'] = house.render_panels(panels)
    return rec


def _cases():
    out = []
    for name, picks in ASSEMBLIES.items():
        h = make_house(gable_angle=35, length=120, width=90, height=70)
        out.append(_rec('box_seams', f'{name}_a35', h, [p for p in h.build_panels() if p.name in picks]))
    h = make_house(gable_angle=45, length=160, width=120, height=90, chimneys=[('roof_panel_left', 25, 30, 14, 20, 30)])
    out.append(_rec('chimney', 'chimney_a45', h, h.build_panels()))
    h = make_house(length=200, width=160, height=90, gable_angle=35, dormers=[('roof_panel_right', 40, 20, 70)])
    out.append(_rec('dormer', 'large_dormer', h, h.build_panels()))
    h = make_house(gable_angle=30)
    out.append(_rec('box_seams', 'gable_wall_to_roof_a30', h, h.build_panels()))
    h = make_house(gable_angle=50, kerf=0.0, length=140, width=100, height=80,
                   chimneys=[('roof_panel_right', 30, 25, 12, 16, 30)])
    out.append(_rec('chimney', 'kerf0_a50', h, h.build_panels()))
    return out


def test_case_record_is_json_and_complete():
    for rec in _cases():
        json.dumps(rec)                                        # serialisable
        names = {p['name'] for p in rec['panels']}
        for m in rec['mates']:
            assert m['a'][0] in names and m['b'][0] in names
        for p in rec['panels']:
            assert len(p['corners']) == len(p['edges']) >= 3
            assert p['bbox'][0] < p['bbox'][2]
    assert 'chimneys' in _cases()[-2]['house']


@pytest.mark.skipif(shutil.which('node') is None, reason='node not installed')
def test_snap_geometry_core_in_node():
    r = subprocess.run(['node', str(HERE / 'review_core_test.js'), str(CORE)],
                       input=json.dumps(_cases()), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert 'ok:' in r.stdout


def _jsdom():
    for cand in (os.environ.get('JSDOM_PATH'), str(HERE.parent / 'node_modules' / 'jsdom')):
        if cand and pathlib.Path(cand).exists():
            return cand
    return None


def _write_gallery(root):
    for name, picks in ASSEMBLIES.items():
        for angle in (30, 60):
            h = make_house(gable_angle=angle, length=120, width=90, height=70)
            panels = [p for p in h.build_panels() if p.name in picks]
            folder = root / 'box_seams'
            folder.mkdir(parents=True, exist_ok=True)
            case = f'{name}_a{angle}'
            (folder / f'{case}.svg').write_text(h.render_panels(panels), encoding='utf-8')
            (folder / f'{case}.json').write_text(json.dumps(case_record('box_seams', case, 't', h, panels)), encoding='utf-8')
    return build_review(root)


@pytest.mark.skipif(shutil.which('node') is None or _jsdom() is None,
                    reason='needs node + jsdom (set JSDOM_PATH=<.../node_modules/jsdom>)')
def test_review_page_end_to_end_in_jsdom(tmp_path):
    """Load the real page, select/drag/rotate/snap panels, drop a note, export the feedback."""
    page = _write_gallery(tmp_path)
    r = subprocess.run(['node', str(HERE / 'review_dom_smoke.js'), str(page)], capture_output=True, text=True,
                       env=dict(os.environ, JSDOM_PATH=_jsdom()))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert 'dom smoke test passed' in r.stdout


def test_review_page_is_one_self_contained_file(tmp_path):
    page = _write_gallery(tmp_path).read_text(encoding='utf-8')
    assert page.count('<script') == 3 and 'src=' not in page and 'http://' not in page.replace('http://www.w3.org', '')
    assert '/*__' not in page                       # every placeholder was filled


def test_collect_moves_downloaded_feedback_and_summarises(tmp_path, capsys):
    inbox, dest = tmp_path / 'inbox', tmp_path / 'feedback'
    inbox.mkdir()
    (inbox / 'house_review_20261031-1200-abc123_20261031121500.json').write_text(json.dumps({
        'schema': 'house-review/1', 'run': 'r1', 'exported_at': '2026-10-31T12:15:00Z',
        'cases': {'chimney/a35': {'notes': 'overall ok', 'poses': {'chimney_front_0': {}}, 'pins': [
            {'id': 'p1', 'panel': 'chimney_left_0', 'target': {'type': 'finger', 'edge': 'front_end', 'finger': 1},
             'category': 'bug', 'severity': 'high', 'status': 'open', 'text': 'notch 0.3mm too shallow'}]}}}))
    (inbox / 'unrelated.json').write_text('{}')
    assert review_cli.main(['collect', '--inbox', str(inbox), '--dest', str(dest)]) == 0
    out = capsys.readouterr().out
    assert 'BUG/high/open @ chimney_left_0 · front_end finger#2: notch 0.3mm too shallow' in out
    assert [p.name for p in dest.iterdir()] == ['house_review_20261031-1200-abc123_20261031121500.json']
    assert (inbox / 'unrelated.json').exists() and not list(inbox.glob('house_review_*'))
    assert review_cli.main(['collect', '--inbox', str(inbox), '--dest', str(dest)]) == 1       # nothing left
