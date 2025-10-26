"""
Architectural Components System for HouseMaker

Provides comprehensive support for:
1. Roof patterns (gable, flat, hip, gambrel, shed)
2. Door and window cutouts with positioning logic
3. Architectural style decorative patterns
4. Attic windows for tall/steep gabled houses

All components automatically scale based on house dimensions for aesthetic proportions.
"""

import math
from typing import Dict, List, Tuple, Optional, NamedTuple
from enum import Enum
from .geometry import Point, HouseGeometry
from .constants import COORDINATE_PRECISION
from .exceptions import GeometryError


class RoofType(Enum):
    """Different roof patterns supported by the system"""
    GABLE = "gable"           # Standard triangular gable roof (default)
    FLAT = "flat"             # Flat roof (no gable)
    HIP = "hip"               # Hip roof (sloped on all four sides)
    GAMBREL = "gambrel"       # Gambrel roof (barn-style with two slopes)
    SHED = "shed"             # Shed roof (single slope)
    MANSARD = "mansard"       # Mansard roof (four-sided gambrel)


class WindowType(Enum):
    """Different window styles"""
    RECTANGULAR = "rectangular"   # Simple rectangular window
    ARCHED = "arched"             # Arched top window
    CIRCULAR = "circular"         # Circular window
    ATTIC = "attic"              # Small attic window for gable walls
    BAY = "bay"                  # Bay window (protruding)
    DORMER = "dormer"            # Dormer window (on roof)
    DOUBLE_HUNG = "double_hung"   # Traditional double-hung sash windows
    CASEMENT = "casement"         # Side-hinged casement windows
    PALLADIAN = "palladian"       # Palladian window (arch with flanking rectangles)
    GOTHIC_PAIR = "gothic_pair"   # Paired Gothic arched windows
    COLONIAL_SET = "colonial_set" # Set of 3 colonial windows with shutters
    CROSS_PANE = "cross_pane"     # Cross-pattern mullioned window (gingerbread style)
    MULTI_PANE = "multi_pane"     # Multi-pane grid window (advent calendar style)


class DoorType(Enum):
    """Different door styles"""
    RECTANGULAR = "rectangular"   # Simple rectangular door
    ARCHED = "arched"             # Arched top door
    DOUBLE = "double"             # Double door
    DUTCH = "dutch"              # Dutch door (split horizontal)


class ArchitecturalStyle(Enum):
    """Architectural styles for decorative patterns"""
    BASIC = "basic"                    # Clean, minimal style
    FACHWERKHAUS = "fachwerkhaus"      # German timber frame style
    FARMHOUSE = "farmhouse"            # American farmhouse style
    COLONIAL = "colonial"              # Colonial style
    BRICK = "brick"                    # Brick pattern style
    VICTORIAN = "victorian"            # Victorian ornate style
    TUDOR = "tudor"                    # Tudor revival style
    CRAFTSMAN = "craftsman"            # Arts and crafts style
    GINGERBREAD = "gingerbread"        # Festive gingerbread house style with ornate cutouts


class ComponentPosition(NamedTuple):
    """Position and size specification for architectural components"""
    x: float          # X position (relative to panel)
    y: float          # Y position (relative to panel)
    width: float      # Component width
    height: float     # Component height
    panel: str        # Target panel name


class WindowAssembly:
    """Complete window assembly with decorative elements"""
    
    def __init__(self, window_type: WindowType, position: ComponentPosition,
                 style_params: Optional[Dict] = None):
        self.type = window_type
        self.position = position
        self.style_params = style_params or {}
        self.decorative_elements = []
        self._generate_assembly()
    
    def _generate_assembly(self):
        """Generate complete window assembly with decorative elements"""
        if self.type == WindowType.COLONIAL_SET:
            self._generate_colonial_set()
        elif self.type == WindowType.PALLADIAN:
            self._generate_palladian_window()
        elif self.type == WindowType.GOTHIC_PAIR:
            self._generate_gothic_pair()
        elif self.type == WindowType.DOUBLE_HUNG:
            self._generate_double_hung()
        elif self.type == WindowType.CROSS_PANE:
            self._generate_cross_pane_window()
        elif self.type == WindowType.MULTI_PANE:
            self._generate_multi_pane_window()
        else:
            # Standard single window with basic frame
            self._generate_standard_frame()
    
    def _generate_colonial_set(self):
        """Generate set of 3 colonial windows with shutters and pediments"""
        # Main window set (3 windows with shared header)
        window_width = self.position.width / 3
        spacing = window_width * 0.1
        
        for i in range(3):
            x_offset = i * (window_width + spacing)
            self.decorative_elements.append({
                'type': 'window_opening',
                'x': self.position.x + x_offset,
                'y': self.position.y + 4,  # Account for header
                'width': window_width,
                'height': self.position.height - 8,  # Account for header and sill
            })
            
            # Add shutters
            self.decorative_elements.extend([
                {'type': 'shutters', 'x': self.position.x + x_offset - 2, 'y': self.position.y + 4, 'width': 2, 'height': self.position.height - 8},
                {'type': 'shutters', 'x': self.position.x + x_offset + window_width, 'y': self.position.y + 4, 'width': 2, 'height': self.position.height - 8}
            ])
        
        # Shared header/pediment and sill
        self.decorative_elements.extend([
            {'type': 'pediment', 'x': self.position.x - 2, 'y': self.position.y, 'width': self.position.width + 4, 'height': 4},
            {'type': 'sill', 'x': self.position.x - 1, 'y': self.position.y + self.position.height - 2, 'width': self.position.width + 2, 'height': 2}
        ])
    
    def _generate_palladian_window(self):
        """Generate Palladian window (central arch flanked by rectangles)"""
        central_width = self.position.width * 0.6
        side_width = self.position.width * 0.2
        
        # Central arched opening
        self.decorative_elements.append({'type': 'arched_opening', 'x': self.position.x + side_width, 'y': self.position.y + 3, 'width': central_width, 'height': self.position.height - 6})
        
        # Side rectangular openings
        self.decorative_elements.extend([
            {'type': 'window_opening', 'x': self.position.x, 'y': self.position.y + 8, 'width': side_width, 'height': self.position.height - 14},
            {'type': 'window_opening', 'x': self.position.x + side_width + central_width, 'y': self.position.y + 8, 'width': side_width, 'height': self.position.height - 14}
        ])
        
        # Columns between sections
        self.decorative_elements.extend([
            {'type': 'column', 'x': self.position.x + side_width - 1, 'y': self.position.y, 'width': 2, 'height': self.position.height},
            {'type': 'column', 'x': self.position.x + side_width + central_width - 1, 'y': self.position.y, 'width': 2, 'height': self.position.height}
        ])
    
    def _generate_gothic_pair(self):
        """Generate pair of Gothic arched windows"""
        window_width = (self.position.width - 3) / 2  # Account for central mullion
        
        for i in range(2):
            x_offset = i * (window_width + 3)
            self.decorative_elements.append({'type': 'gothic_opening', 'x': self.position.x + x_offset, 'y': self.position.y + 2, 'width': window_width, 'height': self.position.height - 4})
        
        # Central mullion
        self.decorative_elements.append({'type': 'mullion', 'x': self.position.x + window_width + 1, 'y': self.position.y, 'width': 2, 'height': self.position.height})
    
    def _generate_double_hung(self):
        """Generate traditional double-hung window with frame details"""
        self.decorative_elements.extend([
            {'type': 'window_opening', 'x': self.position.x + 2, 'y': self.position.y + 3, 'width': self.position.width - 4, 'height': self.position.height - 6},
            {'type': 'frame', 'x': self.position.x, 'y': self.position.y, 'width': self.position.width, 'height': self.position.height},
            {'type': 'sash_divider', 'x': self.position.x + 2, 'y': self.position.y + self.position.height / 2 - 0.5, 'width': self.position.width - 4, 'height': 1}
        ])
    
    def _generate_cross_pane_window(self):
        """Generate cross-pattern mullioned window (gingerbread style)"""
        # Main window opening
        self.decorative_elements.append({
            'type': 'window_opening',
            'x': self.position.x + 1,
            'y': self.position.y + 1,
            'width': self.position.width - 2,
            'height': self.position.height - 2
        })
        
        # Cross mullions dividing window into 4 panes
        center_x = self.position.x + self.position.width / 2
        center_y = self.position.y + self.position.height / 2
        
        # Vertical mullion
        self.decorative_elements.append({
            'type': 'mullion',
            'x': center_x - 0.5,
            'y': self.position.y + 1,
            'width': 1,
            'height': self.position.height - 2
        })
        
        # Horizontal mullion
        self.decorative_elements.append({
            'type': 'mullion',
            'x': self.position.x + 1,
            'y': center_y - 0.5,
            'width': self.position.width - 2,
            'height': 1
        })
        
        # Decorative frame
        self.decorative_elements.append({
            'type': 'decorative_frame',
            'x': self.position.x,
            'y': self.position.y,
            'width': self.position.width,
            'height': self.position.height
        })
    
    def _generate_multi_pane_window(self):
        """Generate multi-pane grid window (advent calendar style)"""
        # Main window opening
        self.decorative_elements.append({
            'type': 'window_opening',
            'x': self.position.x + 1.5,
            'y': self.position.y + 1.5,
            'width': self.position.width - 3,
            'height': self.position.height - 3
        })
        
        # Create 3x2 grid of panes (6 small panes total)
        pane_width = (self.position.width - 4) / 3
        pane_height = (self.position.height - 4) / 2
        
        # Vertical mullions (2 internal divisions for 3 columns)
        for i in range(1, 3):
            mullion_x = self.position.x + 1.5 + i * pane_width - 0.5
            self.decorative_elements.append({
                'type': 'mullion',
                'x': mullion_x,
                'y': self.position.y + 1.5,
                'width': 1,
                'height': self.position.height - 3
            })
        
        # Horizontal mullion (1 internal division for 2 rows)
        mullion_y = self.position.y + 1.5 + pane_height - 0.5
        self.decorative_elements.append({
            'type': 'mullion',
            'x': self.position.x + 1.5,
            'y': mullion_y,
            'width': self.position.width - 3,
            'height': 1
        })
        
        # Ornate frame with corner decorations
        self.decorative_elements.append({
            'type': 'ornate_frame',
            'x': self.position.x,
            'y': self.position.y,
            'width': self.position.width,
            'height': self.position.height
        })
    
    def _generate_standard_frame(self):
        """Generate basic window frame for simple windows"""
        self.decorative_elements.append({'type': 'frame', 'x': self.position.x - 1, 'y': self.position.y - 1, 'width': self.position.width + 2, 'height': self.position.height + 2})


