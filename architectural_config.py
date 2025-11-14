"""
Architectural Configuration System

Central configuration class that manages all architectural components:
- Roof types and geometry
- Door and window placement with aesthetic proportions
- Architectural style patterns
- Integration with existing HouseMaker system
"""

from typing import Dict, List, Tuple, Optional
from .architectural_components import (
    RoofType, WindowType, DoorType, ArchitecturalStyle,
    Window, Door, RoofGeometry, ComponentPositioner, ArchitecturalPatternGenerator,
    ProportionalSizer
)
from .geometry import HouseGeometry


class ArchitecturalConfiguration:
    """
    Central configuration for all architectural components of a house.
    
    This class manages:
    - Roof type and associated geometry
    - Doors and windows with automatic proportional sizing
    - Architectural style patterns
    - Integration with existing HouseMaker workflow
    """
    
    def __init__(self, house_geometry: HouseGeometry,
                 roof_type: RoofType = RoofType.GABLE,
                 architectural_style: ArchitecturalStyle = ArchitecturalStyle.BASIC):
        self.house_geometry = house_geometry
        self.roof_type = roof_type
        self.architectural_style = architectural_style
        
        # Initialize subsystems
        self.roof_geometry = RoofGeometry(roof_type, house_geometry)
        self.positioner = ComponentPositioner(house_geometry)
        self.pattern_generator = ArchitecturalPatternGenerator(architectural_style, house_geometry)
        self.sizer = ProportionalSizer(house_geometry)
        
        # Component storage
        self.windows: List[Window] = []
        self.doors: List[Door] = []
        
        # Custom component configurations
        self._custom_windows: Dict[str, List[Window]] = {}
        self._custom_doors: Dict[str, List[Door]] = {}
    
    def add_automatic_components(self,
                                add_windows: bool = True,
                                add_doors: bool = True,
                                window_type: WindowType = WindowType.RECTANGULAR,
                                door_type: DoorType = DoorType.RECTANGULAR,
                                door_panel: str = 'gable_wall_front'):
        """
        Add automatically sized and positioned components to appropriate panels,
        using collision avoidance to prevent overlapping.
        
        Args:
            add_windows: Whether to add windows
            add_doors: Whether to add doors
            window_type: Type of windows to add
            door_type: Type of doors to add
            door_panel: Panel to place door on ('gable_wall_front' or 'side_wall_right' at ground level)
        """
        panel_dims = self.house_geometry.get_panel_dimensions()
        
        # First pass: Add doors (they have priority for positioning)
        # Doors are always placed at ground level
        if add_doors:
            for panel_name in panel_dims.keys():
                if panel_name == door_panel:  # Place door on specified panel
                    doors = self.positioner.get_recommended_doors(panel_name, door_type, existing_components=[])
                    self.doors.extend(doors)
        
        # Second pass: Add windows, avoiding existing doors
        if add_windows:
            for panel_name in panel_dims.keys():
                if 'wall' in panel_name and not panel_name.startswith('roof'):
                    # Get existing components for this panel (doors already placed)
                    existing_components = [comp.position for comp in self.doors if comp.position.panel == panel_name]
                    
                    # Add regular windows, avoiding existing components
                    windows = self.positioner.get_recommended_windows(panel_name, window_type, existing_components=existing_components)
                    self.windows.extend(windows)
                    
                    # Update existing components list with newly added windows
                    existing_components.extend([w.position for w in windows])
                    
                    # Add attic windows for gable walls if conditions are met
                    if (panel_name.startswith('gable_wall') and
                        self.positioner.can_add_attic_window(
                            self.house_geometry.gable_peak_height,
                            self.house_geometry.theta)):
                        attic_windows = self.positioner.get_recommended_windows(
                            panel_name, WindowType.ATTIC, existing_components=existing_components)
                        self.windows.extend(attic_windows)
    
    def add_custom_window(self, panel_name: str, x: float, y: float, 
                         width: Optional[float] = None, height: Optional[float] = None,
                         window_type: WindowType = WindowType.RECTANGULAR) -> bool:
        """
        Add a custom positioned window with optional custom dimensions.
        
        Args:
            panel_name: Target panel name
            x, y: Position within the panel
            width, height: Custom dimensions (if None, uses proportional sizing)
            window_type: Type of window
            
        Returns:
            True if window was successfully added, False if invalid placement
        """
        # Use proportional sizing if dimensions not provided
        if width is None or height is None:
            width, height = self.sizer.get_window_dimensions(panel_name, window_type)
        
        # Create window
        from .architectural_components import ComponentPosition
        position = ComponentPosition(x, y, width, height, panel_name)
        window = Window(window_type, position)
        
        # Validate placement
        panel_dims = self.house_geometry.get_panel_dimensions().get(panel_name)
        if not panel_dims:
            return False
        
        if not self.positioner.validate_component_placement(position, panel_dims):
            return False
        
        # Add to collection
        if panel_name not in self._custom_windows:
            self._custom_windows[panel_name] = []
        self._custom_windows[panel_name].append(window)
        self.windows.append(window)
        
        return True
    
    def add_custom_door(self, panel_name: str, x: float, y: float,
                       width: Optional[float] = None, height: Optional[float] = None,
                       door_type: DoorType = DoorType.RECTANGULAR) -> bool:
        """
        Add a custom positioned door with optional custom dimensions.
        
        Args:
            panel_name: Target panel name
            x, y: Position within the panel
            width, height: Custom dimensions (if None, uses proportional sizing)
            door_type: Type of door
            
        Returns:
            True if door was successfully added, False if invalid placement
        """
        # Use proportional sizing if dimensions not provided
        if width is None or height is None:
            width, height = self.sizer.get_door_dimensions(panel_name)
        
        # Create door
        from .architectural_components import ComponentPosition
        position = ComponentPosition(x, y, width, height, panel_name)
        door = Door(door_type, position)
        
        # Validate placement
        panel_dims = self.house_geometry.get_panel_dimensions().get(panel_name)
        if not panel_dims:
            return False
        
        if not self.positioner.validate_component_placement(position, panel_dims):
            return False
        
        # Add to collection
        if panel_name not in self._custom_doors:
            self._custom_doors[panel_name] = []
        self._custom_doors[panel_name].append(door)
        self.doors.append(door)
        
        return True
    
    def get_windows_for_panel(self, panel_name: str) -> List[Window]:
        """Get all windows assigned to a specific panel"""
        return [w for w in self.windows if w.position.panel == panel_name]
    
    def get_doors_for_panel(self, panel_name: str) -> List[Door]:
        """Get all doors assigned to a specific panel"""
        return [d for d in self.doors if d.position.panel == panel_name]
    
    def get_pattern_for_panel(self, panel_name: str) -> str:
        """Get decorative pattern SVG for a specific panel"""
        panel_dims = self.house_geometry.get_panel_dimensions().get(panel_name)
        if not panel_dims:
            return ""
        
        return self.pattern_generator.generate_pattern_for_panel(panel_name, panel_dims)
    
    def get_required_roof_panels(self) -> List[str]:
        """Get list of roof panels required for the current roof type"""
        return self.roof_geometry.get_required_panels()
    
    def get_roof_panel_dimensions(self, panel_name: str) -> Tuple[float, float]:
        """Get dimensions for a specific roof panel"""
        return self.roof_geometry.get_panel_dimensions(panel_name)
    
    def has_gable_modification(self) -> bool:
        """Check if the current roof type modifies gable wall geometry"""
        return self.roof_geometry.gable_modification.get('has_gable', True)
    
    def get_gable_modification_info(self) -> Dict:
        """Get information about how the roof type modifies gable walls"""
        return self.roof_geometry.gable_modification
    
    def clear_components(self):
        """Clear all doors and windows"""
        self.windows.clear()
        self.doors.clear()
        self._custom_windows.clear()
        self._custom_doors.clear()
    
    def get_component_summary(self) -> Dict:
        """Get summary of all architectural components"""
        return {
            'roof_type': self.roof_type.value,
            'architectural_style': self.architectural_style.value,
            'total_windows': len(self.windows),
            'total_doors': len(self.doors),
            'windows_by_panel': {
                panel: len(self.get_windows_for_panel(panel))
                for panel in self.house_geometry.get_panel_dimensions().keys()
                if self.get_windows_for_panel(panel)
            },
            'doors_by_panel': {
                panel: len(self.get_doors_for_panel(panel))
                for panel in self.house_geometry.get_panel_dimensions().keys()
                if self.get_doors_for_panel(panel)
            },
            'roof_panels': self.get_required_roof_panels(),
            'has_decorative_patterns': self.architectural_style != ArchitecturalStyle.BASIC
        }
    
    def validate_all_components(self) -> List[str]:
        """
        Validate all components and return list of any issues found.
        
        Returns:
            List of validation error messages (empty if all valid)
        """
        issues = []
        panel_dims = self.house_geometry.get_panel_dimensions()
        
        for window in self.windows:
            panel_name = window.position.panel
            if panel_name not in panel_dims:
                issues.append(f"Window references unknown panel: {panel_name}")
                continue
            
            if not self.positioner.validate_component_placement(window.position, panel_dims[panel_name]):
                issues.append(f"Window placement invalid on {panel_name}: "
                            f"position=({window.position.x}, {window.position.y}), "
                            f"size=({window.position.width}×{window.position.height})")
        
        for door in self.doors:
            panel_name = door.position.panel
            if panel_name not in panel_dims:
                issues.append(f"Door references unknown panel: {panel_name}")
                continue
            
            if not self.positioner.validate_component_placement(door.position, panel_dims[panel_name]):
                issues.append(f"Door placement invalid on {panel_name}: "
                            f"position=({door.position.x}, {door.position.y}), "
                            f"size=({door.position.width}×{door.position.height})")
        
        return issues


