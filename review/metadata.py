"""JSON-able description of panels and a test case, consumed by the review page."""

from dataclasses import asdict
from typing import Dict, Iterable, List

from ..mates import Mate, TAB_SLOT, declared_mates
from ..panel import Panel


def panel_record(panel: Panel) -> dict:
    b = panel.bbox
    return {
        'name': panel.name,
        'label': panel.label,
        'nominal_size': list(panel.nominal_size) if panel.nominal_size else None,
        'bbox': [b.min_x, b.min_y, b.max_x, b.max_y],
        'corners': [[c.x, c.y] for c in panel.corners],
        'edges': list(panel.edge_names),
        'joints': {e: {'role': j.role, 'length': j.length, 'depth': j.depth,
                       'fingers': [list(f) for f in j.fingers],
                       'nominal': [list(f) for f in j.nominal]} for e, j in panel.joints.items()},
        'slots': [asdict(s) for s in panel.slots],
    }


def mate_record(mate: Mate) -> dict:
    return {'kind': mate.kind, 'a': list(mate.a), 'b': list(mate.b), 'shift': mate.shift, 'note': mate.note}


def case_record(group: str, case: str, title: str, house, panels: Iterable[Panel]) -> dict:
    """Everything the page needs to know about one SVG besides the SVG itself."""
    panels = list(panels)
    by_name: Dict[str, Panel] = {p.name: p for p in panels}
    mates: List[Mate] = [m for m in declared_mates(by_name)
                         if m.a[0] in by_name and m.b[0] in by_name]
    g = house.geometry
    return {
        'group': group, 'case': case, 'title': title,
        'house': house.describe(),
        'material': {'thickness': g.thickness, 'kerf': g.kerf, 'finger_length': g.finger_length},
        'panels': [panel_record(p) for p in panels],
        'mates': [mate_record(m) for m in mates],
    }
