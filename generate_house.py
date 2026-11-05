#!/usr/bin/env python3
"""
Standalone House Box Generator with Architectural Components
Generate laser-cutting ready SVG files for house boxes with finger joints,
architectural components, and decorative patterns.

Usage:
    python generate_house.py --length 80 --width 60 --height 70 --angle 35
    python generate_house.py --output my_house.svg --length 100 --width 80 --height 90
    python generate_house.py --architectural-preset farmhouse --length 120 --width 100
    python generate_house.py --roof-type hip --architectural-style tudor --window-type arched
    python generate_house.py --add-additional-gable --additional-gable-width 30

Examples:
    # Basic house (80x60x70mm, 35° gable, 3mm material)
    python generate_house.py
    
    # Custom dimensions with architectural preset
    python generate_house.py --length 100 --width 80 --height 90 --architectural-preset colonial
    
    # Advanced architectural features
    python generate_house.py --roof-type gambrel --architectural-style farmhouse --window-type arched --door-type double
    
    # Modern flat roof design
    python generate_house.py --architectural-preset modern_flat --length 120 --width 100
"""

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path for imports to work properly
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

try:
    from house_maker.constants import DEFAULT_KERF
    from house_maker import (HouseMaker, RoofType, ArchitecturalStyle, WindowType, DoorType, ShingleType,
                             PlacementError)
except ImportError as e:
    print(f"Error importing house_maker modules: {e}")
    print("Make sure all required modules are available in the house_maker directory")
    sys.exit(1)


def create_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Generate laser-cutting ready SVG files for house boxes with architectural components",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_house.py
  python generate_house.py --length 100 --width 80 --height 90
  python generate_house.py --architectural-preset farmhouse --output farmhouse.svg
  python generate_house.py --roof-type hip --architectural-style tudor --window-type arched
  python generate_house.py --architectural-preset modern_flat --no-auto-components

House dimensions:
  length (x): Front-to-back depth of house
  width (y):  Side-to-side width of house
  height (z): Wall height to start of roof
  angle:      Gable roof angle in degrees (for gable roofs)