def create_preset_configuration(house_geometry: HouseGeometry, preset_name: str) -> ArchitecturalConfiguration:
    """
    Create a preset architectural configuration.
    
    Args:
        house_geometry: The house geometry to configure
        preset_name: Name of the preset configuration
        
    Available presets:
        - 'basic': Simple house with minimal decoration
        - 'farmhouse': American farmhouse style with board and batten
        - 'colonial': Colonial style with clapboard siding
        - 'tudor': Tudor revival with timber framing
        - 'victorian': Victorian style with ornate details
        - 'craftsman': Arts and crafts style
        - 'german': Fachwerkhaus timber frame style
        - 'brick': Brick pattern style
        - 'modern_flat': Modern house with flat roof
        - 'barn_gambrel': Barn-style with gambrel roof
    """
    preset_configs = {
        'basic': {
            'roof_type': RoofType.GABLE,
            'style': ArchitecturalStyle.BASIC,
            'window_type': WindowType.RECTANGULAR,
            'door_type': DoorType.RECTANGULAR
        },
        'farmhouse': {
            'roof_type': RoofType.GABLE,
            'style': ArchitecturalStyle.FARMHOUSE,
            'window_type': WindowType.RECTANGULAR,
            'door_type': DoorType.RECTANGULAR
        },
        'colonial': {
            'roof_type': RoofType.GABLE,
            'style': ArchitecturalStyle.COLONIAL,
            'window_type': WindowType.RECTANGULAR,
            'door_type': DoorType.RECTANGULAR
        },
        'tudor': {
            'roof_type': RoofType.GABLE,
            'style': ArchitecturalStyle.TUDOR,
            'window_type': WindowType.ARCHED,
            'door_type': DoorType.ARCHED
        },
        'victorian': {
            'roof_type': RoofType.GABLE,
            'style': ArchitecturalStyle.VICTORIAN,
            'window_type': WindowType.ARCHED,
            'door_type': DoorType.RECTANGULAR
        },
        'craftsman': {
            'roof_type': RoofType.GABLE,
            'style': ArchitecturalStyle.CRAFTSMAN,
            'window_type': WindowType.RECTANGULAR,
            'door_type': DoorType.RECTANGULAR
        },
        'german': {
            'roof_type': RoofType.GABLE,
            'style': ArchitecturalStyle.FACHWERKHAUS,
            'window_type': WindowType.RECTANGULAR,
            'door_type': DoorType.ARCHED
        },
        'brick': {
            'roof_type': RoofType.GABLE,
            'style': ArchitecturalStyle.BRICK,
            'window_type': WindowType.RECTANGULAR,
            'door_type': DoorType.RECTANGULAR
        },
        'modern_flat': {
            'roof_type': RoofType.FLAT,
            'style': ArchitecturalStyle.BASIC,
            'window_type': WindowType.RECTANGULAR,
            'door_type': DoorType.RECTANGULAR
        },
        'barn_gambrel': {
            'roof_type': RoofType.GAMBREL,
            'style': ArchitecturalStyle.FARMHOUSE,
            'window_type': WindowType.RECTANGULAR,
            'door_type': DoorType.DOUBLE
        }
    }
    
    if preset_name not in preset_configs:
        raise ValueError(f"Unknown preset: {preset_name}. Available presets: {list(preset_configs.keys())}")
    
    config = preset_configs[preset_name]
    
    # Create configuration
    arch_config = ArchitecturalConfiguration(
        house_geometry=house_geometry,
        roof_type=config['roof_type'],
        architectural_style=config['style']
    )
    
    # Add automatic components
    arch_config.add_automatic_components(
        add_windows=True,
        add_doors=True,
        window_type=config['window_type'],
        door_type=config['door_type']
    )
    
    return arch_config