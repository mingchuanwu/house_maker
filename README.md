# HouseMaker - Professional Laser-Cut House Box Generator


A standalone Python library for generating precise laser-cut house boxes with sophisticated finger joint coordination. Built from scratch with professional-grade geometric calculations and SVG generation.

## Features

- **Parametric Design**: Customizable house dimensions, gable angles, and material thickness
- **Perfect Finger Joints**: Sophisticated male/female coordination system with kerf compensation for tight fit (±0.000mm tolerance)
- **Material Optimization**: Configurable material sheet dimensions with efficient panel layout and multi-row support
- **Manufacturing Ready**: Professional SVG output optimized for laser cutting with 0.0254mm line width precision
- **Comprehensive Architectural System**: Complete system for creating architecturally accurate house designs
  - **Roof**: Gable roofs are generated. Other roof types (flat, hip, gambrel, shed, mansard) are accepted but not implemented yet and fall back to gable with a warning
  - **8 Architectural Styles**: Basic, fachwerkhaus, farmhouse, colonial, brick, Tudor, Victorian, and Craftsman with decorative patterns
  - **13 Window Types**: Rectangular, arched, circular, attic, bay, dormer, double_hung, casement, palladian, gothic_pair, colonial_set, cross_pane, multi_pane
  - **4 Door Types**: Rectangular, double, arched, and Dutch doors with proportional sizing
  - **Chimney**: vertical chimney with a level top on the sloped roof (4 walls + casing; the downslope wall is taller). Footprint is scored on the roof panel; walls and casing are derived from one geometric model
  - **Dormers** (`--add-additional-gable`): gable dormer with horizontal ridge; its depth follows from width and pitch (default pitch = main roof pitch). Ridge fingers and face tabs/slots are generated when the dormer is large enough
  - **Attic Window Support**: Automatic detection for tall houses and steep gables (>30° and sufficient height)
  - **Proportional Sizing**: All components automatically sized using golden ratio (1.618) and architectural best practices
- **10 Preset Configurations**: Pre-configured architectural combinations (farmhouse, colonial, Tudor, German, modern, etc.)
- **CLI & Python API**: Both command-line and programmatic interfaces with full backward compatibility

## Quick Start - Command Line

### Basic Usage
```bash
# Generate a basic house box with default settings
python3 generate_house.py

# Custom dimensions
python3 generate_house.py --length 100 --width 80 --height 90

# Specify output file and roof angle
python3 generate_house.py --output my_house.svg --angle 45 --thickness 6

# Custom material sheet size (24×18 inches)
python3 generate_house.py --material-width 609.6 --material-height 457.2

# Verbose output with detailed information
python3 generate_house.py --length 100 --width 80 --height 90 --verbose

# Architectural Features - Use presets for easy styling
python3 generate_house.py --architectural-preset farmhouse --length 120 --width 100
python3 generate_house.py --architectural-preset tudor --length 140 --width 110 --height 85

# Custom architectural combinations
python3 generate_house.py --roof-type hip --architectural-style colonial --length 130 --width 105
python3 generate_house.py --roof-type gambrel --window-type arched --door-type double --length 150

# Advanced architectural house with all features
python3 generate_house.py --roof-type hip --architectural-style tudor \
    --window-type arched --door-type double --length 120 --width 100 --height 80 \
    --output tudor_hip_house.svg --verbose

# House with chimney (4 walls + casing; chimney width is the interior width, depth is the plan depth)
python3 generate_house.py --width 90 --length 90 --height 180 --angle 45 \
    --thickness 3 --kerf 0.2 \
    --add-chimney --chimney-panel roof_panel_right \
    --chimney-x 40 --chimney-y 15 \
    --chimney-width 12 --chimney-depth 18 --chimney-height 25 \
    --output house_with_chimney.svg --verbose
```