class DoorAssembly:
    """Complete door assembly with decorative elements"""
    
    def __init__(self, door_type: DoorType, position: ComponentPosition,
                 style_params: Optional[Dict] = None):
        self.type = door_type
        self.position = position
        self.style_params = style_params or {}
        self.decorative_elements = []
        self._generate_assembly()
    
    def _generate_assembly(self):
        """Generate complete door assembly with decorative elements"""
        self._add_door_frame()
        
        if self.type == DoorType.ARCHED:
            self._add_arched_elements()
        elif self.type == DoorType.DOUBLE:
            self._add_double_door_elements()
        elif self.type == DoorType.DUTCH:
            self._add_dutch_door_elements()
        
        self._add_entrance_steps()
    
    def _add_door_frame(self):
        """Add door frame and surround"""
        surround_extra = 3
        self.decorative_elements.extend([
            {'type': 'door_surround', 'x': self.position.x - surround_extra, 'y': self.position.y - 1, 'width': self.position.width + 2 * surround_extra, 'height': self.position.height + 4},
            {'type': 'door_pediment', 'x': self.position.x - surround_extra - 2, 'y': self.position.y + self.position.height + 1, 'width': self.position.width + 2 * surround_extra + 4, 'height': 4}
        ])
    
    def _add_arched_elements(self):
        """Add elements specific to arched doors"""
        self.decorative_elements.append({'type': 'arch_molding', 'x': self.position.x - 2, 'y': self.position.y, 'width': self.position.width + 4, 'height': self.position.height * 0.3})
    
    def _add_double_door_elements(self):
        """Add elements for double doors"""
        center_x = self.position.x + self.position.width / 2
        self.decorative_elements.append({'type': 'door_mullion', 'x': center_x - 0.5, 'y': self.position.y, 'width': 1, 'height': self.position.height})
    
    def _add_dutch_door_elements(self):
        """Add elements for Dutch doors"""
        mid_y = self.position.y + self.position.height / 2
        self.decorative_elements.append({'type': 'door_divider', 'x': self.position.x, 'y': mid_y - 1, 'width': self.position.width, 'height': 2})
    
    def _add_entrance_steps(self):
        """Add entrance steps/threshold"""
        step_width = self.position.width + 6
        self.decorative_elements.append({'type': 'entrance_steps', 'x': self.position.x - 3, 'y': self.position.y - 3, 'width': step_width, 'height': 3})


class Window:
    """Window component with position and styling information"""
    
    def __init__(self, window_type: WindowType, position: ComponentPosition,
                 style_params: Optional[Dict] = None):
        self.type = window_type
        self.position = position
        self.style_params = style_params or {}
        self.assembly = None  # Will be set for sophisticated window types
        
        # Validate position
        self._validate_position()
    
    def _validate_position(self):
        """Validate that window position is reasonable"""
        if self.position.width <= 0 or self.position.height <= 0:
            raise GeometryError("window_validation", "Window dimensions must be positive")
        
        # Minimum window sizes for manufacturability
        if self.position.width < 5.0 or self.position.height < 5.0:
            raise GeometryError("window_validation", "Window too small for laser cutting (minimum 5mm)")


class Door:
    """Door component with position and styling information"""
    
    def __init__(self, door_type: DoorType, position: ComponentPosition,
                 style_params: Optional[Dict] = None):
        self.type = door_type
        self.position = position
        self.style_params = style_params or {}
        
        # Validate position
        self._validate_position()
    
    def _validate_position(self):
        """Validate that door position is reasonable"""
        if self.position.width <= 0 or self.position.height <= 0:
            raise GeometryError("door_validation", "Door dimensions must be positive")
        
        # Minimum door sizes
        if self.position.width < 8.0 or self.position.height < 15.0:
            raise GeometryError("door_validation", "Door too small (minimum 8×15mm)")


