"""Assemble the single-file review page from the SVG + JSON files written by the component tests."""

import hashlib
import json
import pathlib
import time
from typing import List

from . import DEFAULT_INBOX

HERE = pathlib.Path(__file__).resolve().parent


def collect_cases(root: pathlib.Path) -> List[dict]:
    """Every ``<group>/<case>.svg`` with a sibling ``<case>.json`` metadata file."""
    cases = []
    for meta_path in sorted(root.glob('*/*.json')):
        svg_path = meta_path.with_suffix('.svg')
        if not svg_path.exists():
            continue
        rec = json.loads(meta_path.read_text(encoding='utf-8'))
        rec['svg'] = svg_path.read_text(encoding='utf-8')
        cases.append(rec)
    return cases


def build_review(root, inbox: str = DEFAULT_INBOX) -> pathlib.Path:
    root = pathlib.Path(root)
    cases = collect_cases(root)
    digest = hashlib.sha1(json.dumps([c['svg'] for c in cases]).encode()).hexdigest()[:6]
    run = time.strftime('%Y%m%d-%H%M') + '-' + digest
    data = json.dumps({'run': run, 'inbox': inbox, 'cases': cases}).replace('</', '<\\/')
    page = (HERE / 'viewer.html').read_text(encoding='utf-8')
    page = (page.replace('/*__CSS__*/', (HERE / 'viewer.css').read_text(encoding='utf-8'))
                .replace('/*__CORE__*/', (HERE / 'viewer_core.js').read_text(encoding='utf-8'))
                .replace('/*__APP__*/', (HERE / 'viewer_app.js').read_text(encoding='utf-8'))
                .replace('/*__DATA__*/', data))
    out = root / 'review.html'
    out.write_text(page, encoding='utf-8')
    return out