### Command Line Options
```bash
python3 generate_house.py [OPTIONS]

Dimensions:
  --length, -l    House length in mm (default: 80)
  --width, -w     House width in mm (default: 60)
  --height, -z    Wall height in mm (default: 70)
  --angle, -a     Gable angle in degrees (default: 35)

Material:
  --thickness, -t           Material thickness in mm (default: 3)
  --finger-length, -f       Finger joint length in mm (default: 10)
  --kerf, -k               Laser kerf compensation in mm (default: 0.1)
  --material-width         Material sheet width in mm (default: 457.2 = 18 inches)
  --material-height        Material sheet height in mm (default: 304.8 = 12 inches)

Architectural Features:
  --roof-type             Roof type: gable, flat, hip, gambrel, shed, mansard
  --architectural-style   Style: basic, fachwerkhaus, farmhouse, colonial, brick, tudor, victorian, craftsman
  --window-type          Window type: rectangular, arched, circular, attic
  --door-type            Door type: rectangular, double, arched, dutch
  --architectural-preset  Preset: basic, farmhouse, colonial, tudor, german, victorian, craftsman, brick_house, modern_flat, barn_gambrel
  --no-auto-components   Disable automatic door/window placement

Output:
  --output, -o        Output SVG filename (default: house_box.svg)
  --no-labels         Disable panel labels in SVG
  --spacing, -s       Panel spacing in mm (default: 3)
  --rotated-layout    Use rotated layout pattern
  --verbose, -v       Show detailed generation information
```

## Architectural Features

The HouseMaker system includes a comprehensive architectural component system with automatic proportional sizing, multiple roof types, door/window positioning, and decorative style patterns.

### Roof Types (6 Available)
- **Gable** (default): Traditional triangular roof with two sloping sides
- **Flat**: Simple rectangular roof panel for modern designs
- **Hip**: Four-sided roof with sloping panels on all sides
- **Gambrel**: Barn-style roof with two slopes on each side
- **Shed**: Single-slope roof, ideal for modern minimalist designs
- **Mansard**: French-style roof with steep lower slopes and flat upper section

### Architectural Styles (8 Available)
- **Basic**: Clean, simple design without decorative elements
- **Fachwerkhaus**: German timber frame patterns with diagonal braces
- **Farmhouse**: Traditional rural style with practical proportions
- **Colonial**: American colonial style with symmetrical features
- **Brick**: Brick pattern textures and classic proportions
- **Tudor**: English Tudor style with distinctive window arrangements
- **Victorian**: Ornate Victorian style with decorative details
- **Craftsman**: Arts and crafts movement style with horizontal emphasis

### Window & Door Types
**Window Types (4 Available):**
- **Rectangular**: Standard rectangular windows
- **Arched**: Classical arched top windows
- **Circular**: Round porthole-style windows
- **Attic**: Small windows for steep gables (automatically used when appropriate)

**Door Types (4 Available):**
- **Rectangular**: Standard rectangular doors
- **Double**: Wide double doors for main entrances
- **Arched**: Classical arched top doors
- **Dutch**: Split doors with separate upper and lower sections

### Preset Configurations (10 Available)
Ready-to-use architectural combinations:
- **basic**: Simple gable roof with basic style
- **farmhouse**: Gambrel roof with farmhouse style and practical components
- **colonial**: Gable roof with colonial style and symmetrical layout
- **tudor**: Gable roof with Tudor style and arched components
- **german**: Gable roof with Fachwerkhaus style (traditional German timber frame)
- **victorian**: Gable roof with Victorian style and ornate details
- **craftsman**: Gable roof with Craftsman style and horizontal emphasis
- **brick_house**: Gable roof with brick patterns and classic proportions
- **modern_flat**: Flat roof with basic style for contemporary designs
- **barn_gambrel**: Gambrel roof with farmhouse style for barn-like structures

## Python API

### Basic Usage
```python
from house_maker import HouseMaker

# Create a house box with default settings
house = HouseMaker(length=100, width=80, height=70)
house.generate_svg("my_house.svg")

# Get cutting information
summary = house.get_cutting_summary()
print(f"Total panels: {summary['total_panels']}")
print(f"Material needed: {summary['svg_dimensions_mm']}")
```

