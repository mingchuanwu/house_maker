"""
Enhanced Multi-Finger Joint Generation System
Improves upon the original single-joint system to provide multiple joints for long edges
while maintaining compatibility with the existing architecture
"""

import math
from typing import List, Tuple, Dict
from .geometry import Point, HouseGeometry
from .exceptions import FingerJointError
from .constants import COORDINATE_PRECISION


class MultiFingerJointGenerator:
    """
    Enhanced finger joint generator that creates multiple joints for long edges
    
    Key improvements:
    1. Calculates optimal number of joints based on edge length
    2. Distributes joints evenly along the edge
    3. Maintains structural integrity with proper joint spacing
    4. Preserves existing kerf compensation system
    5. Ensures male/female relationships remain correct
    """
    
    def __init__(self, geometry: HouseGeometry, single_joints: bool = False):
        self.geometry = geometry
        self.thickness = geometry.thickness
        self.finger_length = geometry.finger_length
        self.single_joints = single_joints  # Force single joint per edge
        
        # Kerf-compensated dimensions (preserve existing system)
        self.male_thickness = geometry.thickness + geometry.kerf
        self.female_thickness = geometry.thickness - geometry.kerf
        self.cutout_thickness = geometry.thickness - geometry.kerf
        self.cutout_length = geometry.finger_length - geometry.kerf
        
        # Optimized multi-joint parameters (from successful testing)
        self.min_joint_spacing = self.finger_length * 0.8  # Reduced from 1.5x to 0.8x
        self.max_joints_per_edge = 7  # Odd number for symmetry
        self.min_edge_length_for_multiple = self.finger_length * 2.5  # Reduced from 3x to 2.5x
    
    def calculate_optimal_joint_count(self, edge_length: float) -> int:
        """
        Calculate optimal number of joints for an edge based on its length
        
        Rules:
        1. If single_joints mode: always return 1
        2. Short edges (< 3*finger_length): 1 joint
        3. Medium edges: 3 joints
        4. Long edges: 5 or 7 joints based on length
        5. Always use odd numbers for symmetry
        
        Args:
            edge_length: Length of the edge
            
        Returns:
            Number of joints to place (always odd)
        """
        # Rule 0: If single_joints mode is enabled, always use 1 joint
        if self.single_joints:
            return 1
            
        # Rule 1: Very short edges get 1 joint
        if edge_length < self.min_edge_length_for_multiple:
            return 1
        
        # Rule 2: Calculate based on how many joints can fit with proper spacing
        # Reserve space at both ends (half finger length each end)
        reserved_end_space = self.finger_length  # Total for both ends
        available_space = edge_length - reserved_end_space
        
        # Calculate maximum joints that can fit
        # Each joint needs: finger_length + min_spacing (except the last one)
        joint_plus_spacing = self.finger_length + self.min_joint_spacing
        max_possible_joints = int((available_space + self.min_joint_spacing) / joint_plus_spacing)
        
        # Ensure odd number for symmetry and within limits
        max_possible_joints = min(max_possible_joints, self.max_joints_per_edge)
        
        if max_possible_joints >= 7:
            return 7
        elif max_possible_joints >= 5:
            return 5
        elif max_possible_joints >= 3:
            return 3
        else:
            return 1
    
    def calculate_joint_positions(self, edge_length: float, joint_count: int, offset: float = 0.0) -> List[Tuple[float, float]]:
        """
        Calculate evenly distributed joint positions along an edge
        
        Args:
            edge_length: Length of the edge
            joint_count: Number of joints to place
            offset: Offset to add to all joint positions (for gable wall alignment)
            
        Returns:
            List of (start, end) positions for each joint
        """
        if joint_count == 1:
            # Single centered joint (existing behavior)
            start = (edge_length - self.finger_length) / 2 + offset
            return [(start, start + self.finger_length)]
        
        # Multiple joints - distribute evenly
        positions = []
        
        # Calculate total space occupied by joints
        total_joint_length = joint_count * self.finger_length
        
        # Multiple joints - distribute evenly with equal gaps
        total_gap_space = edge_length - total_joint_length
        
        # For n joints, we need n+1 gaps (before first, between joints, after last)
        gap_count = joint_count + 1
        gap_size = total_gap_space / gap_count
        
        # Verify gaps are reasonable
        min_reasonable_gap = self.finger_length * 0.3  # 30% of finger length minimum
        if gap_size < min_reasonable_gap:
            # Reduce joint count if gaps become too small
            return self.calculate_joint_positions(edge_length, max(1, joint_count - 2), offset)
        
        # Place joints with calculated gaps
        current_pos = gap_size + offset
        for i in range(joint_count):
            positions.append((current_pos, current_pos + self.finger_length))
            current_pos += self.finger_length + gap_size
        
        return positions
    
    def generate_multi_joint_edge(self, start_point: Point, end_point: Point,
                                 has_joint: bool, is_male: bool,
                                 thickness_direction: int = 1,
                                 panel_name: str = None, edge_name: str = None) -> str:
        """
        Generate SVG path for an edge with multiple finger joints
        
        Args:
            start_point: Starting point of the edge
            end_point: Ending point of the edge
            has_joint: True if this edge should have finger joints
            is_male: True for male joints (tabs), False for female joints (gaps)
            thickness_direction: 1 for standard direction, -1 for reversed direction
            panel_name: Name of the panel (for gable wall adjustment)
            edge_name: Name of the edge (for gable wall adjustment)
            
        Returns:
            SVG path string for the edge with multiple joints
        """
        if not has_joint:
            # Simple straight line (e.g., smooth top edge of walls)
            return f"L {end_point.x:.{COORDINATE_PRECISION}f},{end_point.y:.{COORDINATE_PRECISION}f}"
        
        # Calculate edge vector and length
        dx = end_point.x - start_point.x
        dy = end_point.y - start_point.y
        edge_length = (dx * dx + dy * dy) ** 0.5
        
        if edge_length < self.finger_length * 1.5:
            # Edge too short for any joints
            return f"L {end_point.x:.{COORDINATE_PRECISION}f},{end_point.y:.{COORDINATE_PRECISION}f}"
        
        # Calculate unit vectors
        ux = dx / edge_length  # Unit vector along edge
        uy = dy / edge_length
        
        # Calculate perpendicular vector pointing outward from panel
        if thickness_direction == 1:
            outward_vx = -uy  # 90° counterclockwise
            outward_vy = ux
        else:
            outward_vx = uy   # 90° clockwise
            outward_vy = -ux
        
        # Direction for male vs female joints
        vx = outward_vx
        vy = outward_vy
        
        # Determine optimal number of joints and their positions
        # For gable wall bottom edges, adjust positions to align with floor
        offset = 0.0
        calc_length = edge_length
        
        if panel_name in ['gable_wall_front', 'gable_wall_back'] and edge_name == 'bottom':
            # Gable wall bottom is y + 2*thickness, but should align with floor edge (y)
            # So calculate positions based on floor length (edge_length - 2*thickness)
            # And add thickness offset to shift joints to the right position
            calc_length = edge_length - 2 * self.thickness
            offset = self.thickness
        
        # CRITICAL: Gable wall roof edges must have exactly ONE joint to match roof internal cutouts
        if panel_name in ['gable_wall_front', 'gable_wall_back'] and edge_name in ['roof_left', 'roof_right']:
            joint_count = 1
        else:
            joint_count = self.calculate_optimal_joint_count(calc_length)
        
        joint_positions = self.calculate_joint_positions(calc_length, joint_count, offset)
        
        # Generate path segments
        path_parts = []
        current_pos = 0.0
        
        # Use kerf-compensated dimensions
        joint_thickness = self.male_thickness if is_male else self.female_thickness
        
        for joint_start, joint_end in joint_positions:
            # Move to start of joint
            if joint_start > current_pos:
                x1 = start_point.x + ux * joint_start
                y1 = start_point.y + uy * joint_start
                path_parts.append(f"L {x1:.{COORDINATE_PRECISION}f},{y1:.{COORDINATE_PRECISION}f}")
            
            # Create the joint
            x1 = start_point.x + ux * joint_start
            y1 = start_point.y + uy * joint_start
            
            # Extend in calculated direction
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
            
            current_pos = joint_end
        
        # Complete to end point
        path_parts.append(f"L {end_point.x:.{COORDINATE_PRECISION}f},{end_point.y:.{COORDINATE_PRECISION}f}")
        
        return " ".join(path_parts)
    
    def get_joint_info_for_edge(self, edge_length: float) -> Dict:
        """
        Get information about joints that would be placed on an edge
        
        Args:
            edge_length: Length of the edge
            
        Returns:
            Dictionary with joint count, positions, and other info
        """
        joint_count = self.calculate_optimal_joint_count(edge_length)
        joint_positions = self.calculate_joint_positions(edge_length, joint_count)
        
        return {
            'joint_count': joint_count,
            'joint_positions': joint_positions,
            'edge_length': edge_length,
            'joint_length': self.finger_length,
            'total_joint_coverage': joint_count * self.finger_length,
            'coverage_percentage': (joint_count * self.finger_length / edge_length) * 100
        }