class ProportionalSizer:
    """Calculates aesthetically pleasing proportions for architectural components"""
    
    # Architectural proportion constants
    GOLDEN_RATIO = 1.618
    DOOR_HEIGHT_RATIO = 0.8    # Door height as fraction of wall height
    DOOR_WIDTH_RATIO = 0.4     # Door width relative to door height
    WINDOW_HEIGHT_RATIO = 0.3  # Window height as fraction of wall height
    WINDOW_WIDTH_RATIO = 1.2   # Window width relative to window height
    ATTIC_WINDOW_SCALE = 0.6   # Attic windows are smaller
    
    def __init__(self, house_geometry: HouseGeometry):
        self.house_geometry = house_geometry
    
    def get_door_dimensions(self, panel_name: str) -> Tuple[float, float]:
        """Calculate aesthetically pleasing door dimensions"""
        panel_dims = self.house_geometry.get_panel_dimensions().get(panel_name)
        if not panel_dims:
            return (15.0, 30.0)  # Fallback minimum
        
        panel_width, panel_height = panel_dims
        
        # For gable walls, use the rectangular portion height
        if panel_name.startswith('gable_wall'):
            usable_height = self.house_geometry.z
        else:
            usable_height = panel_height
        
        # Calculate door height (80% of usable wall height, but reasonable limits)
        door_height = usable_height * self.DOOR_HEIGHT_RATIO
        door_height = max(15.0, min(door_height, usable_height - 10))  # Min 15mm, max wall-10mm
        
        # Calculate door width using proportional ratio
        door_width = door_height * self.DOOR_WIDTH_RATIO
        door_width = max(8.0, min(door_width, panel_width - 20))  # Min 8mm, max wall-20mm
        
        return (door_width, door_height)
    
    def get_window_dimensions(self, panel_name: str, window_type: WindowType) -> Tuple[float, float]:
        """Calculate aesthetically pleasing window dimensions"""
        panel_dims = self.house_geometry.get_panel_dimensions().get(panel_name)
        if not panel_dims:
            return (12.0, 10.0)  # Fallback minimum
        
        panel_width, panel_height = panel_dims
        
        # Base window dimensions
        if panel_name.startswith('gable_wall'):
            # For gable walls, consider the triangular portion for attic windows
            if window_type == WindowType.ATTIC:
                # Attic windows in the triangular gable area
                base_height = self.house_geometry.gable_peak_height * 0.4
                base_width = base_height * self.GOLDEN_RATIO
                scale = self.ATTIC_WINDOW_SCALE
            else:
                # Regular windows in rectangular portion
                usable_height = self.house_geometry.z
                base_height = usable_height * self.WINDOW_HEIGHT_RATIO
                base_width = base_height * self.WINDOW_WIDTH_RATIO
                scale = 1.0
        else:
            # Side wall windows
            base_height = panel_height * self.WINDOW_HEIGHT_RATIO
            base_width = base_height * self.WINDOW_WIDTH_RATIO
            scale = 1.0
        
        # Apply scaling and constraints
        window_height = base_height * scale
        window_width = base_width * scale
        
        # Special handling for different window types
        if window_type == WindowType.CIRCULAR:
            # Circular windows are square with diameter = height
            window_width = window_height
        elif window_type == WindowType.BAY:
            # Bay windows are wider
            window_width *= 1.5
        elif window_type == WindowType.ARCHED:
            # Arched windows need extra height for the arch
            window_height *= 1.2
        
        # Apply reasonable limits
        window_height = max(5.0, min(window_height, panel_height * 0.6))
        window_width = max(5.0, min(window_width, panel_width * 0.8))
        
        return (window_width, window_height)
    
    def get_pattern_scale(self, panel_name: str) -> float:
        """Get appropriate scale factor for decorative patterns"""
        panel_dims = self.house_geometry.get_panel_dimensions().get(panel_name)
        if not panel_dims:
            return 1.0
        
        panel_width, panel_height = panel_dims
        panel_area = panel_width * panel_height
        
        # Scale patterns based on panel size
        # Base scale for 100x100mm panel = 1.0
        base_area = 10000  # 100mm x 100mm
        scale = math.sqrt(panel_area / base_area)
        
        # Constrain scale to reasonable range
        return max(0.5, min(scale, 3.0))