### Architectural Configuration
```python
from house_maker import HouseMaker, RoofType, ArchitecturalStyle, WindowType, DoorType

# Using architectural presets (easiest method)
house = HouseMaker(
    length=120, width=100, height=80,
    architectural_preset='farmhouse'  # Auto-configures roof, style, and components
)

# Custom architectural configuration
house = HouseMaker(
    length=140, width=120, height=90,
    roof_type=RoofType.HIP,
    architectural_style=ArchitecturalStyle.TUDOR,
    window_type=WindowType.ARCHED,
    door_type=DoorType.ARCHED,
    auto_add_components=True  # Automatically add doors/windows
)

# Get architectural summary
summary = house.get_architectural_summary()
print(f"Style: {summary['architectural_style']}")
print(f"Roof: {summary['roof_type']} ({summary['roof_panels']} panels)")
print(f"Components: {summary['total_windows']} windows, {summary['total_doors']} doors")
```

### Advanced Configuration
```python
# Custom material dimensions and precise laser settings
house = HouseMaker(
    length=120,           # House length in mm
    width=100,            # House width in mm
    height=80,            # Wall height in mm
    gable_angle=45,       # Roof angle in degrees
    thickness=3.2,        # Material thickness in mm
    finger_length=12,     # Finger joint length in mm
    kerf=0.15,           # Laser kerf compensation in mm
    material_width=600,   # Material sheet width in mm
    material_height=400   # Material sheet height in mm
)

# Generate SVG with custom spacing and labels
house.generate_svg("custom_house.svg", spacing=5, include_labels=True)
```

### Component Management
```python
# Add custom components after creation
house.add_window('side_wall_left', x=20, y=25, width=15, height=12, window_type=WindowType.ARCHED)
house.add_door('gable_wall_front', x=35, y=5, door_type=DoorType.DOUBLE)

# Get recommended window size for wall
recommended_size = house.get_recommended_window_size('side_wall_left')
print(f"Recommended window: {recommended_size[0]}×{recommended_size[1]}mm")

# Change roof type after creation
house.change_roof_type(RoofType.GAMBREL)

# Apply different preset
house.apply_preset('tudor')
```

### Working with Panels
```python
# Get individual panel information
panels = house.get_panel_info()
for panel_name, info in panels.items():
    print(f"{panel_name}: {info['width']}×{info['height']}mm")

# Check material requirements
cutting_summary = house.get_cutting_summary()
print(f"SVG dimensions: {cutting_summary['svg_dimensions_mm']}")
print(f"Panel counts: {cutting_summary['panel_counts']}")
```

### Advanced Usage - Internal Classes
```python
from house_maker.geometry import HouseGeometry
from house_maker.svg_generator import SVGGenerator
from house_maker.constants import HouseStyle

# Create geometry with custom dimensions
geometry = HouseGeometry(
    x=100,              # length (mm)
    y=80,               # width (mm)
    z=90,               # height (mm)
    theta=45,           # gable angle (degrees)
    thickness=3,        # material thickness (mm)
    finger_length=15,   # finger joint length (mm)
    kerf=0.1           # kerf compensation (mm)
)

# Generate SVG with internal classes
svg_gen = SVGGenerator(geometry, HouseStyle.BASIC_HOUSE)
svg_content = svg_gen.generate_svg(include_labels=True)

# Save to file
with open("advanced_house.svg", "w") as f:
    f.write(svg_content)
```

## House Styles

- **BASIC_HOUSE**: Complete house with floor, 4 walls, and 2 roof panels
- **HOUSE_NO_ROOF**: Floor and 4 walls only (no roof panels)
- **WALLS_ONLY**: 4 walls only (no floor or roof)

## Panel Types

1. **Floor Panel**: Rectangular base with male joints on all edges
2. **Side Walls**: Rectangular with mixed male/female joints  
3. **Gable Walls**: House-shaped with triangular top sections
4. **Roof Panels**: Angled rectangles with asymmetric dimensions

## Finger Joint System

Perfect coordination ensures proper assembly:

- **Floor**: Male joints to connect to all walls
- **Side Walls**: Female bottom (floor), male sides (gables), smooth top
- **Gable Walls**: Female bottom/sides, male roof edges  
- **Roof Panels**: Differentiated edge joints + internal cutouts

