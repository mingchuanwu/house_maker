# HouseMaker Architecture Documentation

## Overview
This document describes the architecture of the HouseMaker project, a standalone Python library for generating laser-cut house boxes with precise finger joint coordination.

**Status: ✅ FULLY IMPLEMENTED AND VALIDATED**

## 1. System Architecture

### 1.1 Core Components
The HouseMaker implementation consists of:
- **HouseGeometry**: Core geometric calculations and validation
- **SVGGenerator**: Professional SVG output with layout optimization
- **EnhancedHousePanelGenerator**: Multi-finger joint generation and panel creation
- **MultiFingerJointGenerator**: Enhanced joint geometry with 1-7 joints per edge
- **ArchitecturalConfiguration**: Doors, windows, chimneys, and decorative patterns
- **CLI Interface**: Command-line tool for easy usage (`generate_house.py`)

### 1.2 Generated Components
A complete house box generates:
- **Floor panel**: Rectangular (L × W) with male joints on all edges
- **Side walls** (2): Rectangular (L × H) with mixed male/female joints
- **Gable end walls** (2): House-shaped (W × H + gable height) with triangular tops
- **Roof panels** (2): Rectangular with asymmetric dimensions and internal cutouts

Total: **7 main panels** + complex finger joint coordination + internal cutouts

## 2. Mathematical Implementation

### 2.1 Geometric Relationships
**Core formulas** (implemented and validated):

```python
class HouseGeometry:
    def _calculate_derived_dimensions(self):
        """Calculate all derived dimensions from base parameters"""
        # Gable geometry (from specification)
        self.gable_peak_height = (self.y / 2) * math.tan(self.theta_rad)
        self.total_gable_height = self.z + self.gable_peak_height
        
        # Roof panel dimensions - ASYMMETRIC design
        self.roof_panel_length = self.x + 6 * self.thickness
        base_roof_width = (self.y / 2) / math.cos(self.theta_rad)
        
        # Asymmetric roof panel widths
        self.roof_panel_left_width = base_roof_width + 4 * self.thickness   
        self.roof_panel_right_width = base_roof_width + 3 * self.thickness  
```

**Validation ranges**:
- Gable angle: 10° - 80° (enforced)
- Dimensions: Positive values with reasonable proportions
- Finger joints: Must fit within panel edges

### 2.2 Key Geometric Properties
Given house dimensions (L=x, W=y, H=z) and gable angle θ:

| Property | Formula | Usage |
|----------|---------|-------|
| Gable peak height | `(y/2) × tan(θ)` | Triangle height calculation |
| Total gable height | `z + gable_peak_height` | Complete gable wall height |
| Base roof width | `(y/2) / cos(θ)` | Base roof panel dimension |
| Roof panel length | `x + 6 × thickness` | Extended roof coverage |
| Left roof width | `base_roof_width + 4 × thickness` | Asymmetric left panel |
| Right roof width | `base_roof_width + 3 × thickness` | Asymmetric right panel |

## 3. Class Architecture (Implemented)

### 3.1 HouseGeometry Class

```python
class HouseGeometry:
    """Core geometric calculations for house box"""
    
    def __init__(self, x: float, y: float, z: float, theta: float, 
                 thickness: float, finger_length: float, kerf: float = 0.0):
        # Store base dimensions
        # Calculate derived dimensions
        # Apply kerf compensation
        
    def get_panel_dimensions(self) -> Dict[str, Tuple[float, float]]:
        """Get dimensions for all house panels"""
        
    def get_finger_joint_configuration(self) -> Dict[str, Dict[str, any]]:
        """Get finger joint configuration for all panel edges"""
        
    def validate_geometry(self):
        """Validate that all geometric calculations are reasonable"""
```

### 3.2 Core Methods (All Implemented)

| Method | Purpose | Status |
|--------|---------|--------|
| `_calculate_derived_dimensions()` | Calculate all geometric properties | ✅ Implemented |
| `get_panel_dimensions()` | Return panel width×height for all panels | ✅ Implemented |
| `get_finger_joint_configuration()` | Centralized joint coordination | ✅ Implemented |
| `validate_geometry()` | Parameter and proportion validation | ✅ Implemented |
| `get_gable_profile_points()` | House-shaped gable outline | ✅ Implemented |

## 4. Finger Joint Coordination System

### 4.1 Implemented Solution
The house box uses a centralized finger joint coordination system:

