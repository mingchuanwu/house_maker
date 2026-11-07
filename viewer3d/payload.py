"""
The viewer's data: every part of the assembled model (`model3d`) with its group, colour, mesh and explode vector.

The explode vector is the offset of the part per millimetre of the viewer's explode slider. Panel frame normals
do not all point outward (the floor's points up, a chimney's front and back share one), so each direction is the
frame normal turned to point away from the centre of what the part belongs to:

* box panels (floor, walls, roof) move away from the centre of the house;
* chimney and dormer parts move away from the centre of their own assembly, plus with the roof panel they sit on;
* window/door casings move with their wall, half as far again, so they separate from it.
"""

import re
from typing import Dict, List, Sequence, Tuple

from ..config import ArchitecturalConfiguration
from ..geometry import HouseGeometry
from ..model3d import house_frames, panel_solid
from ..panel import Panel

Vec = Tuple[float, float, float]

GROUPS = ('floor', 'walls', 'roof', 'casings', 'chimney', 'dormer')
CASING_EXTRA = 1.5
DECIMALS = 4


def part_group(name: str) -> str:
    if name.startswith('chimney'):
        return 'chimney'
    if name.startswith('additional_gable'):
        return 'dormer'
    if 'casing' in name:
        return 'casings'
    if name.startswith('roof_panel'):
        return 'roof'
    if name == 'floor':
        return 'floor'
    return 'walls'


def _centre(vertices: Sequence[Vec]) -> Vec:
    xs, ys, zs = zip(*vertices)
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)


def _away(n: Vec, frm: Vec, to: Vec, fallback: Vec = (0.0, 0.0, 0.0)) -> Vec:
    """`n` or `-n`, whichever points from `frm` towards `to` (by `fallback` when `n` is square to that)."""
    d = sum(n[i] * (to[i] - frm[i]) for i in range(3))
    if abs(d) < 1e-6:
        d = sum(n[i] * fallback[i] for i in range(3))
    return n if d >= 0 else (-n[0], -n[1], -n[2])


def _add(a: Vec, b: Vec, k: float = 1.0) -> Vec:
    return (a[0] + k * b[0], a[1] + k * b[1], a[2] + k * b[2])


def _assembly(name: str):
    """('chimney' | 'dormer', index) for chimney/dormer parts, else None."""
    m = re.match(r'(chimney|additional_gable)_.*_(\d+)$', name)
    return (m.group(1), int(m.group(2))) if m else None


def _explode_vectors(names: List[str], frames, centres: Dict[str, Vec],
                     config: ArchitecturalConfiguration) -> Dict[str, Vec]:
    box = [n for n in names if part_group(n) in ('floor', 'walls', 'roof')]
    house = _centre([centres[n] for n in box]) if box else (0.0, 0.0, 0.0)
    out = {n: _away(frames[n].n, house, centres[n]) for n in box}
    groups: Dict[tuple, List[str]] = {}
    for n in names:
        if _assembly(n):
            groups.setdefault(_assembly(n), []).append(n)
    for (kind, i), members in groups.items():
        holder = (config.chimneys if kind == 'chimney' else config.additional_gables)[i].position.panel
        carry = out.get(holder, (0.0, 0.0, 0.0))
        middle = _centre([centres[m] for m in members])
        for m in members:
            n = frames[m].n
            if abs(sum(n[k] * carry[k] for k in range(3))) > 0.9:      # lies on the roof (chimney collar): ride out
                out[m] = _add(carry, _away(n, (0.0, 0.0, 0.0), carry))
            else:
                out[m] = _add(carry, _away(n, middle, centres[m], fallback=carry))
    for n in names:
        if part_group(n) == 'casings' and n not in out:
            wall = re.sub(r'_[wd]\d+_(window|door)_casing$', '', n)
            out[n] = tuple(CASING_EXTRA * c for c in out.get(wall, frames[n].n))
    return out


def build_payload(geometry: HouseGeometry, config: ArchitecturalConfiguration, panels: Sequence[Panel],
                  title: str = 'house') -> dict:
    """{'title', 'units', 'parts': [{name, group, color, explode, vertices, triangles}]} (flat number lists)."""
    by_name = {p.name: p for p in panels}
    frames = house_frames(geometry, config, by_name)
    solids = {n: panel_solid(by_name[n], f, geometry.kerf) for n, f in frames.items()}
    centres = {n: _centre(s.mesh.vertices) for n, s in solids.items()}
    explode = _explode_vectors(list(solids), frames, centres, config)
    parts = []
    for name, solid in solids.items():
        parts.append({
            'name': name,
            'group': part_group(name),
            'color': list(solid.color),
            'explode': [round(c, DECIMALS) for c in explode[name]],
            'vertices': [round(c, DECIMALS) for v in solid.mesh.vertices for c in v],
            'triangles': [i for t in solid.mesh.triangles for i in t],
        })
    return {'title': title, 'units': 'mm', 'parts': parts}
