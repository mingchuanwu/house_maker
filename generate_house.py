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



# ------------------------------------------------------------------ repeatable roof features
ROOF_SIDES = {'left': 'roof_panel_left', 'right': 'roof_panel_right',
              'roof_panel_left': 'roof_panel_left', 'roof_panel_right': 'roof_panel_right'}
FEATURE_KEYS = {
    'dormer': {'x': 30.0, 'y': 15.0, 'width': 25.0, 'wall': None, 'pitch': None, 'overhang': 3.0},
    'chimney': {'x': 50.0, 'y': 20.0, 'width': 10.0, 'depth': 15.0, 'height': 20.0},
    'dormers': {'count': None, 'width': 25.0, 'wall': None, 'pitch': None, 'overhang': 3.0, 'y': None},
    'cross_gable': {'x': None, 'width': 30.0, 'pitch': None, 'overhang': 3.0},
}
LAYOUT_SIDES = dict(ROOF_SIDES, both='both')


def feature_spec(kind):
    """argparse type for --dormer / --chimney: 'SIDE[:key=value]...' (SIDE: left, right, roof_panel_left or
    roof_panel_right; keys in FEATURE_KEYS[kind]) -> (spec text, roof panel, {key: value}) with defaults filled in."""
    keys = FEATURE_KEYS[kind]
    sides = LAYOUT_SIDES if kind == 'dormers' else ROOF_SIDES

    def parse(text):
        side, *pairs = text.split(':')
        if side not in sides:
            which = 'left, right or both (e.g. both:count=2)' if kind == 'dormers' else 'left or right (e.g. left:x=30:y=20)'
            raise argparse.ArgumentTypeError(f"{text!r}: start with the roof side, {which}")
        values = {}
        for pair in pairs:
            key, sep, value = pair.partition('=')
            if not sep or key not in keys:
                raise argparse.ArgumentTypeError(f"{text!r}: {pair!r} is not key=value with a key from "
                                                 f"{', '.join(keys)}")
            if key in values:
                raise argparse.ArgumentTypeError(f"{text!r}: {key} given twice")
            try:
                values[key] = float(value)
            except ValueError:
                raise argparse.ArgumentTypeError(f"{text!r}: {key}={value!r} is not a number") from None
        if kind == 'cross_gable' and 'x' not in values:
            raise argparse.ArgumentTypeError(f"{text!r}: give x= (where along the side wall the gable starts, mm)")
        if kind == 'dormers':
            if 'count' not in values or values['count'] < 1 or values['count'] != int(values['count']):
                raise argparse.ArgumentTypeError(f"{text!r}: give count=N (a whole number of dormers, at least 1)")
            values['count'] = int(values['count'])
        return text, sides[side], {**keys, **values}
    return parse

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
    
    # Repeatable roof features
    parser.add_argument('--dormer', action='append', default=[], type=feature_spec('dormer'), metavar='SIDE[:KEY=VALUE...]',
                       help='Add a dormer; repeat for more. SIDE is left or right (roof panel); keys: x, y, width, wall '
                            '(side wall height, 0 = none), pitch, overhang - e.g. --dormer left:x=25:y=30:width=35:wall=12. '
                            'Unset keys use the --additional-gable-* defaults')
    parser.add_argument('--dormers', action='append', default=[], type=feature_spec('dormers'), metavar='SIDE:count=N[:KEY=VALUE...]',
                       help='Add a row of N identical dormers on a roof side (left, right or both): over the windows below '
                            'when there are N window columns, else evenly spaced; as low on the roof as they fit. Keys: '
                            'count (required), width, wall, pitch, overhang, y - e.g. --dormers both:count=3:width=30')
    parser.add_argument('--cross-gable', action='append', default=[], type=feature_spec('cross_gable'), dest='cross_gable',
                       metavar='SIDE:x=X[:KEY=VALUE...]',
                       help='Add a cross gable: the side wall (left or right) rises into a gable with its own small roof '
                            'running back into the main roof. Keys: x (required, along the side wall, mm), width, pitch, '
                            'overhang - e.g. --cross-gable left:x=80:width=40')
    parser.add_argument('--chimney', action='append', default=[], type=feature_spec('chimney'), metavar='SIDE[:KEY=VALUE...]',
                       help='Add a chimney; repeat for more. Keys: x, y, width, depth, height - e.g. --chimney left:x=90:y=20')

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
                       help='Additional gable roof pitch: slope of each dormer roof panel from horizontal, in degrees, '
                            'between 0 and 90; the apex angle is 180 - 2 x pitch (default: 45, a 90 degree apex). '
                            'The depth follows from the width and pitch (horizontal ridge).')
    parser.add_argument('--additional-gable-wall-height', type=float, default=None,
                       help='Additional gable side wall height in mm; 0 = no side walls '
                            '(default: on roofs steeper than 45 degrees walls as tall as the gable, otherwise none)')
    parser.add_argument('--additional-gable-overhang', type=float, default=3.0,
                       help='Additional gable roof overhang in mm (default: 3)')
    
    # Output options
    parser.add_argument('--output', '-o', type=str, default='house_box.svg',
                       help='Output SVG filename (default: house_box.svg)')
    parser.add_argument('--3d', dest='model_3d', default='3mf', choices=['3mf', 'stl', 'glb', 'view', 'all', 'none'],
                       help='Also write the assembled house as a 3D model next to the SVG (default: 3mf; '
                            '"view" writes <name>.view.html, the built-in 3D viewer; "all" writes 3mf, stl, glb and '
                            'the viewer; "none" skips it)')
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