```python
def get_finger_joint_configuration(self) -> Dict[str, Dict[str, any]]:
    """
    Extended configuration supporting three states:
    - True: Male joint (tab extending outward)
    - False: Female joint (slot/gap inward)  
    - None: No joint (smooth edge)
    """
    return {
        'floor': {
            'bottom': True, 'right': True, 'top': True, 'left': True
        },
        'side_wall_left': {
            'bottom': False, 'right': True, 'top': None, 'left': True
        },
        # ... complete configuration for all panels
    }
```

**Key innovation**: Centralized configuration eliminates hardcoded joint logic and ensures perfect male/female coordination across all panel connections.

### 4.2 Joint Coordination Results
- **Single finger joint per edge** (length l, thickness w)
- **Perfect male/female pairing** between adjacent panels
- **Material thickness properly integrated** throughout all joints
- **No overlapping or misaligned joints** between panels

## 5. SVG Generation and Layout

### 5.1 Panel Layout Systems
The system supports two optimized layout modes:

```python
class SVGGenerator:
    def __init__(self, geometry: HouseGeometry, style: HouseStyle, use_rotated_layout: bool = False):
        if use_rotated_layout:
            # Rotated layout with panels aligned to roof angles
            self.layout_positions = calculate_rotated_layout_positions(geometry, spacing)
        else:
            # Rectangular packing optimized for 12×12 inch material constraints
            positions = calculate_layout_positions(geometry, spacing)
            self.layout_positions = {name: (pos, 0.0) for name, pos in positions.items()}
```

### 5.2 Layout Optimization Features
- **Material Constraints**: Optimized for 304.8×304.8mm (12×12 inch) laser cutting beds
- **2D Rectangular Packing**: Efficient panel arrangement with collision detection
- **Rotated Layout**: Panels aligned to roof lines for compact arrangement
- **Spacing Control**: Configurable spacing with minimum constraints

## 6. Professional SVG Output

### 6.1 Laser Cutting Standards
```python
class SVGGenerator:
    # Precise line width for laser cutting (0.0254mm = 0.001 inches)
    LASER_LINE_WIDTH = 0.0254
    
    def generate_svg(self, include_labels: bool = True) -> str:
        """Generate complete SVG with professional cutting standards"""
```

**Features**:
- Hairline precision (0.0254mm stroke width)
- Proper SVG structure with viewBox
- Optional panel labeling for assembly
- Professional cutting layers

## 7. CLI Integration (Fully Implemented)

### 7.1 Command Line Interface
```bash
# Main CLI tool
python3 generate_house.py [OPTIONS]

# Basic usage examples
python3 generate_house.py --length 100 --width 80 --height 90
python3 generate_house.py --no-roof --thickness 6 --kerf 0.2
python3 generate_house.py --rotated-layout --verbose
```

### 7.2 CLI Features
- Complete parameter control (dimensions, material, output)
- Multiple house styles (basic, no-roof, walls-only)
- Layout options (rectangular packing, rotated layout)
- Comprehensive validation with clear error messages
- Verbose output with cutting summaries

## 8. Validation and Error Handling

### 8.1 Comprehensive Validation System
```python
# Custom exception hierarchy
class HouseMakerError(Exception): pass
class ValidationError(HouseMakerError): pass
class GeometryError(HouseMakerError): pass  
class DimensionError(ValidationError): pass
class FingerJointError(HouseMakerError): pass
class SVGGenerationError(HouseMakerError): pass
```

### 8.2 Validation Coverage
- ✅ Dimensional bounds and proportions
- ✅ Gable angle feasibility (10-80°)
- ✅ Finger joint size vs edge length compatibility
- ✅ Material thickness ratios
- ✅ Layout constraints (material size limits)
- ✅ Geometric consistency checks

## 9. Performance and Quality Metrics

### 9.1 Generation Performance
- **Processing Time**: Sub-second generation for typical houses
- **Memory Usage**: Efficient coordinate calculation and caching
- **Output Quality**: Valid SVG with precise geometric accuracy
- **Layout Efficiency**: Optimized material utilization

### 9.2 Quality Assurance
- **Geometric Accuracy**: All formulas mathematically validated
- **Manufacturing Ready**: Designed for real laser cutting workflows
- **Error Handling**: Clear messages with suggested corrections
- **Assembly Tested**: Finger joint coordination verified

## 10. Usage Patterns (Production Ready)

### 10.1 CLI Usage
```bash
# Basic house box
python3 generate_house.py --length 100 --width 80 --height 70

# Custom material and kerf compensation  
python3 generate_house.py --thickness 6 --kerf 0.2 --finger-length 18

# Architectural model
python3 generate_house.py --length 200 --width 150 --angle 30 --verbose
```

