"""
Panel: the single contract between "what to build" (builders) and "how to lay out / draw it".

A Panel is expressed in its own local coordinates. Layout decides where it goes; the renderer
translates it. Builders never know about other panels, the sheet, or CSS.
"""

from dataclasses import dataclass, field
from functools import cached_property
from typing import Dict, List, Optional

from .geometry import Point
from .joints import JointSpec, SlotSpec
from .svgpath import BBox, parse_path, path_bbox, union_bbox

# Pattern line classes understood by the renderer
PATTERN_DECORATIVE = 'decorative-line'
PATTERN_ROOF = 'roof-pattern'
PATTERN_CHIMNEY = 'chimney-pattern'


@dataclass
class Panel:
    name: str                       # unique id, also the SVG group id
    label: str                      # human readable label printed under the panel
    cut: List[str]                  # closed outlines and holes (laser cut lines)
    score: List[str] = field(default_factory=list)      # engraved / scored lines
    pattern: str = ''               # decorative engraving (single path string)
    pattern_class: str = PATTERN_DECORATIVE
    nominal_size: Optional[tuple] = None      # (width, height) of the nominal panel (without tabs)
    # Construction record, so mating edges can be checked against what was actually drawn
    corners: List[Point] = field(default_factory=list)          # nominal outline corners, CCW
    edge_names: List[str] = field(default_factory=list)         # edge i runs corners[i] -> corners[i+1]
    joints: Dict[str, JointSpec] = field(default_factory=dict)  # edge name -> planned fingers
    slots: List[SlotSpec] = field(default_factory=list)         # internal slots

    @cached_property
    def bbox(self) -> BBox:
        """Actual cut extent, including protruding finger tabs."""
        return union_bbox([path_bbox(d) for d in self.cut])

    @cached_property
    def cut_length(self) -> float:
        total = 0.0
        for d in self.cut:
            for sub in parse_path(d):
                pts = sub + sub[:1]
                total += sum(((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5 for a, b in zip(pts, pts[1:]))
        return total

    @cached_property
    def area(self) -> float:
        """Material area: outer outline minus holes (shoelace)."""
        def shoelace(pts):
            return abs(sum(a.x * b.y - b.x * a.y for a, b in zip(pts, pts[1:] + pts[:1]))) / 2
        areas = sorted((shoelace(sub) for d in self.cut for sub in parse_path(d)), reverse=True)
        return areas[0] - sum(areas[1:]) if areas else 0.0
