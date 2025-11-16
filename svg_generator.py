"""
SVG generation system for house box panels with architectural components
Produces precise laser-cutting ready SVG with 0.0254mm line width
Includes door/window cutouts and decorative patterns
"""

from typing import Dict, List, Optional
from .geometry import HouseGeometry, Point, calculate_layout_positions, calculate_rotated_layout_positions, calculate_rotated_bounding_box
from .multi_finger_joints import EnhancedHousePanelGenerator
from .constants import HouseStyle, COORDINATE_PRECISION
from .exceptions import SVGGenerationError
from .architectural_config import ArchitecturalConfiguration


class SVGGenerator:
    """
    Generates precise SVG files for laser cutting house boxes
    
    Features:
    - 0.0254mm line width (hairline precision)
    - Accurate coordinate positioning
    - Proper SVG structure for laser cutting
    """
    
    # Precise line width for laser cutting (0.0254mm = 0.001 inches)
    LASER_LINE_WIDTH = 0.0254
    # Decorative pattern line width (3x laser width for visual distinction)
    DECORATIVE_LINE_WIDTH = 0.0254 * 3
    
    def __init__(self, geometry: HouseGeometry, style: HouseStyle = HouseStyle.BASIC_HOUSE,
                 use_rotated_layout: bool = False, material_width: float = 457.2, material_height: float = 304.8,
                 architectural_config: Optional[ArchitecturalConfiguration] = None,
                 single_joints: bool = False):
        self.geometry = geometry
        self.style = style
        self.use_rotated_layout = use_rotated_layout
        self.material_width = material_width   # 18 inches in mm
        self.material_height = material_height # 12 inches in mm
        self.architectural_config = architectural_config
        # Use enhanced multi-finger joint system for improved structural integrity
        self.panel_generator = EnhancedHousePanelGenerator(geometry, architectural_config, single_joints)
        
        # Calculate layout positions with optimized spacing for material efficiency
        if use_rotated_layout:
            self.layout_positions = calculate_rotated_layout_positions(geometry, max(3.0, self.geometry.thickness))
        else:
            # Convert to expected format for compatibility
            simple_positions = calculate_layout_positions(geometry, 2 * self.geometry.thickness,
                                                        material_width, material_height)
            self.layout_positions = {name: (pos, 0.0) for name, pos in simple_positions.items()}
        
        # Calculate total bounds for SVG viewport
        self._calculate_svg_bounds()
    
    def _calculate_svg_bounds(self):
        """Calculate the total bounding box for the SVG considering rotations"""
        panel_dims = self.geometry.get_panel_dimensions()
        
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for panel_name, (position, rotation) in self.layout_positions.items():
            if panel_name in panel_dims:
                width, height = panel_dims[panel_name]
                
                # Calculate rotated bounding box
                if rotation != 0.0:
                    rotated_width, rotated_height = calculate_rotated_bounding_box(width, height, rotation)
                else:
                    rotated_width, rotated_height = width, height
                
                min_x = min(min_x, position.x)
                min_y = min(min_y, position.y)
                max_x = max(max_x, position.x + rotated_width)
                max_y = max(max_y, position.y + rotated_height)
        
        # Add margin
        margin = 10.0
        self.svg_width = max_x - min_x + 2 * margin
        self.svg_height = max_y - min_y + 2 * margin
        self.svg_offset_x = -min_x + margin
        self.svg_offset_y = -min_y + margin
    
    def generate_svg(self, include_labels: bool = True) -> str:
        """
        Generate complete SVG for house box
        
        Args:
            include_labels: Whether to include panel labels
            
        Returns:
            Complete SVG string ready for laser cutting
        """
        try:
            # SVG header with precise dimensions
            svg_parts = [
                '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
                f'<svg xmlns="http://www.w3.org/2000/svg"',
                f'     width="{self.svg_width:.{COORDINATE_PRECISION}f}mm"',
                f'     height="{self.svg_height:.{COORDINATE_PRECISION}f}mm"',
                f'     viewBox="0 0 {self.svg_width:.{COORDINATE_PRECISION}f} {self.svg_height:.{COORDINATE_PRECISION}f}">',
                '',
                '  <!-- HouseMaker Generated SVG for Laser Cutting -->',
                f'  <!-- Line width: {self.LASER_LINE_WIDTH}mm (hairline precision) -->',
                '',
                '  <defs>',
                '    <style type="text/css">',
                '      .cut-line {',
                f'        stroke: #000000;',
                f'        stroke-width: {self.LASER_LINE_WIDTH:.6f}mm;',
                f'        fill: none;',
                f'        stroke-linecap: round;',
                f'        stroke-linejoin: round;',
                '      }',
                '      .decorative-line {',
                f'        stroke: #000000;',
                f'        stroke-width: {self.DECORATIVE_LINE_WIDTH:.6f}mm;',
                f'        fill: none;',
                f'        stroke-linecap: round;',
                f'        stroke-linejoin: round;',
                '      }',
                '      .chimney-pattern {',
                '        stroke: #000000;',
                '        stroke-width: 0.1mm;',
                '        fill: none;',
                '        stroke-linecap: round;',
                '        stroke-linejoin: round;',
                '      }',
                '      .roof-pattern {',
                '        stroke: #000000;',
                '        stroke-width: 0.1mm;',
                '        fill: none;',
                '        stroke-linecap: round;',
                '        stroke-linejoin: round;',
                '      }',
                '      .label-text {',
                '        font-family: Arial, sans-serif;',
                '        font-size: 1.5mm;',
                '        fill: #666666;',
                '        text-anchor: middle;',
                '        dominant-baseline: text-before-edge;',
                '      }',
                '    </style>',
                '  </defs>',
                '',
                '  <g id="house_box_panels" transform="translate({:.{precision}f},{:.{precision}f})">'.format(
                    self.svg_offset_x, self.svg_offset_y, precision=COORDINATE_PRECISION)
            ]
            
            # Generate panels based on house style
            panels_to_generate = self._get_panels_for_style()
            
            for panel_name in panels_to_generate:
                if panel_name in self.layout_positions:
                    position, rotation = self.layout_positions[panel_name]
                    panel_svg = self._generate_panel_svg(panel_name, position, rotation, include_labels)
                    svg_parts.append(panel_svg)
            
            # Generate chimney panels if any chimneys exist
            if self.architectural_config and self.architectural_config.chimneys:
                chimney_panels = self._generate_chimney_panels(include_labels)
                svg_parts.extend(chimney_panels)
            
            # Generate casing panels for doors and windows
            if self.architectural_config:
                casing_panels = self._generate_casing_panels(include_labels)
                svg_parts.extend(casing_panels)
            
            # Close SVG
            svg_parts.extend([
                '  </g>',
                '</svg>'
            ])
            
            return '\n'.join(svg_parts)
            
        except Exception as e:
            raise SVGGenerationError("complete_svg", str(e))
    
    def _get_panels_for_style(self) -> List[str]:
        """Get list of panels to generate based on house style"""
        base_panels = ['floor', 'side_wall_left', 'side_wall_right', 
                      'gable_wall_front', 'gable_wall_back']
        
        if self.style == HouseStyle.BASIC_HOUSE:
            return base_panels + ['roof_panel_left', 'roof_panel_right']
        elif self.style == HouseStyle.HOUSE_NO_ROOF:
            return base_panels
        elif self.style == HouseStyle.WALLS_ONLY:
            return ['side_wall_left', 'side_wall_right', 'gable_wall_front', 'gable_wall_back']
        else:
            return base_panels + ['roof_panel_left', 'roof_panel_right']
    
    def _generate_panel_svg(self, panel_name: str, position: Point, rotation: float, include_labels: bool) -> str:
        """Generate SVG for a single panel with proper rotations to match layout"""
        try:
            # Generate the panel path at origin (0,0)
            origin = Point(0, 0)
            if panel_name == 'floor':
                result = self.panel_generator.generate_floor_panel(origin)
            elif panel_name in ['side_wall_left', 'side_wall_right']:
                result = self.panel_generator.generate_wall_panel(origin, panel_name)
            elif panel_name in ['gable_wall_front', 'gable_wall_back']:
                result = self.panel_generator.generate_gable_wall_panel(origin, panel_name)
            elif panel_name in ['roof_panel_left', 'roof_panel_right']:
                result = self.panel_generator.generate_roof_panel(origin, panel_name)
            else:
                raise SVGGenerationError(panel_name, f"Unknown panel type: {panel_name}")
            
            # Handle both old string format and new tuple format for backward compatibility
            if isinstance(result, tuple):
                structural_path, decorative_patterns = result
            else:
                # Legacy format - treat everything as structural
                structural_path = result
                decorative_patterns = ""
            
            # Calculate transform for rotation and translation
            if rotation != 0.0:
                # Get panel dimensions for rotation center calculation
                panel_dims = self.geometry.get_panel_dimensions()[panel_name]
                center_x = panel_dims[0] / 2
                center_y = panel_dims[1] / 2
                
                # Correct transform order: translate first, then rotate around panel center
                transform = f'transform="translate({position.x},{position.y}) rotate({rotation},{center_x},{center_y})"'
            else:
                transform = f'transform="translate({position.x},{position.y})"'
            
            # Get panel dimensions for text positioning
            panel_dims = self.geometry.get_panel_dimensions()[panel_name]
            
            # Create SVG group for this panel with transform
            panel_parts = [
                f'    <!-- {panel_name.replace("_", " ").title()} -->',
                f'    <g id="{panel_name}" {transform}>',
                f'      <path class="cut-line" d="{structural_path}" />',
            ]
            
            # Add decorative patterns with appropriate line width
            if decorative_patterns and decorative_patterns.strip():
                # Use roof-pattern class for roof panels (0.1mm), decorative-line for others
                pattern_class = "roof-pattern" if "roof_panel" in panel_name else "decorative-line"
                panel_parts.append(f'      <path class="{pattern_class}" d="{decorative_patterns}" />')
            
            # Add label if requested - position at bottom of panel, outside boundaries
            if include_labels:
                # Position text at bottom center of panel, below the panel boundary
                label_x = panel_dims[0] / 2
                label_y = panel_dims[1] + 5.0  # 5mm below panel bottom
                label_text = panel_name.replace('_', ' ').title()
                
                panel_parts.extend([
                    f'      <text class="label-text" x="{label_x:.{COORDINATE_PRECISION}f}" '
                    f'y="{label_y:.{COORDINATE_PRECISION}f}">{label_text}</text>'
                ])
            
            panel_parts.append('    </g>')
            panel_parts.append('')
            
            return '\n'.join(panel_parts)
            
        except Exception as e:
            raise SVGGenerationError(panel_name, str(e))
    
    def _generate_chimney_panels(self, include_labels: bool) -> List[str]:
        """
        Generate SVG for all chimney wall panels in 3-column layout
        
        Layout (left to right):
        - Column 1: Chimney walls (front, back, left, right)
        - Column 2: Roof casings (front, back, left, right)
        - Column 3: Top casings (front, back, left, right)
        
        Args:
            include_labels: Whether to include panel labels
            
        Returns:
            List of SVG strings for chimney panels
        """
        chimney_svgs = []
        
        # Calculate layout position for chimney panels (place them to the right of main panels)
        # Find the rightmost panel position
        max_x = 0
        for panel_name, (position, rotation) in self.layout_positions.items():
            panel_dims = self.geometry.get_panel_dimensions().get(panel_name)
            if panel_dims:
                width, height = panel_dims
                panel_right = position.x + width
                max_x = max(max_x, panel_right)
        
        # Base position for chimney panels
        base_x = max_x + 20.0  # 20mm spacing from main panels
        base_y = 0.0
        
        # Generate each chimney's panels in 3-column layout
        for chimney_idx, chimney in enumerate(self.architectural_config.chimneys):
            # Define the 3 columns of panels
            column1_panels = ['chimney_front', 'chimney_back', 'chimney_left', 'chimney_right']
            column2_panels = ['chimney_roof_casing_front', 'chimney_roof_casing_back',
                            'chimney_roof_casing_left', 'chimney_roof_casing_right']
            column3_panels = ['chimney_top_casing_front', 'chimney_top_casing_back',
                            'chimney_top_casing_left', 'chimney_top_casing_right']
            
            # Track column widths for positioning
            column_spacing = 20.0  # Spacing between columns
            column_x_positions = [base_x, 0, 0]  # Will be calculated
            column_max_widths = [0, 0, 0]
            
            # Calculate column 1 width
            for panel_name in column1_panels:
                panel_dims = chimney.get_panel_dimensions()[panel_name]
                column_max_widths[0] = max(column_max_widths[0], panel_dims[0])
            
            # Calculate column 2 and 3 widths
            for panel_name in column2_panels:
                panel_dims = chimney.get_panel_dimensions()[panel_name]
                column_max_widths[1] = max(column_max_widths[1], panel_dims[0])
            
            for panel_name in column3_panels:
                panel_dims = chimney.get_panel_dimensions()[panel_name]
                column_max_widths[2] = max(column_max_widths[2], panel_dims[0])
            
            # Set column X positions
            column_x_positions[0] = base_x
            column_x_positions[1] = column_x_positions[0] + column_max_widths[0] + column_spacing
            column_x_positions[2] = column_x_positions[1] + column_max_widths[1] + column_spacing
            
            # Process all 3 columns
            all_columns = [column1_panels, column2_panels, column3_panels]
            
            for col_idx, column_panels in enumerate(all_columns):
                column_y = base_y
                
                for panel_name in column_panels:
                    # Calculate position for this panel
                    panel_position = Point(column_x_positions[col_idx], column_y)
                    
                    # Generate the panel
                    if 'casing' in panel_name:
                        structural_path, decorative = self.panel_generator.generate_chimney_casing(
                            panel_position, chimney, panel_name)
                    else:
                        structural_path, decorative = self.panel_generator.generate_chimney_panel(
                            panel_position, chimney, panel_name)
                    
                    # Get panel dimensions for labeling
                    panel_dims = chimney.get_panel_dimensions()[panel_name]
                    
                    # Create SVG group for this chimney panel
                    panel_parts = [
                        f'    <!-- {panel_name.replace("_", " ").title()} (Chimney {chimney_idx + 1}) -->',
                        f'    <g id="{panel_name}_{chimney_idx}">',
                        f'      <path class="cut-line" d="{structural_path}" />',
                    ]
                    
                    # Add decorative brick pattern with 0.1mm line width for chimney walls (not casings)
                    if decorative and decorative.strip() and 'casing' not in panel_name:
                        panel_parts.append(f'      <path class="chimney-pattern" d="{decorative}" />')
                    
                    # Add label if requested
                    if include_labels:
                        label_x = panel_position.x + panel_dims[0] / 2
                        label_y = panel_position.y + panel_dims[1] + 5.0
                        label_text = f"{panel_name.replace('_', ' ').title()} {chimney_idx + 1}"
                        panel_parts.append(
                            f'      <text class="label-text" x="{label_x:.{COORDINATE_PRECISION}f}" '
                            f'y="{label_y:.{COORDINATE_PRECISION}f}">{label_text}</text>')
                    
                    panel_parts.append('    </g>')
                    panel_parts.append('')
                    
                    chimney_svgs.append('\n'.join(panel_parts))
                    
                    # Move to next position in this column (stack vertically)
                    column_y += panel_dims[1] + 10.0  # 10mm spacing between panels
        
        return chimney_svgs
    
    def _generate_casing_panels(self, include_labels: bool) -> List[str]:
        """
        Generate SVG for all door and window casing panels
        
        Args:
            include_labels: Whether to include panel labels
            
        Returns:
            List of SVG strings for casing panels
        """
        casing_svgs = []
        
        # Find the rightmost position for layout
        max_x = 0
        for panel_name, (position, rotation) in self.layout_positions.items():
            panel_dims = self.geometry.get_panel_dimensions().get(panel_name)
            if panel_dims:
                width, height = panel_dims
                panel_right = position.x + width
                max_x = max(max_x, panel_right)
        
        # Add spacing for chimney panels if they exist
        if self.architectural_config and self.architectural_config.chimneys:
            # Chimneys are already placed, so add more spacing
            casing_x = max_x + 20.0  # Additional spacing
            # Find max Y from chimney panels
            casing_y = 0.0
            for chimney in self.architectural_config.chimneys:
                all_panel_names = ['chimney_front', 'chimney_back', 'chimney_left', 'chimney_right',
                                  'chimney_roof_casing_front', 'chimney_roof_casing_back',
                                  'chimney_roof_casing_left', 'chimney_roof_casing_right',
                                  'chimney_top_casing_front', 'chimney_top_casing_back',
                                  'chimney_top_casing_left', 'chimney_top_casing_right']
                for panel_name in all_panel_names:
                    panel_dims = chimney.get_panel_dimensions().get(panel_name)
                    if panel_dims:
                        casing_y += panel_dims[1] + 10.0
        else:
            casing_x = max_x + 20.0
            casing_y = 0.0
        
        # Collect all casing panels from all walls
        all_casing_dims = {}
        
        # Get windows and doors from each panel
        from .geometry import Point
        
        for panel_name in self._get_panels_for_style():
            # Get windows for this panel
            windows = self.architectural_config.get_windows_for_panel(panel_name)
            for idx, window in enumerate(windows):
                window_casings = self.panel_generator.generate_window_casing_panels(window, f"{panel_name}_w{idx}")
                all_casing_dims.update(window_casings)
            
            # Get doors for this panel
            doors = self.architectural_config.get_doors_for_panel(panel_name)
            for idx, door in enumerate(doors):
                door_casings = self.panel_generator.generate_door_casing_panels(door, f"{panel_name}_d{idx}")
                all_casing_dims.update(door_casings)
        
        # Generate SVG for each casing piece
        for casing_name, (width, height, svg_path) in all_casing_dims.items():
            position = Point(casing_x, casing_y)
            
            # Generate the casing panel with pre-computed path
            structural_path, decorative = self.panel_generator.generate_casing_panel(
                position, casing_name, width, height, svg_path)
            
            # Create SVG group for this casing panel
            panel_parts = [
                f'    <!-- {casing_name.replace("_", " ").title()} -->',
                f'    <g id="{casing_name}">',
                f'      <path class="cut-line" d="{structural_path}" />',
            ]
            
            # Add label if requested
            if include_labels:
                label_x = position.x + width / 2
                label_y = position.y + height + 5.0
                # Simplify label text
                label_parts = casing_name.split('_')
                if 'casing' in label_parts:
                    # Extract panel type and casing position
                    casing_idx = label_parts.index('casing')
                    position_label = label_parts[casing_idx + 1] if casing_idx + 1 < len(label_parts) else ''
                    label_text = f"Casing {position_label}"
                else:
                    label_text = casing_name.replace('_', ' ').title()
                    
                panel_parts.append(
                    f'      <text class="label-text" x="{label_x:.{COORDINATE_PRECISION}f}" '
                    f'y="{label_y:.{COORDINATE_PRECISION}f}">{label_text}</text>')
            
            panel_parts.append('    </g>')
            panel_parts.append('')
            
            casing_svgs.append('\n'.join(panel_parts))
            
            # Move to next position (stack vertically with small spacing)
            casing_y += height + 3.0  # 3mm spacing between casing pieces
        
        return casing_svgs
    
    def get_cutting_summary(self) -> Dict[str, any]:
        """Get summary information for the cutting job"""
        panel_dims = self.geometry.get_panel_dimensions()
        panels_to_generate = self._get_panels_for_style()
        
        total_cut_length = 0.0
        panel_areas = {}
        
        for panel_name in panels_to_generate:
            if panel_name in panel_dims:
                width, height = panel_dims[panel_name]
                
                # Estimate perimeter (cut length) for rectangular panels
                if 'gable' in panel_name:
                    # Approximate gable perimeter (more complex calculation needed for exact)
                    perimeter = 2 * width + 2 * height * 0.8  # Rough estimate
                else:
                    perimeter = 2 * (width + height)
                
                area = width * height
                panel_areas[panel_name] = {'width': width, 'height': height, 
                                         'area': area, 'perimeter': perimeter}
                total_cut_length += perimeter
        
        return {
            'total_panels': len(panels_to_generate),
            'total_cut_length_mm': total_cut_length,
            'total_cut_length_m': total_cut_length / 1000,
            'svg_dimensions_mm': (self.svg_width, self.svg_height),
            'material_dimensions': {
                'length': self.geometry.x,
                'width': self.geometry.y,
                'height': self.geometry.z,
                'thickness': self.geometry.thickness
            },
            'panel_details': panel_areas,
            'house_geometry': {
                'gable_angle_degrees': self.geometry.theta,
                'gable_peak_height': self.geometry.gable_peak_height,
                'roof_panel_left_width': self.geometry.roof_panel_left_width,
                'roof_panel_right_width': self.geometry.roof_panel_right_width
            }
        }
    
    def save_svg(self, filename: str, include_labels: bool = True):
        """Save SVG to file"""
        svg_content = self.generate_svg(include_labels)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(svg_content)
        except Exception as e:
            raise SVGGenerationError("file_save", f"Could not save to {filename}: {str(e)}")
    
    def get_assembly_instructions(self) -> List[str]:
        """Generate human-readable assembly instructions"""
        return [
            "House Box Assembly Instructions:",
            "",
            "1. Start with the floor panel (center piece)",
            "2. Attach the four wall panels to the floor:",
            "   - Side walls connect with female joints to floor's male joints",
            "   - Gable walls connect with female joints to floor's male joints",
            "3. Connect the walls to each other:",
            "   - Side walls have male joints that fit into gable walls' female joints",
            "4. For complete house with roof:",
            "   - Each roof panel has female joints at both ends",
            "   - Roof panels connect to the male joints on gable wall slopes",
            "5. Press all joints firmly together for secure assembly",
            "",
            f"Material thickness: {self.geometry.thickness}mm",
            f"Gable angle: {self.geometry.theta}°",
            f"Finger joint length: {self.geometry.finger_length}mm"
        ]