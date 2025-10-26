"""
Geometric calculations for house box components
Based on the detailed specification diagrams provided
"""

import math
from typing import Dict, Tuple, List, NamedTuple
from .constants import DEGREES_TO_RADIANS, COORDINATE_PRECISION, ANGLE_PRECISION
from .exceptions import GeometryError, DimensionError


class Point(NamedTuple):
    """2D point with x, y coordinates"""
    x: float
    y: float

    def __str__(self):
        return f"{self.x:.{COORDINATE_PRECISION}f},{self.y:.{COORDINATE_PRECISION}f}"


class HouseGeometry:
    """
    Core geometric calculations for house box based on specification diagrams
    
    Key relationships from diagrams:
    - x: length dimension
    - y: width dimension  
    - z: height dimension (wall height)
    - θ (theta): gable angle in degrees
    - w: material thickness
    - l: finger joint length
    """
    
    def __init__(self, x: float, y: float, z: float, theta: float, 
                 thickness: float, finger_length: float, kerf: float = 0.0):
        """
        Initialize house geometry with base dimensions
        
        Args:
            x: Length dimension (side wall width, floor length)
            y: Width dimension (gable wall width, floor width) 
            z: Height dimension (wall height to start of gable)
            theta: Gable angle in degrees
            thickness: Material thickness (w)
            finger_length: Finger joint length (l)
            kerf: Laser kerf compensation
        """
        self.x = x
        self.y = y  
        self.z = z
        self.theta = theta
        self.thickness = thickness
        self.finger_length = finger_length
        self.kerf = kerf
        
        # Convert angle to radians for calculations
        self.theta_rad = theta * DEGREES_TO_RADIANS
        
        # Calculate derived dimensions
        self._calculate_derived_dimensions()
    
    def _calculate_derived_dimensions(self):
        """Calculate all derived dimensions from base parameters"""
        # Gable geometry (from specification diagrams)
        self.gable_peak_height = (self.y / 2) * math.tan(self.theta_rad)
        self.total_gable_height = self.z + self.gable_peak_height
        
        # Roof panel dimensions
        self.roof_panel_length = self.x + 6 * self.thickness  # House length + 6*thickness
        
        # Base roof width calculation - stored for reuse (calculated from gable geometry)
        self.base_roof_width = (self.y / 2) / math.cos(self.theta_rad)
        
        # Asymmetric roof panel widths as requested
        self.roof_panel_left_width = self.base_roof_width + 4 * self.thickness   # Left: +4*thickness
        self.roof_panel_right_width = self.base_roof_width + 3 * self.thickness  # Right: +3*thickness
                
        # Apply kerf compensation to all dimensions
        if self.kerf > 0:
            self.x_kerf = self.x + self.kerf
            self.y_kerf = self.y + self.kerf
            self.z_kerf = self.z + self.kerf
            self.roof_panel_left_width_kerf = self.roof_panel_left_width + self.kerf
            self.roof_panel_right_width_kerf = self.roof_panel_right_width + self.kerf
        else:
            self.x_kerf = self.x
            self.y_kerf = self.y
            self.z_kerf = self.z
            self.roof_panel_left_width_kerf = self.roof_panel_left_width
            self.roof_panel_right_width_kerf = self.roof_panel_right_width
    
    @property
    def length(self) -> float:
        """House length (x dimension)"""
        return self.x
    
    @property
    def width(self) -> float:
        """House width (y dimension)"""
        return self.y
    
    @property
    def height(self) -> float:
        """House height (z dimension)"""
        return self.z
    
    def get_gable_peak_height(self) -> float:
        """Get the height of the gable peak above the wall"""
        return self.gable_peak_height
    
    def get_roof_panel_left_width(self) -> float:
        """Get the width of left roof panel"""
        return self.roof_panel_left_width_kerf
        
    def get_roof_panel_right_width(self) -> float:
        """Get the width of right roof panel"""
        return self.roof_panel_right_width_kerf
    
    def get_roof_panel_length(self) -> float:
        """Get the length of roof panels"""
        return self.roof_panel_length
    
    def get_panel_dimensions(self) -> Dict[str, Tuple[float, float]]:
        """
        Get dimensions for all house panels
        
        Returns:
            Dict mapping panel names to (width, height) tuples
        """
        return {
            'floor': (self.x_kerf, self.y_kerf),
            'side_wall_left': (self.x_kerf, self.z_kerf),
            'side_wall_right': (self.x_kerf, self.z_kerf),
            'gable_wall_front': (self.y_kerf + 2 * self.thickness, self.total_gable_height),
            'gable_wall_back': (self.y_kerf + 2 * self.thickness, self.total_gable_height),
            'roof_panel_left': (self.roof_panel_length, self.roof_panel_left_width_kerf),
            'roof_panel_right': (self.roof_panel_length, self.roof_panel_right_width_kerf)
        }
    
    def get_gable_profile_points(self, width: float, base_height: float) -> List[Point]:
        """
        Get the points defining the gable wall profile (house shape)
        
        Args:
            width: Gable wall width (y dimension)
            base_height: Height to start of triangular gable (z dimension)
            
        Returns:
            List of points defining the gable outline
        """
        peak_height = (width / 2) * math.tan(self.theta_rad)
        total_height = base_height + peak_height
        
        # Define gable profile points (clockwise from bottom-left)
        points = [
            Point(0, 0),                           # Bottom-left corner
            Point(width, 0),                       # Bottom-right corner  
            Point(width, base_height),             # Top-right of rectangular part
            Point(width / 2, total_height),       # Peak of gable
            Point(0, base_height),                # Top-left of rectangular part
            Point(0, 0)                           # Close the path
        ]
        
        return points
    
    def calculate_finger_joint_positions(self, edge_length: float, 
                                       is_male: bool = True) -> List[Tuple[float, float]]:
        """
        Calculate finger joint positions along an edge
        
        Args:
            edge_length: Length of the edge to place joints on
            is_male: True for male joints (tabs), False for female joints (holes)
            
        Returns:
            List of (start, end) positions for each finger joint
        """
        if edge_length <= 2 * self.finger_length:
            raise GeometryError("finger_joint_calculation", 
                              f"Edge too short ({edge_length}) for finger joints")
        
        # Calculate number of fingers that fit
        num_fingers = int(edge_length // self.finger_length)
        if num_fingers % 2 == 0:
            num_fingers -= 1  # Ensure odd number for symmetry
        
        # Calculate actual finger and gap sizes for even distribution
        finger_size = edge_length / num_fingers
        
        positions = []
        for i in range(num_fingers):
            start = i * finger_size
            end = start + finger_size
            
            # Alternate between male and female joints
            joint_is_male = (i % 2 == 0) if is_male else (i % 2 == 1)
            
            if joint_is_male:
                positions.append((start, end))
        
        return positions
    
    def get_finger_joint_configuration(self) -> Dict[str, Dict[str, any]]:
        """
        Get finger joint configuration for all panel edges
        
        Extended configuration supporting three states:
        - True: Male joint (tab extending outward)
        - False: Female joint (slot/gap inward)
        - None: No joint (smooth edge)
        
        Based on user feedback and corrected edge adjacency analysis:
        - Floor: ALL MALE joints (provides tabs to all walls)
        - Side walls: Mixed (bottom=female, sides=female, top=smooth)
        - Gable walls: Mixed (bottom=female, sides=male, roof_edges=male)
        - Roof panels: Differentiated edge joints + internal cutouts
        
        Returns:
            Dict mapping panel names to edge configurations
        """
        return {
            'floor': {
                'bottom': True,  # Male joint to gable_wall_front (using consistent naming)
                'right': True,   # Male joint to side_wall_right
                'top': True,     # Male joint to gable_wall_back
                'left': True     # Male joint to side_wall_left
            },
            'side_wall_left': {
                'bottom': False, # Female joint from floor
                'right': True,   # Male joint from gable_wall_front
                'top': None,     # No joint (smooth edge where roof sits)
                'left': True     # Male joint from gable_wall_back
            },
            'side_wall_right': {
                'bottom': False, # Female joint from floor
                'right': True,   # Male joint from gable_wall_back
                'top': None,     # No joint (smooth edge where roof sits)
                'left': True     # Male joint from gable_wall_front
            },
            'gable_wall_front': {
                'bottom': False,    # Female joint from floor
                'right': False,     # female joint to side_wall_right
                'roof_right': True, # Male joint to roof_panel_right
                'roof_left': True,  # Male joint to roof_panel_left
                'left': False       # female joint to side_wall_left
            },
            'gable_wall_back': {
                'bottom': False,    # Female joint from floor
                'right': False,     # female joint to side_wall_left (back connection)
                'roof_right': True, # Male joint to roof_panel_right
                'roof_left': True,  # Male joint to roof_panel_left
                'left': False       # female joint to side_wall_right (back connection)
            },
            'roof_panel_left': {
                'gable_edge': False,  # Female joint from gable walls
                'left': None,         # No joint (smooth edge)
                'outer': None,        # No joint (smooth edge)
                'right': None,        # No joint (smooth edge)
                'internal_cutouts': ['vertical', 'vertical']  # Two vertical female cutouts
            },
            'roof_panel_right': {
                'gable_edge': True,   # Male joint (differentiated from left panel)
                'left': None,         # No joint (smooth edge)
                'outer': None,        # No joint (smooth edge)
                'right': None,        # No joint (smooth edge)
                'internal_cutouts': ['vertical', 'vertical']  # Two vertical female cutouts
            }
        }
    
    def validate_geometry(self):
        """Validate that all geometric calculations are reasonable"""
        if self.gable_peak_height <= 0:
            raise GeometryError("gable_calculation", "Gable peak height must be positive")
            
        if self.roof_panel_left_width <= 0 or self.roof_panel_right_width <= 0:
            raise GeometryError("roof_calculation", "Roof panel widths must be positive")
            
        if self.total_gable_height > 5 * max(self.x, self.y, self.z):
            raise GeometryError("proportions", "House geometry is unreasonably tall")
            
        # Validate finger joint feasibility
        min_edge = min(self.x, self.y, self.z)
        if self.finger_length > min_edge / 3:
            raise GeometryError("finger_joints", 
                              f"Finger joints too large ({self.finger_length}) for smallest edge ({min_edge})")


def calculate_rotated_bounding_box(width: float, height: float, angle_degrees: float) -> Tuple[float, float]:
    """Calculate the bounding box dimensions after rotation"""
    import math
    angle_rad = math.radians(abs(angle_degrees))
    cos_a = abs(math.cos(angle_rad))
    sin_a = abs(math.sin(angle_rad))
    
    # Rotated bounding box dimensions
    new_width = width * cos_a + height * sin_a
    new_height = width * sin_a + height * cos_a
    
    return new_width, new_height


def calculate_rotated_layout_positions(geometry: HouseGeometry, spacing: float) -> Dict[str, Tuple[Point, float]]:
    """
    Calculate rotated layout positions as shown in the example SVG
    
    Layout pattern:
    1. Roof panels rotated at ±(90-θ) angles aligned to gable roof lines
    2. Floor panel rotated -90° and positioned under gable wall front
    3. Side walls rotated ±90° and positioned next to floor panel sides
    4. Gable wall front rotated 180° at top
    5. Gable wall back positioned at bottom
    
    Args:
        geometry: HouseGeometry instance with calculated dimensions
        spacing: Minimum spacing between panels
        
    Returns:
        Dict mapping panel names to (Point position, rotation_angle) tuples
    """
    panel_dims = geometry.get_panel_dimensions()
    
    # Calculate rotation angles
    roof_angle = 90 - geometry.theta  # (90-θ) for roof panels
    
    positions = {}
    
    # Start with gable wall front at top (rotated 180°)
    gable_front_width, gable_front_height = panel_dims['gable_wall_front']
    gable_front_x = spacing
    gable_front_y = spacing
    positions['gable_wall_front'] = (Point(gable_front_x, gable_front_y), 180.0)
    
    # Roof panels positioned next to gable wall front, aligned to roof lines
    roof_width, roof_height = panel_dims['roof_panel_left']
    
    # Calculate rotated roof panel dimensions
    roof_left_bbox_w, roof_left_bbox_h = calculate_rotated_bounding_box(roof_width, roof_height, roof_angle)
    roof_right_bbox_w, roof_right_bbox_h = calculate_rotated_bounding_box(roof_width, roof_height, -roof_angle)
    
    # Position roof panel left (rotated -(90-θ)) - aligned to left roof line
    roof_left_x = gable_front_x - roof_left_bbox_w - spacing
    roof_left_y = gable_front_y + spacing
    positions['roof_panel_left'] = (Point(roof_left_x, roof_left_y), roof_angle)
    
    # Position roof panel right (rotated +(90-θ)) - aligned to right roof line
    roof_right_x = gable_front_x + gable_front_width + spacing
    roof_right_y = gable_front_y + spacing
    positions['roof_panel_right'] = (Point(roof_right_x, roof_right_y), -roof_angle)
    
    # Floor panel rotated -90° positioned in second row
    floor_width, floor_height = panel_dims['floor']
    # After -90° rotation, floor dimensions swap
    floor_rotated_width = floor_height
    floor_rotated_height = floor_width
    
    # Position floor in second row with better spacing
    floor_x = gable_front_x  # More left margin to avoid overlap
    floor_y = gable_front_y + gable_front_height + spacing * 3  # More downward spacing
    positions['floor'] = (Point(floor_x, floor_y), -90.0)
    
    # Side walls rotated ±90° positioned next to floor with better spacing
    side_wall_width, side_wall_height = panel_dims['side_wall_left']
    # After ±90° rotation, dimensions swap
    side_wall_rotated_width = side_wall_height
    side_wall_rotated_height = side_wall_width
    
    # Side wall left (rotated -90°, positioned to left of floor)
    side_left_x = floor_x - side_wall_rotated_width - spacing * 2  # More spacing
    side_left_y = floor_y + (floor_rotated_height - side_wall_rotated_height)
    positions['side_wall_left'] = (Point(side_left_x, side_left_y), 90.0)
    
    # Side wall right (rotated +90°, positioned to right of floor)
    side_right_x = floor_x + floor_rotated_width + spacing * 2  # More spacing
    side_right_y = floor_y + (floor_rotated_height - side_wall_rotated_height)
    positions['side_wall_right'] = (Point(side_right_x, side_right_y), -90.0)
    
    # Gable wall back positioned under floor
    gable_back_width, gable_back_height = panel_dims['gable_wall_back']
    gable_back_x = floor_x + (floor_rotated_width - gable_back_width) / 2
    gable_back_y = floor_y + floor_rotated_height + spacing * 2  # More spacing
    positions['gable_wall_back'] = (Point(gable_back_x, gable_back_y), 0.0)
    
    return positions


def calculate_layout_positions(geometry: HouseGeometry, spacing: float,
                             material_width: float = 457.2, material_height: float = 304.8) -> Dict[str, Point]:
    """
    Calculate optimal 2D rectangular packing layout with configurable material constraints
    
    Implements proper 2D packing algorithm that respects user-defined material size.
    Width is a hard constraint, but height can extend across multiple sheets.
    
    Args:
        geometry: HouseGeometry instance with calculated dimensions
        spacing: Minimum spacing between panels
        material_width: Material width constraint in mm (default: 18 inches = 457.2mm)
        material_height: Material height reference in mm (default: 12 inches = 304.8mm, not a hard limit)
        
    Returns:
        Dict mapping panel names to Point positions (top-left corner)
    """
    panel_dims = geometry.get_panel_dimensions()
    
    # Material constraints - 18×12 inches default, landscape orientation
    MATERIAL_WIDTH = material_width   # Hard constraint - cannot exceed this width
    MATERIAL_HEIGHT = material_height # Soft constraint - can use multiple sheets if needed
    
    # Minimal spacing for efficient packing
    min_spacing = max(spacing, 2.0)  # 2mm minimum spacing
    
    
    # Get all panel dimensions (all rectangular, no rotations)
    panels = {}
    for panel_name, (width, height) in panel_dims.items():
        panels[panel_name] = {'width': width, 'height': height, 'area': width * height}
        
        # Check if any single panel exceeds material WIDTH constraint (height can extend)
        if width > MATERIAL_WIDTH:
            raise GeometryError("layout_constraints", f"Panel {panel_name} width ({width:.1f}mm) exceeds material width ({MATERIAL_WIDTH:.1f}mm)")
    
    # Sort panels by height first (tallest first), then by area - better for 2D packing
    sorted_panels = sorted(panels.items(), key=lambda x: (x[1]['height'], x[1]['area']), reverse=True)
    
    # 2D rectangular packing algorithm with material constraints
    positions = {}
    placed_rects = []  # List of (x, y, width, height) for collision detection
    
    for panel_name, panel_info in sorted_panels:
        width, height = panel_info['width'], panel_info['height']
        
        # Find best position for this panel within material WIDTH constraint only
        best_pos = _find_best_position_2d(width, height, placed_rects, min_spacing,
                                         MATERIAL_WIDTH, None)  # No height limit
        
        if best_pos is None:
            # Fallback to simple positioning if 2D packing fails
            best_pos = _find_best_position(width, height, placed_rects, min_spacing)
        
        positions[panel_name] = Point(best_pos[0], best_pos[1])
        placed_rects.append((best_pos[0], best_pos[1], width, height))
        
    
    # Calculate total bounding box and check constraints
    if placed_rects:
        max_x = max(x + w for x, y, w, h in placed_rects)
        max_y = max(y + h for x, y, w, h in placed_rects)
        total_area = sum(w * h for x, y, w, h in placed_rects)
        bounding_area = max_x * max_y
        efficiency = (total_area / bounding_area) * 100 if bounding_area > 0 else 0
        
        # Only check width constraint - height can extend across multiple sheets
        if max_x > MATERIAL_WIDTH:
            raise GeometryError("layout_constraints", f"Layout width ({max_x:.1f}mm) exceeds material width ({MATERIAL_WIDTH:.1f}mm)")
        
        # Calculate number of sheets needed based on height
        sheets_needed = max(1, int(max_y / MATERIAL_HEIGHT) + (1 if max_y % MATERIAL_HEIGHT > 0 else 0))
    
    return positions


def _find_best_position(width: float, height: float, placed_rects: list, spacing: float) -> tuple:
    """
    Find the best position to place a rectangle among already placed rectangles
    
    Args:
        width, height: Dimensions of rectangle to place
        placed_rects: List of (x, y, w, h) for already placed rectangles
        spacing: Minimum spacing between rectangles
        
    Returns:
        (x, y) position for the new rectangle
    """
    if not placed_rects:
        return (0, 0)
    
    # Try positions: bottom-left corners of existing rectangles and origin
    candidate_positions = [(0, 0)]
    
    for x, y, w, h in placed_rects:
        # Try right edge and bottom edge of each existing rectangle
        candidate_positions.extend([
            (x + w + spacing, y),  # Right of rectangle
            (x, y + h + spacing),  # Below rectangle
        ])
    
    # Find the position with minimum y, then minimum x (bottom-left priority)
    valid_positions = []
    
    for pos_x, pos_y in candidate_positions:
        if _position_is_valid(pos_x, pos_y, width, height, placed_rects, spacing):
            valid_positions.append((pos_x, pos_y))
    
    if valid_positions:
        # Sort by y first (minimize height), then by x (minimize width)
        best_pos = min(valid_positions, key=lambda p: (p[1], p[0]))
        return best_pos
    else:
        # Fallback: place to the right of all existing rectangles
        max_right = max(x + w for x, y, w, h in placed_rects) if placed_rects else 0
        return (max_right + spacing, 0)


def _find_best_position_2d(width: float, height: float, placed_rects: list,
                          spacing: float, material_width: float, material_height: float = None) -> tuple:
    """
    Find the best position to place a rectangle with 2D packing and material constraints
    
    Args:
        width, height: Dimensions of rectangle to place
        placed_rects: List of (x, y, w, h) for already placed rectangles
        spacing: Minimum spacing between rectangles
        material_width: Material width constraint (hard limit)
        material_height: Material height reference (soft limit, can be None for unlimited)
        
    Returns:
        (x, y) position for the new rectangle, or None if it doesn't fit
    """
    if not placed_rects:
        # First panel - check if it fits in material width
        if width <= material_width:
            return (0, 0)
        else:
            return None
    
    # Generate comprehensive candidate positions for 2D packing
    candidate_positions = [(0, 0)]
    
    # Add positions based on existing rectangles
    for x, y, w, h in placed_rects:
        candidate_positions.extend([
            (x + w + spacing, y),          # Right of rectangle
            (x, y + h + spacing),          # Below rectangle
            (x + w + spacing, y + h + spacing),  # Bottom-right corner
        ])
    
    # Also try positions based on "skyline" - tops of existing rectangles
    for x, y, w, h in placed_rects:
        # Try placing on top of each rectangle
        candidate_positions.append((x, y + h + spacing))
        # Try placing aligned with right edge but on top
        if x + w + spacing < material_width:
            candidate_positions.append((x + w + spacing, y + h + spacing))
    
    # Remove duplicates
    candidate_positions = list(set(candidate_positions))
    
    # Filter positions that fit within material constraints
    valid_positions = []
    
    for pos_x, pos_y in candidate_positions:
        # Check material width constraint (height is unlimited)
        width_ok = pos_x + width <= material_width
        position_ok = _position_is_valid(pos_x, pos_y, width, height, placed_rects, spacing)
        
        if width_ok and position_ok:
            valid_positions.append((pos_x, pos_y))
    
    if valid_positions:
        # Prioritize positions that minimize wasted space
        # Sort by: minimize Y (prefer lower positions), then minimize X
        best_pos = min(valid_positions, key=lambda p: (p[1], p[0]))
        return best_pos
    else:
        # No valid position found within material constraints
        return None


def _position_is_valid(x: float, y: float, width: float, height: float,
                      placed_rects: list, spacing: float) -> bool:
    """Check if a position is valid (no overlaps with existing rectangles)"""
    new_rect = (x, y, width, height)
    
    for existing_rect in placed_rects:
        if _rectangles_overlap(new_rect, existing_rect, spacing):
            return False
    
    return True


def _rectangles_overlap(rect1: tuple, rect2: tuple, spacing: float) -> bool:
    """Check if two rectangles overlap considering required spacing"""
    x1, y1, w1, h1 = rect1
    x2, y2, w2, h2 = rect2
    
    # Calculate all non-overlap conditions with detailed logging
    cond1 = x1 + w1 + spacing <= x2  # rect1 is to the left of rect2
    cond2 = x2 + w2 + spacing <= x1  # rect2 is to the left of rect1
    cond3 = y1 + h1 + spacing <= y2  # rect1 is above rect2
    cond4 = y2 + h2 + spacing <= y1  # rect2 is above rect1
    
    # Any true condition means no overlap
    no_overlap = cond1 or cond2 or cond3 or cond4
    overlaps = not no_overlap
    
    # Return collision result
    
    return overlaps