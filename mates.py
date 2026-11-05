"""
Declared mating relationships between panels, as data.

Used by the review tool (snap two panels together, ghost a tab inside its slot) and available to
tests. Two kinds:

* ``edge``     two edges that touch when the panels are laid flat next to each other. Panel B's edge
               runs the opposite way to A's; point ``s_b`` (from B's edge start) meets point
               ``s_a = shift + (len_b - s_b)`` of A's edge. ``shift`` is chosen so the fingers line up.
* ``tab_slot`` a tab on one panel's edge passes through an internal slot of another panel.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .panel import Panel

EDGE = 'edge'
TAB_SLOT = 'tab_slot'


@dataclass(frozen=True)
class Mate:
    kind: str
    a: Tuple[str, str]               # (panel, edge)
    b: Tuple[str, object]            # edge mate: (panel, edge); tab_slot: (panel, slot index)
    shift: float = 0.0
    note: str = ''


def _edge_length(panel: Panel, edge: str) -> float:
    i = panel.edge_names.index(edge)
    p, q = panel.corners[i], panel.corners[(i + 1) % len(panel.corners)]
    return ((q.x - p.x) ** 2 + (q.y - p.y) ** 2) ** 0.5


def edge_shift(a: Panel, a_edge: str, b: Panel, b_edge: str) -> float:
    """Offset that makes the fingers of the two edges coincide (centres the edges if no fingers)."""
    la, lb = _edge_length(a, a_edge), _edge_length(b, b_edge)
    ja, jb = a.joints.get(a_edge), b.joints.get(b_edge)
    if ja and jb:      # align finger centres (drawn widths differ by the kerf)
        centre = lambda f: (f[0] + f[1]) / 2
        return centre(ja.nominal[0]) - lb + centre(jb.nominal[-1])
    return (la - lb) / 2


def _has_edge(panels: Dict[str, Panel], name: str, edge: str) -> bool:
    return name in panels and edge in panels[name].edge_names


def declared_mates(panels: Dict[str, Panel]) -> List[Mate]:
    """All mates that can be derived from the panels present (by naming convention)."""
    out: List[Mate] = []

    def edge(a: str, ae: str, b: str, be: str, note: str = ''):
        if _has_edge(panels, a, ae) and _has_edge(panels, b, be):
            out.append(Mate(EDGE, (a, ae), (b, be), edge_shift(panels[a], ae, panels[b], be), note))

    def tab_slot(a: str, ae: str, b: str, slot: int, note: str = ''):
        if (_has_edge(panels, a, ae) and ae in panels[a].joints and b in panels
                and slot < len(panels[b].slots)):
            out.append(Mate(TAB_SLOT, (a, ae), (b, slot), 0.0, note))

    # --- main box
    edge('floor', 'bottom', 'side_wall_left', 'bottom', 'floor ↔ side wall')
    edge('floor', 'top', 'side_wall_right', 'bottom', 'floor ↔ side wall')
    edge('floor', 'right', 'gable_wall_front', 'bottom', 'floor ↔ gable wall')
    edge('floor', 'left', 'gable_wall_back', 'bottom', 'floor ↔ gable wall')
    edge('side_wall_left', 'right', 'gable_wall_front', 'left', 'side wall ↔ gable wall')
    edge('side_wall_left', 'left', 'gable_wall_back', 'right', 'side wall ↔ gable wall')
    edge('side_wall_right', 'right', 'gable_wall_back', 'left', 'side wall ↔ gable wall')
    edge('side_wall_right', 'left', 'gable_wall_front', 'right', 'side wall ↔ gable wall')
    edge('roof_panel_right', 'ridge', 'roof_panel_left', 'ridge', 'roof ridge')
    for gable, slot in (('gable_wall_front', 0), ('gable_wall_back', 1)):
        tab_slot(gable, 'roof_left', 'roof_panel_left', slot, 'gable tab → roof slot')
        tab_slot(gable, 'roof_right', 'roof_panel_right', slot, 'gable tab → roof slot')

    # --- chimneys (suffix _<index>)
    for name in panels:
        if name.startswith('chimney_front_'):
            i = name.rsplit('_', 1)[1]
            for wall, end in (('front', 'front_end'), ('back', 'back_end')):
                edge(f'chimney_{wall}_{i}', 'left', f'chimney_left_{i}', end, 'chimney corner')
                edge(f'chimney_{wall}_{i}', 'right', f'chimney_right_{i}', end, 'chimney corner')

    # --- dormers
    for name in panels:
        if name.startswith('additional_gable_front_'):
            i = name.rsplit('_', 1)[1]
            edge(f'additional_gable_roof_right_{i}', 'ridge', f'additional_gable_roof_left_{i}', 'ridge', 'dormer ridge')
            tab_slot(name, 'rake_left', f'additional_gable_roof_left_{i}', 0, 'dormer face tab → roof slot')
            tab_slot(name, 'rake_right', f'additional_gable_roof_right_{i}', 0, 'dormer face tab → roof slot')
    return out