class RoofGeometry:
    """Handles different roof type geometry calculations"""
    
    def __init__(self, roof_type: RoofType, house_geometry: HouseGeometry):
        self.roof_type = roof_type
        self.house_geometry = house_geometry
        self._calculate_roof_specific_geometry()
    
    def _calculate_roof_specific_geometry(self):
        """Calculate geometry specific to different roof types"""
        if self.roof_type == RoofType.FLAT:
            self._calculate_flat_roof()
        elif self.roof_type == RoofType.HIP:
            self._calculate_hip_roof()
        elif self.roof_type == RoofType.GAMBREL:
            self._calculate_gambrel_roof()
        elif self.roof_type == RoofType.SHED:
            self._calculate_shed_roof()
        elif self.roof_type == RoofType.MANSARD:
            self._calculate_mansard_roof()
        else:  # GABLE (default)
            self._calculate_gable_roof()
    
    def _calculate_flat_roof(self):
        """Calculate flat roof dimensions"""
        # Flat roof is just a rectangular panel covering the top
        self.roof_panels = {
            'roof_flat': {
                'width': self.house_geometry.x + 2 * self.house_geometry.thickness,
                'height': self.house_geometry.y + 2 * self.house_geometry.thickness,
                'shape': 'rectangular'
            }
        }
        self.gable_modification = {'has_gable': False}
    
    def _calculate_hip_roof(self):
        """Calculate hip roof dimensions"""
        # Hip roof has triangular ends and trapezoidal sides
        base_roof_width = self.house_geometry.base_roof_width
        
        self.roof_panels = {
            'roof_front_hip': {
                'width': self.house_geometry.x + 2 * self.house_geometry.thickness,
                'height': base_roof_width,
                'shape': 'trapezoid'
            },
            'roof_back_hip': {
                'width': self.house_geometry.x + 2 * self.house_geometry.thickness, 
                'height': base_roof_width,
                'shape': 'trapezoid'
            },
            'roof_left_hip': {
                'width': self.house_geometry.y,
                'height': base_roof_width,
                'shape': 'triangle'
            },
            'roof_right_hip': {
                'width': self.house_geometry.y,
                'height': base_roof_width,
                'shape': 'triangle'
            }
        }
        self.gable_modification = {'has_gable': False}
    
    def _calculate_gambrel_roof(self):
        """Calculate gambrel roof dimensions (barn-style)"""
        # Gambrel has two slopes - steep lower, shallow upper
        lower_angle = min(60, self.house_geometry.theta + 15)  # Steeper lower slope
        upper_angle = max(30, self.house_geometry.theta - 15)  # Shallower upper slope
        
        # Calculate break point (typically 2/3 up the roof)
        break_height = (self.house_geometry.y / 2) * 0.66
        lower_width = break_height / math.cos(math.radians(lower_angle))
        upper_width = ((self.house_geometry.y / 2) - break_height) / math.cos(math.radians(upper_angle))
        
        self.roof_panels = {
            'roof_lower_left': {
                'width': self.house_geometry.x + 2 * self.house_geometry.thickness,
                'height': lower_width,
                'shape': 'rectangular'
            },
            'roof_lower_right': {
                'width': self.house_geometry.x + 2 * self.house_geometry.thickness,
                'height': lower_width,
                'shape': 'rectangular'
            },
            'roof_upper_left': {
                'width': self.house_geometry.x + 2 * self.house_geometry.thickness,
                'height': upper_width,
                'shape': 'rectangular'
            },
            'roof_upper_right': {
                'width': self.house_geometry.x + 2 * self.house_geometry.thickness,
                'height': upper_width,
                'shape': 'rectangular'
            }
        }
        self.gable_modification = {'has_gable': True, 'gambrel_style': True}
    
    def _calculate_shed_roof(self):
        """Calculate shed roof dimensions (single slope)"""
        # Single slope from front to back
        roof_width = self.house_geometry.y / math.cos(self.house_geometry.theta_rad)
        
        self.roof_panels = {
            'roof_shed': {
                'width': self.house_geometry.x + 2 * self.house_geometry.thickness,
                'height': roof_width,
                'shape': 'rectangular'
            }
        }
        # Modify gable walls for shed roof (one high, one low)
        shed_height_diff = self.house_geometry.y * math.tan(self.house_geometry.theta_rad)
        self.gable_modification = {
            'has_gable': False,
            'front_height': self.house_geometry.z,
            'back_height': self.house_geometry.z + shed_height_diff
        }
    
    def _calculate_mansard_roof(self):
        """Calculate mansard roof dimensions (four-sided gambrel)"""
        # Similar to gambrel but on all four sides
        lower_angle = min(70, self.house_geometry.theta + 25)
        upper_angle = max(15, self.house_geometry.theta - 30)
        
        # Calculate dimensions for both directions
        y_break_height = (self.house_geometry.y / 2) * 0.75
        x_break_height = (self.house_geometry.x / 2) * 0.75
        
        self.roof_panels = {
            'roof_mansard_front_lower': {
                'width': self.house_geometry.x + 2 * self.house_geometry.thickness,
                'height': y_break_height / math.cos(math.radians(lower_angle)),
                'shape': 'rectangular'
            },
            'roof_mansard_back_lower': {
                'width': self.house_geometry.x + 2 * self.house_geometry.thickness,
                'height': y_break_height / math.cos(math.radians(lower_angle)),
                'shape': 'rectangular'
            },
            'roof_mansard_left_lower': {
                'width': self.house_geometry.y,
                'height': x_break_height / math.cos(math.radians(lower_angle)),
                'shape': 'rectangular'
            },
            'roof_mansard_right_lower': {
                'width': self.house_geometry.y,
                'height': x_break_height / math.cos(math.radians(lower_angle)),
                'shape': 'rectangular'
            },
            'roof_mansard_top': {
                'width': self.house_geometry.x - 2 * x_break_height,
                'height': self.house_geometry.y - 2 * y_break_height,
                'shape': 'rectangular'
            }
        }
        self.gable_modification = {'has_gable': False}
    
    def _calculate_gable_roof(self):
        """Calculate standard gable roof dimensions (existing behavior)"""
        self.roof_panels = {
            'roof_panel_left': {
                'width': self.house_geometry.roof_panel_length,
                'height': self.house_geometry.roof_panel_left_width,
                'shape': 'rectangular'
            },
            'roof_panel_right': {
                'width': self.house_geometry.roof_panel_length,
                'height': self.house_geometry.roof_panel_right_width,
                'shape': 'rectangular'
            }
        }
        self.gable_modification = {'has_gable': True}
    
    def get_required_panels(self) -> List[str]:
        """Get list of panels required for this roof type"""
        return list(self.roof_panels.keys())
    
    def get_panel_dimensions(self, panel_name: str) -> Tuple[float, float]:
        """Get dimensions for a specific roof panel"""
        if panel_name not in self.roof_panels:
            raise GeometryError("roof_panel", f"Unknown roof panel: {panel_name}")
        
        panel = self.roof_panels[panel_name]
        return (panel['width'], panel['height'])


