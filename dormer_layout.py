"""
Dormer layout: several identical dormers on a roof panel, placed the way houses usually have them.

* Across the roof: over the windows of the wall below when there are as many window columns as dormers, otherwise
  evenly spaced - the house's length cut into equal bays, one dormer in the middle of each.
* Up the roof: one row, as low (as close to the eave) as all of them fit, unless a height is given.
* Afterwards the panel's dormer coverage is checked once (`ArchitecturalConfiguration.check_dormer_coverage`).

Positions are worked out in world space (the panel frames of `placement3d`), so a window's x on a side wall and a
dormer's x on the roof above it line up whichever way each panel is drawn.
"""

import copy
import math
from typing import List, Optional

from .components import AdditionalGable
from .config import ArchitecturalConfiguration
from .exceptions import PlacementError
from .geometry import HouseGeometry
from .placement3d import box_frames

WALL_BELOW = {'roof_panel_left': 'side_wall_left', 'roof_panel_right': 'side_wall_right'}
SIDES = {'left': ('roof_panel_left',), 'right': ('roof_panel_right',), 'both': ('roof_panel_left', 'roof_panel_right'),
         'roof_panel_left': ('roof_panel_left',), 'roof_panel_right': ('roof_panel_right',)}
Y_STEP = 0.1                     # mm: resolution of the search for the lowest row


def dormer_centres(geometry: HouseGeometry, config: ArchitecturalConfiguration, panel: str, count: int) -> List[float]:
    """Centres (roof panel x, drawn coordinates) of `count` dormers: over the windows below if there are `count`
    window columns, else in the middle of `count` equal bays along the house."""
    frames = box_frames(geometry)
    roof, wall = frames[panel], frames[WALL_BELOW[panel]]
    windows = config.get_windows_for_panel(WALL_BELOW[panel])
    columns = sorted({round(wall.to_world(w.position.x + w.position.width / 2, w.position.y, 0.0)[0], 6)
                      for w in windows})
    xs = columns if len(columns) == count else [geometry.x * (i + 0.5) / count for i in range(count)]
    return sorted((x - roof.origin[0]) / roof.eu[0] + roof.shift for x in xs)   # roof eu runs along +x or -x


def add_dormers(geometry: HouseGeometry, config: ArchitecturalConfiguration, side: str, count: int,
                width: float = 25.0, y: Optional[float] = None, roof_overhang: float = 3.0,
                pitch: Optional[float] = None, wall_height: Optional[float] = None) -> List[AdditionalGable]:
    """Add `count` identical dormers on one roof panel or both (`side`: left, right or both). Returns them. If the row
    does not fit, the error proposes the widest dormers, and the most dormers, that would (each laid out to check)."""
    if side not in SIDES:
        raise PlacementError('dormers', f"side must be left, right or both, not {side!r}")
    if count < 1:
        raise PlacementError('dormers', f"count must be at least 1, not {count}")
    args = (y, roof_overhang, pitch, wall_height)

    def fits(n, w):
        """Lay the row out on a copy (silently): does it fit?"""
        try:
            _layout(geometry, copy.deepcopy(config), side, n, w, *args, warn=False)
            return True
        except PlacementError:
            return False

    try:
        # all or nothing: a row whose third dormer does not fit must not leave the first two behind
        _layout(geometry, copy.deepcopy(config), side, count, width, *args, warn=False)
    except PlacementError as e:
        hints = []
        lo, hi = 15.0, width                                  # 15 mm: the smallest dormer
        if hi > lo and fits(count, lo):
            while hi - lo > 0.05:
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if fits(count, mid) else (lo, mid)
            hints.append(f"width at most {math.floor(lo * 10) / 10:.1f} for {count} dormers")
        fewer = next((n for n in range(count - 1, 0, -1) if fits(n, width)), None)
        if fewer:
            hints.append(f"count at most {fewer} at width {width:g}")
        if not hints:
            raise
        raise PlacementError('dormers', e.message.split(': ', 1)[1] + ". The row would fit with " + "; or ".join(hints)) from e
    return _layout(geometry, config, side, count, width, *args)


def _layout(geometry: HouseGeometry, config: ArchitecturalConfiguration, side: str, count: int, width: float,
            y: Optional[float], roof_overhang: float, pitch: Optional[float],
            wall_height: Optional[float], warn: bool = True) -> List[AdditionalGable]:
    added = []
    for panel in SIDES[side]:
        xs = [c - width / 2 for c in dormer_centres(geometry, config, panel, count)]
        row = y
        if row is None:
            top = geometry.get_panel_dimensions()[panel][1]
            lowest = []
            for x in xs:
                v = next((top - i * Y_STEP for i in range(int(top / Y_STEP) + 1)
                          if config.dormer_fits(panel, x, top - i * Y_STEP, width, roof_overhang, pitch, wall_height)),
                         None)
                if v is None:                    # nowhere on the slope: let the placement explain why (with hints)
                    config.add_additional_gable(panel, x, top / 2, width, None, roof_overhang, pitch, wall_height)
                lowest.append(v)
            row = min(lowest)                    # one row: as low as all of them fit
        for x in xs:
            added.append(config.add_additional_gable(panel, x, row, width, None, roof_overhang, pitch, wall_height,
                                                     warn_coverage=False))
    for panel in SIDES[side] if warn else ():
        config.check_dormer_coverage(panel)
    return added
