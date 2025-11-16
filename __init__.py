"""
HouseMaker - Professional Laser-Cut House Box Generator

A standalone Python library for generating precise laser-cut house boxes 
with sophisticated finger joint coordination.
"""

from .geometry import HouseGeometry
from .svg_generator import SVGGenerator
from .constants import HouseStyle
from .architectural_components import (
    RoofType, WindowType, DoorType, ArchitecturalStyle, ShingleType,
    RoofGeometry, ArchitecturalPatternGenerator, Chimney
)
from .architectural_config import ArchitecturalConfiguration, create_preset_configuration
from .exceptions import (
    HouseMakerError,
    ValidationError,
    GeometryError,
    DimensionError,
    FingerJointError,
    SVGGenerationError
)

__version__ = "1.0.0"
__author__ = "HouseMaker Project"

# Main API exports
__all__ = [
    'HouseMaker',
    'HouseGeometry',
    'SVGGenerator',
    'HouseStyle',
    'RoofType',
    'WindowType',
    'DoorType',
    'ArchitecturalStyle',
    'ShingleType',
    'Chimney',
    'ArchitecturalConfiguration',
    'create_preset_configuration',
    'HouseMakerError',
    'ValidationError',
    'GeometryError',
    'DimensionError',
    'FingerJointError',
    'SVGGenerationError'
]


