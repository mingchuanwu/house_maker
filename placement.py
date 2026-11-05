"""
Component sizing and automatic placement (proportions, floors, collision avoidance).

Pure planning on top of HouseGeometry; produces component objects, never SVG.
"""

import math
from typing import List, Optional, Tuple

from .components import ComponentPosition, Door, DoorType, Window, WindowType
from .geometry import HouseGeometry


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
    
    def get_door_dimensions(self, panel_name: str, floor_height: float = None) -> Tuple[float, float]:
        """
        Calculate aesthetically pleasing door dimensions based on floor height.
        
        Args:
            panel_name: Name of the panel
            floor_height: Height of the floor where door is located (ground floor)
                         If None, uses old method with entire wall height
        
        Returns:
            Tuple of (door_width, door_height) in mm
        """
        panel_dims = self.house_geometry.get_panel_dimensions().get(panel_name)
        if not panel_dims:
            return (15.0, 30.0)  # Fallback minimum
        
        panel_width, panel_height = panel_dims
        
        # Use floor height if provided, otherwise use wall height
        if floor_height is not None:
            usable_height = floor_height
        elif panel_name.startswith('gable_wall'):
            # For gable walls, use the rectangular portion height
            usable_height = self.house_geometry.z
        else:
            usable_height = panel_height
        
        # Calculate door height (80% of floor/wall height, but reasonable limits)
        door_height = usable_height * self.DOOR_HEIGHT_RATIO
        door_height = max(15.0, min(door_height, usable_height - 10))  # Min 15mm, max height-10mm
        
        # Calculate door width using proportional ratio
        door_width = door_height * self.DOOR_WIDTH_RATIO
        door_width = max(8.0, min(door_width, panel_width - 20))  # Min 8mm, max wall-20mm
        
        return (door_width, door_height)
    
    def get_window_dimensions(self, panel_name: str, window_type: WindowType,
                             floor_height: float = None) -> Tuple[float, float]:
        """
        Calculate aesthetically pleasing window dimensions based on floor height.
        
        Args:
            panel_name: Name of the panel
            window_type: Type of window
            floor_height: Height of the floor where window is located
                         If None, uses old method with entire wall height
        
        Returns:
            Tuple of (window_width, window_height) in mm
        """
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
                # Regular windows based on floor height if provided
                if floor_height is not None:
                    usable_height = floor_height
                else:
                    usable_height = self.house_geometry.z
                base_height = usable_height * self.WINDOW_HEIGHT_RATIO
                base_width = base_height * self.WINDOW_WIDTH_RATIO
                scale = 1.0
        else:
            # Side wall windows based on floor height if provided
            if floor_height is not None:
                base_height = floor_height * self.WINDOW_HEIGHT_RATIO
            else:
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
        
        # Apply reasonable limits based on floor height if available
        max_height = floor_height * 0.6 if floor_height else panel_height * 0.6
        window_height = max(5.0, min(window_height, max_height))
        window_width = max(5.0, min(window_width, panel_width * 0.8))
        
        return (window_width, window_height)
    


