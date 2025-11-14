"""
Simplified finger joint generation system for house box panels
Implements single finger joint per edge with proper male/female coordination
Based on systematic edge adjacency analysis
"""

import math
from typing import List, Tuple, Dict
from .geometry import Point, HouseGeometry
from .exceptions import FingerJointError
from .constants import COORDINATE_PRECISION


class FingerJointGenerator:
    """
    Generates single centered finger joints per edge
    
    Based on user specification diagrams showing:
    - One finger joint per edge (length l, thickness w)  
    - Male and female joints are mirror images
    - Simple rectangular joint design
    """
    
    def __init__(self, geometry: HouseGeometry):
        self.geometry = geometry
        # Use original dimensions for design calculations,
        # but apply kerf compensation for manufacturing precision
        self.thickness = geometry.thickness
        self.finger_length = geometry.finger_length
        # Kerf-compensated dimensions for tight joints
        self.male_thickness = geometry.thickness + geometry.kerf  # Male fingers larger to account for kerf shrinkage
        self.female_thickness = geometry.thickness - geometry.kerf  # Female slots smaller to account for kerf expansion
        self.cutout_thickness = geometry.thickness - geometry.kerf  # Internal cutouts smaller for kerf expansion
        self.cutout_length = geometry.finger_length - geometry.kerf
    
    def generate_edge_with_joint(self, start_point: Point, end_point: Point,
                                has_joint: bool, is_male: bool,
                                thickness_direction: int = 1) -> str:
        """
        Generate SVG path for an edge with optional single finger joint
        
        Args:
            start_point: Starting point of the edge
            end_point: Ending point of the edge
            has_joint: True if this edge should have a finger joint
            is_male: True for male joint (tab), False for female joint (gap)
            thickness_direction: 1 for standard direction, -1 for reversed direction
            
        Returns:
            SVG path string for the edge
        """
        if not has_joint:
            # Simple straight line (e.g., smooth top edge of walls)
            return f"L {end_point.x:.{COORDINATE_PRECISION}f},{end_point.y:.{COORDINATE_PRECISION}f}"
        
        # Calculate edge vector and length
        dx = end_point.x - start_point.x
        dy = end_point.y - start_point.y
        edge_length = (dx * dx + dy * dy) ** 0.5
        
        if edge_length < self.finger_length * 1.5:
            # Edge too short for finger joint
            return f"L {end_point.x:.{COORDINATE_PRECISION}f},{end_point.y:.{COORDINATE_PRECISION}f}"
        
        # Calculate unit vectors
        ux = dx / edge_length  # Unit vector along edge
        uy = dy / edge_length
        
        # Calculate perpendicular vector pointing outward from panel
        # Two perpendicular options: 90° clockwise or counterclockwise rotation
        perp1_x = -uy  # 90° counterclockwise
        perp1_y = ux
        perp2_x = uy   # 90° clockwise
        perp2_y = -ux
        
        # Choose the correct perpendicular based on which points "outward" from panel center
        # This is a heuristic: for most panels, outward means away from the panel's geometric center
        # We'll use the perpendicular that points away from the opposite edge
        
        # For simplicity, let's use thickness_direction to indicate which perpendicular to use
        # thickness_direction=1 means use perp1, thickness_direction=-1 means use perp2
        if thickness_direction == 1:
            outward_vx = perp1_x
            outward_vy = perp1_y
        else:
            outward_vx = perp2_x
            outward_vy = perp2_y
        
        # Direction is already determined by _get_joint_direction()
        # No need to flip based on is_male here
        vx = outward_vx
        vy = outward_vy
        
        
        # Center the finger joint on the edge
        joint_start = (edge_length - self.finger_length) / 2
        joint_end = joint_start + self.finger_length
        
        path_parts = []
        
        # Both male and female use the same path generation logic now
        # The difference is already handled in the vector calculation above
        
        # Move to start of joint
        x1 = start_point.x + ux * joint_start
        y1 = start_point.y + uy * joint_start
        path_parts.append(f"L {x1:.{COORDINATE_PRECISION}f},{y1:.{COORDINATE_PRECISION}f}")
        
        # Extend in calculated direction using kerf-compensated dimensions
        # Male joints are larger to compensate for kerf shrinkage
        # Female joints are smaller to compensate for kerf expansion
        joint_thickness = self.male_thickness if is_male else self.female_thickness
        
        x2 = x1 + vx * joint_thickness
        y2 = y1 + vy * joint_thickness
        path_parts.append(f"L {x2:.{COORDINATE_PRECISION}f},{y2:.{COORDINATE_PRECISION}f}")

        # Along joint edge
        x3 = start_point.x + ux * joint_end + vx * joint_thickness
        y3 = start_point.y + uy * joint_end + vy * joint_thickness
        path_parts.append(f"L {x3:.{COORDINATE_PRECISION}f},{y3:.{COORDINATE_PRECISION}f}")
        
        # Back to edge
        x4 = start_point.x + ux * joint_end
        y4 = start_point.y + uy * joint_end
        path_parts.append(f"L {x4:.{COORDINATE_PRECISION}f},{y4:.{COORDINATE_PRECISION}f}")
        
        # Complete to end point
        path_parts.append(f"L {end_point.x:.{COORDINATE_PRECISION}f},{end_point.y:.{COORDINATE_PRECISION}f}")
        
        return " ".join(path_parts)
    
    def generate_internal_female_cutout(self, center_x: float, center_y: float,
                                      orientation: str = 'horizontal') -> str:
        """
        Generate internal female cutout for roof panels
        Two female cutouts inside each roof panel as shown in diagrams
        Uses kerf-compensated dimensions for tight fit after laser cutting.
        """
        # Use kerf-compensated dimensions for internal cutouts
        # Cutouts are smaller so they expand to correct size after kerf
        half_length = self.cutout_length / 2
        half_thickness = self.cutout_thickness / 2
        
        if orientation == 'horizontal':
            # Horizontal cutout
            return (f"M {center_x - half_length:.{COORDINATE_PRECISION}f},"
                   f"{center_y - half_thickness:.{COORDINATE_PRECISION}f} "
                   f"L {center_x + half_length:.{COORDINATE_PRECISION}f},"
                   f"{center_y - half_thickness:.{COORDINATE_PRECISION}f} "
                   f"L {center_x + half_length:.{COORDINATE_PRECISION}f},"
                   f"{center_y + half_thickness:.{COORDINATE_PRECISION}f} "
                   f"L {center_x - half_length:.{COORDINATE_PRECISION}f},"
                   f"{center_y + half_thickness:.{COORDINATE_PRECISION}f} Z")
        else:
            # Vertical cutout
            return (f"M {center_x - half_thickness:.{COORDINATE_PRECISION}f},"
                   f"{center_y - half_length:.{COORDINATE_PRECISION}f} "
                   f"L {center_x + half_thickness:.{COORDINATE_PRECISION}f},"
                   f"{center_y - half_length:.{COORDINATE_PRECISION}f} "
                   f"L {center_x + half_thickness:.{COORDINATE_PRECISION}f},"
                   f"{center_y + half_length:.{COORDINATE_PRECISION}f} "
                   f"L {center_x - half_thickness:.{COORDINATE_PRECISION}f},"
                   f"{center_y + half_length:.{COORDINATE_PRECISION}f} Z")