## Key Classes

### HouseGeometry (Calculations)
- Gable peak height calculation: `(width/2) * tan(θ)`
- Roof panel width calculation: `(width/2) / cos(θ)` 
- Asymmetric roof panel dimensions
- Kerf compensation on all dimensions
- Comprehensive geometric validation

### SVGGenerator (Precision Output)
- 0.0254mm line width (laser cutting standard)
- Optimized panel layout with material constraints
- Proper SVG structure with cutting layers
- Optional panel labeling and rotated layouts

### HousePanelGenerator (Finger Joints)
- Centralized finger joint configuration
- Single centered finger joints per edge
- Male/female coordination system
- Internal cutouts for roof panels

## Geometric Calculations

### Base Formulas
Given house dimensions (length=x, width=y, height=z) and gable angle θ:

- **Gable peak height**: `(y/2) * tan(θ)`
- **Total gable height**: `z + gable_peak_height`
- **Base roof width**: `(y/2) / cos(θ)`
- **Roof panel length**: `x + 6 * thickness`

### Asymmetric Roof Panels
- **Left roof width**: `base_roof_width + 4 * thickness`
- **Right roof width**: `base_roof_width + 3 * thickness`

## Layout Optimization

The system includes two layout modes with configurable material constraints:

1. **Rectangular Packing**: Optimized 2D packing with user-defined material sheet size
   - **Width Constraint**: Hard limit - panels cannot exceed material width
   - **Height Constraint**: Soft limit - layout can extend across multiple sheets
   - **Default**: 18×12 inches (457.2×304.8mm) in landscape orientation
   
2. **Rotated Layout**: Rotated panels aligned to roof lines for compact arrangement

### Material Sheet Configuration
- **Default Size**: 18×12 inches (457.2×304.8mm) - common plywood/MDF size
- **Layout Strategy**: Width-constrained, unlimited height (multiple sheets)
- **Custom Sizes**: Configurable via CLI parameters or Python API
- **Multi-sheet Support**: Layout automatically spans multiple sheets as needed

## Validation Features

- Dimensional constraints (positive values, reasonable proportions)
- Gable angle limits (10° - 80°)
- Material thickness ratios
- Finger joint feasibility checks
- Material width constraints (configurable, default 18 inches)
- Multi-sheet layout support (unlimited height)

## Output Formats

### SVG Files
- Hairline precision (0.0254mm stroke width)
- Laser-cutting ready with proper viewBox
- Optional panel labels for assembly
- Professional cutting layers

### Cutting Summary
- Material requirements and panel count
- Cut length estimates (total perimeter)
- Panel dimensions and positions
- Assembly information

## Project Structure

```
house_maker/
├── generate_house.py     # CLI
├── __init__.py, maker.py # public API: HouseMaker facade
├── constants.py, exceptions.py
├── geometry.py           # HouseGeometry: all panel dimensions (kerf-compensated, pure math)
├── components.py         # enums, Window, Door, Chimney, AdditionalGable (own geometry, no SVG)
├── dormer_geometry.py    # pure 3D dormer maths
├── placement.py          # sizing + automatic placement of windows/doors
├── config.py             # ArchitecturalConfiguration: component registry + placement validation
├── joints.py             # finger-joint engine (plan -> JointSpec, trace -> path)
├── builders/             # box.py, chimney.py, dormer.py: geometry -> Panel
├── cutouts.py, casings.py, patterns.py   # window/door cutouts, trim, engraving patterns
├── panel.py              # Panel: the contract between builders, layout and render
├── assembly.py           # which panels exist (reads the config, calls builders)
├── layout.py, render.py  # packing on the sheet; SVG output
├── svg_generator.py      # build -> layout -> render facade
├── svgpath.py            # small SVG path reader (extents, tests)
├── mates.py              # declared mating edges / tab↔slot pairs (used by the review page and tests)
├── review/               # human review page (viewer_*.js/html/css), builder, feedback collector
├── kerf.py               # kerf offset of arbitrary cut paths (cut-outs, trim frames)
├── warnings_util.py      # warnings attributed to the caller's code
├── tools/mutate.py       # mutation-testing runner (off by default; ≤ 3 workers, checks free memory)
├── tests/                # pytest suite (run `make test`)
├── docs/ARCHITECTURE_REVIEW.md   # findings and progress tracker
└── template/             # example SVG files
```