class ComponentPositioner:
    """Handles positioning logic for doors and windows"""
    
    def __init__(self, house_geometry: HouseGeometry):
        self.house_geometry = house_geometry
        self.sizer = ProportionalSizer(house_geometry)
    
    def calculate_number_of_floors(self) -> int:
        """
        Calculate the number of floors based on house height and dimensions.
        Uses the formula: house_height // ((house_length + house_width)/2) as floor height
        
        If remaining height > 1/4 * floor_height, it becomes an attic floor.
        Otherwise, the extra height is added to the ground floor as high ceiling.
        
        Returns:
            Number of floors (minimum 1)
        """
        avg_dimension = (self.house_geometry.x + self.house_geometry.y) / 2
        floor_height = avg_dimension
        
        if floor_height <= 0:
            return 1
        
        num_floors = int(self.house_geometry.z // floor_height)
        remaining_height = self.house_geometry.z - (num_floors * floor_height)
        
        # If remaining height > 1/4 of floor height, add an attic floor
        if remaining_height > floor_height * 0.25:
            num_floors += 1
        
        return max(1, num_floors)
    
    def get_floor_height(self, floor_index: int = 0) -> float:
        """
        Get the height of a specific floor.
        Ground floor (index 0) may have extra height if remaining_height < 1/4 floor_height.
        Attic floor (last floor) may be shorter if it's made from remaining height.
        
        Args:
            floor_index: 0-based floor index (0 = ground floor)
            
        Returns:
            Height of the specified floor in mm
        """
        avg_dimension = (self.house_geometry.x + self.house_geometry.y) / 2
        standard_floor_height = avg_dimension
        
        if standard_floor_height <= 0:
            return self.house_geometry.z
        
        num_standard_floors = int(self.house_geometry.z // standard_floor_height)
        remaining_height = self.house_geometry.z - (num_standard_floors * standard_floor_height)
        total_floors = self.calculate_number_of_floors()
        
        # Determine if we have an attic
        has_attic = remaining_height > standard_floor_height * 0.25
        
        if has_attic:
            # Last floor is attic with remaining height
            if floor_index == total_floors - 1:
                return remaining_height
            else:
                return standard_floor_height
        else:
            # Extra height goes to ground floor
            if floor_index == 0:
                return standard_floor_height + remaining_height
            else:
                return standard_floor_height
    
    def validate_component_placement(self, component: ComponentPosition, 
                                   panel_dims: Tuple[float, float]) -> bool:
        """Validate that a component fits within its target panel"""
        panel_width, panel_height = panel_dims
        
        # Check bounds
        eps = 1e-9      # exact-fit placements must not be rejected by floating-point rounding
        if (component.x + component.width > panel_width + eps or
            component.y + component.height > panel_height + eps):
            return False
        
        # Check minimum margins from edges
        margin = self.house_geometry.thickness
        if (component.x < margin - eps or component.y < margin - eps or
            component.x + component.width > panel_width - margin + eps or
            component.y + component.height > panel_height - margin + eps):
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
        
        # Create windows
        windows = []
        for pos in positions:
            window = Window(window_type, pos)
            windows.append(window)
            
            # For assemblies that shouldn't be repeated, limit to one per wall
            if window_type in [WindowType.COLONIAL_SET, WindowType.PALLADIAN, WindowType.MULTI_PANE]:
                break
        
        return windows
    
    def get_recommended_doors(self, panel_name: str,
                            door_type: DoorType = DoorType.RECTANGULAR,
                            existing_components: List[ComponentPosition] = None) -> List[Door]:
        """Get recommended doors with proper proportions for a panel"""
        # Doors are always on ground floor (floor 0)
        ground_floor_height = self.get_floor_height(0)
        
        # Calculate appropriate door size based on ground floor height
        door_size = self.sizer.get_door_dimensions(panel_name, ground_floor_height)
        
        # Get positions for this door size, avoiding existing components
        positions = self._get_positions_for_component(panel_name, 'door', door_size, existing_components)
        
        # Create door objects
        doors = []
        for pos in positions:
            door = Door(door_type, pos)
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
                # Calculate number of floors and distribute windows
                num_floors = self.calculate_number_of_floors()
                
                # Place windows on each floor with floor-specific sizing
                floor_y_start = 0
                for floor in range(num_floors):
                    # Get this floor's height
                    floor_height = self.get_floor_height(floor)
                    
                    # Calculate window size for THIS specific floor
                    comp_width, comp_height = self.sizer.get_window_dimensions(
                        panel_name, WindowType.RECTANGULAR, floor_height)
                    
                    # Position window in the middle of this floor
                    window_y = floor_y_start + floor_height * 0.4
                    
                    # Ensure window doesn't go beyond this floor or panel height
                    if window_y + comp_height > floor_y_start + floor_height - margin:
                        floor_y_start += floor_height
                        continue
                    if window_y + comp_height > panel_height - margin:
                        break
                    
                    min_spacing = comp_width * 0.2
                    
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
                                break  # One window per floor
                    
                    floor_y_start += floor_height
            
            elif component_type == 'door':
                # Center door horizontally, place at ground level (bottom) with proper clearance
                center_x = (panel_width - comp_width) / 2
                door_y = margin
                positions.append(ComponentPosition(center_x, door_y, comp_width, comp_height, panel_name))
        
        elif panel_name.startswith('gable_wall'):
            # Gable wall recommendations
            if component_type == 'window':
                # Calculate number of floors and distribute windows on gable walls too
                num_floors = self.calculate_number_of_floors()
                
                # Place windows on each floor with floor-specific sizing (only in the rectangular portion, not the gable)
                floor_y_start = 0
                for floor in range(num_floors):
                    # Get this floor's height
                    floor_height = self.get_floor_height(floor)
                    
                    # Calculate window size for THIS specific floor
                    comp_width, comp_height = self.sizer.get_window_dimensions(
                        panel_name, WindowType.RECTANGULAR, floor_height)
                    
                    window_y = floor_y_start + floor_height * 0.4
                    
                    # Ensure window stays in the rectangular portion of gable wall
                    if window_y + comp_height > self.house_geometry.z - margin:
                        break
                    if window_y + comp_height > floor_y_start + floor_height - margin:
                        floor_y_start += floor_height
                        continue
                    
                    min_spacing = comp_width * 0.2
                    
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
                    
                    floor_y_start += floor_height
                
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
                # Center door horizontally at ground level (bottom)
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