class EnhancedHousePanelGenerator:
    """
    Enhanced panel generator that uses the multi-finger joint system
    while maintaining compatibility with the existing architecture
    """
    
    def __init__(self, geometry: HouseGeometry, architectural_config=None, single_joints: bool = False):
        self.geometry = geometry
        self.multi_joint_generator = MultiFingerJointGenerator(geometry, single_joints)
        self.joint_config = geometry.get_finger_joint_configuration()
        self.architectural_config = architectural_config
    
    def generate_floor_panel(self, position: Point) -> tuple:
        """Generate floor panel using enhanced multi-finger joint system"""
        width = self.geometry.length
        height = self.geometry.width
        
        corners = [
            Point(position.x, position.y),                    # Bottom-left
            Point(position.x + width, position.y),           # Bottom-right
            Point(position.x + width, position.y + height),  # Top-right
            Point(position.x, position.y + height)           # Top-left
        ]
        
        edge_names = ['bottom', 'right', 'top', 'left']
        return self._generate_panel_with_multi_joints('floor', position, corners, edge_names)
    
    def generate_wall_panel(self, position: Point, wall_type: str) -> tuple:
        """Generate side wall panel using enhanced multi-finger joint system"""
        panel_dimensions = self.geometry.get_panel_dimensions()
        width, height = panel_dimensions[wall_type]
        
        corners = [
            Point(position.x, position.y),                    # Bottom-left
            Point(position.x + width, position.y),           # Bottom-right
            Point(position.x + width, position.y + height),  # Top-right
            Point(position.x, position.y + height)           # Top-left
        ]
        
        edge_names = ['bottom', 'right', 'top', 'left']
        return self._generate_panel_with_multi_joints(wall_type, position, corners, edge_names)
    
    def generate_gable_wall_panel(self, position: Point, gable_type: str) -> tuple:
        """Generate gable wall panel using enhanced multi-finger joint system"""
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
        return self._generate_panel_with_multi_joints(gable_type, position, corners, edge_names)
    
    def generate_roof_panel(self, position: Point, roof_type: str) -> tuple:
        """Generate roof panel using enhanced multi-finger joint system"""
        roof_panel_length = self.geometry.get_roof_panel_length()
        
        # Get width based on roof panel type
        if roof_type == 'roof_panel_left':
            roof_panel_width = self.geometry.get_roof_panel_left_width()
        elif roof_type == 'roof_panel_right':
            roof_panel_width = self.geometry.get_roof_panel_right_width()
        else:
            roof_panel_width = self.geometry.get_roof_panel_left_width()
        
        corners = [
            Point(position.x, position.y),                              # Bottom-left
            Point(position.x + roof_panel_length, position.y),         # Bottom-right
            Point(position.x + roof_panel_length, position.y + roof_panel_width), # Top-right
            Point(position.x, position.y + roof_panel_width)           # Top-left
        ]
        
        edge_names = ['gable_edge', 'right', 'outer', 'left']
        structural_path, decorative = self._generate_panel_with_multi_joints(roof_type, position, corners, edge_names)
        
        # Add shingles pattern to roof panels
        shingles_pattern = self._generate_roof_shingles_pattern(position, roof_panel_length, roof_panel_width)
        if shingles_pattern:
            decorative = (decorative + " " + shingles_pattern).strip()
        
        return structural_path, decorative
    
    def _generate_panel_with_multi_joints(self, panel_name: str, position: Point,
                                        corners: List[Point], edge_names: List[str]) -> tuple:
        """
        Generate panel using enhanced multi-finger joint system
        
        Args:
            panel_name: Name of panel (must exist in joint_config)
            position: Panel position
            corners: List of corner points defining panel shape
            edge_names: List of edge names corresponding to corners
            
        Returns:
            Tuple of (structural_path, decorative_patterns) for compatibility with SVG generator
        """
        if panel_name not in self.joint_config:
            raise FingerJointError(f"No configuration found for panel: {panel_name}")
            
        panel_config = self.joint_config[panel_name]
        path = f"M {corners[0].x:.{COORDINATE_PRECISION}f},{corners[0].y:.{COORDINATE_PRECISION}f}"
        
        # Generate each edge with enhanced multi-joint system
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
                    # Male joint
                    has_joint = True
                    is_male = True
                    thickness_direction = self._get_joint_direction(panel_name, edge_name, i, is_male=True)
                elif joint_type is False:
                    # Female joint
                    has_joint = True
                    is_male = False
                    thickness_direction = self._get_joint_direction(panel_name, edge_name, i, is_male=False)
                else:
                    raise FingerJointError(f"Invalid joint_type configuration: {joint_type}")
            else:
                # Edge not in config - default to smooth
                has_joint = False
                is_male = False
                thickness_direction = 1
            
            # Use enhanced multi-joint generation
            path += " " + self.multi_joint_generator.generate_multi_joint_edge(
                start_corner, end_corner, has_joint, is_male, thickness_direction,
                panel_name=panel_name, edge_name=edge_name)
        
        path += " Z"
        
        # Add internal features if specified (preserve existing functionality)
        if 'internal_cutouts' in panel_config:
            cutouts = panel_config['internal_cutouts']
            if cutouts and len(cutouts) > 0:
                path += self._generate_internal_cutouts(position, panel_name, cutouts)
        
        # Handle architectural components (preserve existing functionality)
        structural_path = path
        decorative_patterns = ""
        
        if self.architectural_config:
            structural_cutouts, decorative_patterns = self._generate_architectural_features(position, panel_name, corners)
            if structural_cutouts:
                structural_path += " " + structural_cutouts
        
        return structural_path, decorative_patterns
    
    def _get_joint_direction(self, panel_name: str, edge_name: str, edge_index: int, is_male: bool) -> int:
        """
        Determine the correct joint direction (same logic as original system)
        """
        # Use existing logic from original system
        if panel_name in ['floor', 'side_wall_left', 'side_wall_right']:
            outward_direction = -1
        elif panel_name in ['gable_wall_front', 'gable_wall_back']:
            if edge_index in [0, 1, 4]:  # bottom, right, left edges
                outward_direction = -1
            else:  # roof edges
                outward_direction = -1
        elif panel_name in ['roof_panel_left', 'roof_panel_right']:
            outward_direction = -1
        else:
            outward_direction = -1
        
        # Apply joint type: male uses outward direction, female uses opposite
        if is_male:
            result = outward_direction
        else:
            result = -outward_direction
            
        return result
    
    def _generate_internal_cutouts(self, position: Point, panel_name: str, cutouts: List[str]) -> str:
        """
        Generate internal cutouts for gable wall finger joints
        
        CRITICAL ALIGNMENT WITH GABLE WALLS:
        - Right panel (male joint on gable edge): Alignment starts at position.y
          Cutout center = position.y + base_roof_width/2
        
        - Left panel (female joint on gable edge): Offset by 1×thickness due to female joint
          Cutout center = position.y + thickness + base_roof_width/2
        
        The male joints on gable walls are centered on the sloped edge (base_roof_width length).
        """
        cutout_paths = []
        
        if panel_name.startswith('roof_panel'):
            roof_panel_length = self.geometry.get_roof_panel_length()
            base_roof_width = self.geometry.base_roof_width
            
            if panel_name == 'roof_panel_left':
                # Left panel has female joint on gable edge, requiring 1×thickness offset
                cutout_center_y = position.y + self.geometry.thickness + (base_roof_width / 2)
            elif panel_name == 'roof_panel_right':
                # Right panel has male joint on gable edge, no offset needed
                cutout_center_y = position.y + (base_roof_width / 2)
            else:
                cutout_center_y = position.y + (base_roof_width / 2)
            
            for i, orientation in enumerate(cutouts):
                if i == 0:
                    cutout_x = position.x + 2.5 * self.geometry.thickness
                    cutout_y = cutout_center_y
                elif i == 1:
                    cutout_x = position.x + roof_panel_length - 2.5 * self.geometry.thickness
                    cutout_y = cutout_center_y
                else:
                    continue
                
                cutout_paths.append(
                    self.multi_joint_generator.generate_internal_female_cutout(
                        cutout_x, cutout_y, orientation))
        
        return " ".join(cutout_paths)
    
    def _generate_architectural_features(self, position: Point, panel_name: str, corners: List[Point]) -> tuple:
        """Generate architectural features including door/window cutouts and decorative patterns"""
        if not self.architectural_config:
            return "", ""
        
        structural_cutouts = []
        decorative_patterns = []
        
        # Get windows for this panel
        windows = self.architectural_config.get_windows_for_panel(panel_name)
        for window in windows:
            # Generate window cutout
            cutout_path = self._generate_window_cutout(window, position)
            if cutout_path:
                structural_cutouts.append(cutout_path)
        
        # Get doors for this panel
        doors = self.architectural_config.get_doors_for_panel(panel_name)
        for door in doors:
            # Generate door cutout
            cutout_path = self._generate_door_cutout(door, position)
            if cutout_path:
                structural_cutouts.append(cutout_path)
        
        # Get chimneys for this panel (roof panels only)
        chimneys = self.architectural_config.get_chimneys_for_panel(panel_name)
        for chimney in chimneys:
            # Generate chimney cutout
            cutout_path = self._generate_chimney_cutout(chimney, position)
            if cutout_path:
                structural_cutouts.append(cutout_path)
        
        # Get decorative patterns for this panel
        panel_dims = self.geometry.get_panel_dimensions().get(panel_name)
        if panel_dims:
            pattern = self.architectural_config.get_pattern_for_panel(panel_name)
            if pattern:
                decorative_patterns.append(pattern)
        
        return " ".join(structural_cutouts), " ".join(decorative_patterns)
    
    def _generate_window_cutout(self, window, position: Point) -> str:
        """Generate SVG path for a window cutout (with separate casing)"""
        from .architectural_components import WindowType
        
        # Calculate absolute position (window position is relative to panel origin)
        abs_x = position.x + window.position.x
        abs_y = position.y + window.position.y
        width = window.position.width
        height = window.position.height
        
        # Generate cutout based on window type
        if window.type == WindowType.RECTANGULAR:
            return self._generate_rectangular_cutout(abs_x, abs_y, width, height)
        elif window.type == WindowType.ARCHED:
            return self._generate_arched_cutout(abs_x, abs_y, width, height)
        elif window.type == WindowType.CIRCULAR:
            return self._generate_circular_cutout(abs_x, abs_y, width, height)
        elif window.type == WindowType.ATTIC:
            return self._generate_rectangular_cutout(abs_x, abs_y, width, height)
        elif window.type == WindowType.CROSS_PANE:
            return self._generate_cross_pane_cutout(abs_x, abs_y, width, height)
        elif window.type == WindowType.MULTI_PANE:
            return self._generate_multi_pane_cutout(abs_x, abs_y, width, height)
        elif window.type == WindowType.COLONIAL_SET:
            return self._generate_colonial_set_cutout(abs_x, abs_y, width, height)
        elif window.type == WindowType.PALLADIAN:
            return self._generate_palladian_cutout(abs_x, abs_y, width, height)
        elif window.type == WindowType.GOTHIC_PAIR:
            return self._generate_gothic_pair_cutout(abs_x, abs_y, width, height)
        elif window.type == WindowType.DOUBLE_HUNG:
            return self._generate_double_hung_cutout(abs_x, abs_y, width, height)
        elif window.type == WindowType.CASEMENT:
            return self._generate_rectangular_cutout(abs_x, abs_y, width, height)
        elif window.type == WindowType.BAY:
            return self._generate_rectangular_cutout(abs_x, abs_y, width, height)
        elif window.type == WindowType.DORMER:
            return self._generate_dormer_cutout(abs_x, abs_y, width, height)
        else:
            # Fallback to rectangular cutout
            return self._generate_rectangular_cutout(abs_x, abs_y, width, height)
    
    def _generate_door_cutout(self, door, position: Point) -> str:
        """Generate SVG path for a door cutout (without integrated casing)"""
        from .architectural_components import DoorType
        
        # Calculate absolute position (door position is relative to panel origin)
        abs_x = position.x + door.position.x
        abs_y = position.y + door.position.y
        width = door.position.width
        height = door.position.height
        
        # Generate cutout based on door type
        if door.type == DoorType.RECTANGULAR:
            return self._generate_rectangular_cutout(abs_x, abs_y, width, height)
        elif door.type == DoorType.ARCHED:
            return self._generate_arched_cutout(abs_x, abs_y, width, height)
        elif door.type == DoorType.DOUBLE:
            # Double door is two rectangular sections
            half_width = width / 2
            left = self._generate_rectangular_cutout(abs_x, abs_y, half_width - 0.5, height)
            right = self._generate_rectangular_cutout(abs_x + half_width + 0.5, abs_y, half_width - 0.5, height)
            return left + " " + right
        elif door.type == DoorType.DUTCH:
            # Dutch door is split horizontally
            half_height = height / 2
            top = self._generate_rectangular_cutout(abs_x, abs_y + half_height + 0.5, width, half_height - 0.5)
            bottom = self._generate_rectangular_cutout(abs_x, abs_y, width, half_height - 0.5)
            return top + " " + bottom
        else:
            return self._generate_rectangular_cutout(abs_x, abs_y, width, height)
    
    def _generate_rectangular_cutout(self, x: float, y: float, width: float, height: float) -> str:
        """Generate a rectangular cutout"""
        return (f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                f"L {x + width:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
                f"L {x:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} Z")
    
    def _generate_arched_cutout(self, x: float, y: float, width: float, height: float) -> str:
        """Generate an arched cutout (rectangular with arched top)"""
        arch_height = height * 0.3  # Top 30% is the arch
        rect_height = height - arch_height
        
        # Start at bottom left
        path = f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
        # Bottom edge
        path += f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
        # Right edge up to arch
        path += f"L {x + width:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
        # Arch at top (using quadratic bezier curve)
        path += f"Q {x + width/2:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
        path += f"{x:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
        # Close path
        path += "Z"
        
        return path
    
    def _generate_circular_cutout(self, x: float, y: float, width: float, height: float) -> str:
        """Generate a circular cutout"""
        # Use the smaller dimension to ensure it fits
        diameter = min(width, height)
        radius = diameter / 2
        center_x = x + width / 2
        center_y = y + height / 2
        
        # Generate circle using 4 cubic bezier curves (standard SVG technique)
        # Magic number for bezier control points to approximate a circle
        control_offset = radius * 0.552284749831
        
        path = f"M {center_x:.{COORDINATE_PRECISION}f},{center_y - radius:.{COORDINATE_PRECISION}f} "
        path += f"C {center_x + control_offset:.{COORDINATE_PRECISION}f},{center_y - radius:.{COORDINATE_PRECISION}f} "
        path += f"{center_x + radius:.{COORDINATE_PRECISION}f},{center_y - control_offset:.{COORDINATE_PRECISION}f} "
        path += f"{center_x + radius:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
        path += f"C {center_x + radius:.{COORDINATE_PRECISION}f},{center_y + control_offset:.{COORDINATE_PRECISION}f} "
        path += f"{center_x + control_offset:.{COORDINATE_PRECISION}f},{center_y + radius:.{COORDINATE_PRECISION}f} "
        path += f"{center_x:.{COORDINATE_PRECISION}f},{center_y + radius:.{COORDINATE_PRECISION}f} "
        path += f"C {center_x - control_offset:.{COORDINATE_PRECISION}f},{center_y + radius:.{COORDINATE_PRECISION}f} "
        path += f"{center_x - radius:.{COORDINATE_PRECISION}f},{center_y + control_offset:.{COORDINATE_PRECISION}f} "
        path += f"{center_x - radius:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
        path += f"C {center_x - radius:.{COORDINATE_PRECISION}f},{center_y - control_offset:.{COORDINATE_PRECISION}f} "
        path += f"{center_x - control_offset:.{COORDINATE_PRECISION}f},{center_y - radius:.{COORDINATE_PRECISION}f} "
        path += f"{center_x:.{COORDINATE_PRECISION}f},{center_y - radius:.{COORDINATE_PRECISION}f} Z"
        
        return path
    
    def _generate_cross_pane_cutout(self, x: float, y: float, width: float, height: float) -> str:
        """Generate a cross-pane window cutout with cross mullions"""
        center_x = x + width / 2
        center_y = y + height / 2
        mullion_width = 1.0  # 1mm mullion width
        
        # Main window opening
        main = self._generate_rectangular_cutout(x, y, width, height)
        
        # Vertical mullion (center)
        vert_mullion = self._generate_rectangular_cutout(
            center_x - mullion_width/2, y, mullion_width, height)
        
        # Horizontal mullion (center)
        horiz_mullion = self._generate_rectangular_cutout(
            x, center_y - mullion_width/2, width, mullion_width)
        
        return main + " " + vert_mullion + " " + horiz_mullion
    
    def _generate_multi_pane_cutout(self, x: float, y: float, width: float, height: float) -> str:
        """Generate a multi-pane window cutout (3x2 grid with internal mullions)"""
        mullion_width = 1.0  # 1mm mullion width
        pane_width = width / 3
        pane_height = height / 2
        
        # Main window opening
        main = self._generate_rectangular_cutout(x, y, width, height)
        
        # Vertical mullions (2 internal divisions for 3 columns)
        mullions = []
        for i in range(1, 3):
            mullion_x = x + i * pane_width - mullion_width/2
            mullions.append(self._generate_rectangular_cutout(
                mullion_x, y, mullion_width, height))
        
        # Horizontal mullion (1 internal division for 2 rows)
        mullion_y = y + pane_height - mullion_width/2
        mullions.append(self._generate_rectangular_cutout(
            x, mullion_y, width, mullion_width))
        
        return main + " " + " ".join(mullions)
    
    def _generate_colonial_set_cutout(self, x: float, y: float, width: float, height: float) -> str:
        """Generate a colonial set window cutout (3 separate windows)"""
        window_width = width / 3
        spacing = window_width * 0.1
        actual_window_width = window_width - spacing
        
        cutouts = []
        for i in range(3):
            window_x = x + i * window_width + spacing/2
            cutouts.append(self._generate_rectangular_cutout(
                window_x, y, actual_window_width, height))
        
        return " ".join(cutouts)
    
    def _generate_palladian_cutout(self, x: float, y: float, width: float, height: float) -> str:
        """Generate a Palladian window cutout (arched center + 2 rectangular sides)"""
        central_width = width * 0.6
        side_width = width * 0.2
        
        # Central arched window
        center_x = x + side_width
        center = self._generate_arched_cutout(center_x, y, central_width, height)
        
        # Left rectangular window
        left = self._generate_rectangular_cutout(x, y, side_width, height)
        
        # Right rectangular window
        right_x = x + side_width + central_width
        right = self._generate_rectangular_cutout(right_x, y, side_width, height)
        
        return left + " " + center + " " + right
    
    def _generate_gothic_pair_cutout(self, x: float, y: float, width: float, height: float) -> str:
        """Generate a Gothic pair window cutout (2 gothic arched windows)"""
        window_width = (width - 3) / 2  # Account for central mullion
        spacing = 3.0
        
        # Left gothic window
        left = self._generate_gothic_arch_cutout(x, y, window_width, height)
        
        # Right gothic window
        right_x = x + window_width + spacing
        right = self._generate_gothic_arch_cutout(right_x, y, window_width, height)
        
        return left + " " + right
    
    def _generate_gothic_arch_cutout(self, x: float, y: float, width: float, height: float) -> str:
        """Generate a single Gothic arched window cutout"""
        # Gothic arch is a pointed arch created with two curves meeting at the top
        rect_height = height * 0.7  # Lower 70% is rectangular
        arch_height = height * 0.3  # Upper 30% is the pointed arch
        
        path = f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
        # Right edge up to arch
        path += f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
        path += f"L {x + width:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
        # Right side of pointed arch
        path += f"Q {x + width * 0.75:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
        path += f"{x + width/2:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
        # Left side of pointed arch
        path += f"Q {x + width * 0.25:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
        path += f"{x:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
        # Left edge
        path += "Z"
        
        return path
    
    def _generate_double_hung_cutout(self, x: float, y: float, width: float, height: float) -> str:
        """Generate a double-hung window cutout with horizontal division"""
        divider_height = 1.0  # 1mm divider height
        mid_y = y + height / 2
        
        # Main window opening
        main = self._generate_rectangular_cutout(x, y, width, height)
        
        # Horizontal divider in the middle
        divider = self._generate_rectangular_cutout(
            x, mid_y - divider_height/2, width, divider_height)
        
        return main + " " + divider
    
    def _generate_dormer_cutout(self, x: float, y: float, width: float, height: float) -> str:
        """Generate a dormer window cutout (rectangular with peaked roof top)"""
        peak_height = height * 0.2  # Top 20% is peaked
        rect_height = height - peak_height
        
        # Start at bottom left
        path = f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
        # Right edge up to peak
        path += f"L {x + width:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
        path += f"L {x + width:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
        # Right slope to peak
        path += f"L {x + width/2:.{COORDINATE_PRECISION}f},{y + height:.{COORDINATE_PRECISION}f} "
        # Left slope from peak
        path += f"L {x:.{COORDINATE_PRECISION}f},{y + rect_height:.{COORDINATE_PRECISION}f} "
        # Close path
        path += "Z"
        
        return path
    
    def generate_window_casing_panels(self, window, panel_name: str) -> Dict[str, Tuple[float, float, str]]:
        """
        Generate dimensions for window casing as a single frame piece with inner cutout.
        Casing shape matches the window type (rectangular, arched, circular, etc.).
        Returns dictionary mapping casing name to (width, height, svg_path) tuple.
        Skip casings for attic windows.
        """
        from .architectural_components import WindowType
        
        # Skip casings for attic windows (too small)
        if window.type == WindowType.ATTIC:
            return {}
        
        inner_width = window.position.width
        inner_height = window.position.height
        
        # Casing dimensions based on material thickness
        casing_width = self.geometry.thickness  # Frame width = 1 * thickness
        extension = 0.4 * self.geometry.thickness  # Horizontal extension = 0.2 * thickness per side
        
        # Generate casing based on window type
        if window.type == WindowType.ARCHED:
            return self._generate_arched_window_casing(inner_width, inner_height, casing_width, extension, panel_name)
        elif window.type == WindowType.CIRCULAR:
            return self._generate_circular_window_casing(inner_width, inner_height, casing_width, extension, panel_name)
        else:
            # Rectangular casing for most window types
            # (rectangular, bay, dormer, double_hung, casement, colonial_set, cross_pane, multi_pane, palladian, gothic_pair)
            return self._generate_rectangular_window_casing(inner_width, inner_height, casing_width, extension, panel_name)
    
    def _generate_rectangular_window_casing(self, inner_width: float, inner_height: float,
                                           casing_width: float, extension: float, panel_name: str) -> Dict[str, Tuple[float, float, str]]:
        """Generate rectangular window casing matching test.svg pattern exactly"""
        # Frame body dimensions (the narrow vertical part)
        tab_height = casing_width * 1.5
        frame_width = inner_width + 2 * casing_width
        frame_height = inner_height + 2 * tab_height
        
        # Tab dimensions (horizontal extensions at top and bottom ONLY)
        # Total width at tabs is wider than frame body
        tab_width_total = frame_width + 2 * extension
        
        # Total bounding box dimensions
        outer_width = tab_width_total
        outer_height = frame_height
        
        # Inner cutout position (centered in frame body)
        inner_x = extension + casing_width
        inner_y = tab_height
        
        # Create path matching screenshot exactly
        # The frame has a narrower body with wider tabs at top and bottom
        # frame_height = inner_height + 2*casing_width (total height including casings)
        # tab_height = casing_width (height of top and bottom tabs)
        # Frame body spans from Y=tab_height to Y=(frame_height - tab_height)
        
        svg_path = (
            # Start at bottom-left of bottom tab
            f"M 0.000,{outer_height:.{COORDINATE_PRECISION}f} "
            # Across bottom tab to the right
            f"L {outer_width:.{COORDINATE_PRECISION}f},{outer_height:.{COORDINATE_PRECISION}f} "
            # Up to top of bottom tab (bottom of frame body sides)
            f"L {outer_width:.{COORDINATE_PRECISION}f},{outer_height - tab_height:.{COORDINATE_PRECISION}f} "
            # Step LEFT (inward) to right edge of frame body
            f"L {outer_width - extension:.{COORDINATE_PRECISION}f},{outer_height - tab_height:.{COORDINATE_PRECISION}f} "
            # Up right side of frame body
            f"L {outer_width - extension:.{COORDINATE_PRECISION}f},{tab_height:.{COORDINATE_PRECISION}f} "
            # Step RIGHT (outward) to right edge of top tab
            f"L {outer_width:.{COORDINATE_PRECISION}f},{tab_height:.{COORDINATE_PRECISION}f} "
            # Up to top of top tab
            f"L {outer_width:.{COORDINATE_PRECISION}f},0.000 "
            # Across top tab to the left
            f"L 0.000,0.000 "
            # Down to bottom of top tab (top of frame body sides)
            f"L 0.000,{tab_height:.{COORDINATE_PRECISION}f} "
            # Step RIGHT (inward) to left edge of frame body
            f"L {extension:.{COORDINATE_PRECISION}f},{tab_height:.{COORDINATE_PRECISION}f} "
            # Down left side of frame body
            f"L {extension:.{COORDINATE_PRECISION}f},{outer_height - tab_height:.{COORDINATE_PRECISION}f} "
            # Step LEFT (outward) to left edge of bottom tab
            f"L 0.000,{outer_height - tab_height:.{COORDINATE_PRECISION}f} "
            # Close path back to start
            f"Z "
            # Inner cutout (counter-clockwise)
            f"M {inner_x:.{COORDINATE_PRECISION}f},{inner_y:.{COORDINATE_PRECISION}f} "
            f"L {inner_x:.{COORDINATE_PRECISION}f},{inner_y + inner_height:.{COORDINATE_PRECISION}f} "
            f"L {inner_x + inner_width:.{COORDINATE_PRECISION}f},{inner_y + inner_height:.{COORDINATE_PRECISION}f} "
            f"L {inner_x + inner_width:.{COORDINATE_PRECISION}f},{inner_y:.{COORDINATE_PRECISION}f} Z"
        )
        
        # Score lines create border region, COMPLETELY INSIDE red cut line
        # Two rectangles: outer inset from frame body, inner at window cutout position
        # The area between them represents the frame border to be folded
        
        score_inset = 0.2 * self.geometry.thickness  # Small inset from frame edges
        
        # Outer score rectangle - inset from frame body edges (not tabs)
        # Frame body area is from Y=tab_height to Y=(outer_height - tab_height)
        score_outer_x = extension + score_inset
        score_outer_y = score_inset
        score_outer_width = frame_width - 2 * score_inset
        score_outer_height = outer_height - 2 * score_inset
        
        # Inner score rectangle - matches the window cutout position (not inset from it)
        # This defines where the window opening will be after folding
        score_inner_x = inner_x - score_inset
        score_inner_y = inner_y - score_inset
        score_inner_width = inner_width + 2 * score_inset
        score_inner_height = inner_height + 2 * score_inset
        
        # Two separate rectangle paths
        score_lines = (
            # Outer rectangle (inset from frame body) From top-left corner, counterclock-wise
            f"M {score_outer_x - extension:.{COORDINATE_PRECISION}f},{score_outer_y:.{COORDINATE_PRECISION}f} "
            f"L {score_outer_x - extension:.{COORDINATE_PRECISION}f},{score_outer_y + tab_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "
            f"L {score_outer_x:.{COORDINATE_PRECISION}f},{score_outer_y + tab_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "
            f"L {score_outer_x:.{COORDINATE_PRECISION}f},{score_inner_y + score_inner_height:.{COORDINATE_PRECISION}f} "
            f"L {score_outer_x - extension:.{COORDINATE_PRECISION}f},{score_inner_y + score_inner_height:.{COORDINATE_PRECISION}f} " # LEFT
            f"L {score_outer_x - extension:.{COORDINATE_PRECISION}f},{score_inner_y + score_inner_height + tab_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "

            # bottom line
            f"L {score_outer_x + score_outer_width + extension:.{COORDINATE_PRECISION}f},{score_inner_y + score_inner_height + tab_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "
            f"L {score_outer_x + score_outer_width + extension:.{COORDINATE_PRECISION}f},{score_outer_y + tab_height + score_inner_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "
            f"L {score_outer_x + score_outer_width:.{COORDINATE_PRECISION}f},{score_outer_y + tab_height + score_inner_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "
            f"L {score_outer_x + score_outer_width:.{COORDINATE_PRECISION}f},{score_inner_y:.{COORDINATE_PRECISION}f} " # UP 
            f"L {score_outer_x + score_outer_width + extension:.{COORDINATE_PRECISION}f},{score_inner_y:.{COORDINATE_PRECISION}f} " # RIGHT
            f"L {score_outer_x + score_outer_width + extension:.{COORDINATE_PRECISION}f},{score_outer_y:.{COORDINATE_PRECISION}f} Z" # UP

            # Inner rectangle (outset from window cutout)
            f"M {score_inner_x:.{COORDINATE_PRECISION}f},{score_inner_y:.{COORDINATE_PRECISION}f} "
            f"L {score_inner_x + score_inner_width:.{COORDINATE_PRECISION}f},{score_inner_y:.{COORDINATE_PRECISION}f} "
            f"L {score_inner_x + score_inner_width:.{COORDINATE_PRECISION}f},{score_inner_y + score_inner_height:.{COORDINATE_PRECISION}f} "
            f"L {score_inner_x:.{COORDINATE_PRECISION}f},{score_inner_y + score_inner_height:.{COORDINATE_PRECISION}f} Z"
        )
        
        return {
            f'{panel_name}_window_casing': (outer_width, outer_height, svg_path),
            f'{panel_name}_window_casing_scores': (outer_width, outer_height, score_lines)
        }
    
    def _generate_arched_window_casing(self, inner_width: float, inner_height: float,
                                      casing_width: float, extension: float, panel_name: str) -> Dict[str, Tuple[float, float, str]]:
        """Generate arched window casing (arched on both inner and outer edges)"""
        # Outer frame dimensions
        outer_width = inner_width + 2 * casing_width + 2 * extension
        outer_height = inner_height + 2 * casing_width
        
        # Inner cutout position
        inner_x = extension + casing_width
        inner_y = casing_width
        
        # Calculate arch dimensions (top 30% of window is arched)
        inner_arch_start = inner_height * 0.7
        
        # Outer arch starts at same relative position but with casing offset
        outer_arch_start = inner_arch_start + casing_width
        
        # Create path with ARCHED outer perimeter and ARCHED inner cutout
        svg_path = (
            # Outer perimeter with arched top (clockwise)
            f"M 0.000,0.000 "  # Bottom-left
            f"L 0.000,{outer_arch_start:.{COORDINATE_PRECISION}f} "  # Up left side to arch start
            # Outer arch using quadratic bezier
            f"Q {outer_width/2:.{COORDINATE_PRECISION}f},{outer_height:.{COORDINATE_PRECISION}f} "
            f"{outer_width:.{COORDINATE_PRECISION}f},{outer_arch_start:.{COORDINATE_PRECISION}f} "  # Arch across top
            f"L {outer_width:.{COORDINATE_PRECISION}f},0.000 "  # Down right side
            f"L 0.000,0.000 Z "  # Close bottom
            # Inner arched cutout (counter-clockwise)
            f"M {inner_x:.{COORDINATE_PRECISION}f},{inner_y:.{COORDINATE_PRECISION}f} "  # Bottom-left of opening
            f"L {inner_x + inner_width:.{COORDINATE_PRECISION}f},{inner_y:.{COORDINATE_PRECISION}f} "  # Bottom edge
            f"L {inner_x + inner_width:.{COORDINATE_PRECISION}f},{inner_y + inner_arch_start:.{COORDINATE_PRECISION}f} "  # Up right side
            # Inner arch using quadratic bezier (counter-clockwise)
            f"Q {inner_x + inner_width/2:.{COORDINATE_PRECISION}f},{inner_y + inner_height:.{COORDINATE_PRECISION}f} "
            f"{inner_x:.{COORDINATE_PRECISION}f},{inner_y + inner_arch_start:.{COORDINATE_PRECISION}f} "  # Arch back
            f"Z"  # Close
        )
        
        return {
            f'{panel_name}_window_casing': (outer_width, outer_height, svg_path)
        }
    
    def _generate_circular_window_casing(self, inner_width: float, inner_height: float,
                                        casing_width: float, extension: float, panel_name: str) -> Dict[str, Tuple[float, float, str]]:
        """Generate circular window casing (ring/donut shape - circular outer and inner edges)"""
        # Use the smaller dimension for the circle
        inner_diameter = min(inner_width, inner_height)
        inner_radius = inner_diameter / 2
        
        # Outer circle has casing width added
        outer_radius = inner_radius + casing_width
        outer_diameter = outer_radius * 2
        outer_size = outer_diameter  # Bounding box
        
        # Center position
        center_x = outer_size / 2
        center_y = outer_size / 2
        
        # Magic number for bezier control points to approximate a circle
        inner_control_offset = inner_radius * 0.552284749831
        outer_control_offset = outer_radius * 0.552284749831
        
        # Create path with CIRCULAR outer perimeter and CIRCULAR inner cutout (ring/donut shape)
        svg_path = (
            # Outer circle using 4 cubic bezier curves (clockwise from top)
            f"M {center_x:.{COORDINATE_PRECISION}f},{center_y - outer_radius:.{COORDINATE_PRECISION}f} "
            f"C {center_x + outer_control_offset:.{COORDINATE_PRECISION}f},{center_y - outer_radius:.{COORDINATE_PRECISION}f} "
            f"{center_x + outer_radius:.{COORDINATE_PRECISION}f},{center_y - outer_control_offset:.{COORDINATE_PRECISION}f} "
            f"{center_x + outer_radius:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
            f"C {center_x + outer_radius:.{COORDINATE_PRECISION}f},{center_y + outer_control_offset:.{COORDINATE_PRECISION}f} "
            f"{center_x + outer_control_offset:.{COORDINATE_PRECISION}f},{center_y + outer_radius:.{COORDINATE_PRECISION}f} "
            f"{center_x:.{COORDINATE_PRECISION}f},{center_y + outer_radius:.{COORDINATE_PRECISION}f} "
            f"C {center_x - outer_control_offset:.{COORDINATE_PRECISION}f},{center_y + outer_radius:.{COORDINATE_PRECISION}f} "
            f"{center_x - outer_radius:.{COORDINATE_PRECISION}f},{center_y + outer_control_offset:.{COORDINATE_PRECISION}f} "
            f"{center_x - outer_radius:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
            f"C {center_x - outer_radius:.{COORDINATE_PRECISION}f},{center_y - outer_control_offset:.{COORDINATE_PRECISION}f} "
            f"{center_x - outer_control_offset:.{COORDINATE_PRECISION}f},{center_y - outer_radius:.{COORDINATE_PRECISION}f} "
            f"{center_x:.{COORDINATE_PRECISION}f},{center_y - outer_radius:.{COORDINATE_PRECISION}f} Z "
            # Inner circle cutout using 4 cubic bezier curves (counter-clockwise from top for hole)
            f"M {center_x:.{COORDINATE_PRECISION}f},{center_y - inner_radius:.{COORDINATE_PRECISION}f} "
            f"C {center_x - inner_control_offset:.{COORDINATE_PRECISION}f},{center_y - inner_radius:.{COORDINATE_PRECISION}f} "
            f"{center_x - inner_radius:.{COORDINATE_PRECISION}f},{center_y - inner_control_offset:.{COORDINATE_PRECISION}f} "
            f"{center_x - inner_radius:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
            f"C {center_x - inner_radius:.{COORDINATE_PRECISION}f},{center_y + inner_control_offset:.{COORDINATE_PRECISION}f} "
            f"{center_x - inner_control_offset:.{COORDINATE_PRECISION}f},{center_y + inner_radius:.{COORDINATE_PRECISION}f} "
            f"{center_x:.{COORDINATE_PRECISION}f},{center_y + inner_radius:.{COORDINATE_PRECISION}f} "
            f"C {center_x + inner_control_offset:.{COORDINATE_PRECISION}f},{center_y + inner_radius:.{COORDINATE_PRECISION}f} "
            f"{center_x + inner_radius:.{COORDINATE_PRECISION}f},{center_y + inner_control_offset:.{COORDINATE_PRECISION}f} "
            f"{center_x + inner_radius:.{COORDINATE_PRECISION}f},{center_y:.{COORDINATE_PRECISION}f} "
            f"C {center_x + inner_radius:.{COORDINATE_PRECISION}f},{center_y - inner_control_offset:.{COORDINATE_PRECISION}f} "
            f"{center_x + inner_control_offset:.{COORDINATE_PRECISION}f},{center_y - inner_radius:.{COORDINATE_PRECISION}f} "
            f"{center_x:.{COORDINATE_PRECISION}f},{center_y - inner_radius:.{COORDINATE_PRECISION}f} Z"
        )
        
        return {
            f'{panel_name}_window_casing': (outer_size, outer_size, svg_path)
        }
    
    def generate_door_casing_panels(self, door, panel_name: str) -> Dict[str, Tuple[float, float, str]]:
        """
        Generate dimensions for door casing as a single 3-sided frame piece (no bottom) with inner cutout.
        Casing shape matches the door type (rectangular, arched).
        Returns dictionary mapping casing name to (width, height, svg_path) tuple.
        Left and right vertical frames are symmetric.
        """
        from .architectural_components import DoorType
        
        inner_width = door.position.width
        inner_height = door.position.height
        
        # Casing dimensions based on material thickness
        casing_width = self.geometry.thickness  # Frame width = 1 * thickness
        extension = 0.4 * self.geometry.thickness  # Horizontal extension = 0.4 * thickness per side
        
        # Generate casing based on door type
        if door.type == DoorType.ARCHED:
            return self._generate_arched_door_casing(inner_width, inner_height, casing_width, extension, panel_name)
        else:
            # Rectangular casing for most door types (rectangular, double, dutch)
            return self._generate_rectangular_door_casing(inner_width, inner_height, casing_width, extension, panel_name)
    
    def _generate_rectangular_door_casing(self, inner_width: float, inner_height: float,
                                         casing_width: float, extension: float, panel_name: str) -> Dict[str, Tuple[float, float, str]]:
        """Generate rectangular door casing matching door_frame_example.svg - U-shape open at bottom with small tabs"""
        # Frame body (U-shaped, no bottom bar)
        top_bar_height = 1.5 * casing_width  # Height of the horizontal top bar
        frame_width = inner_width + 2 * casing_width
        frame_height = inner_height  # Full height for the vertical sides
        
        # Top section with tab
        tab_width_total = frame_width + 2 * extension
        
        # Total dimensions
        outer_width = tab_width_total
        outer_height = frame_height + top_bar_height
        
        # Inner door opening - matches door size exactly
        inner_x = extension + casing_width
        inner_y = top_bar_height
        
        # U-shaped frame: vertical sides go all the way down, horizontal bar only at top with tab
        svg_path = (
            # Start at bottom-left of left vertical side
            f"M {extension:.{COORDINATE_PRECISION}f},{outer_height:.{COORDINATE_PRECISION}f} "
            # Up left vertical side
            f"L {extension:.{COORDINATE_PRECISION}f},{top_bar_height:.{COORDINATE_PRECISION}f} "
            # Step LEFT to start of top tab
            f"L 0.000,{top_bar_height:.{COORDINATE_PRECISION}f} "
            # Up to top of tab
            f"L 0.000,0.000 "
            # Across top tab
            f"L {outer_width:.{COORDINATE_PRECISION}f},0.000 "
            # Down to top bar level
            f"L {outer_width:.{COORDINATE_PRECISION}f},{top_bar_height:.{COORDINATE_PRECISION}f} "
            # Step RIGHT (inward)
            f"L {outer_width - extension:.{COORDINATE_PRECISION}f},{top_bar_height:.{COORDINATE_PRECISION}f} "
            # Down right vertical side
            f"L {outer_width - extension:.{COORDINATE_PRECISION}f},{outer_height:.{COORDINATE_PRECISION}f} "
            # Step LEFT to inner-right
            f"L {inner_x + inner_width:.{COORDINATE_PRECISION}f},{outer_height:.{COORDINATE_PRECISION}f} "
            # Up inner-right side
            f"L {inner_x + inner_width:.{COORDINATE_PRECISION}f},{inner_y:.{COORDINATE_PRECISION}f} "
            # Across inner top
            f"L {inner_x:.{COORDINATE_PRECISION}f},{inner_y:.{COORDINATE_PRECISION}f} "
            # Down inner-left side
            f"L {inner_x:.{COORDINATE_PRECISION}f},{outer_height:.{COORDINATE_PRECISION}f} "
            # Close
            f"Z"
        )
        
        # Score lines create U-shaped border region, COMPLETELY INSIDE red cut line
        # Must not overlap or extend beyond cut line boundaries
        # Similar to window frame, but U-shaped (no bottom bar)
        
        score_inset = extension / 2  # Inset from both outer and inner edges
        
        # Outer score rectangle - inset from frame body edges (not tabs), forming U-shape
        score_outer_x = extension + score_inset
        score_outer_y = score_inset # top_bar_height + score_inset
        score_outer_width = frame_width - 2 * score_inset
        score_outer_height = frame_height + top_bar_height - 2 * score_inset  # Goes to bottom
        
        # Inner score rectangle - inset FROM door cutout (smaller than opening), forming U-shape
        score_inner_x = inner_x - score_inset
        score_inner_y = inner_y - score_inset
        score_inner_width = inner_width + 2 * score_inset
        score_inner_height = inner_height - 2 * score_inset  # Inset from bottom
        inner_casing_width = casing_width - 2 * score_inset 
        
        # Single continuous U-shaped border path (similar to window but U-shaped)
        # This creates the border region between outer and inner edges
        score_lines = (
            # Outer U-shape (clockwise from bottom-left)
            f"M {score_outer_x:.{COORDINATE_PRECISION}f},{score_outer_y + score_outer_height:.{COORDINATE_PRECISION}f} "
            f"L {score_outer_x:.{COORDINATE_PRECISION}f},{score_outer_y + top_bar_height - 2 * score_inset :.{COORDINATE_PRECISION}f} "
            f"L {score_outer_x - extension:.{COORDINATE_PRECISION}f},{score_outer_y + top_bar_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "
            f"L {score_outer_x - extension:.{COORDINATE_PRECISION}f},{score_outer_y:.{COORDINATE_PRECISION}f} "

            f"L {score_outer_x + score_outer_width + extension:.{COORDINATE_PRECISION}f},{score_outer_y:.{COORDINATE_PRECISION}f} "
            f"L {score_outer_x + score_outer_width + extension:.{COORDINATE_PRECISION}f},{score_outer_y + top_bar_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "
            f"L {score_outer_x + score_outer_width:.{COORDINATE_PRECISION}f},{score_outer_y + top_bar_height - 2 * score_inset:.{COORDINATE_PRECISION}f} "

            f"L {score_outer_x + score_outer_width:.{COORDINATE_PRECISION}f},{score_outer_y + score_outer_height:.{COORDINATE_PRECISION}f} "
            # Step inward to inner U-shape
            f"L {score_inner_x + score_inner_width:.{COORDINATE_PRECISION}f},{score_outer_y + score_outer_height:.{COORDINATE_PRECISION}f} "
            # Inner U-shape (counter-clockwise from bottom-right)
            f"L {score_inner_x + score_inner_width:.{COORDINATE_PRECISION}f},{score_inner_y:.{COORDINATE_PRECISION}f} "
            f"L {score_inner_x:.{COORDINATE_PRECISION}f},{score_inner_y:.{COORDINATE_PRECISION}f} "
            f"L {score_inner_x:.{COORDINATE_PRECISION}f},{score_outer_y + score_outer_height:.{COORDINATE_PRECISION}f} "
            f"Z"
        )
        
        return {
            f'{panel_name}_door_casing': (outer_width, outer_height, svg_path),
            f'{panel_name}_door_casing_scores': (outer_width, outer_height, score_lines)
        }
    
    def _generate_arched_door_casing(self, inner_width: float, inner_height: float,
                                    casing_width: float, extension: float, panel_name: str) -> Dict[str, Tuple[float, float, str]]:
        """Generate arched door casing (horseshoe shape with arch at BOTTOM, opening at TOP for upside-down gable walls)"""
        # Outer frame dimensions (3-sided, opening at top)
        outer_width = inner_width + 2 * casing_width + 2 * extension
        outer_height = inner_height + casing_width
        
        # Inner cutout position
        inner_x = extension + casing_width
        inner_y = 0.0  # No top casing (opening is at top)
        inner_right_x = inner_x + inner_width
        
        # Calculate arch dimensions (bottom 30% of door is arched)
        inner_arch_start = inner_height * 0.7
        
        # For outer arch, calculate where rectangular portion ends
        outer_arch_start = inner_arch_start + casing_width
        
        # Create path with ARCHED outer perimeter (arch at bottom) and ARCHED inner cutout
        # The outer edge follows the arch shape of the door
        svg_path = (
            # Start at top-left
            f"M 0.000,0.000 "
            # Down left side to where arch begins
            f"L 0.000,{outer_arch_start:.{COORDINATE_PRECISION}f} "
            # Outer arch across bottom using quadratic bezier
            f"Q {outer_width/2:.{COORDINATE_PRECISION}f},{outer_height:.{COORDINATE_PRECISION}f} "
            f"{outer_width:.{COORDINATE_PRECISION}f},{outer_arch_start:.{COORDINATE_PRECISION}f} "
            # Up right side
            f"L {outer_width:.{COORDINATE_PRECISION}f},0.000 "
            # Inward to inner-right top
            f"L {inner_right_x:.{COORDINATE_PRECISION}f},0.000 "
            # Down inner-right to arch start
            f"L {inner_right_x:.{COORDINATE_PRECISION}f},{inner_arch_start:.{COORDINATE_PRECISION}f} "
            # Inner arch using quadratic bezier (arch at bottom)
            f"Q {inner_x + inner_width/2:.{COORDINATE_PRECISION}f},{inner_height:.{COORDINATE_PRECISION}f} "
            f"{inner_x:.{COORDINATE_PRECISION}f},{inner_arch_start:.{COORDINATE_PRECISION}f} "
            # Up inner-left
            f"L {inner_x:.{COORDINATE_PRECISION}f},0.000 "
            # Close path
            f"Z"
        )
        
        return {
            f'{panel_name}_door_casing': (outer_width, outer_height, svg_path)
        }
    
    def generate_casing_panel(self, position: Point, casing_name: str, width: float, height: float, svg_path: str) -> tuple:
        """
        Generate a casing panel from pre-computed SVG path.
        Translates the path to the correct position.
        
        Args:
            position: Position in SVG
            casing_name: Name of the casing piece
            width: Width of the casing piece
            height: Height of the casing piece
            svg_path: Pre-computed SVG path (relative to 0,0)
            
        Returns:
            Tuple of (structural_path, decorative_patterns)
        """
        # Parse the path and translate all coordinates
        import re
        
        # Find all coordinate pairs in the path
        def translate_coords(match):
            x = float(match.group(1)) + position.x
            y = float(match.group(2)) + position.y
            return f"{x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}"
        
        # Replace all coordinate pairs
        translated_path = re.sub(
            r'([-\d.]+),([-\d.]+)',
            translate_coords,
            svg_path
        )
        
        return translated_path, ""
    
    def _generate_chimney_cutout(self, chimney, position: Point) -> str:
        """
        Generate chimney score lines on roof panel to mark footprint location.
        Chimney no longer uses finger joints - just score lines to show where it sits.
        
        Args:
            chimney: Chimney object with position and roof_angle
            position: Position of the roof panel
            
        Returns:
            SVG path string for score lines marking chimney footprint
        """
        import math
        
        # Calculate absolute position of chimney on roof panel
        chimney_x = position.x + chimney.position.x
        chimney_y = position.y + chimney.position.y
        chimney_width = chimney.position.width
        chimney_depth = chimney.position.height  # Depth along roof slope
        
        # Calculate horizontal spacing on roof panel
        # The chimney depth projects onto the roof as: depth / cos(roof_angle)
        horizontal_spacing = chimney_depth / math.cos(math.radians(chimney.roof_angle))
        
        # Generate score line rectangle for chimney footprint
        # This marks where the chimney will sit on the roof
        score_line = (
            f"M {chimney_x:.{COORDINATE_PRECISION}f},{chimney_y:.{COORDINATE_PRECISION}f} "
            f"L {chimney_x + chimney_width:.{COORDINATE_PRECISION}f},{chimney_y:.{COORDINATE_PRECISION}f} "
            f"L {chimney_x + chimney_width:.{COORDINATE_PRECISION}f},{chimney_y + horizontal_spacing:.{COORDINATE_PRECISION}f} "
            f"L {chimney_x:.{COORDINATE_PRECISION}f},{chimney_y + horizontal_spacing:.{COORDINATE_PRECISION}f} Z"
        )
        
        return score_line
    
    def generate_chimney_panel(self, position: Point, chimney, wall_name: str) -> tuple:
        """
        Generate a single chimney wall panel with angled base to sit on sloped roof
        
        For a VERTICAL chimney on a sloped roof at angle θ:
        - Front/back walls (parallel to ridge): NO height variation - RECTANGLES
        - Left/right walls (perpendicular to ridge, along slope): height varies by depth × tan(θ) - TRAPEZOIDS
        
        Args:
            position: Position to place this wall panel in the SVG
            chimney: Chimney object with dimensions and roof_angle
            wall_name: Name of wall ('chimney_front', 'chimney_back', 'chimney_left', 'chimney_right')
            
        Returns:
            Tuple of (structural_path, decorative_patterns)
        """
        panel_dims = chimney.get_panel_dimensions()
        if wall_name not in panel_dims:
            return ("", "")
        
        width, height = panel_dims[wall_name]
        
        # Get chimney footprint depth (along roof slope) from position
        footprint_depth = chimney.position.height  # This is the depth along roof slope
        
        if 'left' in wall_name or 'right' in wall_name:
            # Left/right walls are perpendicular to ridge - trapezoid shape
            # Base edge is angled based on depth along slope
            # Right panel is mirrored version of left panel
            is_mirrored = 'right' in wall_name
            corners = self._generate_angled_base_wall(position, width, height, chimney.roof_angle, footprint_depth, is_mirrored)
        else:
            # Front/back walls parallel to ridge - rectangles with finger joint on bottom
            corners = [
                Point(position.x, position.y),
                Point(position.x + width, position.y),
                Point(position.x + width, position.y + height),
                Point(position.x, position.y + height)
            ]
        
        # Generate simple rectangular path for front/back walls (no finger joints)
        if 'front' in wall_name or 'back' in wall_name:
            # Simple rectangle - no finger joints
            path = f"M {corners[0].x:.{COORDINATE_PRECISION}f},{corners[0].y:.{COORDINATE_PRECISION}f}"
            for i in range(1, len(corners)):
                path += f" L {corners[i].x:.{COORDINATE_PRECISION}f},{corners[i].y:.{COORDINATE_PRECISION}f}"
            path += " Z"
        else:
            # Left/right trapezoids - no finger joints
            path = f"M {corners[0].x:.{COORDINATE_PRECISION}f},{corners[0].y:.{COORDINATE_PRECISION}f}"
            for i in range(1, len(corners)):
                path += f" L {corners[i].x:.{COORDINATE_PRECISION}f},{corners[i].y:.{COORDINATE_PRECISION}f}"
            path += " Z"
        
        # Generate brick pattern for chimney walls
        decorative_pattern = self._generate_chimney_brick_pattern(wall_name, position, width, height, corners)
        
        return path, decorative_pattern
    
    def generate_chimney_casing(self, position: Point, chimney) -> tuple:
        """
        Generate single chimney casing piece with inner cutout
        
        Dimensions from diagram:
        - Outer: (k + 2.3 * thickness) × (l + 3 * thickness)
        - Inner cutout: (k + 0.3 * thickness) × (l + thickness)
        Where k = chimney depth, l = k / cos(roof_angle)
        
        Args:
            position: Position in SVG
            chimney: Chimney object
            
        Returns:
            Tuple of (structural_path, decorative_patterns)
        """
        panel_dims = chimney.get_panel_dimensions()
        if 'chimney_casing' not in panel_dims:
            return ("", "")
        
        outer_width, outer_height = panel_dims['chimney_casing']
        inner_width, inner_height = chimney.get_casing_cutout_dimensions()
        
        # Calculate centered cutout position
        cutout_x = position.x + (outer_width - inner_width) / 2
        cutout_y = position.y + (outer_height - inner_height) / 2
        
        # Generate path with outer perimeter and inner cutout
        path = (
            # Outer perimeter (clockwise)
            f"M {position.x:.{COORDINATE_PRECISION}f},{position.y:.{COORDINATE_PRECISION}f} "
            f"L {position.x + outer_width:.{COORDINATE_PRECISION}f},{position.y:.{COORDINATE_PRECISION}f} "
            f"L {position.x + outer_width:.{COORDINATE_PRECISION}f},{position.y + outer_height:.{COORDINATE_PRECISION}f} "
            f"L {position.x:.{COORDINATE_PRECISION}f},{position.y + outer_height:.{COORDINATE_PRECISION}f} Z "
            # Inner cutout (counter-clockwise to create hole)
            f"M {cutout_x:.{COORDINATE_PRECISION}f},{cutout_y:.{COORDINATE_PRECISION}f} "
            f"L {cutout_x:.{COORDINATE_PRECISION}f},{cutout_y + inner_height:.{COORDINATE_PRECISION}f} "
            f"L {cutout_x + inner_width:.{COORDINATE_PRECISION}f},{cutout_y + inner_height:.{COORDINATE_PRECISION}f} "
            f"L {cutout_x + inner_width:.{COORDINATE_PRECISION}f},{cutout_y:.{COORDINATE_PRECISION}f} Z"
        )
        
        return path, ""
    
    def _generate_angled_base_wall(self, position: Point, width: float, height: float, roof_angle: float, slope_depth: float = None, is_mirrored: bool = False) -> List[Point]:
        """
        Generate corners for a chimney wall with angled base to match roof slope
        
        For a VERTICAL chimney on a sloped roof at angle θ:
        - The height difference is based on how far the wall extends along the slope direction
        - For left/right walls (perpendicular to ridge): height_diff = depth × tan(θ)
        - Right panel is mirrored version of left panel
        
        Args:
            position: Base position
            width: Width of the wall panel
            height: Height of the wall extending above roof
            roof_angle: Roof gable angle in degrees
            slope_depth: Depth of chimney footprint along roof slope (for left/right walls)
            is_mirrored: If True, create mirrored trapezoid (for right panel)
            
        Returns:
            List of corner points for the trapezoid
        """
        import math
        
        # The base needs to be cut at roof_angle to sit flush on sloped roof
        # For left/right walls going along the slope:
        # Height difference = depth along slope × tan(θ)
        theta_rad = math.radians(roof_angle)
        
        if slope_depth is not None:
            # Use the provided slope depth for accurate height difference
            height_diff = slope_depth * math.tan(theta_rad)
        else:
            # Fallback to using width
            height_diff = width * math.tan(theta_rad)
        
        # Create TRAPEZOID: angled base (following roof slope), horizontal top (vertical chimney)
        # For a vertical chimney, the base follows the roof angle but the top is level
        # The left and right edges are VERTICAL (same height: height_diff + height)
        
        if is_mirrored:
            # Right panel: mirror of left - slope goes the opposite direction
            corners = [
                Point(position.x, position.y + height_diff),  # Bottom-left (higher due to mirrored slope)
                Point(position.x + width, position.y),  # Bottom-right (lower due to mirrored slope)
                Point(position.x + width, position.y + height_diff + height),  # Top-right (goes up vertically)
                Point(position.x, position.y + height_diff + height)  # Top-left (at same height as top-right)
            ]
        else:
            # Left panel: standard orientation
            corners = [
                Point(position.x, position.y),  # Bottom-left (starts lower due to slope)
                Point(position.x + width, position.y + height_diff),  # Bottom-right (higher due to slope)
                Point(position.x + width, position.y + height_diff + height),  # Top-right (goes up vertically by height)
                Point(position.x, position.y + height_diff + height)  # Top-left (at same height as top-right - HORIZONTAL top edge!)
            ]
        
        return corners
    
    def _generate_chimney_wall_with_finger_joint(self, corners: List[Point], width: float, height: float, wall_name: str, chimney) -> str:
        """
        Generate chimney front/back wall with centered male finger joint at top edge
        
        Both front and back walls have male joints protruding from their top edges.
        Finger joint length is proportional to chimney width (width/2) for better fit.
        """
        thickness = self.geometry.thickness
        
        # Use chimney width/2 for finger joint length (proportional to chimney size)
        finger_length = chimney.position.width / 2
        
        # Center finger joint on top edge
        joint_start = (width - finger_length) / 2
        joint_end = joint_start + finger_length
        
        bottom_left = corners[0]
        bottom_right = corners[1]
        top_right = corners[2]
        top_left = corners[3]
        
        if 'front' in wall_name:
            # Front wall: Male joint at TOP edge (protrudes upward)
            path = f"M {bottom_left.x:.{COORDINATE_PRECISION}f},{bottom_left.y:.{COORDINATE_PRECISION}f} "
            # Bottom edge
            path += f"L {bottom_right.x:.{COORDINATE_PRECISION}f},{bottom_right.y:.{COORDINATE_PRECISION}f} "
            # Right edge up
            path += f"L {top_right.x:.{COORDINATE_PRECISION}f},{top_right.y:.{COORDINATE_PRECISION}f} "
            # Top edge to joint start
            path += f"L {top_right.x - joint_start:.{COORDINATE_PRECISION}f},{top_right.y:.{COORDINATE_PRECISION}f} "
            # Male joint protrudes UP
            path += f"L {top_right.x - joint_start:.{COORDINATE_PRECISION}f},{top_right.y + thickness:.{COORDINATE_PRECISION}f} "
            # Across joint
            path += f"L {top_right.x - joint_end:.{COORDINATE_PRECISION}f},{top_right.y + thickness:.{COORDINATE_PRECISION}f} "
            # Back down
            path += f"L {top_right.x - joint_end:.{COORDINATE_PRECISION}f},{top_right.y:.{COORDINATE_PRECISION}f} "
            # Continue to top left
            path += f"L {top_left.x:.{COORDINATE_PRECISION}f},{top_left.y:.{COORDINATE_PRECISION}f} "
            # Left edge down
            path += "Z"
        else:
            # Back wall: Male joint at TOP edge (protrudes upward like front)
            path = f"M {bottom_left.x:.{COORDINATE_PRECISION}f},{bottom_left.y:.{COORDINATE_PRECISION}f} "
            # Bottom edge
            path += f"L {bottom_right.x:.{COORDINATE_PRECISION}f},{bottom_right.y:.{COORDINATE_PRECISION}f} "
            # Right edge up
            path += f"L {top_right.x:.{COORDINATE_PRECISION}f},{top_right.y:.{COORDINATE_PRECISION}f} "
            # Top edge to joint start
            path += f"L {top_right.x - joint_start:.{COORDINATE_PRECISION}f},{top_right.y:.{COORDINATE_PRECISION}f} "
            # Male joint protrudes UP
            path += f"L {top_right.x - joint_start:.{COORDINATE_PRECISION}f},{top_right.y + thickness:.{COORDINATE_PRECISION}f} "
            # Across joint
            path += f"L {top_right.x - joint_end:.{COORDINATE_PRECISION}f},{top_right.y + thickness:.{COORDINATE_PRECISION}f} "
            # Back down
            path += f"L {top_right.x - joint_end:.{COORDINATE_PRECISION}f},{top_right.y:.{COORDINATE_PRECISION}f} "
            # Continue to top left
            path += f"L {top_left.x:.{COORDINATE_PRECISION}f},{top_left.y:.{COORDINATE_PRECISION}f} "
            # Left edge down
            path += "Z"
        
        return path
    
    def _generate_chimney_brick_pattern(self, wall_name: str, position: Point, width: float, height: float, corners: List[Point]) -> str:
        """
        Generate brick pattern for chimney panels with 0.1mm line width
        Properly fills trapezoid from bottom sloped edge to top, and rectangles completely
        
        Args:
            position: Base position of the panel
            width: Width of the panel
            height: Height of the panel (for trapezoid, this is the maximum height)
            corners: Corner points of the panel (for trapezoid boundaries)
            
        Returns:
            SVG path string for brick pattern
        """
        
        margin = 0.8  # Margin to avoid touching panel edges
        
        lines = []
        
        # Brick dimensions
        brick_height = 2.5  # 2.5mm brick height
        brick_width = brick_height * 2.5
        
        # Determine if this is a trapezoid panel
        # Check if top edge (corners[0] to corners[1]) is diagonal (Y values differ)
        if len(corners) == 4:
            is_trapezoid = abs(corners[0].y - corners[1].y) > 0.01
        else:
            is_trapezoid = False
        
        if is_trapezoid:
            # Detect if this is a mirrored trapezoid (right panel) by checking if slope goes opposite direction
            # Standard: corners[0].y < corners[1].y (left edge lower, right edge higher)
            # Mirrored: corners[0].y > corners[1].y (left edge higher, right edge lower)
            is_mirrored = corners[0].y > corners[1].y
            
            # CRITICAL: Use actual corner Y values, NOT the height parameter
            # The height parameter doesn't include height_diff from slope
            y_min = min(c.y for c in corners)  # Top of shape
            y_max = max(c.y for c in corners)  # Bottom of shape - THIS IS THE ACTUAL MAX Y
            
            if is_mirrored:
                # Mirrored trapezoid (right panel): corners[1].y < corners[0].y
                # Diagonal is on LEFT side, vertical is on RIGHT side
                slope_end_y = corners[0].y  # Where diagonal ends (higher Y)
                
                def get_bounds_at_y(y_pos):
                    """Get left and right X bounds at given Y position for mirrored trapezoid"""
                    if y_pos <= slope_end_y:
                        # In sloped region: left edge is diagonal, right edge is vertical
                        # Interpolate left edge from corners[1] to corners[0]
                        if slope_end_y > corners[1].y:
                            t = (y_pos - corners[1].y) / (slope_end_y - corners[1].y)
                        else:
                            t = 0.0
                        left_x = corners[1].x + t * (corners[0].x - corners[1].x)  # Interpolate left
                        right_x = corners[1].x  # Right is always at same X
                    else:
                        # In rectangular region: both edges are vertical
                        left_x = corners[3].x  # Bottom-left X
                        right_x = corners[2].x  # Bottom-right X
                    return left_x, right_x
            else:
                # Standard trapezoid (left panel): corners[0].y < corners[1].y
                # Diagonal is on RIGHT side, vertical is on LEFT side
                slope_end_y = corners[1].y  # Where diagonal ends
                
                def get_bounds_at_y(y_pos):
                    """Get left and right X bounds at given Y position for standard trapezoid"""
                    if y_pos <= slope_end_y:
                        # In sloped region: left edge is vertical, right edge is diagonal
                        # Interpolate right edge from corners[0] to corners[1]
                        if slope_end_y > corners[0].y:
                            t = (y_pos - corners[0].y) / (slope_end_y - corners[0].y)
                        else:
                            t = 0.0
                        left_x = corners[0].x  # Left is always at same X
                        right_x = corners[0].x + t * (corners[1].x - corners[0].x)  # Interpolate right
                    else:
                        # In rectangular region: both edges are vertical
                        left_x = corners[3].x  # Bottom-left X
                        right_x = corners[2].x  # Bottom-right X
                    return left_x, right_x
        else:
            # Rectangle
            y_min = position.y
            y_max = position.y + height
            
            def get_bounds_at_y(y_pos):
                """Get left and right X bounds (constant for rectangle)"""
                return position.x, position.x + width
        
        # Start from top (smallest Y) with margin
        y = y_min + margin
        y_end = y_max - margin
        row = 0
        
        
        # Fill entire height from bottom to top
        while y < y_end:
            # Get bounds at current Y
            left_x, right_x = get_bounds_at_y(y)
            row_start_x = left_x + margin
            row_end_x = right_x - margin
            row_width = row_end_x - row_start_x
            
            # Calculate next row Y first
            next_y = min(y + brick_height, y_end)
            
            # Skip drawing if too narrow, but always advance Y
            # UNLESS we're very close to y_end (within one brick_height)
            if row_width < brick_width * 0.3:
                if y_end - y > brick_height:  # Still have significant distance to go
                    y += brick_height
                    row += 1
                    continue
                else:  # Close to end, break out to avoid getting stuck
                    break
            
            # Get bounds at next Y for proper clipping
            left_x_next, right_x_next = get_bounds_at_y(next_y)
            row_start_x_next = left_x_next + margin
            row_end_x_next = right_x_next - margin
            
            # Draw horizontal mortar line at current Y (clipped to current width)
            lines.append(f"M {row_start_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                        f"L {row_end_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")
            
            # Offset for brick bond pattern
            x_offset = (brick_width / 2) if row % 2 == 1 else 0
            x = row_start_x + x_offset
            
            # Draw vertical mortar lines - these may be angled for trapezoids
            first_brick_x = x  # Remember first position
            brick_num = 0
            while x < row_end_x:
                # Draw vertical line for all bricks EXCEPT at the very first position (left edge)
                # AND the very last position (right edge)
                if x > first_brick_x + 0.1 and x < row_end_x - 0.1:
                    # For vertical line, clip to bounds at both Y levels
                    x_bottom = x  # X at current level
                    
                    # Clip to bounds at next level
                    if x_bottom < row_start_x_next:
                        x_bottom = row_start_x_next
                    if x_bottom > row_end_x_next:
                        x_bottom = row_end_x_next
                    
                    # Only draw if within bounds at both levels
                    if row_start_x <= x <= row_end_x and row_start_x_next <= x_bottom <= row_end_x_next:
                        lines.append(f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                                    f"L {x_bottom:.{COORDINATE_PRECISION}f},{next_y:.{COORDINATE_PRECISION}f}")
                
                x += brick_width
                brick_num += 1
            
            y = next_y
            row += 1
        
        # Add final horizontal line at bottom (clipped)
        if lines:
            left_x_bottom, right_x_bottom = get_bounds_at_y(y_end)
            bottom_start_x = left_x_bottom + margin
            bottom_end_x = right_x_bottom - margin
            
            if bottom_end_x > bottom_start_x + 0.1:
                lines.append(f"M {bottom_start_x:.{COORDINATE_PRECISION}f},{y_end:.{COORDINATE_PRECISION}f} "
                            f"L {bottom_end_x:.{COORDINATE_PRECISION}f},{y_end:.{COORDINATE_PRECISION}f}")
        
        return " ".join(lines)
    
    def _generate_roof_shingles_pattern(self, position: Point, width: float, height: float) -> str:
        """
        Generate shingles pattern for roof panels with 0.1mm line width
        Supports multiple shingle types based on configuration
        
        Args:
            position: Base position of the roof panel
            width: Width of the roof panel
            height: Height of the roof panel
            
        Returns:
            SVG path string for shingles pattern
        """
        from .architectural_components import ShingleType
        
        # Get shingle type from architectural config, default to standard shingles
        shingle_type = ShingleType.SHINGLES
        if self.architectural_config and hasattr(self.architectural_config, 'shingle_type'):
            shingle_type = self.architectural_config.shingle_type
        
        # Generate pattern based on shingle type
        if shingle_type == ShingleType.SPANTILE:
            return self._generate_spantile_pattern(position, width, height)
        elif shingle_type == ShingleType.SPANISH:
            return self._generate_spanish_tile_pattern(position, width, height)
        elif shingle_type == ShingleType.SCALLOPS:
            return self._generate_scallop_pattern(position, width, height)
        elif shingle_type == ShingleType.S_TILE:
            return self._generate_s_tile_pattern(position, width, height)
        else:  # ShingleType.SHINGLES (default)
            return self._generate_standard_shingles_pattern(position, width, height)
    
    def _generate_standard_shingles_pattern(self, position: Point, width: float, height: float) -> str:
        """Generate standard rectangular shingles pattern"""
        margin = 0.8
        lines = []
        
        shingle_height = 4.0
        shingle_width = 8.0
        overlap = 1.5
        
        y = position.y + margin
        y_end = position.y + height - margin
        row = 0
        
        while y < y_end:
            next_y = min(y + shingle_height - overlap, y_end)
            
            row_start_x = position.x + margin
            row_end_x = position.x + width - margin
            
            # Horizontal line
            lines.append(f"M {row_start_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                        f"L {row_end_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")
            
            # Vertical lines with offset
            x_offset = (shingle_width / 2) if row % 2 == 1 else 0
            x = row_start_x + x_offset
            
            while x < row_end_x - 0.1:
                if x > row_start_x + 0.1:
                    line_end_y = min(y + shingle_height, y_end)
                    lines.append(f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                                f"L {x:.{COORDINATE_PRECISION}f},{line_end_y:.{COORDINATE_PRECISION}f}")
                x += shingle_width
            
            y = next_y
            row += 1
        
        return " ".join(lines)
    
    def _generate_spantile_pattern(self, position: Point, width: float, height: float) -> str:
        """Generate Spanish tile (Spantile) pattern with wavy curves"""
        margin = 0.8
        lines = []
        
        tile_height = 5.0  # Height of each tile row
        tile_width = 6.0   # Width of individual tiles
        
        y = position.y + margin
        y_end = position.y + height - margin
        row = 0
        
        while y < y_end:
            row_start_x = position.x + margin
            row_end_x = position.x + width - margin
            
            # Wavy horizontal line using quadratic curves
            x = row_start_x
            path_parts = [f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}"]
            
            while x < row_end_x:
                next_x = min(x + tile_width, row_end_x)
                mid_x = (x + next_x) / 2
                # Create wave with control point above the line
                path_parts.append(f" Q {mid_x:.{COORDINATE_PRECISION}f},{y - 1.5:.{COORDINATE_PRECISION}f} {next_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")
                x = next_x
            
            lines.append("".join(path_parts))
            
            y += tile_height
            row += 1
        
        return " ".join(lines)
    
    def _generate_spanish_tile_pattern(self, position: Point, width: float, height: float) -> str:
        """Generate Spanish tile pattern with rounded edges"""
        margin = 0.8
        lines = []
        
        tile_height = 5.0
        tile_width = 7.0
        
        y = position.y + margin
        y_end = position.y + height - margin
        row = 0
        
        while y < y_end:
            row_start_x = position.x + margin
            row_end_x = position.x + width - margin
            
            # Horizontal line
            lines.append(f"M {row_start_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                        f"L {row_end_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")
            
            # Rounded vertical separators
            x_offset = (tile_width / 2) if row % 2 == 1 else 0
            x = row_start_x + x_offset
            
            while x < row_end_x - 0.1:
                if x > row_start_x + 0.1:
                    # Curved vertical line for tile edge
                    curve_y = min(y + tile_height, y_end)
                    mid_y = (y + curve_y) / 2
                    lines.append(f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                                f"Q {x + 0.5:.{COORDINATE_PRECISION}f},{mid_y:.{COORDINATE_PRECISION}f} "
                                f"{x:.{COORDINATE_PRECISION}f},{curve_y:.{COORDINATE_PRECISION}f}")
                x += tile_width
            
            y += tile_height
            row += 1
        
        return " ".join(lines)
    
    def _generate_scallop_pattern(self, position: Point, width: float, height: float) -> str:
        """Generate scalloped/fish-scale shingles pattern"""
        margin = 0.8
        lines = []
        
        scale_height = 4.0  # Height of each scallop row
        scale_width = 5.0   # Width of individual scallops
        overlap = 2.0       # Vertical overlap
        
        y = position.y + margin
        y_end = position.y + height - margin
        row = 0
        
        while y < y_end:
            row_start_x = position.x + margin
            row_end_x = position.x + width - margin
            
            # Offset every other row
            x_offset = (scale_width / 2) if row % 2 == 1 else 0
            x = row_start_x + x_offset
            
            # Draw scalloped bottom edges for each scale
            while x < row_end_x:
                next_x = min(x + scale_width, row_end_x)
                if next_x - x > scale_width * 0.3:  # Only draw if wide enough
                    mid_x = (x + next_x) / 2
                    curve_y = min(y + scale_height, y_end)
                    # Scallop curve pointing down
                    lines.append(f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                                f"Q {mid_x:.{COORDINATE_PRECISION}f},{curve_y:.{COORDINATE_PRECISION}f} "
                                f"{next_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")
                x += scale_width
            
            y += scale_height - overlap
            row += 1
        
        return " ".join(lines)
    
    def _generate_s_tile_pattern(self, position: Point, width: float, height: float) -> str:
        """Generate S-shaped tiles pattern with alternating curves"""
        margin = 0.8
        lines = []
        
        tile_height = 5.0
        tile_width = 6.0
        
        y = position.y + margin
        y_end = position.y + height - margin
        row = 0
        
        while y < y_end:
            row_start_x = position.x + margin
            row_end_x = position.x + width - margin
            
            # S-shaped curves
            x = row_start_x
            while x < row_end_x:
                next_x = min(x + tile_width, row_end_x)
                if next_x - x > tile_width * 0.3:
                    mid_x = (x + next_x) / 2
                    curve_y = min(y + tile_height, y_end)
                    mid_y = (y + curve_y) / 2
                    
                    # S-curve: up then down (or down then up for alternating rows)
                    if row % 2 == 0:
                        lines.append(f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                                    f"Q {x:.{COORDINATE_PRECISION}f},{mid_y:.{COORDINATE_PRECISION}f} "
                                    f"{mid_x:.{COORDINATE_PRECISION}f},{mid_y:.{COORDINATE_PRECISION}f} "
                                    f"Q {next_x:.{COORDINATE_PRECISION}f},{mid_y:.{COORDINATE_PRECISION}f} "
                                    f"{next_x:.{COORDINATE_PRECISION}f},{curve_y:.{COORDINATE_PRECISION}f}")
                    else:
                        lines.append(f"M {x:.{COORDINATE_PRECISION}f},{curve_y:.{COORDINATE_PRECISION}f} "
                                    f"Q {x:.{COORDINATE_PRECISION}f},{mid_y:.{COORDINATE_PRECISION}f} "
                                    f"{mid_x:.{COORDINATE_PRECISION}f},{mid_y:.{COORDINATE_PRECISION}f} "
                                    f"Q {next_x:.{COORDINATE_PRECISION}f},{mid_y:.{COORDINATE_PRECISION}f} "
                                    f"{next_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")
                x += tile_width
            
            y += tile_height
            row += 1
        
        return " ".join(lines)
    
    def generate_panel_info(self, panel_name: str, corners: List[Point], edge_names: List[str]) -> Dict:
        """
        Generate information about the joints that would be created for a panel
        
        Returns:
            Dictionary with detailed joint information for analysis
        """
        info = {
            'panel_name': panel_name,
            'edges': {}
        }
        
        for i, edge_name in enumerate(edge_names):
            start_corner = corners[i]
            end_corner = corners[(i + 1) % len(corners)]
            
            # Calculate edge length
            dx = end_corner.x - start_corner.x
            dy = end_corner.y - start_corner.y
            edge_length = (dx * dx + dy * dy) ** 0.5
            
            # Get joint information
            joint_info = self.multi_joint_generator.get_joint_info_for_edge(edge_length)
            joint_info['edge_name'] = edge_name
            
            info['edges'][edge_name] = joint_info
        
        return info


def generate_internal_female_cutout(self, center_x: float, center_y: float,
                                  orientation: str = 'horizontal') -> str:
    """
    Generate internal female cutout (preserve existing functionality)
    """
    half_length = self.cutout_length / 2
    half_thickness = self.cutout_thickness / 2
    
    if orientation == 'horizontal':
        return (f"M {center_x - half_length:.{COORDINATE_PRECISION}f},"
               f"{center_y - half_thickness:.{COORDINATE_PRECISION}f} "
               f"L {center_x + half_length:.{COORDINATE_PRECISION}f},"
               f"{center_y - half_thickness:.{COORDINATE_PRECISION}f} "
               f"L {center_x + half_length:.{COORDINATE_PRECISION}f},"
               f"{center_y + half_thickness:.{COORDINATE_PRECISION}f} "
               f"L {center_x - half_length:.{COORDINATE_PRECISION}f},"
               f"{center_y + half_thickness:.{COORDINATE_PRECISION}f} Z")
    else:
        return (f"M {center_x - half_thickness:.{COORDINATE_PRECISION}f},"
               f"{center_y - half_length:.{COORDINATE_PRECISION}f} "
               f"L {center_x + half_thickness:.{COORDINATE_PRECISION}f},"
               f"{center_y - half_length:.{COORDINATE_PRECISION}f} "
               f"L {center_x + half_thickness:.{COORDINATE_PRECISION}f},"
               f"{center_y + half_length:.{COORDINATE_PRECISION}f} "
               f"L {center_x - half_thickness:.{COORDINATE_PRECISION}f},"
               f"{center_y + half_length:.{COORDINATE_PRECISION}f} Z")

# Add the missing method to the class
MultiFingerJointGenerator.generate_internal_female_cutout = generate_internal_female_cutout