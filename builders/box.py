"""
Main box panels: floor, side walls, gable walls and roof panels.

The finger-joint *policy* (which edge is male/female, where fingers are inset) lives here, next to
the outlines it applies to. Joint mechanics are in `joints`, decoration and cutouts arrive as
plain data in `PanelFeatures`.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..constants import COORDINATE_PRECISION
from ..geometry import HouseGeometry, Point
from ..joints import FEMALE, MALE, FingerJointEngine, SlotSpec
from ..panel import Panel, PATTERN_DECORATIVE, PATTERN_ROOF

_P = COORDINATE_PRECISION


@dataclass(frozen=True)
class EdgePlan:
    name: str
    role: Optional[str] = None          # MALE | FEMALE | None (smooth edge)
    inset: float = 0.0                  # in units of material thickness
    count: Optional[int] = None         # force the number of fingers


@dataclass
class PanelFeatures:
    """Everything a builder needs to know about a panel's decoration, as plain data."""
    cutouts: List[str] = field(default_factory=list)   # extra through-cuts (windows, doors), local coords
    score: List[str] = field(default_factory=list)     # engraved lines (e.g. chimney footprint)
    pattern: str = ''                                  # decorative engraving


def _edges(*plans: EdgePlan) -> Tuple[EdgePlan, ...]:
    return plans


_SIDE_WALL = _edges(EdgePlan('bottom', FEMALE), EdgePlan('right', MALE),
                    EdgePlan('top'), EdgePlan('left', MALE))
# Gable walls: bottom is wider than the floor edge it mates with (inset by 1 thickness each side);
# sloped edges carry exactly ONE tab, matching the single slot cut into the roof panel.
_GABLE_WALL = _edges(EdgePlan('bottom', FEMALE, inset=1.0), EdgePlan('right', FEMALE),
                     EdgePlan('roof_right', MALE, count=1), EdgePlan('roof_left', MALE, count=1),
                     EdgePlan('left', FEMALE))

EDGE_PLANS: Dict[str, Tuple[EdgePlan, ...]] = {
    'floor': _edges(EdgePlan('bottom', MALE), EdgePlan('right', MALE),
                    EdgePlan('top', MALE), EdgePlan('left', MALE)),
    'side_wall_left': _SIDE_WALL,
    'side_wall_right': _SIDE_WALL,
    'gable_wall_front': _GABLE_WALL,
    'gable_wall_back': _GABLE_WALL,
    # Roof panels meet at the ridge (female on the left panel, male on the right one); the other
    # edges are smooth. Gable tabs pass through two slots near each end.
    'roof_panel_left': _edges(EdgePlan('ridge', FEMALE), EdgePlan('right'), EdgePlan('eave'),
                              EdgePlan('left')),
    'roof_panel_right': _edges(EdgePlan('ridge', MALE), EdgePlan('right'), EdgePlan('eave'),
                               EdgePlan('left')),
}


class BoxPanelBuilder:
    def __init__(self, geometry: HouseGeometry, engine: FingerJointEngine):
        geometry.validate_geometry()
        self.geometry = geometry
        self.engine = engine

    # ------------------------------------------------------------------ outlines
    def _corners(self, name: str) -> List[Point]:
        g = self.geometry
        w, h = g.get_panel_dimensions()[name]
        if name.startswith('gable_wall'):
            return [Point(0, 0), Point(w, 0), Point(w, g.z_kerf), Point(w / 2, h), Point(0, g.z_kerf)]
        return [Point(0, 0), Point(w, 0), Point(w, h), Point(0, h)]

    def _slots(self, name: str) -> List[SlotSpec]:
        """Slots for the gable tabs (positions come from HouseGeometry.roof_slot_rects)."""
        if not name.startswith('roof_panel'):
            return []
        return [self.engine.make_slot((x0 + x1) / 2, (y0 + y1) / 2, 'vertical')
                for x0, y0, x1, y1 in self.geometry.roof_slot_rects(name)]

    # ------------------------------------------------------------------ build
    def build(self, name: str, features: Optional[PanelFeatures] = None) -> Panel:
        features = features or PanelFeatures()
        plans = EDGE_PLANS[name]
        corners = self._corners(name)
        t = self.geometry.thickness

        specs = []
        for i, plan in enumerate(plans):
            a, b = corners[i], corners[(i + 1) % len(corners)]
            length = ((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5
            specs.append(self.engine.plan_edge(length, plan.role, plan.inset * t, plan.count)
                         if plan.role else None)
        joints = {plan.name: s for plan, s in zip(plans, specs) if s}
        path = self.engine.trace_outline(corners, specs)

        slots = self._slots(name)
        cut = [path] + [self.engine.slot_path(s) for s in slots] + list(features.cutouts)
        is_roof = name.startswith('roof_panel')
        return Panel(name=name, label=name.replace('_', ' ').title(), cut=cut,
                     score=list(features.score), pattern=features.pattern,
                     pattern_class=PATTERN_ROOF if is_roof else PATTERN_DECORATIVE,
                     nominal_size=self.geometry.get_panel_dimensions()[name],
                     corners=corners, edge_names=[p.name for p in plans], joints=joints, slots=slots)
