"""
Build the gallery: every house in `houses.HOUSES` is made by running its command line through the CLI's own
`build_house`, then written as a full 3D viewer page (views/NAME.view.html) and added to index.html - a table of the
command, a description and a small inline 3D preview (orbit only) - all self-contained, no server, no network.

    python -m house_maker.gallery [OUT_DIR]          (default: this directory; `make gallery`)
"""

import html
import json
import pathlib
import shlex
from typing import List

from ..generate_house import build_house, create_parser
from ..viewer3d import build_payload
from .houses import HOUSES

HERE = pathlib.Path(__file__).resolve().parent
VIEWER3D = HERE.parent / 'viewer3d'
PREVIEW_DECIMALS = 2              # mm: plenty for a thumbnail, and keeps index.html small


def command(entry: dict) -> str:
    return ('house-maker ' + entry['args']).strip()


def facts(house) -> str:
    """A line of what the house is made of, counted from the build."""
    cfg, g = house.architectural_config, house.geometry
    bits = [f"{g.x:g} x {g.y:g} x {g.z:g} mm", f"{g.theta:g}° roof", f"{len(house.build_panels())} parts"]
    for label, items in (('window', cfg.windows), ('dormer', cfg.additional_gables), ('cross gable', cfg.cross_gables),
                         ('chimney', cfg.chimneys)):
        if items:
            bits.append(f"{len(items)} {label}{'s' if len(items) > 1 else ''}")
    return ' · '.join(bits)


def _preview(payload: dict) -> dict:
    parts = [{'color': p['color'], 'vertices': [round(c, PREVIEW_DECIMALS) for c in p['vertices']],
              'triangles': p['triangles']} for p in payload['parts']]
    return {'parts': parts}


def build_gallery(out_dir=HERE) -> pathlib.Path:
    out = pathlib.Path(out_dir)
    (out / 'views').mkdir(parents=True, exist_ok=True)
    parser = create_parser()
    rows: List[str] = []
    previews = []
    for i, entry in enumerate(HOUSES):
        house = build_house(parser.parse_args(shlex.split(entry['args'])))
        view = out / 'views' / f"{entry['name']}.view.html"
        house.generate_view(str(view), title=entry['title'])
        previews.append(_preview(build_payload(house.geometry, house.architectural_config, house.build_panels(),
                                               entry['name'])))
        cmd = html.escape(command(entry))
        rows.append(f'''<tr>
  <td class="cmd"><pre><code>{cmd}</code></pre><button class="copy" data-cmd="{cmd}">Copy</button></td>
  <td class="desc"><b>{html.escape(entry['title'])}</b><p>{html.escape(entry['description'])}</p>
      <p class="facts">{html.escape(facts(house))}</p></td>
  <td class="view"><canvas class="preview" data-index="{i}" width="320" height="240"></canvas>
      <a href="views/{entry['name']}.view.html">open the full 3D viewer</a></td>
</tr>''')
    data = json.dumps(previews, separators=(',', ':')).replace('</', '<\\/')
    page = (HERE / 'index.template.html').read_text(encoding='utf-8')
    page = (page.replace('/*__CSS__*/', (HERE / 'gallery.css').read_text(encoding='utf-8'))
                .replace('<!--__ROWS__-->', '\n'.join(rows))
                .replace('/*__CORE__*/', (VIEWER3D / 'viewer_core.js').read_text(encoding='utf-8'))
                .replace('/*__PREVIEW__*/', (HERE / 'preview.js').read_text(encoding='utf-8'))
                .replace('/*__DATA__*/', data))
    index = out / 'index.html'
    index.write_text(page, encoding='utf-8')
    return index
