"""
Architectural configuration: the registry of everything that decorates the house box.

Owns the *what* (style, shingles, windows, doors, chimneys, dormers) and validates placement.
It knows nothing about SVG, finger joints or layout; builders receive plain data derived from it.

Errors: methods raise `PlacementError` (a `HouseMakerError`) with a precise reason instead of
printing warnings and returning False.
"""

import math
from typing import Dict, List, Optional, Tuple

from .components import (
    AdditionalGable, ArchitecturalStyle, Chimney, ComponentPosition, Door, DoorType,
    RoofType, ShingleType, Window, WindowType
)
from .exceptions import GeometryError, PlacementError
from .geometry import HouseGeometry
from .placement import ComponentPositioner, ProportionalSizer
from .warnings_util import warn_caller

ROOF_PANELS = ['roof_panel_left', 'roof_panel_right']
Rect = Tuple[float, float, float, float]       # x0, y0, x1, y1
EPS = 1e-9          # exact-fit placements must not be rejected by floating-point rounding


def _overlap(a: Rect, b: Rect) -> bool:
    """Do two rectangles share area? Touching edges do not count."""
    return not (a[2] <= b[0] + EPS or b[2] <= a[0] + EPS or a[3] <= b[1] + EPS or b[3] <= a[1] + EPS)


