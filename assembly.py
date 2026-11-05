"""
Assembly planning: decide *which* panels the house consists of and build them.

This is the only place that reads the architectural configuration. Builders receive plain data
(`PanelFeatures`, component objects) and return `Panel`s in local coordinates.
"""

from typing import List, Optional

from .builders.box import BoxPanelBuilder, PanelFeatures
from .builders.chimney import build_chimney_panels, footprint_score as chimney_footprint, roof_cutout as chimney_cutout
from .builders.dormer import build_dormer_panels, footprint_score as dormer_footprint
from .casings import door_casing_pieces, window_casing_pieces
from .config import ArchitecturalConfiguration
from .constants import HouseStyle
from .cutouts import door_cutout, window_cutout
from .exceptions import PlacementError
from .geometry import HouseGeometry, Point
from .joints import FingerJointEngine
from .kerf import compensate_part, compensate_void
from .panel import Panel
from .svgpath import parse_path
from .patterns import ArchitecturalPatternGenerator, roof_pattern

_ORIGIN = Point(0, 0)
_BASE = ['floor', 'side_wall_left', 'side_wall_right', 'gable_wall_front', 'gable_wall_back']
_ROOF = ['roof_panel_left', 'roof_panel_right']


def box_panel_names(style: HouseStyle) -> List[str]:
    """Names of the main box panels for a house style."""
    if style == HouseStyle.HOUSE_NO_ROOF:
        return list(_BASE)
    if style == HouseStyle.WALLS_ONLY:
        return [n for n in _BASE if n != 'floor']
    return _BASE + _ROOF


def _title(name: str) -> str:
    return name.replace('_', ' ').title()


def _casing_label(name: str) -> str:
    parts = name.split('_')
    if 'casing' in parts:
        i = parts.index('casing')
        return f"Casing {parts[i + 1] if i + 1 < len(parts) else ''}".strip()
    return _title(name)


def _box_features(name: str, geometry: HouseGeometry, config: ArchitecturalConfiguration,
                  wall_patterns: ArchitecturalPatternGenerator) -> PanelFeatures:
    """Collect the decoration of one main panel from the configuration as plain data."""
    f = PanelFeatures()
    k = geometry.kerf                                          # cut-outs are holes: drawn kerf/2 smaller all round
    f.cutouts += [compensate_void(window_cutout(w), k) for w in config.get_windows_for_panel(name)]
    f.cutouts += [compensate_void(door_cutout(d), k) for d in config.get_doors_for_panel(name)]
    f.score += [chimney_footprint(c) for c in config.get_chimneys_for_panel(name)]
    f.cutouts += [chimney_cutout(c, geometry.kerf) for c in config.get_chimneys_for_panel(name)]
    f.score += [dormer_footprint(g) for g in config.get_additional_gables_for_panel(name)]
    nominal = geometry.get_panel_dimensions()[name]
    pattern = wall_patterns.generate_pattern_for_panel(name, nominal)
    if name.startswith('roof_panel'):
        tiles = roof_pattern(config.shingle_type, _ORIGIN, *nominal)
        pattern = (pattern + " " + tiles).strip() if tiles else pattern
    f.pattern = pattern
    return f


def build_panels(geometry: HouseGeometry, style: HouseStyle,
                 config: Optional[ArchitecturalConfiguration],
                 single_joints: bool = False) -> List[Panel]:
    """Build every panel of the house in local coordinates."""
    engine = FingerJointEngine(geometry.thickness, geometry.finger_length, geometry.kerf, single_joints)
    box = BoxPanelBuilder(geometry, engine)
    if config is None:
        return [box.build(name) for name in box_panel_names(style)]

    wall_patterns = ArchitecturalPatternGenerator(config.architectural_style, geometry, config.stone_jitter)
    panels: List[Panel] = [box.build(name, _box_features(name, geometry, config, wall_patterns))
                           for name in box_panel_names(style)]

    has_roof = any(n.startswith('roof_panel') for n in box_panel_names(style))
    if (config.chimneys or config.additional_gables) and not has_roof:
        raise PlacementError('roof feature', f"chimneys and dormers need roof panels, but house style "
                                             f"{style.name} has none")
    for idx, chimney in enumerate(config.chimneys):
        panels += build_chimney_panels(chimney, idx, engine)
    for idx, dormer in enumerate(config.additional_gables):
        panels += build_dormer_panels(dormer, idx, engine)

    t = geometry.thickness
    for panel_name in box_panel_names(style):
        casings = {}
        for idx, window in enumerate(config.get_windows_for_panel(panel_name)):
            casings.update(window_casing_pieces(window, f'{panel_name}_w{idx}', t))
        for idx, door in enumerate(config.get_doors_for_panel(panel_name)):
            casings.update(door_casing_pieces(door, f'{panel_name}_d{idx}', t))
        for name, (w, h, path) in casings.items():
            if name.endswith('_scores'):
                continue
            score = casings.get(f'{name}_scores')
            cut = compensate_part(path, geometry.kerf)               # frame outline grows, its opening shrinks
            xs, ys = zip(*[(p.x, p.y) for p in parse_path(cut)[0]])
            panels.append(Panel(name, _casing_label(name), [cut], score=[score[2]] if score else [],
                                nominal_size=(max(xs) - min(xs), max(ys) - min(ys))))
    return panels