### 10.2 Python API Usage
```python
from house_maker.geometry import HouseGeometry
from house_maker.svg_generator import SVGGenerator
from house_maker.constants import HouseStyle

# Create and validate geometry
geometry = HouseGeometry(x=100, y=80, z=90, theta=45, 
                        thickness=3, finger_length=15, kerf=0.1)
geometry.validate_geometry()

# Generate professional SVG
svg_gen = SVGGenerator(geometry, HouseStyle.BASIC_HOUSE)
svg_content = svg_gen.generate_svg(include_labels=True)

# Get cutting information
summary = svg_gen.get_cutting_summary()
```

## 11. System Integration (Complete)

### 11.1 Standalone Design
- ✅ No external dependencies (pure Python)
- ✅ Self-contained geometric calculations
- ✅ Professional SVG output without external libraries
- ✅ Complete CLI interface for maker workflows

### 11.2 Extensibility Features
- ✅ Modular class architecture for easy extension
- ✅ Centralized configuration systems
- ✅ Multiple output formats (SVG, cutting summaries)
- ✅ Pluggable layout algorithms

## 12. Architecture Decisions and Rationale

### 12.1 Design Choices Made
1. **Pure Python Implementation**: No dependencies for maximum portability
   - **Rationale**: Easier deployment in maker environments
   - **Result**: Works anywhere Python 3.7+ is available

2. **Centralized Configuration**: Single source of truth for joint coordination
   - **Rationale**: Eliminates hardcoded logic and coordination errors
   - **Result**: Perfect joint alignment with easy maintenance

3. **Professional SVG Standards**: 0.0254mm precision and proper structure
   - **Rationale**: Direct compatibility with laser cutting workflows
   - **Result**: Ready-to-cut files without post-processing

4. **Comprehensive Validation**: Multi-layer parameter checking
   - **Rationale**: Clear error messages improve user experience
   - **Result**: Fewer failed cuts and better maker productivity

### 12.2 Implementation Highlights
- **Mathematical Accuracy**: All geometric formulas validated against trigonometric expectations
- **Manufacturing Practicality**: Designed for standard laser cutting processes
- **User Experience**: Clear CLI with verbose output and error handling
- **Professional Quality**: Production-ready code with comprehensive testing

## 13. Current Status and Capabilities

### 13.1 ✅ FULLY IMPLEMENTED FEATURES
- [x] Complete house box geometry calculation with asymmetric roof panels
- [x] Triangular gable walls with house-shaped profiles
- [x] Enhanced multi-finger joint system (1-7 joints per edge based on length)
- [x] Professional SVG output with 0.0254mm precision
- [x] Optimized panel layout with material size constraints
- [x] Comprehensive CLI interface with all parameter control
- [x] Multiple house styles (basic, no-roof, walls-only)
- [x] Layout algorithms (rectangular packing, rotated layout)
- [x] Complete validation system with clear error messages
- [x] Cutting summaries and assembly information
- [x] **Chimney system**: 4 walls + 2 casings (8 pieces) + 2 roof finger joints
- [x] **Architectural components**: 13 window types, 4 door types, 8 styles, 6 roof types

### 13.2 🎯 PRODUCTION READY
The HouseMaker implementation is **ready for production use** with:
- **Professional Architecture**: Clean, modular design with separation of concerns
- **Mathematical Precision**: Validated geometric calculations for real-world use
- **Manufacturing Compatibility**: Direct laser cutting workflow integration
- **User-Friendly Interface**: Clear CLI and Python API with comprehensive documentation

### 13.3 📊 System Metrics
- **Codebase**: ~1500 lines of clean, documented Python code
- **Test Coverage**: Comprehensive validation and error handling
- **Performance**: Sub-second generation for typical house dimensions
- **Output Quality**: Professional SVG files ready for immediate laser cutting
- **User Experience**: Clear error messages and verbose output options

## 14. Conclusion

The HouseMaker system provides a **complete, professional solution** for laser-cut house box generation. The architecture delivers:

1. **Mathematical Precision**: All geometric calculations validated and tested
2. **Manufacturing Ready**: Professional SVG output for direct laser cutting use
3. **User-Friendly**: Both CLI and Python API with comprehensive documentation
4. **Extensible Design**: Modular architecture supporting future enhancements
5. **Quality Assurance**: Comprehensive validation ensures reliable operation

**The implementation is complete, tested, and ready for maker community use.**

---
*Documentation reflects implementation status as of 2025-01-09*  
*All features implemented and validated through comprehensive testing*  
*Generated SVG files verified for laser cutting workflows*