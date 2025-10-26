"""
SVG generation system for house box panels with architectural components
Produces precise laser-cutting ready SVG with 0.0254mm line width
Includes door/window cutouts and decorative patterns
"""

from typing import Dict, List, Optional
from .geometry import HouseGeometry, Point, calculate_layout_positions, calculate_rotated_layout_positions, calculate_rotated_bounding_box
from .finger_joints import HousePanelGenerator
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
                 architectural_config: Optional[ArchitecturalConfiguration] = None):
        self.geometry = geometry
        self.style = style
        self.use_rotated_layout = use_rotated_layout
        self.material_width = material_width   # 18 inches in mm
        self.material_height = material_height # 12 inches in mm
        self.architectural_config = architectural_config
        self.panel_generator = HousePanelGenerator(geometry, architectural_config)
        
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
            
            # Add decorative patterns with thicker line width if present
            if decorative_patterns and decorative_patterns.strip():
                panel_parts.append(f'      <path class="decorative-line" d="{decorative_patterns}" />')
            
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