def build_house(args) -> 'HouseMaker':
    """The house a parsed command line describes, with every roof feature added (no files written). Shared by
    `main` and the gallery, so a gallery entry's command is exactly what built its model. Raises PlacementError."""
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

    for text, panel, v in args.chimney:
        try:
            house.add_chimney(panel_name=panel, x=v['x'], y=v['y'], width=v['width'], height=v['depth'],
                              chimney_height=v['height'])
        except PlacementError as e:
            raise PlacementError('chimney', f"--chimney {text}: {e.message.split(': ', 1)[1]}") from e
    for text, panel, v in args.dormer:
        try:
            house.add_additional_gable(panel_name=panel, x=v['x'], y=v['y'], width=v['width'],
                                       roof_overhang=v['overhang'], pitch=v['pitch'], wall_height=v['wall'])
        except PlacementError as e:
            raise PlacementError('dormer', f"--dormer {text}: {e.message.split(': ', 1)[1]}") from e

    for text, panel, v in args.cross_gable:
        try:
            house.add_cross_gable(panel, v['x'], width=v['width'], pitch=v['pitch'], roof_overhang=v['overhang'])
        except PlacementError as e:
            raise PlacementError('cross gable', f"--cross-gable {text}: {e.message.split(': ', 1)[1]}") from e
    for text, side, v in args.dormers:
        try:
            house.add_dormers(side, v['count'], width=v['width'], y=v['y'], roof_overhang=v['overhang'],
                              pitch=v['pitch'], wall_height=v['wall'])
        except PlacementError as e:
            raise PlacementError('dormers', f"--dormers {text}: {e.message.split(': ', 1)[1]}") from e

    if args.add_additional_gable:
        dormer = house.add_additional_gable(
            panel_name=args.additional_gable_panel, x=args.additional_gable_x,
            y=args.additional_gable_y, width=args.additional_gable_width,
            roof_overhang=args.additional_gable_overhang, pitch=args.additional_gable_pitch,
            wall_height=args.additional_gable_wall_height)
        if args.verbose:
            g = dormer.geometry
            print(f"\n🏠 Additional gable (dormer) added on {args.additional_gable_panel}")
            print(f"   Width {g.width}mm, pitch {g.phi_deg:.1f}°, apex angle {g.apex_angle_deg:.1f}°")
            print(f"   Depth on roof (from horizontal ridge): {dormer.position.height:.1f}mm, "
                  f"gable height {g.gable_height:.1f}mm, rafter {g.rafter:.1f}mm, ridge {g.ridge:.1f}mm")
            if g.walls:
                print(f"   Side walls {g.wall_height:.1f}mm high, {g.eave_depth:.1f}mm deep")
    return house


def main():
    """Main CLI function"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Validate dimensions
    if not validate_dimensions(args):
        sys.exit(1)
    
    try:
        house = build_house(args)

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
        
        if args.model_3d != 'none':
            for fmt in (('3mf', 'stl', 'glb', 'view') if args.model_3d == 'all' else (args.model_3d,)):
                if fmt == 'view':
                    path = output_path.with_suffix('.view.html')
                    house.generate_view(str(path))
                    print(f"👀 3D viewer: {path.absolute()}")
                    continue
                path = output_path.with_suffix(f'.{fmt}')
                house.generate_3d(str(path), fmt)
                print(f"🧊 3D model ({fmt}): {path.absolute()}")

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