class ComponentPositioner:
    """Handles positioning logic for doors and windows"""
    
    def __init__(self, house_geometry: HouseGeometry):
        self.house_geometry = house_geometry
        self.sizer = ProportionalSizer(house_geometry)
    
    def validate_component_placement(self, component: ComponentPosition, 
                                   panel_dims: Tuple[float, float]) -> bool:
        """Validate that a component fits within its target panel"""
        panel_width, panel_height = panel_dims
        
        # Check bounds
        if (component.x + component.width > panel_width or 
            component.y + component.height > panel_height):
            return False
        
        # Check minimum margins from edges
        margin = self.house_geometry.thickness
        if (component.x < margin or component.y < margin or
            component.x + component.width > panel_width - margin or
            component.y + component.height > panel_height - margin):
            return False
        
        return True
    
    def can_add_attic_window(self, gable_height: float, gable_angle: float) -> bool:
        """Determine if attic windows can be added based on house dimensions"""
        # Requirements: tall house OR steep gable
        min_height_for_attic = 60.0  # 6cm minimum gable height
        min_angle_for_attic = 30.0   # 30 degree minimum angle
        
        return (gable_height >= min_height_for_attic or gable_angle >= min_angle_for_attic)
    
    def get_recommended_windows(self, panel_name: str,
                              window_type: WindowType = WindowType.RECTANGULAR,
                              existing_components: List[ComponentPosition] = None) -> List[Window]:
        """Get recommended windows with proper proportions for a panel"""
        # For sophisticated window types, use assemblies
        if window_type in [WindowType.COLONIAL_SET, WindowType.PALLADIAN,
                          WindowType.GOTHIC_PAIR, WindowType.DOUBLE_HUNG, WindowType.CASEMENT,
                          WindowType.CROSS_PANE, WindowType.MULTI_PANE]:
            return self._get_window_assemblies(panel_name, window_type, existing_components)
        
        # Calculate appropriate window size for standard windows
        window_size = self.sizer.get_window_dimensions(panel_name, window_type)
        
        # Get positions for this window size, avoiding existing components
        positions = self._get_positions_for_component(panel_name, 'window', window_size, existing_components)
        
        # Create window objects
        windows = []
        for pos in positions:
            window = Window(window_type, pos)
            windows.append(window)
        
        return windows
    
    def _get_window_assemblies(self, panel_name: str, window_type: WindowType,
                             existing_components: List[ComponentPosition] = None) -> List[Window]:
        """Get window assemblies for sophisticated window types"""
        panel_dims = self.house_geometry.get_panel_dimensions().get(panel_name)
        if not panel_dims:
            return []
        
        panel_width, panel_height = panel_dims
        existing_components = existing_components or []
        
        # Calculate assembly dimensions based on type
        if window_type == WindowType.COLONIAL_SET:
            # Colonial set needs wider space for 3 windows
            assembly_width = min(panel_width * 0.7, 60.0)  # Max 60mm for 3 windows
            assembly_height = panel_height * 0.35
        elif window_type == WindowType.PALLADIAN:
            # Palladian window needs tall proportions
            assembly_width = min(panel_width * 0.6, 45.0)
            assembly_height = panel_height * 0.5
        elif window_type == WindowType.GOTHIC_PAIR:
            # Gothic pair needs vertical emphasis
            assembly_width = min(panel_width * 0.5, 35.0)
            assembly_height = panel_height * 0.45
        elif window_type == WindowType.CROSS_PANE:
            # Cross-pane needs square proportions for grid
            assembly_width = min(panel_width * 0.35, 20.0)
            assembly_height = min(panel_height * 0.35, 20.0)
        elif window_type == WindowType.MULTI_PANE:
            # Multi-pane needs rectangular proportions for 3x2 grid
            assembly_width = min(panel_width * 0.45, 30.0)
            assembly_height = min(panel_height * 0.4, 25.0)
        else:  # DOUBLE_HUNG, CASEMENT
            # Standard proportions with frame details
            assembly_width = min(panel_width * 0.4, 25.0)
            assembly_height = panel_height * 0.35
        
        # Ensure minimum manufacturability
        assembly_width = max(assembly_width, 10.0)
        assembly_height = max(assembly_height, 8.0)
        
        # Get positions avoiding existing components
        positions = self._get_positions_for_component(panel_name, 'window',
                                                    (assembly_width, assembly_height), existing_components)
        
        # Create window assemblies
        windows = []
        for pos in positions:
            window = Window(window_type, pos)
            window.assembly = WindowAssembly(window_type, pos)
            windows.append(window)
            
            # For assemblies that shouldn't be repeated, limit to one per wall
            if window_type in [WindowType.COLONIAL_SET, WindowType.PALLADIAN, WindowType.MULTI_PANE]:
                break
        
        return windows
    
    def get_recommended_doors(self, panel_name: str,
                            door_type: DoorType = DoorType.RECTANGULAR,
                            existing_components: List[ComponentPosition] = None) -> List[Door]:
        """Get recommended doors with proper proportions for a panel"""
        # Calculate appropriate door size
        door_size = self.sizer.get_door_dimensions(panel_name)
        
        # Get positions for this door size, avoiding existing components
        positions = self._get_positions_for_component(panel_name, 'door', door_size, existing_components)
        
        # Create door objects with assemblies for sophisticated types
        doors = []
        for pos in positions:
            door = Door(door_type, pos)
            # Create assembly for doors that benefit from decorative elements
            if door_type in [DoorType.ARCHED, DoorType.DOUBLE, DoorType.DUTCH]:
                door.assembly = DoorAssembly(door_type, pos)
            doors.append(door)
        
        return doors
    
    def _get_positions_for_component(self, panel_name: str, component_type: str,
                                   component_size: Tuple[float, float],
                                   existing_components: List[ComponentPosition] = None) -> List[ComponentPosition]:
        """Get recommended positions for a component on a specific panel, avoiding collisions"""
        panel_dims = self.house_geometry.get_panel_dimensions().get(panel_name)
        if not panel_dims:
            return []
        
        panel_width, panel_height = panel_dims
        comp_width, comp_height = component_size
        existing_components = existing_components or []
        
        positions = []
        margin = self.house_geometry.thickness * 2
        min_spacing = comp_width * 0.2  # Minimum 20% spacing between components
        
        if panel_name.startswith('side_wall'):
            # Side wall recommendations
            if component_type == 'window':
                window_y = panel_height * 0.35  # Upper third, aesthetically pleasing
                
                # Start with center position if no conflicts
                center_x = (panel_width - comp_width) / 2
                center_pos = ComponentPosition(center_x, window_y, comp_width, comp_height, panel_name)
                
                if not self._has_collision(center_pos, existing_components):
                    positions.append(center_pos)
                else:
                    # If center conflicts, try left and right positions
                    candidate_positions = []
                    
                    # Try multiple positions across the wall
                    for fraction in [0.2, 0.4, 0.6, 0.8]:
                        x = panel_width * fraction - comp_width / 2
                        if x >= margin and x + comp_width <= panel_width - margin:
                            candidate_pos = ComponentPosition(x, window_y, comp_width, comp_height, panel_name)
                            if not self._has_collision(candidate_pos, existing_components):
                                candidate_positions.append(candidate_pos)
                    
                    # Add non-overlapping positions with proper spacing
                    for pos in candidate_positions:
                        if not any(self._components_too_close(pos, existing, min_spacing)
                                  for existing in positions):
                            positions.append(pos)
                            if len(positions) >= 2:  # Limit to 2 windows max for side walls
                                break
            
            elif component_type == 'door':
                # Center door horizontally, place at bottom with proper clearance
                center_x = (panel_width - comp_width) / 2
                door_y = margin
                positions.append(ComponentPosition(center_x, door_y, comp_width, comp_height, panel_name))
        
        elif panel_name.startswith('gable_wall'):
            # Gable wall recommendations
            if component_type == 'window':
                window_y = self.house_geometry.z * 0.382  # Golden ratio complement
                
                # Check if there's room for window without conflicting with door
                center_x = (panel_width - comp_width) / 2
                main_window_pos = ComponentPosition(center_x, window_y, comp_width, comp_height, panel_name)
                
                if not self._has_collision(main_window_pos, existing_components):
                    positions.append(main_window_pos)
                else:
                    # Try to fit window beside door
                    door_positions = [comp for comp in existing_components if comp.panel == panel_name]
                    if door_positions:
                        door = door_positions[0]  # Assume one door per gable wall
                        
                        # Try positions on either side of the door
                        left_x = door.x - comp_width - min_spacing
                        right_x = door.x + door.width + min_spacing
                        
                        # Smaller windows to fit beside door, but ensure minimum size
                        side_comp_width = max(comp_width * 0.7, 5.0)  # Minimum 5mm
                        side_comp_height = max(comp_height * 0.7, 5.0)  # Minimum 5mm
                        
                        # Only try side windows if they can fit properly
                        if (left_x >= margin and
                            left_x + side_comp_width <= panel_width - margin and
                            side_comp_width >= 5.0 and side_comp_height >= 5.0):
                            left_pos = ComponentPosition(left_x, window_y, side_comp_width, side_comp_height, panel_name)
                            if not self._has_collision(left_pos, existing_components):
                                positions.append(left_pos)
                        
                        if (right_x >= margin and
                            right_x + side_comp_width <= panel_width - margin and
                            side_comp_width >= 5.0 and side_comp_height >= 5.0):
                            right_pos = ComponentPosition(right_x, window_y, side_comp_width, side_comp_height, panel_name)
                            if not self._has_collision(right_pos, existing_components):
                                positions.append(right_pos)
                
                # Attic window if conditions are met and no conflicts
                if self.can_add_attic_window(self.house_geometry.gable_peak_height,
                                           self.house_geometry.theta):
                    attic_size = self.sizer.get_window_dimensions(panel_name, WindowType.ATTIC)
                    attic_width, attic_height = attic_size
                    
                    attic_center_x = (panel_width - attic_width) / 2
                    attic_y = self.house_geometry.z + self.house_geometry.gable_peak_height * 0.382
                    
                    gable_width_at_y = self._get_gable_width_at_height(attic_y + attic_height)
                    if attic_width <= gable_width_at_y - margin * 2:
                        attic_pos = ComponentPosition(attic_center_x, attic_y,
                                                    attic_width, attic_height, panel_name)
                        if not self._has_collision(attic_pos, existing_components):
                            positions.append(attic_pos)
            
            elif component_type == 'door':
                # Center door horizontally at bottom
                center_x = (panel_width - comp_width) / 2
                door_y = margin
                positions.append(ComponentPosition(center_x, door_y, comp_width, comp_height, panel_name))
        
        # Filter positions that actually fit within panel bounds
        valid_positions = []
        for pos in positions:
            if self.validate_component_placement(pos, panel_dims):
                valid_positions.append(pos)
        
        return valid_positions
    
    def _has_collision(self, component: ComponentPosition, existing_components: List[ComponentPosition]) -> bool:
        """Check if a component collides with any existing components on the same panel"""
        for existing in existing_components:
            if existing.panel != component.panel:
                continue  # Different panels, no collision
            
            # Check for overlap
            if (component.x < existing.x + existing.width and
                component.x + component.width > existing.x and
                component.y < existing.y + existing.height and
                component.y + component.height > existing.y):
                return True
        
        return False
    
    def _components_too_close(self, comp1: ComponentPosition, comp2: ComponentPosition,
                            min_spacing: float) -> bool:
        """Check if two components are too close together"""
        if comp1.panel != comp2.panel:
            return False
        
        # Calculate center-to-center distance
        center1_x = comp1.x + comp1.width / 2
        center1_y = comp1.y + comp1.height / 2
        center2_x = comp2.x + comp2.width / 2
        center2_y = comp2.y + comp2.height / 2
        
        distance = math.sqrt((center1_x - center2_x)**2 + (center1_y - center2_y)**2)
        min_center_distance = (comp1.width + comp2.width) / 2 + min_spacing
        
        return distance < min_center_distance
    
    def _get_gable_width_at_height(self, height: float) -> float:
        """Calculate the width of the gable wall at a specific height"""
        if height <= self.house_geometry.z:
            # In rectangular portion
            return self.house_geometry.x_kerf
        
        # In triangular portion
        triangle_height = height - self.house_geometry.z
        max_triangle_height = self.house_geometry.gable_peak_height
        
        if triangle_height >= max_triangle_height:
            return 0  # At or above peak
        
        # Linear interpolation for triangle width
        width_at_base = self.house_geometry.x_kerf
        width_at_height = width_at_base * (1 - triangle_height / max_triangle_height)
        
        return width_at_height