class ArchitecturalConfiguration:
    """
    Central configuration for all architectural components of a house.

    Components are held in plain lists (`windows`, `doors`, `chimneys`, `additional_gables`);
    query them with the `get_*_for_panel` methods.
    """

    def __init__(self, house_geometry: HouseGeometry,
                 roof_type: RoofType = RoofType.GABLE,
                 architectural_style: ArchitecturalStyle = ArchitecturalStyle.BASIC,
                 shingle_type: ShingleType = ShingleType.SHINGLES,
                 stone_jitter: bool = True):
        self.house_geometry = house_geometry
        self.architectural_style = architectural_style
        self.shingle_type = shingle_type
        self.stone_jitter = stone_jitter
        self.set_roof_type(roof_type)

        self._positioner = ComponentPositioner(house_geometry)
        self._sizer = ProportionalSizer(house_geometry)

        self.windows: List[Window] = []
        self.doors: List[Door] = []
        self.chimneys: List[Chimney] = []
        self.additional_gables: List[AdditionalGable] = []

    # ------------------------------------------------------------------ settings
    def set_roof_type(self, roof_type: RoofType):
        """Only gable roofs are generated so far; other types fall back to gable with a warning."""
        if roof_type != RoofType.GABLE:
            warn_caller(f"Roof type {roof_type.value!r} is not implemented yet; generating a gable roof")
        self.roof_type = roof_type

    def set_style(self, architectural_style: ArchitecturalStyle, stone_jitter: bool = True):
        self.architectural_style = architectural_style
        self.stone_jitter = stone_jitter

    def get_recommended_window_dimensions(self, panel_name: str,
                                          window_type: WindowType = WindowType.RECTANGULAR):
        """Aesthetically proportioned (width, height) for a window on a panel"""
        return self._sizer.get_window_dimensions(panel_name, window_type)

    def get_recommended_door_dimensions(self, panel_name: str):
        """Aesthetically proportioned (width, height) for a door on a panel"""
        return self._sizer.get_door_dimensions(panel_name)

    # ------------------------------------------------------------------ automatic components
    def add_automatic_components(self, add_windows: bool = True, add_doors: bool = True,
                                 window_type: WindowType = WindowType.RECTANGULAR,
                                 door_type: DoorType = DoorType.RECTANGULAR,
                                 door_panel: str = 'gable_wall_front'):
        """
        Add automatically sized and positioned doors (ground level, on `door_panel`) and windows
        (on every wall, avoiding the doors), using collision avoidance.
        """
        panel_dims = self.house_geometry.get_panel_dimensions()
        panel_names = list(panel_dims)

        def accept(candidates, store):
            """Keep a candidate only if a hand-placed one would be accepted too (margins, gable slope,
            clearance to what is already there): the placer must never produce a bad cut file."""
            for c in candidates:
                if self._wall_problem(c.position, panel_dims[c.position.panel]) is None:
                    store.append(c)

        if add_doors and door_panel in panel_names:
            accept(self._positioner.get_recommended_doors(door_panel, door_type, existing_components=[]),
                   self.doors)

        if add_windows:
            for panel_name in panel_names:
                if 'wall' not in panel_name:
                    continue
                existing = [d.position for d in self.doors if d.position.panel == panel_name]
                windows = self._positioner.get_recommended_windows(
                    panel_name, window_type, existing_components=existing)
                accept(windows, self.windows)
                existing.extend(w.position for w in windows)

                if (panel_name.startswith('gable_wall') and self._positioner.can_add_attic_window(
                        self.house_geometry.gable_peak_height, self.house_geometry.theta)):
                    accept(self._positioner.get_recommended_windows(
                        panel_name, WindowType.ATTIC, existing_components=existing), self.windows)

    # ------------------------------------------------------------------ wall components
    def _wall_position(self, kind: str, panel_name: str, x, y, width, height, default_size):
        panel_dims = self.house_geometry.get_panel_dimensions().get(panel_name)
        if panel_dims is None:
            raise PlacementError(kind, f"unknown panel {panel_name!r}")
        if width is None or height is None:       # fill in only what the caller did not give
            default_w, default_h = default_size(panel_name)
            width = default_w if width is None else width
            height = default_h if height is None else height
        position = ComponentPosition(x, y, width, height, panel_name)
        problem = self._wall_problem(position, panel_dims)
        if problem:
            raise PlacementError(kind, f"({x}, {y}) {width}x{height} on {panel_name}: {problem}")
        return position

    def _wall_problem(self, position: ComponentPosition, panel_dims, ignore=None) -> Optional[str]:
        """Why a window/door position is invalid (margins, gable slope, overlap), or None."""
        if not self._positioner.validate_component_placement(position, panel_dims):
            return f"does not fit on the {panel_dims[0]:.1f}x{panel_dims[1]:.1f} panel with margins"
        g = self.house_geometry
        if position.panel.startswith('gable_wall'):
            # the top corners must stay under both sloped edges of the gable
            width, top = g.gable_wall_width, position.y + position.height
            for cx in (position.x, position.x + position.width):
                limit = g.z_kerf + min(cx, width - cx) * math.tan(g.theta_rad)
                if top > limit - g.thickness / math.cos(g.theta_rad):
                    return "extends above the sloped gable edge"
        rect = (position.x, position.y, position.x + position.width, position.y + position.height)
        gap = g.thickness
        for other in self.windows + self.doors:
            if other is ignore or other.position.panel != position.panel:
                continue
            o = other.position
            if _overlap((rect[0] - gap, rect[1] - gap, rect[2] + gap, rect[3] + gap),
                        (o.x, o.y, o.x + o.width, o.y + o.height)):
                return f"overlaps (or is closer than {gap}mm to) another window/door"
        return None

    def add_custom_window(self, panel_name: str, x: float, y: float,
                          width: Optional[float] = None, height: Optional[float] = None,
                          window_type: WindowType = WindowType.RECTANGULAR) -> Window:
        """Add a window at (x, y) on a wall panel; size defaults to the proportional size."""
        position = self._wall_position(
            'window', panel_name, x, y, width, height,
            lambda p: self._sizer.get_window_dimensions(p, window_type))
        window = Window(window_type, position)
        self.windows.append(window)
        return window

    def add_custom_door(self, panel_name: str, x: float, y: float,
                        width: Optional[float] = None, height: Optional[float] = None,
                        door_type: DoorType = DoorType.RECTANGULAR) -> Door:
        """Add a door at (x, y) on a wall panel; size defaults to the proportional size."""
        position = self._wall_position(
            'door', panel_name, x, y, width, height, self._sizer.get_door_dimensions)
        door = Door(door_type, position)
        self.doors.append(door)
        return door

    def get_windows_for_panel(self, panel_name: str) -> List[Window]:
        return [w for w in self.windows if w.position.panel == panel_name]

    def get_doors_for_panel(self, panel_name: str) -> List[Door]:
        return [d for d in self.doors if d.position.panel == panel_name]

    # ------------------------------------------------------------------ roof components
    def _roof_keepouts(self, panel_name: str) -> List[Rect]:
        """Areas of a roof panel already taken: gable-tab slots and other roof features."""
        t = self.house_geometry.thickness
        rects = [(x0 - t, y0 - t, x1 + t, y1 + t)
                 for x0, y0, x1, y1 in self.house_geometry.roof_slot_rects(panel_name)]
        for c in self.chimneys:
            if c.position.panel == panel_name:
                x, y, w, d = c.footprint()
                left, up, right, down = c.casing_margins()
                rects.append((x - left, y - up, x + w + right, y + d + down))      # casing frame
        for g in self.additional_gables:
            if g.position.panel == panel_name:
                x, y, w, d = g.footprint()
                rects.append((x - t, y - t, x + w + t, y + d + g.roof_overhang + t))
        return rects

    def _check_roof_feature(self, kind: str, panel_name: str, rect: Rect, reach: float = 0.0,
                            margins: Optional[Tuple[float, float, float, float]] = None):
        """rect = footprint (x0, y0, x1, y1); `reach` extends the keep-out downslope (overhang)."""
        if panel_name not in ROOF_PANELS:
            raise PlacementError(kind, f"{kind}s belong on a roof panel ({', '.join(ROOF_PANELS)}), "
                                       f"not {panel_name!r}")
        t = self.house_geometry.thickness
        # clear of the panel edge on every side (and of the casing frame, if the feature has one)
        ml, mt, mr, mb = (max(t, v) for v in (margins or (t, t, t, t)))
        width, height = self.house_geometry.get_panel_dimensions()[panel_name]
        x0, y0, x1, y1 = rect
        if x0 < ml - EPS or y0 < mt - EPS or x1 > width - mr + EPS or y1 > height - mb + EPS:
            raise PlacementError(kind, f"footprint ({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f}) leaves "
                                       f"{panel_name} ({width:.1f}x{height:.1f}) minus a {max(ml, mt, mr, mb):.2f}mm margin")
        keepout = (x0 - ml, y0 - mt, x1 + mr, y1 + reach + mb)
        for other in self._roof_keepouts(panel_name):
            if _overlap(keepout, other):
                raise PlacementError(kind, f"overlaps another roof feature or a gable slot on {panel_name}")

    def add_chimney(self, panel_name: str, x: float, y: float,
                    width: Optional[float] = None, height: Optional[float] = None,
                    chimney_height: float = 20.0) -> Chimney:
        """
        Add a vertical chimney to a roof panel (see `Chimney` for the model).

        Args:
            x, y: top-left of the chimney's outer footprint on the roof panel (mm)
            width: interior width between the side walls (default 8); outer width is width + 2t
            height: plan (horizontal) depth of the chimney (default 12). On the roof panel the
                footprint is depth / cos(roof angle) long.
            chimney_height: minimum exposure above the roof, at the up-slope wall (default 20)
        """
        width = 8.0 if width is None else width
        height = 12.0 if height is None else height
        g = self.house_geometry
        try:
            chimney = Chimney(ComponentPosition(x, y, width, height, panel_name), g.theta,
                              g.thickness, chimney_height)
        except GeometryError as e:
            raise PlacementError('chimney', e.message) from e
        fx, fy, fw, fd = chimney.footprint()
        self._check_roof_feature('chimney', panel_name, (fx, fy, fx + fw, fy + fd),
                                 margins=chimney.casing_margins())
        self.chimneys.append(chimney)
        return chimney

    def add_additional_gable(self, panel_name: str, x: float, y: float,
                             width: Optional[float] = None, height: Optional[float] = None,
                             roof_overhang: float = 3.0, pitch: Optional[float] = None) -> AdditionalGable:
        """
        Add a gable dormer to a roof panel (see `dormer_geometry`).

        Args:
            x, y: top-left of the dormer's bounding box on the roof panel (mm)
            width: dormer width (default 25)
            height: ignored. The depth is fixed by the horizontal-ridge constraint; the derived
                value is available as `result.position.height`.
            roof_overhang: how far the dormer roof projects in front of its face (default 3)
            pitch: dormer roof pitch in degrees; default = the main roof angle
        """
        if height is not None:
            warn_caller("`height` of an additional gable is ignored: the depth is determined by "
                        "the width and roof pitch (horizontal ridge)")
        width = 25.0 if width is None else width
        g = self.house_geometry
        try:
            gable = AdditionalGable(ComponentPosition(x, y, width, 0.0, panel_name), g.theta,
                                    g.thickness, roof_overhang, pitch)
        except (GeometryError, ValueError) as e:
            raise PlacementError('additional gable', getattr(e, 'message', str(e))) from e
        fx, fy, fw, fd = gable.footprint()
        self._check_roof_feature('additional gable', panel_name, (fx, fy, fx + fw, fy + fd),
                                 reach=roof_overhang)
        self.additional_gables.append(gable)
        return gable

    def get_chimneys_for_panel(self, panel_name: str) -> List[Chimney]:
        return [c for c in self.chimneys if c.position.panel == panel_name]

    def get_additional_gables_for_panel(self, panel_name: str) -> List[AdditionalGable]:
        return [g for g in self.additional_gables if g.position.panel == panel_name]

    # ------------------------------------------------------------------ bulk operations
    def clear_components(self):
        """Remove every window, door, chimney and additional gable"""
        self.windows.clear()
        self.doors.clear()
        self.chimneys.clear()
        self.additional_gables.clear()

    def get_required_roof_panels(self) -> List[str]:
        return list(ROOF_PANELS)

    def get_component_summary(self) -> Dict:
        panels = list(self.house_geometry.get_panel_dimensions())

        def by_panel(getter):
            counts = {p: len(getter(p)) for p in panels}
            return {p: n for p, n in counts.items() if n}

        return {
            'roof_type': self.roof_type.value,
            'architectural_style': self.architectural_style.value,
            'total_windows': len(self.windows),
            'total_doors': len(self.doors),
            'total_chimneys': len(self.chimneys),
            'total_additional_gables': len(self.additional_gables),
            'windows_by_panel': by_panel(self.get_windows_for_panel),
            'doors_by_panel': by_panel(self.get_doors_for_panel),
            'chimneys_by_panel': by_panel(self.get_chimneys_for_panel),
            'additional_gables_by_panel': by_panel(self.get_additional_gables_for_panel),
            'roof_panels': self.get_required_roof_panels(),
            'has_decorative_patterns': self.architectural_style != ArchitecturalStyle.BASIC,
        }

    def validate_all_components(self) -> List[str]:
        """Re-validate wall components; returns a list of problems (empty if all valid)."""
        issues = []
        panel_dims = self.house_geometry.get_panel_dimensions()
        for kind, items in (('Window', self.windows), ('Door', self.doors)):
            for item in items:
                p = item.position
                if p.panel not in panel_dims:
                    issues.append(f"{kind} references unknown panel: {p.panel}")
                else:
                    problem = self._wall_problem(p, panel_dims[p.panel], ignore=item)
                    if problem:
                        issues.append(f"{kind} on {p.panel} at ({p.x}, {p.y}) "
                                      f"size {p.width}×{p.height}: {problem}")
        return issues


