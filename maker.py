"""
HouseMaker facade: the simple public entry point.

build model -> (SVGGenerator: build panels -> layout -> render). No generator state is cached,
so adding components after a previous `generate_svg()` is always reflected in the next one.
"""

from .components import ArchitecturalStyle, DoorType, RoofType, ShingleType, WindowType
from .config import ArchitecturalConfiguration, create_preset_configuration
from .constants import DEFAULT_KERF, HouseStyle
from .geometry import HouseGeometry
from .svg_generator import SVGGenerator


class HouseMaker:
    """
    Main API class for HouseMaker - provides a simplified interface
    matching the documentation examples for backward compatibility.
    """
    
    def __init__(self, length=100, width=100, height=80, gable_angle=45,
                 material_thickness=3, finger_length=15, kerf=DEFAULT_KERF,
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
                 stone_jitter=True,
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
            stone_jitter: Enable subtle jitter in stone wall patterns (default: True)
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
        self.geometry.validate_geometry()
        self.style = house_style  # Legacy style for backward compatibility
        self.material_width = material_width
        self.material_height = material_height
        self.single_joints = single_joints
        
        # Initialize architectural configuration
        if architectural_preset:
            # Use preset configuration
            self.architectural_config = create_preset_configuration(self.geometry, architectural_preset)
        else:
            # Use custom configuration
            self.architectural_config = ArchitecturalConfiguration(
                self.geometry, roof_type, architectural_style, shingle_type, stone_jitter
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
    
    def _svg_generator(self):
        return SVGGenerator(self.geometry, self.style,
                            material_width=self.material_width,
                            material_height=self.material_height,
                            architectural_config=self.architectural_config,
                            single_joints=self.single_joints)

    def build_panels(self):
        """All panels of the house (`Panel` objects in local coordinates), before layout."""
        return self._svg_generator().build_panels()

    def render_panels(self, panels, include_labels=True):
        """SVG text for a subset of `build_panels()` (laid out on its own sheet)."""
        return self._svg_generator().render_panels(panels, include_labels)

    def generate_svg(self, filename=None, include_labels=True):
        """
        Generate SVG content or save to file
        
        Args:
            filename: If provided, save to this file. Otherwise return content.
            include_labels: Whether to include panel labels
            
        Returns:
            SVG content string if filename not provided
        """
        
        svg_content = self._svg_generator().generate_svg(include_labels)
        
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
            generator = self._svg_generator()
            summary = generator.get_cutting_summary()
            assembly = generator.get_assembly_instructions()

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

    def describe(self):
        """Plain-dict description of this house (dimensions, style and every component)."""
        g, cfg = self.geometry, self.architectural_config
        pos = lambda c: {'panel': c.position.panel, 'x': c.position.x, 'y': c.position.y,
                         'width': c.position.width, 'height': c.position.height}
        return {
            'dimensions': {'length': g.x, 'width': g.y, 'height': g.z, 'gable_angle': g.theta,
                           'thickness': g.thickness, 'finger_length': g.finger_length, 'kerf': g.kerf},
            'style': cfg.architectural_style.value, 'shingles': cfg.shingle_type.value,
            'windows': [dict(pos(w), type=w.type.value) for w in cfg.windows],
            'doors': [dict(pos(d), type=d.type.value) for d in cfg.doors],
            'chimneys': [dict(pos(c), chimney_height=c.chimney_height) for c in cfg.chimneys],
            'dormers': [dict(pos(d), roof_overhang=d.roof_overhang, pitch=d.geometry.phi_deg)
                        for d in cfg.additional_gables],
        }

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
        return self._svg_generator().get_assembly_instructions()
    
    def get_cutting_summary(self):
        """Get cutting summary"""
        return self._svg_generator().get_cutting_summary()
    
    def get_assembly_instructions(self):
        """Get assembly instructions"""
        return self.get_assembly_info()
    
    # NEW ARCHITECTURAL METHODS
    
    def get_architectural_summary(self):
        """Get summary of architectural components and configuration"""
        return self.architectural_config.get_component_summary()
    
    def add_window(self, panel_name, x, y, width=None, height=None, window_type=WindowType.RECTANGULAR):
        """
        Add a window to a wall panel.

        Args:
            panel_name: e.g. 'gable_wall_front', 'side_wall_left'
            x, y: position within the panel (mm)
            width, height: window size in mm (proportional size if None)

        Returns the Window. Raises PlacementError if it does not fit.
        """
        return self.architectural_config.add_custom_window(panel_name, x, y, width, height, window_type)

    def add_door(self, panel_name, x, y, width=None, height=None, door_type=DoorType.RECTANGULAR):
        """Add a door to a wall panel (same arguments as `add_window`). Raises PlacementError."""
        return self.architectural_config.add_custom_door(panel_name, x, y, width, height, door_type)

    def add_chimney(self, panel_name, x, y, width=None, height=None, chimney_height=20.0):
        """
        Add a vertical chimney to a roof panel ('roof_panel_left' or 'roof_panel_right').

        Args:
            x, y: top-left of the chimney's outer footprint on the roof panel (mm), measured from
                the panel's own edge; on the left roof panel the ridge edge sits `thickness` before
                the peak line, so the same y is physically `thickness` higher up the slope than on
                the right panel
            width: interior width between the side walls (default 8mm); outer width is width + 2t
            height: plan (horizontal) depth (default 12mm); the footprint on the roof panel is
                depth / cos(roof angle) long
            chimney_height: minimum exposure above the roof, at the up-slope wall (default 20mm).
                The chimney top is level, so the downslope wall is taller.

        Returns the Chimney. Raises PlacementError if it does not fit or overlaps another feature.
        """
        return self.architectural_config.add_chimney(panel_name, x, y, width, height, chimney_height)

    def add_additional_gable(self, panel_name, x, y, width=None, height=None, roof_overhang=3.0,
                             pitch=None):
        """
        Add a gable dormer to a roof panel ('roof_panel_left' or 'roof_panel_right').

        The dormer has a horizontal ridge, so its depth follows from its width and pitch;
        `height` is ignored (the derived depth is `result.position.height`).

        Args:
            x, y: top-left of the dormer's bounding box on the roof panel (mm)
            width: dormer width (default 25mm)
            roof_overhang: how far the dormer roof projects in front of its face (default 3mm)
            pitch: dormer roof pitch in degrees (default: the main roof angle)

        Returns the AdditionalGable. Raises PlacementError if it does not fit.
        """
        return self.architectural_config.add_additional_gable(
            panel_name, x, y, width, height, roof_overhang, pitch)

    def get_windows_for_panel(self, panel_name):
        """Get all windows on a specific panel"""
        return self.architectural_config.get_windows_for_panel(panel_name)
    
    def get_doors_for_panel(self, panel_name):
        """Get all doors on a specific panel"""
        return self.architectural_config.get_doors_for_panel(panel_name)
    
    def get_additional_gables_for_panel(self, panel_name):
        """Get all additional gables on a specific panel"""
        return self.architectural_config.get_additional_gables_for_panel(panel_name)
    
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
        return self.architectural_config.get_recommended_window_dimensions(panel_name, window_type)
    
    def get_recommended_door_size(self, panel_name):
        """Get aesthetically pleasing door dimensions for a panel"""
        return self.architectural_config.get_recommended_door_dimensions(panel_name)
    
    def change_roof_type(self, roof_type):
        """Change the roof type and update configuration"""
        self.architectural_config.set_roof_type(roof_type)
    
    def change_architectural_style(self, architectural_style, stone_jitter=True):
        """Change the architectural style for decorative patterns"""
        self.architectural_config.set_style(architectural_style, stone_jitter)
    
    def apply_preset(self, preset_name):
        """Apply a preset architectural configuration"""
        self.architectural_config = create_preset_configuration(self.geometry, preset_name)
