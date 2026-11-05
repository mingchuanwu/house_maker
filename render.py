"""Render placed panels to an SVG document. Knows about CSS classes and labels, not about houses."""

from typing import Dict, List, Tuple

from .constants import COORDINATE_PRECISION
from .panel import Panel

LASER_LINE_WIDTH = 0.0254                    # 0.001 inch hairline for cut lines
DECORATIVE_LINE_WIDTH = LASER_LINE_WIDTH * 3  # visually distinct engraving lines
FONT_SIZE = 2.5                              # label text height in *user units* (= mm: the viewBox is in mm)
LABEL_OFFSET = 3.0                           # label top below the panel's cut extent
LABEL_HEIGHT = FONT_SIZE                     # vertical space reserved for the label text
MARGIN = 10.0

_P = COORDINATE_PRECISION


def _style_block() -> List[str]:
    def rule(cls, stroke, width):
        return [f'      .{cls} {{', f'        stroke: {stroke};', f'        stroke-width: {width:.6f}mm;',
                '        fill: none;', '        stroke-linecap: round;', '        stroke-linejoin: round;',
                '      }']
    lines = ['  <defs>', '    <style type="text/css">']
    lines += rule('cut-line', '#FF0000', LASER_LINE_WIDTH)
    for cls in ('decorative-line', 'chimney-pattern', 'roof-pattern', 'score-line'):
        lines += rule(cls, '#000000', DECORATIVE_LINE_WIDTH)
    lines += ['      .label-text {', '        font-family: Arial, sans-serif;', f'        font-size: {FONT_SIZE}px;',
              '        fill: #666666;', '        text-anchor: middle;',
              '        dominant-baseline: text-before-edge;', '      }',
              '    </style>', '  </defs>']
    return lines


CHAR_WIDTH = 0.6 * FONT_SIZE      # generous label width per character (Arial averages ~0.55em)


def label_reserve(include_labels: bool) -> float:
    return LABEL_OFFSET + LABEL_HEIGHT if include_labels else 0.0


def item_size(panel: Panel, include_labels: bool) -> Tuple[float, float]:
    """Space a panel needs on the sheet: its cut extent, widened/heightened to fit its label."""
    width = panel.bbox.width
    if include_labels:
        width = max(width, len(panel.label) * CHAR_WIDTH)
    return width, panel.bbox.height + label_reserve(include_labels)


def render_svg(panels: List[Panel], positions: Dict[str, Tuple[float, float]],
               include_labels: bool = True) -> Tuple[str, float, float]:
    """
    Args:
        positions: {panel.name: (x, y)} of each panel's cut-extent top-left corner on the sheet.
    Returns: (svg text, width, height)
    """
    sizes = {p.name: item_size(p, include_labels) for p in panels}
    max_x = max(positions[p.name][0] + sizes[p.name][0] for p in panels)
    max_y = max(positions[p.name][1] + sizes[p.name][1] for p in panels)
    width, height = max_x + 2 * MARGIN, max_y + 2 * MARGIN

    out = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        '<svg xmlns="http://www.w3.org/2000/svg"',
        f'     width="{width:.{_P}f}mm"',
        f'     height="{height:.{_P}f}mm"',
        f'     viewBox="0 0 {width:.{_P}f} {height:.{_P}f}">',
        '',
        '  <!-- HouseMaker Generated SVG for Laser Cutting -->',
        f'  <!-- Line width: {LASER_LINE_WIDTH}mm (hairline precision) -->',
        '',
        *_style_block(),
        '',
        f'  <g id="house_box_panels" transform="translate({MARGIN:.{_P}f},{MARGIN:.{_P}f})">',
    ]
    for p in panels:
        px, py = positions[p.name]
        px += (sizes[p.name][0] - p.bbox.width) / 2          # centre the panel in its slot
        tx, ty = px - p.bbox.min_x, py - p.bbox.min_y
        out.append(f'    <!-- {p.label} -->')
        out.append(f'    <g id="{p.name}" transform="translate({tx:.{_P}f},{ty:.{_P}f})">')
        for d in p.cut:
            out.append(f'      <path class="cut-line" d="{d}" />')
        for d in p.score:
            out.append(f'      <path class="score-line" d="{d}" />')
        if p.pattern and p.pattern.strip():
            out.append(f'      <path class="{p.pattern_class}" d="{p.pattern}" />')
        if include_labels:
            lx = p.bbox.min_x + p.bbox.width / 2
            ly = p.bbox.max_y + LABEL_OFFSET
            out.append(f'      <text class="label-text" x="{lx:.{_P}f}" y="{ly:.{_P}f}">{p.label}</text>')
        out.append('    </g>')
        out.append('')
    out += ['  </g>', '</svg>']
    return '\n'.join(out), width, height