_PRESETS = {
    #  name:          (roof,           style,                          window,                door)
    'basic':        (RoofType.GABLE,   ArchitecturalStyle.BASIC,       WindowType.RECTANGULAR, DoorType.RECTANGULAR),
    'farmhouse':    (RoofType.GABLE,   ArchitecturalStyle.FARMHOUSE,   WindowType.RECTANGULAR, DoorType.RECTANGULAR),
    'colonial':     (RoofType.GABLE,   ArchitecturalStyle.COLONIAL,    WindowType.RECTANGULAR, DoorType.RECTANGULAR),
    'tudor':        (RoofType.GABLE,   ArchitecturalStyle.TUDOR,       WindowType.ARCHED,      DoorType.ARCHED),
    'victorian':    (RoofType.GABLE,   ArchitecturalStyle.VICTORIAN,   WindowType.ARCHED,      DoorType.RECTANGULAR),
    'craftsman':    (RoofType.GABLE,   ArchitecturalStyle.CRAFTSMAN,   WindowType.RECTANGULAR, DoorType.RECTANGULAR),
    'german':       (RoofType.GABLE,   ArchitecturalStyle.FACHWERKHAUS, WindowType.RECTANGULAR, DoorType.ARCHED),
    'brick':        (RoofType.GABLE,   ArchitecturalStyle.BRICK,       WindowType.RECTANGULAR, DoorType.RECTANGULAR),
    'stone':        (RoofType.GABLE,   ArchitecturalStyle.STONE,       WindowType.RECTANGULAR, DoorType.RECTANGULAR),
    'modern_flat':  (RoofType.FLAT,    ArchitecturalStyle.BASIC,       WindowType.RECTANGULAR, DoorType.RECTANGULAR),
    'barn_gambrel': (RoofType.GAMBREL, ArchitecturalStyle.FARMHOUSE,   WindowType.RECTANGULAR, DoorType.DOUBLE),
}


def create_preset_configuration(house_geometry: HouseGeometry, preset_name: str) -> ArchitecturalConfiguration:
    """
    Create a preset configuration with automatic windows and doors.

    Presets: basic, farmhouse, colonial, tudor, victorian, craftsman, german, brick, stone,
    modern_flat (flat roof), barn_gambrel (gambrel roof). Non-gable roofs are not generated yet.
    """
    if preset_name not in _PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available presets: {list(_PRESETS)}")
    roof, style, window, door = _PRESETS[preset_name]
    config = ArchitecturalConfiguration(house_geometry, roof_type=roof, architectural_style=style)
    config.add_automatic_components(add_windows=True, add_doors=True, window_type=window, door_type=door)
    return config
