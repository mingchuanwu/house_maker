import json
import pathlib
from collections import defaultdict

import pytest

from house_maker import HouseMaker
from house_maker.review.builder import build_review
from house_maker.review.metadata import case_record

_SAVED = []     # (group, case, relative path, title) of every SVG written this session


def make_house(chimneys=(), dormers=(), **kw):
    """Build a HouseMaker; chimneys/dormers are (panel, x, y[, width, depth[, height]]) tuples."""
    kw.setdefault('auto_add_components', False)
    house = HouseMaker(**kw)
    for c in chimneys:
        house.add_chimney(*c)
    for d in dormers:
        house.add_additional_gable(*d)
    return house


@pytest.fixture
def mk():
    return make_house


def pytest_addoption(parser):
    parser.addoption('--svg-dir', default=None,
                     help='write SVGs of every component test (and an index.html) to this directory '
                          'for visual inspection')


@pytest.fixture(scope='session')
def svg_dir(request, tmp_path_factory):
    """--svg-dir if given, otherwise a throw-away temp dir."""
    given = request.config.getoption('--svg-dir')
    path = pathlib.Path(given).expanduser().resolve() if given else tmp_path_factory.mktemp('svgs')
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def save_svg(svg_dir):
    def _save(group, case, svg, title='', meta=None):
        folder = svg_dir / group
        folder.mkdir(exist_ok=True)
        (folder / f'{case}.svg').write_text(svg, encoding='utf-8')
        if meta is not None:                      # panel/mate description for the review page
            (folder / f'{case}.json').write_text(json.dumps(meta), encoding='utf-8')
        _SAVED.append((group, case, f'{group}/{case}.svg', title))
    return _save


@pytest.fixture
def inspect(save_svg):
    """
    inspect(group, case, house, select, title='') -> list of the selected Panels, and writes an SVG
    containing just those panels. `select` is a list of exact names and/or callables(name)->bool.
    """
    def _inspect(group, case, house, select, title=''):
        panels = house.build_panels()
        tests = [(lambda n, s=s: n == s) if isinstance(s, str) else s for s in select]
        chosen = [p for p in panels if any(t(p.name) for t in tests)]
        assert chosen, f"nothing selected from {[p.name for p in panels]}"
        save_svg(group, case, house.render_panels(chosen), title,
                 meta=case_record(group, case, title, house, chosen))
        return chosen
    return _inspect


def pytest_sessionfinish(session, exitstatus):
    given = session.config.getoption('--svg-dir', default=None)
    if not given or not _SAVED:
        return
    root = pathlib.Path(given).expanduser().resolve()
    groups = defaultdict(list)
    for group, case, rel, title in sorted(set(_SAVED)):
        groups[group].append((case, rel, title))
    body = []
    for group, items in groups.items():
        body.append(f'<h2 id="{group}">{group} ({len(items)})</h2>')
        for case, rel, title in items:
            body.append(f'<section><h3>{case}</h3><p>{title}</p><a href="{rel}">'
                        f'<img src="{rel}" style="max-width:100%;border:1px solid #ccc"></a></section>')
    nav = ' · '.join(f'<a href="#{g}">{g}</a>' for g in groups)
    (root / 'index.html').write_text(
        '<!doctype html><meta charset="utf-8"><title>Component gallery</title>'
        '<body style="font-family:sans-serif;max-width:1400px;margin:auto">'
        f'<h1>Component gallery</h1><p><b><a href="review.html">Open the interactive review page</a></b></p>'
        f'<p>{nav}</p>' + ''.join(body) + '</body>', encoding='utf-8')
    build_review(root)