## Setup and common tasks

```bash
cd /Users/mingchuanwu/src/oss/house_maker
make setup      # uv creates .venv (Python 3.12) and installs the dev dependencies; if npm exists it also runs `npm ci` (jsdom, for the review-page tests)
make test       # full suite
make review     # tests + SVGs + review.html in /tmp/house_gallery, then opens the review page
make feedback   # collect exported review feedback from /tmp/house_review_inbox
make house ARGS="--add-chimney --angle 40"
```

The library itself has **no Python dependencies** (standard library only). Dev dependency: `pytest`
(declared in `pyproject.toml`, locked in `uv.lock`). Optional: `jsdom` (npm, `package.json`) enables the
browser-logic tests of the review page; without it that one test is skipped. `uv sync` also installs the
package in editable mode, so `import house_maker` and the `house-maker` command work from anywhere in the venv.

## Roof ridge

A laser cuts square to the plate, so the two roof panels cannot be bevelled: the ridge fits exactly only at a **45°** roof angle. At other
angles the panels overlap along the ridge (shallower roofs, by up to `t·|cos 2θ|`) or leave a small wedge gap (steeper roofs, up to
`t·|tan(90°−2θ)|`). Finish it by hand; the generated assembly instructions tell you how much for your angle.

## Testing

```bash
cd /Users/mingchuanwu/src/oss
python3 -m pytest house_maker -q                                   # ~2 s
python3 -m pytest house_maker -q --svg-dir /tmp/gallery            # also write SVGs for inspection
open /tmp/gallery/index.html                                       # browse them by component
```

Tests are organised per component (`tests/components/`): each builds the minimal assembly of that
component, checks it numerically, and writes an SVG of just those panels.

| Component | Assembly under test | Checked |
|-----------|--------------------|---------|
| `window` (13 types × side/gable wall), `door` (4 types) | wall + cut-out + casing | cut-out inside wall and window/door rectangle; casing opening = window; score lines inside frame |
| `chimney` (angles 20–60°, both roof panels) | roof panel + footprint score + roof hole + 4 walls + casing | roof slope vs angle; footprint = plan depth / cos θ; hole = footprint − 2t − kerf; walls vs an independent 3D construction (level top, taller down-slope); casing frame; corner joints mate in 3D height; tiny chimney glued consistently |
| `chimney_3d` | the chimney placed on the roof by an independent 3D model | no interpenetration, tabs flush in notches, level top, side walls rest on the roof, wedge gap under front/back walls, casing clear of the walls |
| `dormer` (angles × pitch, large dormers with fingers) | roof panel + face + 2 roof panels | pitch and right angle at the apex; true 3D edge lengths (nominal); lifted face; ridge fingers; face tabs ↔ roof slots (mirrored per panel); notches never reach the valley |
| `dormer_3d` | the dormer on the roof, independent 3D model | ridge ends exactly on the roof, valley on the roof, no interpenetration (ridge limit bounded), tabs flush |
| `box_seams` (24 box configs) | floor/side/gable/roof seams | as-cut finger position/width/depth, shared edge lengths, tab ↔ roof slot, gable slope = angle |
| `assembly_3d` | the whole box in 3D | panels as kerf-eroded slabs never interpenetrate; tabs flush; extents = specification; ridge limit (exact at 45° only) |
| `dimensions`, `panel_invariants` | every panel | absolute sizes vs an independent closed form; drawn outline/fingers/slots/area = plan |
| `wall_style`, `roof_tiles` | panel + engraving | engraving inside the panel for every style and tile type |

