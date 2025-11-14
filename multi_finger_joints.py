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
        return self._generate_panel_with_multi_joints(roof_type, position, corners, edge_names)
    
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
        """Generate internal cutouts (preserve existing functionality)"""
        cutout_paths = []
        
        if panel_name.startswith('roof_panel'):
            roof_panel_length = self.geometry.get_roof_panel_length()
            base_roof_width = self.geometry.base_roof_width
            
            if panel_name == 'roof_panel_left':
                cutout_center_y = position.y + (base_roof_width / 2) + self.geometry.thickness
            elif panel_name == 'roof_panel_right':
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
        
        # Get decorative patterns for this panel
        panel_dims = self.geometry.get_panel_dimensions().get(panel_name)
        if panel_dims:
            pattern = self.architectural_config.get_pattern_for_panel(panel_name)
            if pattern:
                decorative_patterns.append(pattern)
        
        return " ".join(structural_cutouts), " ".join(decorative_patterns)
    
    def _generate_window_cutout(self, window, position: Point) -> str:
        """Generate SVG path for a window cutout"""
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
        """Generate SVG path for a door cutout"""
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