class HouseMaker:
    """
    Main API class for HouseMaker - provides a simplified interface
    matching the documentation examples for backward compatibility.
    """
    
    def __init__(self, length=100, width=100, height=80, gable_angle=45,
                 material_thickness=3, finger_length=15, kerf=0.1,
                 house_style=HouseStyle.BASIC_HOUSE,
                 material_width=457.2, material_height=304.8,
                 # New architectural parameters
                 roof_type=RoofType.GABLE,
                 architectural_style=ArchitecturalStyle.BASIC,
                 shingle_type=ShingleType.SHINGLES,
                 architectural_preset=None,
                 auto_add_components=True,
                 window_type=WindowType.RECTANGULAR,
                 door_type=DoorType.RECTANGULAR,
                 single_joints=False):
        """
        Create a HouseMaker instance with specified dimensions and architectural features
        
        Args:
            length: House length in mm (x dimension)
            width: House width in mm (y dimension)
            height: Wall height in mm (z dimension)
            gable_angle: Roof angle in degrees
            material_thickness: Material thickness in mm
            finger_length: Finger joint length in mm
            kerf: Laser kerf compensation in mm
            house_style: Style from HouseStyle enum (legacy)
            material_width: Material sheet width in mm (default: 18 inches = 457.2mm)
            material_height: Material sheet height in mm (default: 12 inches = 304.8mm)
            
            # Architectural features (NEW!)
            roof_type: Type of roof (gable, flat, hip, gambrel, shed, mansard)
            architectural_style: Decorative style (basic, farmhouse, colonial, tudor, etc.)
            architectural_preset: Use preset configuration ('farmhouse', 'colonial', etc.)
            auto_add_components: Automatically add doors and windows with aesthetic proportions
            window_type: Default window type for automatic placement
            door_type: Default door type for automatic placement
            single_joints: Force single finger joint per edge (default: multiple for long edges)
        """
        self.geometry = HouseGeometry(
            x=length,
            y=width,
            z=height,
            theta=gable_angle,
            thickness=material_thickness,
            finger_length=finger_length,
            kerf=kerf
        )
        self.style = house_style  # Legacy style for backward compatibility
        self.material_width = material_width
        self.material_height = material_height
        self.single_joints = single_joints
        self.svg_generator = None
        
        # Initialize architectural configuration
        if architectural_preset:
            # Use preset configuration
            self.architectural_config = create_preset_configuration(self.geometry, architectural_preset)
        else:
            # Use custom configuration
            self.architectural_config = ArchitecturalConfiguration(
                self.geometry, roof_type, architectural_style, shingle_type
            )
            
            if auto_add_components:
                # Add doors and windows with automatic sizing
                # By default, door is placed on gable_wall_front at ground level
                self.architectural_config.add_automatic_components(
                    add_windows=True,
                    add_doors=True,
                    window_type=window_type,
                    door_type=door_type,
                    door_panel='gable_wall_front'  # Can be changed to 'side_wall_right'
                )
    
    def generate_svg(self, filename=None, include_labels=True):
        """
        Generate SVG content or save to file
        
        Args:
            filename: If provided, save to this file. Otherwise return content.
            include_labels: Whether to include panel labels
            
        Returns:
            SVG content string if filename not provided
        """
        if self.svg_generator is None:
            self.svg_generator = SVGGenerator(self.geometry, self.style,
                                            use_rotated_layout=False,
                                            material_width=self.material_width,
                                            material_height=self.material_height,
                                            architectural_config=self.architectural_config,
                                            single_joints=self.single_joints)
        
        svg_content = self.svg_generator.generate_svg(include_labels)
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(svg_content)
        else:
            return svg_content
    
    def save_design(self, base_name, include_summary=False):
        """
        Save complete design package
        
        Args:
            base_name: Base filename (without extension)
            include_summary: Whether to save cutting summary
        """
        # Generate SVG
        self.generate_svg(f"{base_name}.svg")
        
        if include_summary:
            if self.svg_generator is None:
                self.svg_generator = SVGGenerator(self.geometry, self.style,
                                                use_rotated_layout=False,
                                                material_width=self.material_width,
                                                material_height=self.material_height,
                                                architectural_config=self.architectural_config,
                                                single_joints=self.single_joints)
            
            summary = self.svg_generator.get_cutting_summary()
            assembly = self.svg_generator.get_assembly_instructions()
            
            with open(f"{base_name}_summary.txt", 'w') as f:
                f.write("=== HouseMaker Design Summary ===\n\n")
                f.write(f"Dimensions: {self.geometry.x}×{self.geometry.y}×{self.geometry.z}mm\n")
                f.write(f"Gable angle: {self.geometry.theta}°\n")
                f.write(f"Material thickness: {self.geometry.thickness}mm\n")
                f.write(f"Total panels: {summary['total_panels']}\n")
                f.write(f"Cut length: {summary['total_cut_length_m']:.2f}m\n\n")
                
                f.write("=== Assembly Instructions ===\n")
                for instruction in assembly:
                    f.write(f"{instruction}\n")
    
    def get_geometry_info(self):
        """Get geometry information"""
        return {
            'length': self.geometry.x,
            'width': self.geometry.y,
            'height': self.geometry.z,
            'gable_angle': self.geometry.theta,
            'gable_peak_height': self.geometry.get_gable_peak_height(),
            'roof_panel_left_width': self.geometry.get_roof_panel_left_width(),
            'roof_panel_right_width': self.geometry.get_roof_panel_right_width()
        }
    
    def get_assembly_info(self):
        """Get assembly information"""
        if self.svg_generator is None:
            self.svg_generator = SVGGenerator(self.geometry, self.style,
                                            use_rotated_layout=False,
                                            material_width=self.material_width,
                                            material_height=self.material_height,
                                            architectural_config=self.architectural_config,
                                            single_joints=self.single_joints)
        return self.svg_generator.get_assembly_instructions()
    
    def get_cutting_summary(self):
        """Get cutting summary"""
        if self.svg_generator is None:
            self.svg_generator = SVGGenerator(self.geometry, self.style,
                                            use_rotated_layout=False,
                                            material_width=self.material_width,
                                            material_height=self.material_height,
                                            architectural_config=self.architectural_config,
                                            single_joints=self.single_joints)
        return self.svg_generator.get_cutting_summary()
    
    def get_assembly_instructions(self):
        """Get assembly instructions"""
        return self.get_assembly_info()
    
    # NEW ARCHITECTURAL METHODS
    
    def get_architectural_summary(self):
        """Get summary of architectural components and configuration"""
        return self.architectural_config.get_component_summary()
    
    def add_window(self, panel_name, x, y, width=None, height=None, window_type=WindowType.RECTANGULAR):
        """
        Add a custom window to a specific panel
        
        Args:
            panel_name: Name of the panel (e.g., 'gable_wall_front', 'side_wall_left')
            x, y: Position within the panel (mm)
            width, height: Window dimensions (mm, auto-calculated if None)
            window_type: Type of window
            
        Returns:
            True if window was successfully added, False if invalid placement
        """
        return self.architectural_config.add_custom_window(panel_name, x, y, width, height, window_type)
    
    def add_door(self, panel_name, x, y, width=None, height=None, door_type=DoorType.RECTANGULAR):
        """
        Add a custom door to a specific panel
        
        Args:
            panel_name: Name of the panel (e.g., 'gable_wall_front', 'side_wall_left')
            x, y: Position within the panel (mm)
            width, height: Door dimensions (mm, auto-calculated if None)
            door_type: Type of door
            
        Returns:
            True if door was successfully added, False if invalid placement
        """
        return self.architectural_config.add_custom_door(panel_name, x, y, width, height, door_type)
    
    def add_chimney(self, panel_name, x, y, width=None, height=None, chimney_height=20.0):
        """
        Add a chimney to a roof panel
        
        The chimney will be oriented perpendicular to the roof surface,
        coordinating with the gable angle. The cutout will be smaller than
        the chimney footprint to provide a lip for the chimney to rest on.
        This generates both the roof cutout and 4 chimney wall panels.
        
        Args:
            panel_name: Name of roof panel ('roof_panel_left' or 'roof_panel_right')
            x, y: Position on the roof panel (mm)
            width: Chimney footprint width perpendicular to roof (mm, default: 8mm)
            height: Chimney footprint depth along roof slope (mm, default: 12mm)
            chimney_height: Height of chimney extending above roof (mm, default: 20mm)
        
        Returns:
            True if chimney was successfully added, False if invalid placement
        """
        return self.architectural_config.add_chimney(panel_name, x, y, width, height, chimney_height)
    
    def get_windows_for_panel(self, panel_name):
        """Get all windows on a specific panel"""
        return self.architectural_config.get_windows_for_panel(panel_name)
    
    def get_doors_for_panel(self, panel_name):
        """Get all doors on a specific panel"""
        return self.architectural_config.get_doors_for_panel(panel_name)
    
    def clear_components(self):
        """Clear all doors and windows"""
        self.architectural_config.clear_components()
    
    def validate_components(self):
        """
        Validate all architectural components
        
        Returns:
            List of validation error messages (empty if all valid)
        """
        return self.architectural_config.validate_all_components()
    
    def get_recommended_window_size(self, panel_name, window_type=WindowType.RECTANGULAR):
        """Get aesthetically pleasing window dimensions for a panel"""
        return self.architectural_config.sizer.get_window_dimensions(panel_name, window_type)
    
    def get_recommended_door_size(self, panel_name):
        """Get aesthetically pleasing door dimensions for a panel"""
        return self.architectural_config.sizer.get_door_dimensions(panel_name)
    
    def change_roof_type(self, roof_type):
        """Change the roof type and update configuration"""
        self.architectural_config.roof_type = roof_type
        self.architectural_config.roof_geometry = RoofGeometry(roof_type, self.geometry)
    
    def change_architectural_style(self, architectural_style):
        """Change the architectural style for decorative patterns"""
        self.architectural_config.architectural_style = architectural_style
        self.architectural_config.pattern_generator = ArchitecturalPatternGenerator(
            architectural_style, self.geometry
        )
    
    def apply_preset(self, preset_name):
        """Apply a preset architectural configuration"""
        self.architectural_config = create_preset_configuration(self.geometry, preset_name)