class ArchitecturalPatternGenerator:
    """Generates decorative patterns for different architectural styles"""
    
    def __init__(self, style: ArchitecturalStyle, house_geometry: HouseGeometry):
        self.style = style
        self.house_geometry = house_geometry
        self.sizer = ProportionalSizer(house_geometry)
    
    def generate_pattern_for_panel(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate SVG pattern elements for a specific panel"""
        if self.style == ArchitecturalStyle.BASIC:
            return ""  # No decorative elements
        elif self.style == ArchitecturalStyle.FACHWERKHAUS:
            return self._generate_timber_frame_pattern(panel_name, panel_bounds)
        elif self.style == ArchitecturalStyle.FARMHOUSE:
            return self._generate_farmhouse_pattern(panel_name, panel_bounds)
        elif self.style == ArchitecturalStyle.COLONIAL:
            return self._generate_colonial_pattern(panel_name, panel_bounds)
        elif self.style == ArchitecturalStyle.BRICK:
            return self._generate_brick_pattern(panel_name, panel_bounds)
        elif self.style == ArchitecturalStyle.VICTORIAN:
            return self._generate_victorian_pattern(panel_name, panel_bounds)
        elif self.style == ArchitecturalStyle.TUDOR:
            return self._generate_tudor_pattern(panel_name, panel_bounds)
        elif self.style == ArchitecturalStyle.CRAFTSMAN:
            return self._generate_craftsman_pattern(panel_name, panel_bounds)
        elif self.style == ArchitecturalStyle.GINGERBREAD:
            return self._generate_gingerbread_pattern(panel_name, panel_bounds)
        else:
            return ""
    
    def _generate_timber_frame_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate German Fachwerkhaus timber frame pattern"""
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = self.sizer.get_pattern_scale(panel_name)
        
        # Create timber frame lines with proportional spacing
        lines = []
        
        # Calculate proportional spacing
        post_spacing = max(20 * scale, width / 4)  # Minimum 20mm scaled, or quarter width
        beam_height = height * 0.618  # Golden ratio positioning
        
        # Vertical posts with proportional spacing
        x = post_spacing
        while x < width - margin:
            lines.append(f"M {x:.{COORDINATE_PRECISION}f},{margin:.{COORDINATE_PRECISION}f} "
                        f"L {x:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f}")
            x += post_spacing
        
        # Horizontal beams
        if height > 30 * scale:  # Scaled minimum height
            lines.append(f"M {margin:.{COORDINATE_PRECISION}f},{beam_height:.{COORDINATE_PRECISION}f} "
                        f"L {width-margin:.{COORDINATE_PRECISION}f},{beam_height:.{COORDINATE_PRECISION}f}")
        
        # Diagonal braces with proportional dimensions
        brace_size = min(width, height) * 0.25 * scale
        brace_start_x = width * 0.15
        brace_end_x = brace_start_x + brace_size
        brace_start_y = height * 0.25
        brace_end_y = brace_start_y + brace_size
        
        # Only add braces if there's room
        if brace_end_x < width - margin and brace_end_y < height - margin:
            lines.append(f"M {brace_start_x:.{COORDINATE_PRECISION}f},{brace_start_y:.{COORDINATE_PRECISION}f} "
                        f"L {brace_end_x:.{COORDINATE_PRECISION}f},{brace_end_y:.{COORDINATE_PRECISION}f}")
            
            # Mirror diagonal
            mirror_start_x = width - brace_start_x
            mirror_end_x = width - brace_end_x
            lines.append(f"M {mirror_start_x:.{COORDINATE_PRECISION}f},{brace_start_y:.{COORDINATE_PRECISION}f} "
                        f"L {mirror_end_x:.{COORDINATE_PRECISION}f},{brace_end_y:.{COORDINATE_PRECISION}f}")
        
        return " ".join(lines)
    
    def _generate_farmhouse_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate American farmhouse pattern (board and batten)"""
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = self.sizer.get_pattern_scale(panel_name)
        
        lines = []
        
        # Proportional board spacing (12-20mm scaled)
        board_spacing = max(12 * scale, 8.0)  # Minimum 8mm for manufacturability
        x = margin + board_spacing
        
        while x < width - margin:
            lines.append(f"M {x:.{COORDINATE_PRECISION}f},{margin:.{COORDINATE_PRECISION}f} "
                        f"L {x:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f}")
            x += board_spacing
        
        return " ".join(lines)
    
    def _generate_colonial_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate Colonial style pattern (clapboard siding)"""
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = self.sizer.get_pattern_scale(panel_name)
        
        lines = []
        
        # Proportional clapboard spacing (6-10mm scaled)
        siding_spacing = max(6 * scale, 4.0)  # Minimum 4mm for manufacturability
        y = margin + siding_spacing
        
        while y < height - margin:
            lines.append(f"M {margin:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                        f"L {width-margin:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")
            y += siding_spacing
        
        return " ".join(lines)
    
    def _generate_brick_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate brick pattern"""
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = self.sizer.get_pattern_scale(panel_name)
        
        lines = []
        # Proportional brick dimensions
        brick_height = max(4 * scale, 3.0)  # Minimum 3mm
        brick_width = brick_height * 2  # Maintain 2:1 ratio
        
        y = margin
        row = 0
        while y < height - margin - brick_height:
            # Offset every other row for brick pattern
            x_offset = (brick_width / 2) if row % 2 == 1 else 0
            x = margin + x_offset
            
            # Horizontal mortar line
            lines.append(f"M {margin:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                        f"L {width-margin:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")
            
            # Vertical mortar lines
            while x < width - margin:
                if x > margin:  # Don't draw line at very edge
                    lines.append(f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                                f"L {x:.{COORDINATE_PRECISION}f},{y+brick_height:.{COORDINATE_PRECISION}f}")
                x += brick_width
            
            y += brick_height
            row += 1
        
        return " ".join(lines)
    
    def _generate_victorian_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate Victorian ornate pattern"""
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = self.sizer.get_pattern_scale(panel_name)
        
        lines = []
        
        # Decorative corner brackets
        bracket_size = min(width, height) * 0.1 * scale
        
        # Top corners
        lines.append(f"M {margin:.{COORDINATE_PRECISION}f},{height-margin-bracket_size:.{COORDINATE_PRECISION}f} "
                    f"Q {margin:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f} "
                    f"{margin+bracket_size:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f}")
        
        lines.append(f"M {width-margin-bracket_size:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f} "
                    f"Q {width-margin:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f} "
                    f"{width-margin:.{COORDINATE_PRECISION}f},{height-margin-bracket_size:.{COORDINATE_PRECISION}f}")
        
        return " ".join(lines)
    
    def _generate_tudor_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate Tudor revival pattern (similar to timber frame)"""
        # Tudor is similar to Fachwerkhaus but with more decorative elements
        base_pattern = self._generate_timber_frame_pattern(panel_name, panel_bounds)
        
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = self.sizer.get_pattern_scale(panel_name)
        
        # Add Tudor-specific decorative elements
        decorative_lines = []
        
        # Decorative arch over potential door area
        if panel_name.startswith('gable_wall') and height > 50 * scale:
            arch_center_x = width / 2
            arch_y = margin + 25 * scale
            arch_radius = 8 * scale
            
            # Simple arch using quadratic curve
            decorative_lines.append(
                f"M {arch_center_x-arch_radius:.{COORDINATE_PRECISION}f},{arch_y:.{COORDINATE_PRECISION}f} "
                f"Q {arch_center_x:.{COORDINATE_PRECISION}f},{arch_y-arch_radius:.{COORDINATE_PRECISION}f} "
                f"{arch_center_x+arch_radius:.{COORDINATE_PRECISION}f},{arch_y:.{COORDINATE_PRECISION}f}"
            )
        
        if decorative_lines:
            return base_pattern + " " + " ".join(decorative_lines)
        return base_pattern
    
    def _generate_craftsman_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate Craftsman/Arts and Crafts pattern"""
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = self.sizer.get_pattern_scale(panel_name)
        
        lines = []
        
        # Horizontal emphasis lines at key proportions
        if height > 30 * scale:
            # Line at 1/3 height
            third_y = height * (1/3)
            lines.append(f"M {margin:.{COORDINATE_PRECISION}f},{third_y:.{COORDINATE_PRECISION}f} "
                        f"L {width-margin:.{COORDINATE_PRECISION}f},{third_y:.{COORDINATE_PRECISION}f}")
        
        if height > 45 * scale:
            # Line at 2/3 height
            two_third_y = height * (2/3)
            lines.append(f"M {margin:.{COORDINATE_PRECISION}f},{two_third_y:.{COORDINATE_PRECISION}f} "
                        f"L {width-margin:.{COORDINATE_PRECISION}f},{two_third_y:.{COORDINATE_PRECISION}f}")
        
        # Vertical accent lines at edges
        accent_offset = margin + 2 * scale
        lines.append(f"M {accent_offset:.{COORDINATE_PRECISION}f},{margin:.{COORDINATE_PRECISION}f} "
                    f"L {accent_offset:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f}")
        
        lines.append(f"M {width-accent_offset:.{COORDINATE_PRECISION}f},{margin:.{COORDINATE_PRECISION}f} "
                    f"L {width-accent_offset:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f}")
        
        return " ".join(lines)
    
    def _generate_gingerbread_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate gingerbread house decorative patterns inspired by advent calendar houses.
        
        Creates festive decorative elements including:
        - Scalloped roof edge trim
        - Decorative star and heart cutouts
        - Ornamental border patterns
        - Festive swirl elements
        """
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = self.sizer.get_pattern_scale(panel_name)
        
        lines = []
        
        # Gingerbread patterns vary by panel type
        if "roof" in panel_name:
            # Scalloped decorative edge trim for roof panels
            lines.extend(self._generate_scalloped_trim(width, height, margin, scale))
            
        elif "gable" in panel_name:
            # Front/back gable walls get decorative stars and border trim
            lines.extend(self._generate_decorative_stars(width, height, margin, scale))
            lines.extend(self._generate_ornamental_border(width, height, margin, scale))
            
        elif "side" in panel_name:
            # Side walls get hearts and swirl patterns
            lines.extend(self._generate_decorative_hearts(width, height, margin, scale))
            lines.extend(self._generate_festive_swirls(width, height, margin, scale))
            
        return " ".join(lines)
    
    def _generate_scalloped_trim(self, width: float, height: float, margin: float, scale: float) -> List[str]:
        """Generate scalloped decorative trim along roof edges."""
        lines = []
        
        # Scalloped edge along the bottom edge of roof panels
        scallop_width = 8.0 * scale
        scallop_depth = 3.0 * scale
        num_scallops = int(width / scallop_width)
        
        if num_scallops > 0:
            path_parts = [f"M {margin:.{COORDINATE_PRECISION}f} {height - margin - scallop_depth:.{COORDINATE_PRECISION}f}"]
            
            for i in range(num_scallops):
                scallop_x = margin + i * scallop_width
                # Create curved scallop using quadratic bezier
                if scallop_x + scallop_width < width - margin:
                    mid_x = scallop_x + scallop_width / 2
                    end_x = scallop_x + scallop_width
                    path_parts.append(f" Q {mid_x:.{COORDINATE_PRECISION}f} {height - margin:.{COORDINATE_PRECISION}f} {end_x:.{COORDINATE_PRECISION}f} {height - margin - scallop_depth:.{COORDINATE_PRECISION}f}")
            
            lines.append("".join(path_parts))
        
        return lines
    
    def _generate_decorative_stars(self, width: float, height: float, margin: float, scale: float) -> List[str]:
        """Generate decorative star cutouts for gingerbread houses."""
        lines = []
        
        # Avoid putting decorations too close to edges
        safe_margin = margin + 5 * scale
        safe_width = width - 2 * safe_margin
        safe_height = height - 2 * safe_margin
        
        star_size = 6.0 * scale
        if safe_width > star_size * 2 and safe_height > star_size * 2:
            # Place star in upper area of panel
            star_x = safe_margin + safe_width / 2
            star_y = safe_margin + safe_height * 0.7
            
            # Generate 5-pointed star path
            star_path = self._generate_star_path(star_x, star_y, star_size)
            lines.append(star_path)
        
        return lines
    
    def _generate_decorative_hearts(self, width: float, height: float, margin: float, scale: float) -> List[str]:
        """Generate decorative heart cutouts for gingerbread houses."""
        lines = []
        
        # Avoid putting decorations too close to edges
        safe_margin = margin + 5 * scale
        safe_width = width - 2 * safe_margin
        safe_height = height - 2 * safe_margin
        
        heart_size = 5.0 * scale
        if safe_width > heart_size * 2 and safe_height > heart_size * 2:
            # Place heart in upper area of panel
            heart_x = safe_margin + safe_width / 2
            heart_y = safe_margin + safe_height * 0.7
            
            # Generate heart path using bezier curves
            heart_path = self._generate_heart_path(heart_x, heart_y, heart_size)
            lines.append(heart_path)
        
        return lines
    
    def _generate_ornamental_border(self, width: float, height: float, margin: float, scale: float) -> List[str]:
        """Generate ornamental border trim around panel edges."""
        lines = []
        
        border_inset = margin + 3.0 * scale
        corner_radius = 2.0 * scale
        
        if border_inset + corner_radius < width / 2 and border_inset + corner_radius < height / 2:
            # Decorative border around panel perimeter
            border_path = (f"M {border_inset + corner_radius:.{COORDINATE_PRECISION}f} {border_inset:.{COORDINATE_PRECISION}f} "
                          f"L {width - border_inset - corner_radius:.{COORDINATE_PRECISION}f} {border_inset:.{COORDINATE_PRECISION}f} "
                          f"Q {width - border_inset:.{COORDINATE_PRECISION}f} {border_inset:.{COORDINATE_PRECISION}f} {width - border_inset:.{COORDINATE_PRECISION}f} {border_inset + corner_radius:.{COORDINATE_PRECISION}f} "
                          f"L {width - border_inset:.{COORDINATE_PRECISION}f} {height - border_inset - corner_radius:.{COORDINATE_PRECISION}f} "
                          f"Q {width - border_inset:.{COORDINATE_PRECISION}f} {height - border_inset:.{COORDINATE_PRECISION}f} {width - border_inset - corner_radius:.{COORDINATE_PRECISION}f} {height - border_inset:.{COORDINATE_PRECISION}f} "
                          f"L {border_inset + corner_radius:.{COORDINATE_PRECISION}f} {height - border_inset:.{COORDINATE_PRECISION}f} "
                          f"Q {border_inset:.{COORDINATE_PRECISION}f} {height - border_inset:.{COORDINATE_PRECISION}f} {border_inset:.{COORDINATE_PRECISION}f} {height - border_inset - corner_radius:.{COORDINATE_PRECISION}f} "
                          f"L {border_inset:.{COORDINATE_PRECISION}f} {border_inset + corner_radius:.{COORDINATE_PRECISION}f} "
                          f"Q {border_inset:.{COORDINATE_PRECISION}f} {border_inset:.{COORDINATE_PRECISION}f} {border_inset + corner_radius:.{COORDINATE_PRECISION}f} {border_inset:.{COORDINATE_PRECISION}f} Z")
            
            lines.append(border_path)
        
        return lines
    
    def _generate_festive_swirls(self, width: float, height: float, margin: float, scale: float) -> List[str]:
        """Generate festive swirl decorations for gingerbread houses."""
        lines = []
        
        # Avoid putting decorations too close to edges
        safe_margin = margin + 5 * scale
        safe_width = width - 2 * safe_margin
        safe_height = height - 2 * safe_margin
        
        swirl_size = 4.0 * scale
        if safe_width > swirl_size * 3 and safe_height > swirl_size * 3:
            # Place swirl in corner of safe area
            swirl_x = safe_margin + swirl_size * 1.5
            swirl_y = safe_margin + swirl_size * 1.5
            
            # Generate spiral swirl path
            swirl_path = self._generate_swirl_path(swirl_x, swirl_y, swirl_size)
            lines.append(swirl_path)
        
        return lines
    
    def _generate_star_path(self, cx: float, cy: float, size: float) -> str:
        """Generate SVG path for a 5-pointed star."""
        import math
        
        points = []
        for i in range(10):  # 5 outer + 5 inner points
            angle = (i * math.pi) / 5  # 36 degrees between points
            radius = size if i % 2 == 0 else size * 0.4  # Alternate outer/inner radius
            x = cx + radius * math.cos(angle - math.pi/2)  # Start from top
            y = cy + radius * math.sin(angle - math.pi/2)
            points.append((x, y))
        
        path_data = f"M {points[0][0]:.{COORDINATE_PRECISION}f} {points[0][1]:.{COORDINATE_PRECISION}f}"
        for point in points[1:]:
            path_data += f" L {point[0]:.{COORDINATE_PRECISION}f} {point[1]:.{COORDINATE_PRECISION}f}"
        path_data += " Z"
        
        return path_data
    
    def _generate_heart_path(self, cx: float, cy: float, size: float) -> str:
        """Generate SVG path for a heart shape."""
        # Heart shape using bezier curves
        path_data = (f"M {cx:.{COORDINATE_PRECISION}f} {cy + size * 0.3:.{COORDINATE_PRECISION}f} "  # Bottom point
                    f"C {cx - size * 0.6:.{COORDINATE_PRECISION}f} {cy - size * 0.1:.{COORDINATE_PRECISION}f} {cx - size * 0.6:.{COORDINATE_PRECISION}f} {cy - size * 0.6:.{COORDINATE_PRECISION}f} {cx:.{COORDINATE_PRECISION}f} {cy - size * 0.3:.{COORDINATE_PRECISION}f} "  # Left curve
                    f"C {cx + size * 0.6:.{COORDINATE_PRECISION}f} {cy - size * 0.6:.{COORDINATE_PRECISION}f} {cx + size * 0.6:.{COORDINATE_PRECISION}f} {cy - size * 0.1:.{COORDINATE_PRECISION}f} {cx:.{COORDINATE_PRECISION}f} {cy + size * 0.3:.{COORDINATE_PRECISION}f} "  # Right curve
                    f"Z")
        
        return path_data
    
    def _generate_swirl_path(self, cx: float, cy: float, size: float) -> str:
        """Generate SVG path for a decorative swirl."""
        # Spiral swirl using multiple curves
        path_data = (f"M {cx:.{COORDINATE_PRECISION}f} {cy:.{COORDINATE_PRECISION}f} "
                    f"Q {cx + size * 0.5:.{COORDINATE_PRECISION}f} {cy - size * 0.3:.{COORDINATE_PRECISION}f} {cx + size * 0.7:.{COORDINATE_PRECISION}f} {cy:.{COORDINATE_PRECISION}f} "
                    f"Q {cx + size * 0.5:.{COORDINATE_PRECISION}f} {cy + size * 0.5:.{COORDINATE_PRECISION}f} {cx:.{COORDINATE_PRECISION}f} {cy + size * 0.3:.{COORDINATE_PRECISION}f} "
                    f"Q {cx - size * 0.3:.{COORDINATE_PRECISION}f} {cy:.{COORDINATE_PRECISION}f} {cx - size * 0.1:.{COORDINATE_PRECISION}f} {cy - size * 0.2:.{COORDINATE_PRECISION}f}")
        
        return path_data