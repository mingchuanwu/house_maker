"""Parse HouseMaker SVG output into plain Python structures (black-box test helper)."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List

from house_maker.geometry import Point
from house_maker.svgpath import BBox, parse_path, union_bbox

_NS = '{http://www.w3.org/2000/svg}'
_TRANSLATE = re.compile(r'translate\(\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*\)')


@dataclass
class PanelDoc:
    id: str
    cut: List[List[Point]] = field(default_factory=list)      # sub-paths in *document* coordinates
    score: List[List[Point]] = field(default_factory=list)

    @property
    def bbox(self) -> BBox:
        return union_bbox([BBox(min(p.x for p in s), min(p.y for p in s),
                                max(p.x for p in s), max(p.y for p in s)) for s in self.cut])


@dataclass
class SvgDoc:
    width: float
    height: float
    panels: Dict[str, PanelDoc]

    @property
    def viewbox(self) -> BBox:
        return BBox(0, 0, self.width, self.height)


def _offset(transform: str):
    m = _TRANSLATE.search(transform or '')
    return (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)


def _shift(subpaths, dx, dy):
    return [[Point(p.x + dx, p.y + dy) for p in sub] for sub in subpaths]


def parse_svg(svg: str) -> SvgDoc:
    root = ET.fromstring(svg.split('?>', 1)[1] if svg.startswith('<?xml') else svg)
    vb = [float(v) for v in root.get('viewBox').split()]
    outer = root.find(f'{_NS}g')
    ox, oy = _offset(outer.get('transform'))
    panels: Dict[str, PanelDoc] = {}
    for g in outer.iter(f'{_NS}g'):
        if g is outer:
            continue
        px, py = _offset(g.get('transform'))
        doc = PanelDoc(g.get('id'))
        for path in g.findall(f'{_NS}path'):
            sub = _shift(parse_path(path.get('d')), ox + px, oy + py)
            cls = path.get('class')
            if cls == 'cut-line':
                doc.cut.extend(sub)
            elif cls == 'score-line':
                doc.score.extend(sub)
        if doc.cut:
            panels[doc.id] = doc
    return SvgDoc(vb[2], vb[3], panels)