Cross-cutting tests (`test_kerf_compensation.py`, `test_finger_layout.py`, `test_boundaries.py`, `test_contracts.py`, `test_auto_placement.py`, `test_mates.py`,
`test_random_sweep.py` - set `HOUSE_SWEEP_N=300` for a bigger randomized run - plus `test_output_invariants.py`, `test_layout.py`,
`test_placement.py`, `test_architecture.py`, `test_facade.py`, `test_review_regressions.py`, `test_visual_gallery.py`): determinism,
panels inside the viewBox and not overlapping, labels, sheet width, placement rules, dependency direction, CLI.

## Human review page (move panels, check fit, annotate)

```bash
cd /Users/mingchuanwu/src/oss
python3 -m pytest house_maker -q --svg-dir /tmp/house_gallery     # writes SVGs + panel metadata + review.html
open /tmp/house_gallery/review.html                                # one self-contained file, works offline
```

* **Move** (V): drag panels, `R`/`Shift+R` rotate 90°, `X` flip, arrows nudge (Shift = 1 mm, Alt = 0.01 mm), `G` grid snap.
* **Fit view** (F): panels become translucent; overlapping material is drawn red. A snapped finger pair shows
  the small overlap that the kerf compensation predicts (`kerf-expected`); anything marked `← unexpected` is a real clash.
* **Snap to mate**: select a panel and press one of its *Mates* buttons; it aligns exactly to the mating edge
  (fingers interlocked). Tab-through-slot mates show the tab cross-section (green) in its slot with the clearance.
* **Note** (P): click anywhere; the note attaches to the panel / edge / finger / slot under the cursor, with type
  (bug · improve · question · good), severity and text. **Measure** (M): click two points.
* **Export feedback** downloads `house_review_<run>_<time>.json`. Put it in the inbox
  (`/tmp/house_review_inbox`, or set the browser's download folder to it) and run:

```bash
python3 -m house_maker.review collect        # moves the files into house_maker/review/feedback/ and prints every note
python3 -m house_maker.review summary        # print collected feedback again
```

Every note records the case, panel, edge/finger/slot, the component parameters and your panel arrangement
(plus an SVG snapshot of the case you were viewing), so each one can become a regression test.
Notes and layouts are kept in the browser (localStorage) between runs of the same page; **Import** merges an exported file.

## Example Usage Scenarios

### Basic House Box
```bash
python3 generate_house.py --length 100 --width 80 --height 70
```
Output: `house_box.svg` with complete house including roof

### Custom Material and Sheet Size
```bash
python3 generate_house.py --thickness 6 --finger-length 18 --kerf 0.2
```
For thicker material with larger finger joints and kerf compensation

```bash
python3 generate_house.py --material-width 609.6 --material-height 457.2
```
For larger format sheets (24×18 inches) - useful for bigger houses

### Architectural Model
```bash
python3 generate_house.py --length 200 --width 150 --height 120 --angle 30
```
Larger house with shallow roof angle for architectural modeling

### Storage Box (No Roof)
```bash
python3 generate_house.py --no-roof --length 150 --width 100 --height 80
```
Open-top house shape for storage applications

### Large Format Example
```bash
python3 generate_house.py --length 200 --width 150 --height 100 \
    --material-width 1220 --material-height 610
```
Large house optimized for 4×2 foot (1220×610mm) sheet material

## Assembly Instructions

1. Start with floor panel (center piece)
2. Attach side walls with female joints to floor's male joints
3. Attach gable walls with female joints to floor's male joints  
4. Connect side walls to gable walls (male into female)
5. For complete house: attach roof panels to gable slopes
6. Press all joints firmly together

## Requirements

- Python 3.7+
- No external dependencies (pure Python)
- Designed for laser cutting workflows

## Validation and Error Handling

The system provides comprehensive validation with clear error messages:

- **GeometryError**: Invalid geometric calculations
- **DimensionError**: Parameters outside valid ranges  
- **FingerJointError**: Joint generation issues
- **SVGGenerationError**: Output generation problems

## License

Standalone implementation for educational and practical use in laser cutting and maker projects.


### Versioning

The version comes from the latest git tag (`setuptools-scm`): `git tag -a v1.1.0 -m "..."` then `make build`.
Untagged commits get a dev version such as `1.1.1.dev3+g1a2b3c4`; `house_maker.__version__` reports it.