Architectural options:
  roof-type:         gable, flat, hip, gambrel, shed, mansard
  architectural-style: basic, fachwerkhaus, farmhouse, colonial, brick, stone, tudor, victorian, craftsman, gingerbread
  window-type:       rectangular, arched, circular, attic, bay, dormer, double_hung, casement, palladian, gothic_pair, colonial_set, cross_pane, multi_pane
  door-type:         rectangular, double, arched, dutch
  architectural-preset: Pre-configured combinations (basic, farmhouse, colonial, tudor, stone, etc.)
        """)
    
    # House dimensions
    parser.add_argument('--length', '-l', type=float, default=80.0,
                       help='House length in mm (default: 80)')
    parser.add_argument('--width', '-w', type=float, default=60.0,
                       help='House width in mm (default: 60)')
    parser.add_argument('--height', '-z', type=float, default=70.0,
                       help='Wall height in mm (default: 70)')
    parser.add_argument('--angle', '-a', type=float, default=35.0,
                       help='Gable angle in degrees (default: 35)')
    
    # Material properties
    parser.add_argument('--thickness', '-t', type=float, default=3.0,
                       help='Material thickness in mm (default: 3)')
    parser.add_argument('--finger-length', '-f', type=float, default=10.0,
                       help='Finger joint length in mm (default: 10)')
    parser.add_argument('--single-joints', action='store_true',
                       help='Force single finger joint per edge (default: multiple joints for long edges)')
    parser.add_argument('--kerf', '-k', type=float, default=DEFAULT_KERF,
                       help=f'Laser kerf compensation in mm (default: {DEFAULT_KERF})')
    
    # Material sheet dimensions
    parser.add_argument('--material-width', type=float, default=457.2,
                       help='Material sheet width in mm (default: 457.2 = 18 inches)')
    parser.add_argument('--material-height', type=float, default=304.8,
                       help='Material sheet height in mm (default: 304.8 = 12 inches)')
    
    # Architectural options
    parser.add_argument('--roof-type', type=str, default=None,
                       choices=['gable', 'flat', 'hip', 'gambrel', 'shed', 'mansard'],
                       help='Roof type (default: gable)')
    parser.add_argument('--architectural-style', type=str, default=None,
                       choices=['basic', 'fachwerkhaus', 'farmhouse', 'colonial', 'brick', 'stone', 'tudor', 'victorian', 'craftsman', 'gingerbread'],
                       help='Architectural style (default: basic)')
    
    parser.add_argument('--shingle-type', type=str, default='shingles',
                       choices=['spantile', 'spanish', 'shingles', 'scallops', 's-tile'],
                       help='Roof shingle/tile pattern type (default: shingles)')
    parser.add_argument('--window-type', type=str, default=None,
                       choices=['rectangular', 'arched', 'circular', 'attic', 'bay', 'dormer', 'double_hung', 'casement', 'palladian', 'gothic_pair', 'colonial_set', 'cross_pane', 'multi_pane'],
                       help='Window type (default: rectangular)')
    parser.add_argument('--door-type', type=str, default=None,
                       choices=['rectangular', 'double', 'arched', 'dutch'],
                       help='Door type (default: rectangular)')
    parser.add_argument('--architectural-preset', type=str, default=None,
                       choices=['basic', 'farmhouse', 'colonial', 'tudor', 'german', 'victorian', 'craftsman', 'brick', 'stone', 'modern_flat', 'barn_gambrel'],
                       help='Pre-configured architectural style preset')
    parser.add_argument('--no-auto-components', action='store_true',
                       help='Disable automatic door/window placement')
    parser.add_argument('--stone-jitter', action='store_true', default=True,
                       help='Enable subtle jitter in stone wall patterns for natural look (default: enabled)')
    parser.add_argument('--no-stone-jitter', dest='stone_jitter', action='store_false',
                       help='Disable jitter in stone wall patterns for clean straight lines')
    
    # Chimney options
    parser.add_argument('--add-chimney', action='store_true',
                       help='Add a chimney to the roof panel')
    parser.add_argument('--chimney-panel', type=str, default='roof_panel_left',
                       choices=['roof_panel_left', 'roof_panel_right'],
                       help='Which roof panel to add chimney to (default: roof_panel_left)')
    parser.add_argument('--chimney-x', type=float, default=50.0,
                       help='Chimney X position on roof panel in mm (default: 50)')
    parser.add_argument('--chimney-y', type=float, default=20.0,
                       help='Chimney Y position on roof panel in mm (default: 20)')
    parser.add_argument('--chimney-width', type=float, default=10.0,
                       help='Chimney interior width between the side walls in mm (default: 10)')
    parser.add_argument('--chimney-depth', type=float, default=15.0,
                       help='Chimney plan (horizontal) depth in mm (default: 15)')
    parser.add_argument('--chimney-height', type=float, default=20.0,
                       help='Minimum chimney exposure above the roof (up-slope wall) in mm (default: 20)')
    
    # Additional gable options
    parser.add_argument('--add-additional-gable', action='store_true',
                       help='Add an additional gable (dormer) to the roof panel')
    parser.add_argument('--additional-gable-panel', type=str, default='roof_panel_right',
                       choices=['roof_panel_left', 'roof_panel_right'],
                       help='Which roof panel to add additional gable to (default: roof_panel_right)')
    parser.add_argument('--additional-gable-x', type=float, default=30.0,
                       help='Additional gable X position on roof panel in mm (default: 30)')
    parser.add_argument('--additional-gable-y', type=float, default=15.0,
                       help='Additional gable Y position on roof panel in mm (default: 15)')
    parser.add_argument('--additional-gable-width', type=float, default=25.0,
                       help='Additional gable width in mm (default: 25)')
    parser.add_argument('--additional-gable-pitch', type=float, default=None,
                       help='Additional gable roof pitch in degrees (default: same as the main roof). '
                            'The depth follows from the width and pitch (horizontal ridge).')
    parser.add_argument('--additional-gable-overhang', type=float, default=3.0,
                       help='Additional gable roof overhang in mm (default: 3)')
    
    # Output options
    parser.add_argument('--output', '-o', type=str, default='house_box.svg',
                       help='Output SVG filename (default: house_box.svg)')
    parser.add_argument('--no-labels', action='store_true',
                       help='Disable panel labels in SVG')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed generation information')
    
    return parser


def validate_dimensions(args):
    """Validate that dimensions are reasonable"""
    errors = []
    
    if args.length <= 0:
        errors.append(f"Length must be positive (got {args.length})")
    if args.width <= 0:
        errors.append(f"Width must be positive (got {args.width})")
    if args.height <= 0:
        errors.append(f"Height must be positive (got {args.height})")
    if not (10 <= args.angle <= 80):
        errors.append(f"Angle should be between 10-80 degrees (got {args.angle})")
    if args.thickness <= 0:
        errors.append(f"Thickness must be positive (got {args.thickness})")
    if args.finger_length <= 0:
        errors.append(f"Finger length must be positive (got {args.finger_length})")
    if args.material_width <= 0:
        errors.append(f"Material width must be positive (got {args.material_width})")
    if args.material_height <= 0:
        errors.append(f"Material height must be positive (got {args.material_height})")
    
    # Check proportions
    if args.finger_length > min(args.length, args.width, args.height) / 3:
        errors.append(f"Finger length ({args.finger_length}) too large for smallest dimension")
    
    if errors:
        print("❌ Dimension validation errors:")
        for error in errors:
            print(f"   {error}")
        return False
    
    return True


def _enum(enum_cls, value):
    """Look up an enum member by its value ('s-tile', 'double_hung', ...)."""
    return enum_cls(value)


def convert_architectural_options(args):
    """Convert string arguments to enum types"""
    options = {}
    for attr, key, enum_cls in (('roof_type', 'roof_type', RoofType),
                                ('architectural_style', 'architectural_style', ArchitecturalStyle),
                                ('shingle_type', 'shingle_type', ShingleType),
                                ('window_type', 'window_type', WindowType),
                                ('door_type', 'door_type', DoorType)):
        value = getattr(args, attr)
        if value:
            options[key] = _enum(enum_cls, value)
    if args.architectural_preset:
        options['architectural_preset'] = args.architectural_preset
    options['auto_add_components'] = not args.no_auto_components
    options['stone_jitter'] = args.stone_jitter
    return options


def main():
    """Main CLI function"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Validate dimensions
    if not validate_dimensions(args):
        sys.exit(1)
    
    try:
        # Convert architectural options to enums
        architectural_options = convert_architectural_options(args)
        
        if args.verbose:
            print(f"Creating house: {args.length}×{args.width}×{args.height}mm")
            print(f"Gable angle: {args.angle}°, Material: {args.thickness}mm")
            if architectural_options.get('architectural_preset'):
                print(f"Architectural preset: {args.architectural_preset}")
            elif any(key in architectural_options for key in ['roof_type', 'architectural_style']):
                print(f"Custom architectural options:")
                for key, value in architectural_options.items():
                    if key != 'auto_add_components':
                        print(f"  {key}: {value}")
        
        # Create HouseMaker with all options
        house = HouseMaker(
            length=args.length,
            width=args.width,
            height=args.height,
            gable_angle=args.angle,
            material_thickness=args.thickness,
            finger_length=args.finger_length,
            kerf=args.kerf,
            material_width=args.material_width,
            material_height=args.material_height,
            single_joints=args.single_joints,
            **architectural_options
        )
        
        # Add roof features if requested (PlacementError explains what is wrong)
        if args.add_chimney:
            chimney = house.add_chimney(
                panel_name=args.chimney_panel, x=args.chimney_x, y=args.chimney_y,
                width=args.chimney_width, height=args.chimney_depth,
                chimney_height=args.chimney_height)
            if args.verbose:
                x, y, w, d = chimney.footprint()
                print(f"\n🏭 Chimney added on {args.chimney_panel}")
                print(f"   Outer footprint on roof: {w:.1f}×{d:.1f}mm at ({x}, {y})")
                print(f"   Exposure above roof: {chimney.chimney_height}mm up-slope, "
                      f"{chimney.side_wall_heights()[0]:.1f}mm down-slope (level top)")

        if args.add_additional_gable:
            dormer = house.add_additional_gable(
                panel_name=args.additional_gable_panel, x=args.additional_gable_x,
                y=args.additional_gable_y, width=args.additional_gable_width,
                roof_overhang=args.additional_gable_overhang, pitch=args.additional_gable_pitch)
            if args.verbose:
                g = dormer.geometry
                print(f"\n🏠 Additional gable (dormer) added on {args.additional_gable_panel}")
                print(f"   Width {g.width}mm, pitch {g.phi_deg:.1f}°, apex angle {g.apex_angle_deg:.1f}°")
                print(f"   Depth on roof (from horizontal ridge): {dormer.position.height:.1f}mm, "
                      f"face height {g.gable_height:.1f}mm, rafter {g.rafter:.1f}mm, ridge {g.ridge:.1f}mm")

        if args.verbose:
            # Get architectural summary
            arch_summary = house.get_architectural_summary()
            print(f"\n🏠 Architectural Configuration:")
            print(f"   Roof type: {arch_summary['roof_type']}")
            print(f"   Architectural style: {arch_summary['architectural_style']}")
            print(f"   Components: {arch_summary['total_windows']} windows, {arch_summary['total_doors']} doors")
            print(f"   Roof panels: {len(arch_summary['roof_panels'])} panels - {', '.join(arch_summary['roof_panels'])}")
            
            print(f"\n📐 Geometry:")
            print(f"   Gable peak height: {house.geometry.gable_peak_height:.1f}mm")
            print(f"   Base roof width: {house.geometry.base_roof_width:.1f}mm")
        
        # Generate SVG
        include_labels = not args.no_labels
        house.generate_svg(args.output, include_labels=include_labels)
        
        # Success information
        output_path = Path(args.output)
        print(f"✅ House box SVG generated successfully!")
        print(f"📁 Output: {output_path.absolute()}")
        
        # Get cutting summary
        summary = house.get_cutting_summary()
        print(f"📐 SVG size: {summary['svg_dimensions_mm']}")
        print(f"🔧 Total panels: {summary['total_panels']}")
        
        if args.verbose:
            print(f"\n📊 Panel Information:")
            for panel_name, details in summary['panel_details'].items():
                area_cm2 = details['area'] / 100  # Convert mm² to cm²
                print(f"   {panel_name}: {details['width']:.1f}×{details['height']:.1f}mm ({area_cm2:.1f}cm²)")
            
            print(f"\n🏗️ Manufacturing:")
            print(f"   Cut length: {summary['total_cut_length_m']:.2f}m")
            print(f"   Material usage: {summary['svg_dimensions_mm']}")
            print(f"   Material dimensions: {summary['material_dimensions']['length']}×{summary['material_dimensions']['width']}×{summary['material_dimensions']['height']}mm")
            print(f"   Kerf compensation: {house.geometry.kerf}mm")
    
    except PlacementError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error generating house box: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()