class HousePanelGenerator:
    """
    Generates house panels using centralized finger joint configuration with architectural components
    Eliminates hardcoded logic by using geometry.get_finger_joint_configuration()
    Integrates door/window cutouts and decorative patterns
    """
    
    def __init__(self, geometry: HouseGeometry, architectural_config=None):
        self.geometry = geometry
        self.joint_generator = FingerJointGenerator(geometry)
        self.joint_config = geometry.get_finger_joint_configuration()
        self.architectural_config = architectural_config
    
    def _generate_panel_with_config(self, panel_name: str, position: Point,
                                  corners: List[Point], edge_names: List[str]) -> str:
        """
        Generic panel generator driven by centralized configuration
        
        Args:
            panel_name: Name of panel (must exist in joint_config)
            position: Panel position
            corners: List of corner points defining panel shape
            edge_names: List of edge names corresponding to corners (e.g., ['bottom', 'right', 'top', 'left'])
            
        Returns:
            SVG path string for the panel
        """
        if panel_name not in self.joint_config:
            raise FingerJointError(f"No configuration found for panel: {panel_name}")
            
        panel_config = self.joint_config[panel_name]
        path = f"M {corners[0].x:.{COORDINATE_PRECISION}f},{corners[0].y:.{COORDINATE_PRECISION}f}"
        
        
        # Generate each edge based on configuration
        for i, edge_name in enumerate(edge_names):
            start_corner = corners[i]
            end_corner = corners[(i + 1) % len(corners)]
            
            if edge_name in panel_config:
                joint_type = panel_config[edge_name]
                
                if joint_type is None:
                    # No joint - smooth edge
                    has_joint = False
                    is_male = False
                    thickness_direction = 1
                elif joint_type is True:
                    # Male joint - get final direction for male joint
                    has_joint = True
                    is_male = True
                    thickness_direction = self._get_joint_direction(panel_name, edge_name, i, is_male=True)
                elif joint_type is False:
                    # Female joint - get final direction for female joint (opposite of male)
                    has_joint = True
                    is_male = False
                    thickness_direction = self._get_joint_direction(panel_name, edge_name, i, is_male=False)
                else:
                    # Unknown configuration
                    raise FingerJointError(f"Invalid joint_type configuration: {joint_type}")
            else:
                # Edge not in config - default to smooth
                has_joint = False
                is_male = False
                thickness_direction = 1
            
            
            path += " " + self.joint_generator.generate_edge_with_joint(
                start_corner, end_corner, has_joint, is_male, thickness_direction)
        
        path += " Z"
        
        # Add internal features if specified
        if 'internal_cutouts' in panel_config:
            cutouts = panel_config['internal_cutouts']
            if cutouts and len(cutouts) > 0:
                path += self._generate_internal_cutouts(position, panel_name, cutouts)
        
        # Separate structural path from decorative patterns for different line styles
        structural_path = path
        decorative_patterns = ""
        
        # Add architectural components (doors, windows, decorative patterns)
        if self.architectural_config:
            structural_cutouts, decorative_patterns = self._generate_architectural_features(position, panel_name, corners)
            # Add structural cutouts (doors/windows) to the main structural path
            if structural_cutouts:
                structural_path += " " + structural_cutouts
        else:
            decorative_patterns = ""
        
        return structural_path, decorative_patterns
    
    def _generate_internal_cutouts(self, position: Point, panel_name: str, cutouts: List[str]) -> str:
        """Generate internal cutouts for panels (e.g., roof panels)"""
        cutout_paths = []
        
        if panel_name.startswith('roof_panel'):
            # Get roof panel dimensions based on panel type
            roof_panel_length = self.geometry.get_roof_panel_length()  # Use getter method
            
            # Use pre-calculated base roof width from geometry
            base_roof_width = self.geometry.base_roof_width
            
            if panel_name == 'roof_panel_left':
                # Left panel cutout y-coordinate: ((y/2)/cos(θ))/2 + thickness
                cutout_center_y = position.y + (base_roof_width / 2) + self.geometry.thickness
            elif panel_name == 'roof_panel_right':
                # Right panel cutout y-coordinate: ((y/2)/cos(θ))/2
                cutout_center_y = position.y + (base_roof_width / 2)
            else:
                # Fallback - shouldn't happen
                cutout_center_y = position.y + (base_roof_width / 2)
            
            # Position cutouts with thickness distance from edges
            for i, orientation in enumerate(cutouts):
                if i == 0:  # Left cutout - thickness distance from left edge (center positioning)
                    cutout_x = position.x + 2.5 * self.geometry.thickness
                    cutout_y = cutout_center_y
                elif i == 1:  # Right cutout - thickness distance from right edge (center positioning)
                    cutout_x = position.x + roof_panel_length - 2.5 * self.geometry.thickness
                    cutout_y = cutout_center_y
                else:
                    continue  # Only support 2 cutouts for now
                
                cutout_paths.append(
                    self.joint_generator.generate_internal_female_cutout(
                        cutout_x, cutout_y, orientation))
        
        return " ".join(cutout_paths)
    
    def generate_floor_panel(self, position: Point) -> tuple:
        """Generate floor panel using centralized configuration"""
        width = self.geometry.length
        height = self.geometry.width
        
        corners = [
            Point(position.x, position.y),                    # Bottom-left
            Point(position.x + width, position.y),           # Bottom-right
            Point(position.x + width, position.y + height),  # Top-right
            Point(position.x, position.y + height)           # Top-left
        ]
        
        edge_names = ['bottom', 'right', 'top', 'left']
        return self._generate_panel_with_config('floor', position, corners, edge_names)
    
    def generate_wall_panel(self, position: Point, wall_type: str) -> tuple:
        """Generate side wall panel using centralized configuration"""
        # Use centralized panel dimensions from geometry
        panel_dimensions = self.geometry.get_panel_dimensions()
        width, height = panel_dimensions[wall_type]
        
        corners = [
            Point(position.x, position.y),                    # Bottom-left
            Point(position.x + width, position.y),           # Bottom-right
            Point(position.x + width, position.y + height),  # Top-right
            Point(position.x, position.y + height)           # Top-left
        ]
        
        edge_names = ['bottom', 'right', 'top', 'left']
        return self._generate_panel_with_config(wall_type, position, corners, edge_names)
    
    def generate_gable_wall_panel(self, position: Point, gable_type: str) -> tuple:
        """Generate gable wall panel using centralized configuration"""
        # Use centralized panel dimensions from geometry
        wall_height = self.geometry.height
        panel_dimensions = self.geometry.get_panel_dimensions()
        width, total_height = panel_dimensions[gable_type]
        
        # House-shaped profile points
        corners = [
            Point(position.x, position.y),                           # Bottom-left
            Point(position.x + width, position.y),                  # Bottom-right
            Point(position.x + width, position.y + wall_height),    # Wall top-right
            Point(position.x + width/2, position.y + total_height), # Gable peak
            Point(position.x, position.y + wall_height)             # Wall top-left
        ]
        
        edge_names = ['bottom', 'right', 'roof_right', 'roof_left', 'left']
        return self._generate_panel_with_config(gable_type, position, corners, edge_names)
    
    def generate_roof_panel(self, position: Point, roof_type: str) -> tuple:
        """Generate roof panel using centralized configuration with asymmetric dimensions"""
        roof_panel_length = self.geometry.get_roof_panel_length()
        
        # Get width based on roof panel type
        if roof_type == 'roof_panel_left':
            roof_panel_width = self.geometry.get_roof_panel_left_width()
        elif roof_type == 'roof_panel_right':
            roof_panel_width = self.geometry.get_roof_panel_right_width()
        else:
            # Fallback - shouldn't happen
            roof_panel_width = self.geometry.get_roof_panel_left_width()
        
        corners = [
            Point(position.x, position.y),                              # Bottom-left
            Point(position.x + roof_panel_length, position.y),         # Bottom-right
            Point(position.x + roof_panel_length, position.y + roof_panel_width), # Top-right
            Point(position.x, position.y + roof_panel_width)           # Top-left
        ]
        
        edge_names = ['gable_edge', 'right', 'outer', 'left']
        return self._generate_panel_with_config(roof_type, position, corners, edge_names)
    
    def _get_joint_direction(self, panel_name: str, edge_name: str, edge_index: int, is_male: bool) -> int:
        """
        Determine the correct joint direction for a panel edge
        
        For rectangular panels, edges follow this pattern (clockwise from bottom-left):
        - edge_index 0: bottom edge (outward = downward = clockwise perp)
        - edge_index 1: right edge (outward = rightward = clockwise perp)
        - edge_index 2: top edge (outward = upward = clockwise perp)
        - edge_index 3: left edge (outward = leftward = clockwise perp)
        
        Male joints extend outward, female joints go inward (opposite direction)
        
        Args:
            panel_name: Name of the panel
            edge_name: Name of the edge
            edge_index: Index of the edge in the corner list
            is_male: True for male joint (outward), False for female joint (inward)
        
        Returns:
            1 for counterclockwise perpendicular, -1 for clockwise perpendicular
        """
        
        # Determine base outward direction (for male joints)
        if panel_name in ['floor', 'side_wall_left', 'side_wall_right']:
            # Rectangular panels: all edges use clockwise perpendicular to point outward
            outward_direction = -1
            
        elif panel_name in ['gable_wall_front', 'gable_wall_back']:
            # House-shaped panels: 5 edges [bottom, right, roof_right, roof_left, left]
            if edge_index in [0, 1, 4]:  # bottom, right, left edges
                outward_direction = -1  # clockwise perpendicular
            else:  # roof edges (roof_right, roof_left)
                outward_direction = -1  # clockwise perpendicular for now
                
        elif panel_name in ['roof_panel_left', 'roof_panel_right']:
            # Roof panels: rectangular, all edges use clockwise perpendicular
            outward_direction = -1
            
        else:
            # Default to clockwise
            outward_direction = -1
        
        # Apply joint type: male uses outward direction, female uses opposite (inward)
        if is_male:
            result = outward_direction
        else:
            result = -outward_direction  # Female joints go opposite direction (inward)
            
        return result
    
    def _generate_architectural_features(self, position: Point, panel_name: str, corners: List[Point]) -> tuple:
        """
        Generate architectural features (doors, windows, decorative patterns) for a panel
        
        Args:
            position: Panel position
            panel_name: Name of the panel (e.g., 'gable_wall_front', 'side_wall_left')
            corners: List of corner points defining panel shape
            
        Returns:
            Tuple of (structural_cutouts, decorative_patterns) as separate SVG path strings
        """
        if not self.architectural_config:
            return "", ""
        
        structural_cutouts = []
        decorative_patterns = []
        
        # Get doors and windows for this panel
        doors = self.architectural_config.get_doors_for_panel(panel_name)
        windows = self.architectural_config.get_windows_for_panel(panel_name)
        
        # Generate door cutouts (structural)
        for door in doors:
            cutout = self._generate_cutout(position, door.position, 'door')
            if cutout:
                structural_cutouts.append(cutout)
        
        # Generate window cutouts (structural)
        for window in windows:
            cutout = self._generate_cutout(position, window.position, 'window')
            if cutout:
                structural_cutouts.append(cutout)
        
        # Generate decorative patterns for the architectural style
        if self.architectural_config.pattern_generator:
            patterns = self._generate_decorative_patterns(position, panel_name, corners)
            if patterns:
                decorative_patterns.append(patterns)
        
        return " ".join(structural_cutouts), " ".join(decorative_patterns)
    
    def _generate_cutout(self, panel_position: Point, component_position, component_type: str) -> str:
        """
        Generate SVG cutout for a door or window with proper shapes based on type
        
        Args:
            panel_position: Position of the panel
            component_position: Position object with x, y, width, height
            component_type: 'door' or 'window'
            
        Returns:
            SVG path string for the shaped cutout
        """
        # Calculate absolute position of cutout
        x = panel_position.x + component_position.x
        y = panel_position.y + component_position.y
        width = component_position.width
        height = component_position.height
        
        # Determine the specific component type from architectural config
        if component_type == 'door':
            # Find the door object to get its type
            doors = self.architectural_config.get_doors_for_panel(component_position.panel)
            door_obj = next((d for d in doors if
                           d.position.x == component_position.x and
                           d.position.y == component_position.y), None)
            if door_obj:
                return self._generate_door_cutout(x, y, width, height, door_obj.type)
        elif component_type == 'window':
            # Find the window object to get its type
            windows = self.architectural_config.get_windows_for_panel(component_position.panel)
            window_obj = next((w for w in windows if
                             w.position.x == component_position.x and
                             w.position.y == component_position.y), None)
            if window_obj:
                return self._generate_window_cutout(x, y, width, height, window_obj.type)
        
        # Fallback to rectangular cutout
        return self._generate_rectangular_cutout(x, y, width, height)
    
    def _generate_rectangular_cutout(self, x: float, y: float, width: float, height: float) -> str:
        """Generate a simple rectangular cutout"""
        return (
            f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
            f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
            f"L {x + width:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
            f"L {x:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} Z"
        )
    
    def _generate_door_cutout(self, x: float, y: float, width: float, height: float, door_type) -> str:
        """Generate shaped door cutouts based on door type"""
        from .architectural_components import DoorType
        
        if door_type == DoorType.DUTCH:
            # Dutch door - horizontal split in the middle
            mid_height = height / 2
            return (
                # Bottom half
                f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y + mid_height:.{COORDINATE_PRECISION}f} "
                f"L {x:.{COORDINATE_PRECISION}f},{y + mid_height:.{COORDINATE_PRECISION}f} Z "
                # Top half
                f"M {x:.{COORDINATE_PRECISION}f},{y + mid_height + 2:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y + mid_height + 2:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
                f"L {x:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} Z"
            )
        elif door_type == DoorType.DOUBLE:
            # Double door - vertical split in the middle
            mid_width = width / 2
            return (
                # Left door
                f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + mid_width - 1:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + mid_width - 1:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
                f"L {x:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} Z "
                # Right door
                f"M {x + mid_width + 1:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
                f"L {x + mid_width + 1:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} Z"
            )
        elif door_type == DoorType.ARCHED:
            # Arched door - rectangular bottom with semicircular top
            arch_height = min(width / 2, height * 0.3)  # Arch height is limited
            rect_height = height - arch_height
            center_x = x + width / 2
            arch_top = y + height
            return (
                # Rectangular bottom portion
                f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
                # Arched top using quadratic curve
                f"Q {center_x:.{COORDINATE_PRECISION}f},{arch_top:.{COORDINATE_PRECISION}f} "
                f"{x:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} Z"
            )
        else:
            # Default rectangular door
            return self._generate_rectangular_cutout(x, y, width, height)
    
    def _generate_window_cutout(self, x: float, y: float, width: float, height: float, window_type) -> str:
        """Generate shaped window cutouts based on window type"""
        from .architectural_components import WindowType
        
        if window_type == WindowType.ARCHED:
            # Arched window - rectangular bottom with semicircular top
            arch_height = min(width / 2, height * 0.4)  # Arch height
            rect_height = height - arch_height
            center_x = x + width / 2
            arch_top = y + height
            return (
                # Rectangular bottom portion
                f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
                # Arched top using quadratic curve
                f"Q {center_x:.{COORDINATE_PRECISION}f},{arch_top:.{COORDINATE_PRECISION}f} "
                f"{x:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} Z"
            )
        elif window_type == WindowType.CIRCULAR:
            # Circular window - use the smaller dimension as diameter
            radius = min(width, height) / 2
            center_x = x + width / 2
            center_y = y + height / 2
            return (
                f"M {center_x + radius:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
                f"A {radius:.{COORDINATE_PRECISION}f},{radius:.{COORDINATE_PRECISION}f} 0 1,0 "
                f"{center_x - radius:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
                f"A {radius:.{COORDINATE_PRECISION}f},{radius:.{COORDINATE_PRECISION}f} 0 1,0 "
                f"{center_x + radius:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} Z"
            )
        elif window_type == WindowType.ATTIC:
            # Attic window - smaller rectangular with peaked top
            peak_height = height * 0.2
            rect_height = height - peak_height
            center_x = x + width / 2
            return (
                # Rectangular bottom
                f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
                # Peaked top
                f"L {center_x:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
                f"L {x:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} Z"
            )
        elif window_type == WindowType.CROSS_PANE:
            # Cross-pane window - rectangular with cross mullions
            center_x = x + width / 2
            center_y = y + height / 2
            return (
                # Outer rectangular frame
                f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
                f"L {x:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} Z "
                # Vertical center mullion
                f"M {center_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {center_x:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
                # Horizontal center mullion
                f"M {x:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f}"
            )
        elif window_type == WindowType.MULTI_PANE:
            # Multi-pane window - 3x2 grid (6 panes) with internal mullions
            pane_width = width / 3
            pane_height = height / 2
            patterns = []
            # Outer frame
            patterns.append(
                f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
                f"L {x:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} Z"
            )
            # Vertical mullions
            for i in range(1, 3):
                mullion_x = x + i * pane_width
                patterns.append(
                    f"M {mullion_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                    f"L {mullion_x:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f}"
                )
            # Horizontal mullion
            center_y = y + height / 2
            patterns.append(
                f"M {x:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f}"
            )
            return " ".join(patterns)
        elif window_type == WindowType.COLONIAL_SET:
            # Colonial set - 3 separate windows side by side
            window_width = width / 3
            spacing = window_width * 0.1
            actual_width = window_width - spacing
            patterns = []
            for i in range(3):
                window_x = x + i * window_width + spacing/2
                patterns.append(self._generate_rectangular_cutout(window_x, y, actual_width, height))
            return " ".join(patterns)
        elif window_type == WindowType.PALLADIAN:
            # Palladian window - arched center with 2 rectangular sides
            central_width = width * 0.6
            side_width = width * 0.2
            patterns = []
            # Left rectangular window
            patterns.append(self._generate_rectangular_cutout(x, y, side_width, height))
            # Central arched window
            center_x = x + side_width
            arch_height = central_width / 2
            rect_height = height - arch_height
            center_mid = center_x + central_width / 2
            patterns.append(
                f"M {center_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {center_x + central_width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {center_x + central_width:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
                f"Q {center_mid:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
                f"{center_x:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} Z"
            )
            # Right rectangular window
            patterns.append(self._generate_rectangular_cutout(x + side_width + central_width, y, side_width, height))
            return " ".join(patterns)
        elif window_type == WindowType.GOTHIC_PAIR:
            # Gothic pair - 2 gothic arched windows
            window_width = (width - 3) / 2
            spacing = 3.0
            patterns = []
            # Left gothic window
            patterns.append(self._generate_gothic_arch_cutout(x, y, window_width, height))
            # Right gothic window
            patterns.append(self._generate_gothic_arch_cutout(x + window_width + spacing, y, window_width, height))
            return " ".join(patterns)
        elif window_type == WindowType.DOUBLE_HUNG:
            # Double-hung window - rectangle with horizontal division
            mid_y = y + height / 2
            divider_height = 1.0
            return (
                f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
                f"L {x:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} Z "
                # Horizontal divider
                f"M {x:.{COORDINATE_PRECISION}f},{mid_y - divider_height/2:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{mid_y - divider_height/2:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{mid_y + divider_height/2:.{COORDINATE_PRECISION}f} "
                f"L {x:.{COORDINATE_PRECISION}f},{mid_y + divider_height/2:.{COORDINATE_PRECISION}f} Z"
            )
        elif window_type == WindowType.CASEMENT:
            # Casement window - simple rectangular (side-hinged)
            return self._generate_rectangular_cutout(x, y, width, height)
        elif window_type == WindowType.BAY:
            # Bay window - rectangular (protruding effect shown by wider dimension)
            return self._generate_rectangular_cutout(x, y, width, height)
        elif window_type == WindowType.DORMER:
            # Dormer window - rectangular with peaked roof top
            peak_height = height * 0.2
            rect_height = height - peak_height
            center_x = x + width / 2
            return (
                f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
                f"L {center_x:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
                f"L {x:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} Z"
            )
        else:
            # Default rectangular window
            return self._generate_rectangular_cutout(x, y, width, height)
    
    def _generate_gothic_arch_cutout(self, x: float, y: float, width: float, height: float) -> str:
        """Generate a gothic arched window cutout (pointed arch)"""
        rect_height = height * 0.7
        arch_height = height * 0.3
        center_x = x + width / 2
        return (
            f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
            f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
            f"L {x + width:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
            # Right side of pointed arch
            f"Q {x + width * 0.75:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
            f"{center_x:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
            # Left side of pointed arch
            f"Q {x + width * 0.25:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
            f"{x:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} Z"
        )
    
    def _generate_decorative_patterns(self, position: Point, panel_name: str, corners: List[Point]) -> str:
        """
        Generate detailed decorative patterns based on architectural style
        
        Args:
            position: Panel position
            panel_name: Name of the panel
            corners: List of corner points defining panel shape
            
        Returns:
            SVG path string for detailed architectural patterns
        """
        if not self.architectural_config.pattern_generator:
            return ""
        
        # Get doors and windows for collision detection
        doors = self.architectural_config.get_doors_for_panel(panel_name)
        windows = self.architectural_config.get_windows_for_panel(panel_name)
        cutout_areas = []
        
        # Collect all cutout areas (doors and windows) with absolute coordinates
        for door in doors:
            cutout_areas.append({
                'x': position.x + door.position.x,
                'y': position.y + door.position.y,
                'width': door.position.width,
                'height': door.position.height
            })
        for window in windows:
            cutout_areas.append({
                'x': position.x + window.position.x,
                'y': position.y + window.position.y,
                'width': window.position.width,
                'height': window.position.height
            })
        
        # Get architectural style from the configuration
        style = self.architectural_config.architectural_style
        
        # Generate authentic style-specific patterns with cutout awareness
        patterns = []
        
        if style.value == 'farmhouse':
            patterns.append(self._generate_farmhouse_facade(position, corners, panel_name, cutout_areas))
        elif style.value == 'tudor':
            patterns.append(self._generate_tudor_facade(position, corners, panel_name, cutout_areas))
        elif style.value == 'fachwerkhaus':
            patterns.append(self._generate_fachwerk_facade(position, corners, panel_name, cutout_areas))
        elif style.value == 'colonial':
            patterns.append(self._generate_colonial_facade(position, corners, panel_name, cutout_areas))
        elif style.value == 'victorian':
            patterns.append(self._generate_victorian_facade(position, corners, panel_name, cutout_areas))
        elif style.value == 'craftsman':
            patterns.append(self._generate_craftsman_facade(position, corners, panel_name, cutout_areas))
        elif style.value == 'brick':
            patterns.append(self._generate_brick_facade(position, corners, panel_name, cutout_areas))
        elif style.value == 'gingerbread':
            patterns.append(self._generate_gingerbread_facade(position, corners, panel_name, cutout_areas))
        
        return " ".join(patterns)
    
    def _segment_horizontal_line(self, start_x: float, end_x: float, y: float, cutout_areas: List[dict]) -> List[Tuple[float, float]]:
        """
        Segment a horizontal line around cutout areas
        """
        segments = []
        current_x = start_x
        
        # Sort cutouts by x position for efficient processing
        overlapping_cutouts = []
        for cutout in cutout_areas:
            # Check if cutout intersects with this horizontal line
            if (cutout['y'] <= y <= cutout['y'] + cutout['height'] and
                cutout['x'] < end_x and cutout['x'] + cutout['width'] > start_x):
                overlapping_cutouts.append((cutout['x'], cutout['x'] + cutout['width']))
        
        overlapping_cutouts.sort()
        
        for cutout_start, cutout_end in overlapping_cutouts:
            # Add segment before cutout
            if current_x < cutout_start:
                segments.append((max(current_x, start_x), min(cutout_start, end_x)))
            current_x = max(current_x, cutout_end)
        
        # Add final segment after all cutouts
        if current_x < end_x:
            segments.append((current_x, end_x))
        
        return segments
    
    def _segment_vertical_line(self, x: float, start_y: float, end_y: float, cutout_areas: List[dict]) -> List[Tuple[float, float]]:
        """
        Segment a vertical line around cutout areas
        """
        segments = []
        current_y = start_y
        
        # Sort cutouts by y position for efficient processing
        overlapping_cutouts = []
        for cutout in cutout_areas:
            # Check if cutout intersects with this vertical line
            if (cutout['x'] <= x <= cutout['x'] + cutout['width'] and
                cutout['y'] < end_y and cutout['y'] + cutout['height'] > start_y):
                overlapping_cutouts.append((cutout['y'], cutout['y'] + cutout['height']))
        
        overlapping_cutouts.sort()
        
        for cutout_start, cutout_end in overlapping_cutouts:
            # Add segment before cutout
            if current_y < cutout_start:
                segments.append((max(current_y, start_y), min(cutout_start, end_y)))
            current_y = max(current_y, cutout_end)
        
        # Add final segment after all cutouts
        if current_y < end_y:
            segments.append((current_y, end_y))
        
        return segments
    
    def _generate_farmhouse_facade(self, position: Point, corners: List[Point], panel_name: str, cutout_areas: List[dict] = None) -> str:
        """Generate farmhouse architectural details that work with the actual gable wall geometry"""
        if panel_name not in ['gable_wall_front', 'gable_wall_back']:
            return ""
        
        # The gable wall has a house shape: corners[0] bottom-left, corners[1] bottom-right,
        # corners[2] wall top-right, corners[3] peak, corners[4] wall top-left
        if len(corners) < 5:
            return ""
        
        patterns = []
        
        # Get actual panel geometry
        panel_width = corners[1].x - corners[0].x
        wall_height = corners[2].y - corners[1].y  # Height to wall top (before gable)
        total_height = corners[3].y - corners[0].y  # Total height to peak
        
        # Farmhouse porch roof line (horizontal line across lower portion)
        porch_roof_y = position.y + wall_height * 0.75
        porch_roof = (
            f"M {position.x + panel_width * 0.05:.{COORDINATE_PRECISION}f},{porch_roof_y:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.95:.{COORDINATE_PRECISION}f},{porch_roof_y:.{COORDINATE_PRECISION}f}"
        )
        patterns.append(porch_roof)
        
        # Porch posts (vertical lines from porch roof to bottom)
        post_count = 4
        for i in range(post_count):
            post_x = position.x + panel_width * (0.15 + i * 0.2)
            post = (
                f"M {post_x:.{COORDINATE_PRECISION}f},{porch_roof_y:.{COORDINATE_PRECISION}f} "
                f"L {post_x:.{COORDINATE_PRECISION}f},{position.y + wall_height:.{COORDINATE_PRECISION}f}"
            )
            patterns.append(post)
        
        # Farmhouse facades should only generate decorative patterns (board and batten)
        # Window/door cutouts are handled by ComponentPositioner system
        
        # Board and batten siding pattern (vertical lines)
        board_spacing = panel_width / 12
        for i in range(1, 12):
            board_x = position.x + i * board_spacing
            board_line = (
                f"M {board_x:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.1:.{COORDINATE_PRECISION}f} "
                f"L {board_x:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.9:.{COORDINATE_PRECISION}f}"
            )
            patterns.append(board_line)
        
        return " ".join(patterns)
    
    def _generate_tudor_facade(self, position: Point, corners: List[Point], panel_name: str, cutout_areas: List[dict] = None) -> str:
        """Generate Tudor half-timber architectural details for the actual gable wall geometry"""
        if panel_name not in ['gable_wall_front', 'gable_wall_back']:
            return ""
        
        if len(corners) < 5:
            return ""
        
        if cutout_areas is None:
            cutout_areas = []
        
        patterns = []
        
        # Get actual panel geometry
        panel_width = corners[1].x - corners[0].x
        wall_height = corners[2].y - corners[1].y  # Height to wall top
        
        # Tudor half-timber framework
        # Vertical posts (Ständer) - divide wall into thirds
        post_spacing = panel_width / 3
        for i in range(1, 3):
            post_x = position.x + i * post_spacing
            post = (
                f"M {post_x:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.1:.{COORDINATE_PRECISION}f} "
                f"L {post_x:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.9:.{COORDINATE_PRECISION}f}"
            )
            patterns.append(post)
        
        # Horizontal plates at thirds
        plate_y1 = position.y + wall_height * 0.33
        plate_y2 = position.y + wall_height * 0.66
        
        plate1 = (
            f"M {position.x + panel_width * 0.05:.{COORDINATE_PRECISION}f},{plate_y1:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.95:.{COORDINATE_PRECISION}f},{plate_y1:.{COORDINATE_PRECISION}f}"
        )
        patterns.append(plate1)
        
        plate2 = (
            f"M {position.x + panel_width * 0.05:.{COORDINATE_PRECISION}f},{plate_y2:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.95:.{COORDINATE_PRECISION}f},{plate_y2:.{COORDINATE_PRECISION}f}"
        )
        patterns.append(plate2)
        
        # Diagonal braces in center bay
        center_x = position.x + panel_width/2
        brace_width = panel_width * 0.25
        
        # St. Andrew's Cross
        cross1 = (
            f"M {center_x - brace_width/2:.{COORDINATE_PRECISION}f},{plate_y1:.{COORDINATE_PRECISION}f} "
            f"L {center_x + brace_width/2:.{COORDINATE_PRECISION}f},{plate_y2:.{COORDINATE_PRECISION}f}"
        )
        patterns.append(cross1)
        
        cross2 = (
            f"M {center_x + brace_width/2:.{COORDINATE_PRECISION}f},{plate_y1:.{COORDINATE_PRECISION}f} "
            f"L {center_x - brace_width/2:.{COORDINATE_PRECISION}f},{plate_y2:.{COORDINATE_PRECISION}f}"
        )
        patterns.append(cross2)
        
        # Tudor facades should only generate decorative patterns (half-timber framing)
        # Window/door cutouts are handled by ComponentPositioner system
        
        return " ".join(patterns)
    
    def _generate_fachwerk_facade(self, position: Point, corners: List[Point], panel_name: str, cutout_areas: List[dict] = None) -> str:
        """Generate German Fachwerk half-timber architectural details for the actual gable wall geometry"""
        if panel_name not in ['gable_wall_front', 'gable_wall_back']:
            return ""
        
        if len(corners) < 5:
            return ""
        
        if cutout_areas is None:
            cutout_areas = []
        
        patterns = []
        
        # Get actual panel geometry
        panel_width = corners[1].x - corners[0].x
        wall_height = corners[2].y - corners[1].y  # Height to wall top
        
        # Traditional Fachwerk framework - more complex than Tudor
        # Vertical posts (Ständer) - closer spacing
        post_count = 5
        post_spacing = panel_width / (post_count + 1)
        for i in range(1, post_count + 1):
            post_x = position.x + i * post_spacing
            post = (
                f"M {post_x:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.05:.{COORDINATE_PRECISION}f} "
                f"L {post_x:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.95:.{COORDINATE_PRECISION}f}"
            )
            patterns.append(post)
        
        # Horizontal elements at multiple levels
        horizontal_levels = [0.25, 0.5, 0.75]
        for level in horizontal_levels:
            plate_y = position.y + wall_height * level
            plate = (
                f"M {position.x + panel_width * 0.02:.{COORDINATE_PRECISION}f},{plate_y:.{COORDINATE_PRECISION}f} "
                f"L {position.x + panel_width * 0.98:.{COORDINATE_PRECISION}f},{plate_y:.{COORDINATE_PRECISION}f}"
            )
            patterns.append(plate)
        
        # Complex diagonal bracing system
        # Center bay - traditional Andreaskreuz (St. Andrew's Cross)
        center_x = position.x + panel_width/2
        brace_width = panel_width * 0.3
        mid_height = position.y + wall_height * 0.5
        
        cross1 = (
            f"M {center_x - brace_width/2:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.25:.{COORDINATE_PRECISION}f} "
            f"L {center_x + brace_width/2:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.75:.{COORDINATE_PRECISION}f}"
        )
        patterns.append(cross1)
        
        cross2 = (
            f"M {center_x + brace_width/2:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.25:.{COORDINATE_PRECISION}f} "
            f"L {center_x - brace_width/2:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.75:.{COORDINATE_PRECISION}f}"
        )
        patterns.append(cross2)
        
        # Knee braces (Kopfbänder) at corners
        knee_length = min(panel_width * 0.1, wall_height * 0.1)
        
        # Left knee brace
        knee1 = (
            f"M {position.x + panel_width * 0.05:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.15:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.05 + knee_length:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.15 + knee_length:.{COORDINATE_PRECISION}f}"
        )
        patterns.append(knee1)
        
        # Right knee brace
        knee2 = (
            f"M {position.x + panel_width * 0.95:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.15:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.95 - knee_length:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.15 + knee_length:.{COORDINATE_PRECISION}f}"
        )
        patterns.append(knee2)
        
        # Fachwerkhaus facades should only generate decorative patterns (timber framing)
        # Window/door cutouts are handled by ComponentPositioner system
        
        return " ".join(patterns)
    
    def _generate_colonial_facade(self, position: Point, corners: List[Point], panel_name: str, cutout_areas: List[dict] = None) -> str:
        """Generate Colonial architectural details with symmetrical design and classical proportions"""
        if panel_name not in ['gable_wall_front', 'gable_wall_back']:
            return ""
        
        if len(corners) < 5:
            return ""
        
        if cutout_areas is None:
            cutout_areas = []
        
        patterns = []
        
        # Get actual panel geometry
        panel_width = corners[1].x - corners[0].x
        wall_height = corners[2].y - corners[1].y  # Height to wall top
        
        # Colonial two-story division line
        story_line_y = position.y + wall_height * 0.5
        story_line = (
            f"M {position.x + panel_width * 0.05:.{COORDINATE_PRECISION}f},{story_line_y:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.95:.{COORDINATE_PRECISION}f},{story_line_y:.{COORDINATE_PRECISION}f}"
        )
        patterns.append(story_line)
        
        # Colonial facades should only generate decorative patterns (siding, trim)
        # Window/door cutouts are handled by ComponentPositioner system
        
        # Classical clapboard siding lines
        siding_spacing = wall_height / 15
        for i in range(1, 15):
            siding_y = position.y + i * siding_spacing
            if siding_y < position.y + wall_height * 0.9:  # Don't go all the way to top
                siding_line = (
                    f"M {position.x + panel_width * 0.02:.{COORDINATE_PRECISION}f},{siding_y:.{COORDINATE_PRECISION}f} "
                    f"L {position.x + panel_width * 0.98:.{COORDINATE_PRECISION}f},{siding_y:.{COORDINATE_PRECISION}f}"
                )
                patterns.append(siding_line)
        
        # Corner pilasters (classical elements)
        pilaster_width = panel_width * 0.03
        
        # Left pilaster
        left_pilaster = (
            f"M {position.x + panel_width * 0.02:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.1:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.02:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.9:.{COORDINATE_PRECISION}f} "
            f"M {position.x + panel_width * 0.02 + pilaster_width:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.1:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.02 + pilaster_width:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.9:.{COORDINATE_PRECISION}f}"
        )
        patterns.append(left_pilaster)
        
        # Right pilaster
        right_pilaster = (
            f"M {position.x + panel_width * 0.98:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.1:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.98:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.9:.{COORDINATE_PRECISION}f} "
            f"M {position.x + panel_width * 0.98 - pilaster_width:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.1:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.98 - pilaster_width:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.9:.{COORDINATE_PRECISION}f}"
        )
        patterns.append(right_pilaster)
        
        return " ".join(patterns)
    
    def _generate_victorian_facade(self, position: Point, corners: List[Point], panel_name: str, cutout_areas: List[dict] = None) -> str:
        """Generate Victorian architectural details with ornate trim and decorative elements"""
        if panel_name not in ['gable_wall_front', 'gable_wall_back']:
            return ""
        
        if len(corners) < 5:
            return ""
        
        if cutout_areas is None:
            cutout_areas = []
        
        patterns = []
        
        # Get actual panel geometry
        panel_width = corners[1].x - corners[0].x
        wall_height = corners[2].y - corners[1].y  # Height to wall top
        
        # Victorian decorative shingle pattern (alternating rows)
        shingle_rows = max(8, int(wall_height / 8))
        row_height = wall_height / shingle_rows
        
        for i in range(shingle_rows):
            y_pos = position.y + i * row_height
            
            if i % 2 == 0:
                # Even rows - regular spacing
                shingle_count = max(8, int(panel_width / 10))
                shingle_width = panel_width / shingle_count
                for j in range(shingle_count + 1):
                    x_pos = position.x + j * shingle_width
                    if x_pos <= position.x + panel_width * 0.95:
                        shingle_line = (
                            f"M {x_pos:.{COORDINATE_PRECISION}f},{y_pos:.{COORDINATE_PRECISION}f} "
                            f"L {x_pos:.{COORDINATE_PRECISION}f},{y_pos + row_height:.{COORDINATE_PRECISION}f}"
                        )
                        patterns.append(shingle_line)
            else:
                # Odd rows - offset spacing (creates staggered pattern)
                shingle_count = max(8, int(panel_width / 10))
                shingle_width = panel_width / shingle_count
                for j in range(shingle_count):
                    x_pos = position.x + (j + 0.5) * shingle_width
                    if x_pos <= position.x + panel_width * 0.95:
                        shingle_line = (
                            f"M {x_pos:.{COORDINATE_PRECISION}f},{y_pos:.{COORDINATE_PRECISION}f} "
                            f"L {x_pos:.{COORDINATE_PRECISION}f},{y_pos + row_height:.{COORDINATE_PRECISION}f}"
                        )
                        patterns.append(shingle_line)
        
        # Victorian ornate corner brackets
        bracket_size = min(panel_width * 0.08, wall_height * 0.08)
        
        # Top left decorative bracket (simplified scrollwork)
        bracket1 = (
            f"M {position.x + panel_width * 0.05:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.1:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.05 + bracket_size:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.1:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.05 + bracket_size:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.1 + bracket_size:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.05:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.1 + bracket_size:.{COORDINATE_PRECISION}f} Z"
        )
        patterns.append(bracket1)
        
        # Top right decorative bracket
        bracket2 = (
            f"M {position.x + panel_width * 0.95:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.1:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.95 - bracket_size:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.1:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.95 - bracket_size:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.1 + bracket_size:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.95:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.1 + bracket_size:.{COORDINATE_PRECISION}f} Z"
        )
        patterns.append(bracket2)
        
        # Bay window suggestion (simple projection outline)
        bay_width = panel_width * 0.25
        bay_height = wall_height * 0.3
        bay_x = position.x + panel_width * 0.1
        bay_y = position.y + wall_height * 0.5
        
        bay_outline = (
            f"M {bay_x:.{COORDINATE_PRECISION}f},{bay_y:.{COORDINATE_PRECISION}f} "
            f"L {bay_x + bay_width:.{COORDINATE_PRECISION}f},{bay_y:.{COORDINATE_PRECISION}f} "
            f"L {bay_x + bay_width:.{COORDINATE_PRECISION}f},{bay_y + bay_height:.{COORDINATE_PRECISION}f} "
            f"L {bay_x:.{COORDINATE_PRECISION}f},{bay_y + bay_height:.{COORDINATE_PRECISION}f} Z"
        )
        patterns.append(bay_outline)
        
        # Multi-pane bay window details
        pane_width = bay_width / 4
        pane_height = bay_height * 0.6
        pane_y = bay_y + bay_height * 0.2
        
        for i in range(3):
            pane_x = bay_x + bay_width * 0.1 + i * pane_width
            pane = (
                f"M {pane_x:.{COORDINATE_PRECISION}f},{pane_y:.{COORDINATE_PRECISION}f} "
                f"L {pane_x + pane_width * 0.8:.{COORDINATE_PRECISION}f},{pane_y:.{COORDINATE_PRECISION}f} "
                f"L {pane_x + pane_width * 0.8:.{COORDINATE_PRECISION}f},{pane_y + pane_height:.{COORDINATE_PRECISION}f} "
                f"L {pane_x:.{COORDINATE_PRECISION}f},{pane_y + pane_height:.{COORDINATE_PRECISION}f} Z"
            )
            patterns.append(pane)
        
        # Asymmetrical upper windows
        upper_window_width = panel_width * 0.06
        upper_window_height = wall_height * 0.15
        upper_window_y = position.y + wall_height * 0.25
        
        # Left upper window
        left_upper = (
            f"M {position.x + panel_width * 0.7:.{COORDINATE_PRECISION}f},{upper_window_y:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.7 + upper_window_width:.{COORDINATE_PRECISION}f},{upper_window_y:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.7 + upper_window_width:.{COORDINATE_PRECISION}f},{upper_window_y + upper_window_height:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.7:.{COORDINATE_PRECISION}f},{upper_window_y + upper_window_height:.{COORDINATE_PRECISION}f} Z"
        )
        patterns.append(left_upper)
        
        return " ".join(patterns)
    
    def _generate_craftsman_facade(self, position: Point, corners: List[Point], panel_name: str, cutout_areas: List[dict] = None) -> str:
        """Generate Craftsman architectural details with horizontal emphasis and natural materials"""
        if panel_name not in ['gable_wall_front', 'gable_wall_back']:
            return ""
        
        if len(corners) < 5:
            return ""
        
        if cutout_areas is None:
            cutout_areas = []
        
        patterns = []
        
        # Get actual panel geometry
        panel_width = corners[1].x - corners[0].x
        wall_height = corners[2].y - corners[1].y  # Height to wall top
        
        # Craftsman horizontal band siding (wider bands, fewer of them)
        band_count = max(4, int(wall_height / 18))  # Fewer, wider bands
        band_height = wall_height / band_count
        
        for i in range(band_count):
            band_y = position.y + i * band_height
            
            # Main band line
            band_line = (
                f"M {position.x + panel_width * 0.02:.{COORDINATE_PRECISION}f},{band_y:.{COORDINATE_PRECISION}f} "
                f"L {position.x + panel_width * 0.98:.{COORDINATE_PRECISION}f},{band_y:.{COORDINATE_PRECISION}f}"
            )
            patterns.append(band_line)
            
            # Shadow line for depth
            shadow_y = band_y + 1
            shadow_line = (
                f"M {position.x + panel_width * 0.01:.{COORDINATE_PRECISION}f},{shadow_y:.{COORDINATE_PRECISION}f} "
                f"L {position.x + panel_width * 0.99:.{COORDINATE_PRECISION}f},{shadow_y:.{COORDINATE_PRECISION}f}"
            )
            patterns.append(shadow_line)
        
        # Wide front porch roof line
        porch_roof_y = position.y + wall_height * 0.7
        porch_roof = (
            f"M {position.x + panel_width * 0.05:.{COORDINATE_PRECISION}f},{porch_roof_y:.{COORDINATE_PRECISION}f} "
            f"L {position.x + panel_width * 0.95:.{COORDINATE_PRECISION}f},{porch_roof_y:.{COORDINATE_PRECISION}f}"
        )
        patterns.append(porch_roof)
        
        # Tapered porch columns (signature Craftsman feature)
        column_count = 2
        column_spacing = panel_width / (column_count + 1)
        
        for i in range(1, column_count + 1):
            column_x = position.x + i * column_spacing
            column_base_width = panel_width * 0.03
            column_top_width = column_base_width * 0.6
            
            # Tapered column outline
            column = (
                f"M {column_x - column_base_width/2:.{COORDINATE_PRECISION}f},{position.y + wall_height:.{COORDINATE_PRECISION}f} "
                f"L {column_x + column_base_width/2:.{COORDINATE_PRECISION}f},{position.y + wall_height:.{COORDINATE_PRECISION}f} "
                f"L {column_x + column_top_width/2:.{COORDINATE_PRECISION}f},{porch_roof_y:.{COORDINATE_PRECISION}f} "
                f"L {column_x - column_top_width/2:.{COORDINATE_PRECISION}f},{porch_roof_y:.{COORDINATE_PRECISION}f} Z"
            )
            patterns.append(column)
        
        # Craftsman facades should only generate decorative patterns (exposed rafters, brackets)
        # Window/door cutouts are handled by ComponentPositioner system
        
        # Exposed rafter tails (suggestion at gable peak area)
        rafter_spacing = panel_width / 10
        for i in range(1, 10):
            rafter_x = position.x + i * rafter_spacing
            rafter_tail = (
                f"M {rafter_x:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.05:.{COORDINATE_PRECISION}f} "
                f"L {rafter_x:.{COORDINATE_PRECISION}f},{position.y + wall_height * 0.15:.{COORDINATE_PRECISION}f}"
            )
            patterns.append(rafter_tail)
        
        # Door cutouts are handled by ComponentPositioner system
        
        return " ".join(patterns)
    
    def _generate_gingerbread_facade(self, position: Point, corners: List[Point], panel_name: str, cutout_areas: List[dict] = None) -> str:
        """Generate gingerbread house architectural details with festive decorative patterns"""
        if panel_name not in ['gable_wall_front', 'gable_wall_back']:
            return ""
        
        if len(corners) < 5:
            return ""
        
        if cutout_areas is None:
            cutout_areas = []
        
        patterns = []
        
        # Get actual panel geometry
        panel_width = corners[1].x - corners[0].x
        wall_height = corners[2].y - corners[1].y  # Height to wall top
        total_height = corners[3].y - corners[0].y  # Total height to peak
        peak_x = corners[3].x
        peak_y = corners[3].y
        
        # Scalloped roof trim along the gable edges
        scallop_count = max(6, int(panel_width / 15))  # Number of scallops
        scallop_width = panel_width / scallop_count / 2  # Half width for each side
        
        # Left gable edge scalloped trim
        left_roof_segments = []
        for i in range(scallop_count // 2):
            scallop_center_x = position.x + i * (scallop_width * 2) + scallop_width
            scallop_y_bottom = position.y + wall_height + (i * (peak_y - position.y - wall_height) / (scallop_count // 2))
            scallop_y_top = position.y + wall_height + ((i + 0.5) * (peak_y - position.y - wall_height) / (scallop_count // 2))
            
            # Create scallop using quadratic curve
            if i == 0:
                left_roof_segments.append(f"M {position.x:.{COORDINATE_PRECISION}f},{position.y + wall_height:.{COORDINATE_PRECISION}f}")
            
            left_roof_segments.append(
                f"Q {scallop_center_x:.{COORDINATE_PRECISION}f},{scallop_y_top + 3:.{COORDINATE_PRECISION}f} "
                f"{scallop_center_x + scallop_width:.{COORDINATE_PRECISION}f},{scallop_y_bottom + (scallop_width * 0.4):.{COORDINATE_PRECISION}f}"
            )
        
        patterns.append(" ".join(left_roof_segments))
        
        # Right gable edge scalloped trim (mirror pattern)
        right_roof_segments = []
        for i in range(scallop_count // 2):
            scallop_center_x = peak_x + i * (scallop_width * 2) + scallop_width
            scallop_y_bottom = position.y + wall_height + (i * (peak_y - position.y - wall_height) / (scallop_count // 2))
            scallop_y_top = position.y + wall_height + ((i + 0.5) * (peak_y - position.y - wall_height) / (scallop_count // 2))
            
            if i == 0:
                right_roof_segments.append(f"M {peak_x:.{COORDINATE_PRECISION}f},{peak_y:.{COORDINATE_PRECISION}f}")
            
            right_roof_segments.append(
                f"Q {scallop_center_x:.{COORDINATE_PRECISION}f},{scallop_y_top + 3:.{COORDINATE_PRECISION}f} "
                f"{scallop_center_x + scallop_width:.{COORDINATE_PRECISION}f},{scallop_y_bottom + (scallop_width * 0.4):.{COORDINATE_PRECISION}f}"
            )
        
        patterns.append(" ".join(right_roof_segments))
        
        # Decorative stars scattered across the facade
        star_positions = [
            (0.15, 0.25), (0.85, 0.25), (0.3, 0.45), (0.7, 0.45),
            (0.25, 0.65), (0.75, 0.65), (0.5, 0.35)
        ]
        
        for star_x_ratio, star_y_ratio in star_positions:
            star_x = position.x + panel_width * star_x_ratio
            star_y = position.y + wall_height * star_y_ratio
            star_size = min(panel_width * 0.02, wall_height * 0.03)
            
            # 5-pointed star using line segments
            star_pattern = []
            for i in range(5):
                angle1 = i * 72 * 3.14159 / 180  # Outer points
                angle2 = (i + 0.5) * 72 * 3.14159 / 180  # Inner points
                
                outer_x = star_x + star_size * 1.5 * math.cos(angle1 - 3.14159/2)
                outer_y = star_y + star_size * 1.5 * math.sin(angle1 - 3.14159/2)
                inner_x = star_x + star_size * 0.6 * math.cos(angle2 - 3.14159/2)
                inner_y = star_y + star_size * 0.6 * math.sin(angle2 - 3.14159/2)
                
                if i == 0:
                    star_pattern.append(f"M {outer_x:.{COORDINATE_PRECISION}f},{outer_y:.{COORDINATE_PRECISION}f}")
                else:
                    star_pattern.append(f"L {outer_x:.{COORDINATE_PRECISION}f},{outer_y:.{COORDINATE_PRECISION}f}")
                
                star_pattern.append(f"L {inner_x:.{COORDINATE_PRECISION}f},{inner_y:.{COORDINATE_PRECISION}f}")
            
            star_pattern.append("Z")
            patterns.append(" ".join(star_pattern))
        
        # Decorative hearts near corners
        heart_positions = [(0.1, 0.15), (0.9, 0.15)]
        
        for heart_x_ratio, heart_y_ratio in heart_positions:
            heart_x = position.x + panel_width * heart_x_ratio
            heart_y = position.y + wall_height * heart_y_ratio
            heart_size = min(panel_width * 0.025, wall_height * 0.04)
            
            # Simple heart shape using curves
            heart_pattern = (
                f"M {heart_x:.{COORDINATE_PRECISION}f},{heart_y + heart_size * 0.3:.{COORDINATE_PRECISION}f} "
                f"Q {heart_x - heart_size * 0.5:.{COORDINATE_PRECISION}f},{heart_y - heart_size * 0.2:.{COORDINATE_PRECISION}f} "
                f"{heart_x:.{COORDINATE_PRECISION}f},{heart_y:.{COORDINATE_PRECISION}f} "
                f"Q {heart_x + heart_size * 0.5:.{COORDINATE_PRECISION}f},{heart_y - heart_size * 0.2:.{COORDINATE_PRECISION}f} "
                f"{heart_x:.{COORDINATE_PRECISION}f},{heart_y + heart_size * 0.3:.{COORDINATE_PRECISION}f} Z"
            )
            patterns.append(heart_pattern)
        
        # Ornamental border around the base of the wall
        border_y = position.y + wall_height * 0.9
        border_segments = []
        border_wave_count = max(8, int(panel_width / 12))
        wave_width = panel_width / border_wave_count
        
        for i in range(border_wave_count):
            wave_x = position.x + i * wave_width
            wave_peak_x = wave_x + wave_width / 2
            wave_end_x = wave_x + wave_width
            
            if i == 0:
                border_segments.append(f"M {wave_x:.{COORDINATE_PRECISION}f},{border_y:.{COORDINATE_PRECISION}f}")
            
            border_segments.append(
                f"Q {wave_peak_x:.{COORDINATE_PRECISION}f},{border_y - 2:.{COORDINATE_PRECISION}f} "
                f"{wave_end_x:.{COORDINATE_PRECISION}f},{border_y:.{COORDINATE_PRECISION}f}"
            )
        
        patterns.append(" ".join(border_segments))
        
        # Festive swirls at strategic locations
        swirl_positions = [(0.2, 0.55), (0.8, 0.55)]
        
        for swirl_x_ratio, swirl_y_ratio in swirl_positions:
            swirl_x = position.x + panel_width * swirl_x_ratio
            swirl_y = position.y + wall_height * swirl_y_ratio
            swirl_size = min(panel_width * 0.03, wall_height * 0.05)
            
            # Spiral swirl using quadratic curves
            swirl_pattern = (
                f"M {swirl_x:.{COORDINATE_PRECISION}f},{swirl_y:.{COORDINATE_PRECISION}f} "
                f"Q {swirl_x + swirl_size * 0.5:.{COORDINATE_PRECISION}f},{swirl_y - swirl_size * 0.5:.{COORDINATE_PRECISION}f} "
                f"{swirl_x + swirl_size:.{COORDINATE_PRECISION}f},{swirl_y:.{COORDINATE_PRECISION}f} "
                f"Q {swirl_x + swirl_size * 0.7:.{COORDINATE_PRECISION}f},{swirl_y + swirl_size * 0.7:.{COORDINATE_PRECISION}f} "
                f"{swirl_x:.{COORDINATE_PRECISION}f},{swirl_y + swirl_size * 0.5:.{COORDINATE_PRECISION}f} "
                f"Q {swirl_x - swirl_size * 0.3:.{COORDINATE_PRECISION}f},{swirl_y:.{COORDINATE_PRECISION}f} "
                f"{swirl_x:.{COORDINATE_PRECISION}f},{swirl_y - swirl_size * 0.2:.{COORDINATE_PRECISION}f}"
            )
            patterns.append(swirl_pattern)
        
        return " ".join(patterns)
    
    def _generate_brick_facade(self, position: Point, corners: List[Point], panel_name: str, cutout_areas: List[dict] = None) -> str:
        """Generate brick house architectural details with proper masonry patterns"""
        if panel_name not in ['gable_wall_front', 'gable_wall_back']:
            return ""
        
        if len(corners) < 5:
            return ""
        
        if cutout_areas is None:
            cutout_areas = []
        
        patterns = []
        
        # Get actual panel geometry
        panel_width = corners[1].x - corners[0].x
        wall_height = corners[2].y - corners[1].y  # Height to wall top
        
        # Authentic brick coursing pattern
        # Standard brick proportions: 3:1 ratio (length:height)
        brick_height = max(2.5, wall_height / 25)  # Typical course height
        mortar_thickness = 0.4
        course_height = brick_height + mortar_thickness
        courses = int(wall_height / course_height)
        
        # Horizontal mortar lines (bed joints) - segment around cutouts
        for i in range(courses + 1):
            mortar_y = position.y + i * course_height
            if mortar_y <= position.y + wall_height:
                # Generate segmented horizontal lines that avoid cutouts
                line_segments = self._segment_horizontal_line(position.x, position.x + panel_width, mortar_y, cutout_areas)
                for start_x, end_x in line_segments:
                    if end_x > start_x:  # Only draw if segment has positive length
                        mortar_line = (
                            f"M {start_x:.{COORDINATE_PRECISION}f},{mortar_y:.{COORDINATE_PRECISION}f} "
                            f"L {end_x:.{COORDINATE_PRECISION}f},{mortar_y:.{COORDINATE_PRECISION}f}"
                        )
                        patterns.append(mortar_line)
        
        # Vertical mortar joints (head joints) - running bond pattern, segment around cutouts
        brick_length = brick_height * 3  # Standard 3:1 proportion
        bricks_per_course = int(panel_width / brick_length)
        
        for course in range(min(courses, 8)):  # Show pattern on first 8 courses
            course_y = position.y + course * course_height
            # Running bond: each course offset by half brick length
            offset = (brick_length / 2) if course % 2 == 1 else 0
            
            for brick in range(bricks_per_course + 1):
                joint_x = position.x + offset + brick * brick_length
                if position.x <= joint_x <= position.x + panel_width:
                    # Generate segmented vertical lines that avoid cutouts
                    line_segments = self._segment_vertical_line(joint_x, course_y, course_y + brick_height, cutout_areas)
                    for start_y, end_y in line_segments:
                        if end_y > start_y:  # Only draw if segment has positive length
                            head_joint = (
                                f"M {joint_x:.{COORDINATE_PRECISION}f},{start_y:.{COORDINATE_PRECISION}f} "
                                f"L {joint_x:.{COORDINATE_PRECISION}f},{end_y:.{COORDINATE_PRECISION}f}"
                            )
                            patterns.append(head_joint)
        
        # Brick facade method should ONLY generate decorative patterns (mortar lines)
        # Actual door/window cutouts are handled by the ComponentPositioner system
        # The line segmentation above already avoids those cutout areas
        
        return " ".join(patterns)