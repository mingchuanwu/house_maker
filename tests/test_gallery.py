"""The house gallery: every entry builds through the CLI's own code path, and the page is complete and self-contained."""

import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess

import pytest

from house_maker.gallery import HOUSES, build_gallery, command
from house_maker.generate_house import build_house, create_parser

HERE = pathlib.Path(__file__).resolve().parent
PKG = HERE.parent


@pytest.mark.parametrize('entry', HOUSES, ids=lambda e: e['name'])
def test_every_gallery_house_builds_from_its_command(entry):
    args = create_parser().parse_args(shlex.split(entry['args']))
    house = build_house(args)
    assert house.build_panels()
    assert command(entry).startswith('house-maker')
    assert entry['description'] and entry['title']


def test_names_are_unique():
    names = [e['name'] for e in HOUSES]
    assert len(names) == len(set(names))


@pytest.fixture(scope='module')
def gallery(tmp_path_factory):
    out = tmp_path_factory.mktemp('gallery')
    return out, build_gallery(out)


def test_page_has_a_row_view_and_preview_per_house(gallery):
    out, index = gallery
    page = index.read_text(encoding='utf-8')
    assert '/*__' not in page and '<!--__' not in page
    assert page.count('<script') == 3 and 'src=' not in page and 'https://' not in page
    data = json.loads(re.search(r'<script id="gallery-data" type="application/json">(.*?)</script>', page, re.S).group(1))
    assert len(data) == len(HOUSES) == page.count('<tr>') - 1                   # header row + one per house
    for e in HOUSES:
        assert (out / 'views' / f"{e['name']}.view.html").exists()
        assert command(e).replace('"', '&quot;') in page or command(e) in page


def _jsdom():
    for cand in (os.environ.get('JSDOM_PATH'), str(PKG / 'node_modules' / 'jsdom')):
        if cand and pathlib.Path(cand).exists():
            return cand
    return None


@pytest.mark.skipif(shutil.which('node') is None or _jsdom() is None, reason='needs node + jsdom')
def test_page_loads_in_jsdom(gallery):
    _, index = gallery
    r = subprocess.run(['node', str(HERE / 'gallery_dom_smoke.js'), str(index), str(len(HOUSES))],
                       capture_output=True, text=True, env=dict(os.environ, JSDOM_PATH=_jsdom()))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert 'gallery smoke test passed' in r.stdout


def test_committed_gallery_is_up_to_date(tmp_path):
    """gallery/ in the repository is what `make gallery` writes now (rebuild it after changing houses or features)."""
    fresh = build_gallery(tmp_path)
    committed = PKG / 'gallery' / 'index.html'
    assert committed.exists(), "run `make gallery`"
    assert committed.read_text(encoding='utf-8') == fresh.read_text(encoding='utf-8'), "gallery is stale: run `make gallery`"
