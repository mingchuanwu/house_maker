"""
Decorative engraving patterns: wall styles, roof tiles, chimney brick.

Everything here is deterministic (no global RNG, no hash()) and depends only on its arguments.
Roof/brick helpers take a panel-local `position` (the panel origin) so they can be reused.
"""

import math
import random
import zlib
from typing import List, Tuple

from .components import ArchitecturalStyle, ShingleType
from .constants import COORDINATE_PRECISION
from .geometry import HouseGeometry, Point


def pattern_scale(panel_bounds: Tuple[float, float]) -> float:
    """Scale factor for decorative patterns (1.0 for a 100x100mm panel)."""
    width, height = panel_bounds
    return max(0.5, min(math.sqrt(width * height / 10000), 3.0))


class ArchitecturalPatternGenerator:
    """Generates decorative patterns for different architectural styles"""
    
    def __init__(self, style: ArchitecturalStyle, house_geometry: HouseGeometry, stone_jitter: bool = True):
        self.style = style
        self.house_geometry = house_geometry
        self.stone_jitter = stone_jitter  # Control jitter in stone pattern
    
    def generate_pattern_for_panel(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate SVG pattern elements for a specific panel"""
        if self.style == ArchitecturalStyle.BASIC:
            return ""  # No decorative elements
        elif self.style == ArchitecturalStyle.FACHWERKHAUS:
            return self._generate_timber_frame_pattern(panel_name, panel_bounds)
        elif self.style == ArchitecturalStyle.FARMHOUSE:
            return self._generate_farmhouse_pattern(panel_name, panel_bounds)
        elif self.style == ArchitecturalStyle.COLONIAL:
            return self._generate_colonial_pattern(panel_name, panel_bounds)
        elif self.style == ArchitecturalStyle.BRICK:
            return self._generate_brick_pattern(panel_name, panel_bounds)
        elif self.style == ArchitecturalStyle.STONE:
            return self._generate_stone_pattern(panel_name, panel_bounds)
        elif self.style == ArchitecturalStyle.VICTORIAN:
            return self._generate_victorian_pattern(panel_name, panel_bounds)
        elif self.style == ArchitecturalStyle.TUDOR:
            return self._generate_tudor_pattern(panel_name, panel_bounds)
        elif self.style == ArchitecturalStyle.CRAFTSMAN:
            return self._generate_craftsman_pattern(panel_name, panel_bounds)
        elif self.style == ArchitecturalStyle.GINGERBREAD:
            return self._generate_gingerbread_pattern(panel_name, panel_bounds)
        else:
            return ""
    
    def _generate_timber_frame_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate German Fachwerkhaus timber frame pattern"""
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = pattern_scale(panel_bounds)
        
        # Create timber frame lines with proportional spacing
        lines = []
        
        # Calculate proportional spacing
        post_spacing = max(20 * scale, width / 4)  # Minimum 20mm scaled, or quarter width
        beam_height = height * 0.618  # Golden ratio positioning
        
        # Vertical posts with proportional spacing
        x = post_spacing
        while x < width - margin:
            lines.append(f"M {x:.{COORDINATE_PRECISION}f},{margin:.{COORDINATE_PRECISION}f} "
                        f"L {x:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f}")
            x += post_spacing
        
        # Horizontal beams
        if height > 30 * scale:  # Scaled minimum height
            lines.append(f"M {margin:.{COORDINATE_PRECISION}f},{beam_height:.{COORDINATE_PRECISION}f} "
                        f"L {width-margin:.{COORDINATE_PRECISION}f},{beam_height:.{COORDINATE_PRECISION}f}")
        
        # Diagonal braces with proportional dimensions
        brace_size = min(width, height) * 0.25 * scale
        brace_start_x = width * 0.15
        brace_end_x = brace_start_x + brace_size
        brace_start_y = height * 0.25
        brace_end_y = brace_start_y + brace_size
        
        # Only add braces if there's room
        if brace_end_x < width - margin and brace_end_y < height - margin:
            lines.append(f"M {brace_start_x:.{COORDINATE_PRECISION}f},{brace_start_y:.{COORDINATE_PRECISION}f} "
                        f"L {brace_end_x:.{COORDINATE_PRECISION}f},{brace_end_y:.{COORDINATE_PRECISION}f}")
            
            # Mirror diagonal
            mirror_start_x = width - brace_start_x
            mirror_end_x = width - brace_end_x
            lines.append(f"M {mirror_start_x:.{COORDINATE_PRECISION}f},{brace_start_y:.{COORDINATE_PRECISION}f} "
                        f"L {mirror_end_x:.{COORDINATE_PRECISION}f},{brace_end_y:.{COORDINATE_PRECISION}f}")
        
        return " ".join(lines)
    
    def _generate_farmhouse_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate American farmhouse pattern (board and batten)"""
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = pattern_scale(panel_bounds)
        
        lines = []
        
        # Proportional board spacing (12-20mm scaled)
        board_spacing = max(12 * scale, 8.0)  # Minimum 8mm for manufacturability
        x = margin + board_spacing
        
        while x < width - margin:
            lines.append(f"M {x:.{COORDINATE_PRECISION}f},{margin:.{COORDINATE_PRECISION}f} "
                        f"L {x:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f}")
            x += board_spacing
        
        return " ".join(lines)
    
    def _generate_colonial_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate Colonial style pattern (clapboard siding)"""
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = pattern_scale(panel_bounds)
        
        lines = []
        
        # Proportional clapboard spacing (6-10mm scaled)
        siding_spacing = max(6 * scale, 4.0)  # Minimum 4mm for manufacturability
        y = margin + siding_spacing
        
        while y < height - margin:
            lines.append(f"M {margin:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                        f"L {width-margin:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")
            y += siding_spacing
        
        return " ".join(lines)
    
    def _generate_brick_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate brick pattern"""
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = pattern_scale(panel_bounds)
        
        lines = []
        # Proportional brick dimensions
        brick_height = max(4 * scale, 3.0)  # Minimum 3mm
        brick_width = brick_height * 2  # Maintain 2:1 ratio
        
        y = margin
        row = 0
        while y < height - margin - brick_height:
            # Offset every other row for brick pattern
            x_offset = (brick_width / 2) if row % 2 == 1 else 0
            x = margin + x_offset
            
            # Horizontal mortar line
            lines.append(f"M {margin:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                        f"L {width-margin:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")
            
            # Vertical mortar lines
            while x < width - margin:
                if x > margin:  # Don't draw line at very edge
                    lines.append(f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                                f"L {x:.{COORDINATE_PRECISION}f},{y+brick_height:.{COORDINATE_PRECISION}f}")
                x += brick_width
            
            y += brick_height
            row += 1
        
        return " ".join(lines)
    
    def _generate_stone_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate irregular stone wall pattern with natural jitter and gaps"""
        # Skip roof panels - they use shingle patterns instead
        if 'roof' in panel_name.lower():
            return ""
        
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = pattern_scale(panel_bounds)
        
        lines = []
        
        # Stone pattern with irregular blocks and natural-looking mortar lines
        # Add subtle jitter and occasional gaps for realism
        
        # Stable per-panel seed (str hash() is randomised per process) and a private RNG so the
        # global random state is never touched.
        rng = random.Random(zlib.crc32(panel_name.encode('utf-8')) % 1000)
        
        y = margin
        row = 0
        
        # Define some varied stone heights (scaled appropriately)
        stone_heights = [6 * scale, 8 * scale, 7 * scale, 5 * scale, 9 * scale]
        
        # Further reduced jitter parameters for subtle natural irregularity
        # Only apply if jitter is enabled
        if self.stone_jitter:
            max_jitter = 0.15 * scale  # Very subtle offset for line endpoints
            gap_chance = 0.08  # 8% chance of a small gap in mortar line
        else:
            max_jitter = 0.0  # No jitter - perfectly straight lines
            gap_chance = 0.0  # No gaps
        
        while y < height - margin:
            # Get stone height for this row (cycle through variations)
            stone_height = stone_heights[row % len(stone_heights)]
            
            # Don't exceed panel bounds
            if y + stone_height > height - margin:
                stone_height = height - margin - y
            
            # Draw horizontal mortar line with jitter and gaps
            x_line = margin
            while x_line < width - margin:
                # Subtle jitter for this segment
                y_jitter_start = y + rng.uniform(-max_jitter, max_jitter)
                y_jitter_end = y + rng.uniform(-max_jitter, max_jitter)
                
                # Random segment length (with occasional gaps)
                if rng.random() < gap_chance:
                    # Small gap in mortar line
                    segment_length = rng.uniform(2 * scale, 4 * scale)
                    x_line += segment_length
                    continue
                else:
                    segment_length = rng.uniform(12 * scale, 22 * scale)
                
                x_end = min(x_line + segment_length, width - margin)
                
                lines.append(f"M {x_line:.{COORDINATE_PRECISION}f},{y_jitter_start:.{COORDINATE_PRECISION}f} "
                            f"L {x_end:.{COORDINATE_PRECISION}f},{y_jitter_end:.{COORDINATE_PRECISION}f}")
                
                x_line = x_end
            
            # Generate stones of varying widths across this row
            x = margin
            stone_index = 0
            
            # Vary starting offset for each row to create irregular pattern
            if row % 2 == 1:
                first_stone_width = (8 + (row % 3) * 3) * scale
            else:
                first_stone_width = (12 + (row % 3) * 4) * scale
            
            # Define varied stone widths for this row
            stone_widths = [
                first_stone_width,
                (10 + (row % 4) * 2) * scale,
                (15 + (row % 3) * 3) * scale,
                (8 + (row % 5) * 2) * scale,
                (12 + (row % 3) * 2) * scale,
                (9 + (row % 4) * 3) * scale
            ]
            
            while x < width - margin:
                # Get stone width for this position
                stone_width = stone_widths[stone_index % len(stone_widths)]
                
                # Adjust last stone in row to fit
                if x + stone_width > width - margin:
                    stone_width = width - margin - x
                
                # Draw vertical mortar line with jitter and gaps (but not at very beginning)
                if x > margin + 0.1:
                    y_line = y
                    while y_line < y + stone_height:
                        # Subtle jitter for this segment
                        x_jitter_start = x + rng.uniform(-max_jitter, max_jitter)
                        x_jitter_end = x + rng.uniform(-max_jitter, max_jitter)
                        
                        # Random segment length (with occasional gaps)
                        if rng.random() < gap_chance:
                            # Small gap in mortar line
                            segment_length = rng.uniform(1.5 * scale, 3 * scale)
                            y_line += segment_length
                            continue
                        else:
                            segment_length = rng.uniform(6 * scale, 12 * scale)
                        
                        y_end = min(y_line + segment_length, y + stone_height)
                        
                        lines.append(f"M {x_jitter_start:.{COORDINATE_PRECISION}f},{y_line:.{COORDINATE_PRECISION}f} "
                                    f"L {x_jitter_end:.{COORDINATE_PRECISION}f},{y_end:.{COORDINATE_PRECISION}f}")
                        
                        y_line = y_end
                
                x += stone_width
                stone_index += 1
            
            y += stone_height
            row += 1
        
        # Draw bottom border line with subtle jitter
        x_line = margin
        while x_line < width - margin:
            y_jitter_start = y + rng.uniform(-max_jitter, max_jitter)
            y_jitter_end = y + rng.uniform(-max_jitter, max_jitter)
            
            if rng.random() < gap_chance:
                segment_length = rng.uniform(2 * scale, 4 * scale)
                x_line += segment_length
                continue
            else:
                segment_length = rng.uniform(12 * scale, 22 * scale)
            
            x_end = min(x_line + segment_length, width - margin)
            
            lines.append(f"M {x_line:.{COORDINATE_PRECISION}f},{y_jitter_start:.{COORDINATE_PRECISION}f} "
                        f"L {x_end:.{COORDINATE_PRECISION}f},{y_jitter_end:.{COORDINATE_PRECISION}f}")
            
            x_line = x_end
        
        return " ".join(lines)
    
    def _generate_victorian_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate Victorian ornate pattern"""
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = pattern_scale(panel_bounds)
        
        lines = []
        
        # Decorative corner brackets
        bracket_size = min(width, height) * 0.1 * scale
        
        # Top corners
        lines.append(f"M {margin:.{COORDINATE_PRECISION}f},{height-margin-bracket_size:.{COORDINATE_PRECISION}f} "
                    f"Q {margin:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f} "
                    f"{margin+bracket_size:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f}")
        
        lines.append(f"M {width-margin-bracket_size:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f} "
                    f"Q {width-margin:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f} "
                    f"{width-margin:.{COORDINATE_PRECISION}f},{height-margin-bracket_size:.{COORDINATE_PRECISION}f}")
        
        return " ".join(lines)
    
    def _generate_tudor_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate Tudor revival pattern (similar to timber frame)"""
        # Tudor is similar to Fachwerkhaus but with more decorative elements
        base_pattern = self._generate_timber_frame_pattern(panel_name, panel_bounds)
        
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = pattern_scale(panel_bounds)
        
        # Add Tudor-specific decorative elements
        decorative_lines = []
        
        # Decorative arch over potential door area
        if panel_name.startswith('gable_wall') and height > 50 * scale:
            arch_center_x = width / 2
            arch_y = margin + 25 * scale
            arch_radius = 8 * scale
            
            # Simple arch using quadratic curve
            decorative_lines.append(
                f"M {arch_center_x-arch_radius:.{COORDINATE_PRECISION}f},{arch_y:.{COORDINATE_PRECISION}f} "
                f"Q {arch_center_x:.{COORDINATE_PRECISION}f},{arch_y-arch_radius:.{COORDINATE_PRECISION}f} "
                f"{arch_center_x+arch_radius:.{COORDINATE_PRECISION}f},{arch_y:.{COORDINATE_PRECISION}f}"
            )
        
        if decorative_lines:
            return base_pattern + " " + " ".join(decorative_lines)
        return base_pattern
    
    def _generate_craftsman_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate Craftsman/Arts and Crafts pattern"""
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = pattern_scale(panel_bounds)
        
        lines = []
        
        # Horizontal emphasis lines at key proportions
        if height > 30 * scale:
            # Line at 1/3 height
            third_y = height * (1/3)
            lines.append(f"M {margin:.{COORDINATE_PRECISION}f},{third_y:.{COORDINATE_PRECISION}f} "
                        f"L {width-margin:.{COORDINATE_PRECISION}f},{third_y:.{COORDINATE_PRECISION}f}")
        
        if height > 45 * scale:
            # Line at 2/3 height
            two_third_y = height * (2/3)
            lines.append(f"M {margin:.{COORDINATE_PRECISION}f},{two_third_y:.{COORDINATE_PRECISION}f} "
                        f"L {width-margin:.{COORDINATE_PRECISION}f},{two_third_y:.{COORDINATE_PRECISION}f}")
        
        # Vertical accent lines at edges
        accent_offset = margin + 2 * scale
        lines.append(f"M {accent_offset:.{COORDINATE_PRECISION}f},{margin:.{COORDINATE_PRECISION}f} "
                    f"L {accent_offset:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f}")
        
        lines.append(f"M {width-accent_offset:.{COORDINATE_PRECISION}f},{margin:.{COORDINATE_PRECISION}f} "
                    f"L {width-accent_offset:.{COORDINATE_PRECISION}f},{height-margin:.{COORDINATE_PRECISION}f}")
        
        return " ".join(lines)
    
    def _generate_gingerbread_pattern(self, panel_name: str, panel_bounds: Tuple[float, float]) -> str:
        """Generate gingerbread house decorative patterns inspired by advent calendar houses.
        
        Creates festive decorative elements including:
        - Scalloped roof edge trim
        - Decorative star and heart cutouts
        - Ornamental border patterns
        - Festive swirl elements
        """
        width, height = panel_bounds
        margin = self.house_geometry.thickness
        scale = pattern_scale(panel_bounds)
        
        lines = []
        
        # Gingerbread patterns vary by panel type
        if "roof" in panel_name:
            # Scalloped decorative edge trim for roof panels
            lines.extend(self._generate_scalloped_trim(width, height, margin, scale))
            
        elif "gable" in panel_name:
            # Front/back gable walls get decorative stars and border trim
            lines.extend(self._generate_decorative_stars(width, height, margin, scale))
            lines.extend(self._generate_ornamental_border(width, height, margin, scale))
            
        elif "side" in panel_name:
            # Side walls get hearts and swirl patterns
            lines.extend(self._generate_decorative_hearts(width, height, margin, scale))
            lines.extend(self._generate_festive_swirls(width, height, margin, scale))
            
        return " ".join(lines)
    
    def _generate_scalloped_trim(self, width: float, height: float, margin: float, scale: float) -> List[str]:
        """Generate scalloped decorative trim along roof edges."""
        lines = []
        
        # Scalloped edge along the bottom edge of roof panels
        scallop_width = 8.0 * scale
        scallop_depth = 3.0 * scale
        num_scallops = int(width / scallop_width)
        
        if num_scallops > 0:
            path_parts = [f"M {margin:.{COORDINATE_PRECISION}f} {height - margin - scallop_depth:.{COORDINATE_PRECISION}f}"]
            
            for i in range(num_scallops):
                scallop_x = margin + i * scallop_width
                # Create curved scallop using quadratic bezier
                if scallop_x + scallop_width < width - margin:
                    mid_x = scallop_x + scallop_width / 2
                    end_x = scallop_x + scallop_width
                    path_parts.append(f" Q {mid_x:.{COORDINATE_PRECISION}f} {height - margin:.{COORDINATE_PRECISION}f} {end_x:.{COORDINATE_PRECISION}f} {height - margin - scallop_depth:.{COORDINATE_PRECISION}f}")
            
            lines.append("".join(path_parts))
        
        return lines
    
    def _generate_decorative_stars(self, width: float, height: float, margin: float, scale: float) -> List[str]:
        """Generate decorative star cutouts for gingerbread houses."""
        lines = []
        
        # Avoid putting decorations too close to edges
        safe_margin = margin + 5 * scale
        safe_width = width - 2 * safe_margin
        safe_height = height - 2 * safe_margin
        
        star_size = 6.0 * scale
        if safe_width > star_size * 2 and safe_height > star_size * 2:
            # Place star in upper area of panel
            star_x = safe_margin + safe_width / 2
            star_y = safe_margin + safe_height * 0.7
            
            # Generate 5-pointed star path
            star_path = self._generate_star_path(star_x, star_y, star_size)
            lines.append(star_path)
        
        return lines
    
    def _generate_decorative_hearts(self, width: float, height: float, margin: float, scale: float) -> List[str]:
        """Generate decorative heart cutouts for gingerbread houses."""
        lines = []
        
        # Avoid putting decorations too close to edges
        safe_margin = margin + 5 * scale
        safe_width = width - 2 * safe_margin
        safe_height = height - 2 * safe_margin
        
        heart_size = 5.0 * scale
        if safe_width > heart_size * 2 and safe_height > heart_size * 2:
            # Place heart in upper area of panel
            heart_x = safe_margin + safe_width / 2
            heart_y = safe_margin + safe_height * 0.7
            
            # Generate heart path using bezier curves
            heart_path = self._generate_heart_path(heart_x, heart_y, heart_size)
            lines.append(heart_path)
        
        return lines
    
    def _generate_ornamental_border(self, width: float, height: float, margin: float, scale: float) -> List[str]:
        """Generate ornamental border trim around panel edges."""
        lines = []
        
        border_inset = margin + 3.0 * scale
        corner_radius = 2.0 * scale
        
        if border_inset + corner_radius < width / 2 and border_inset + corner_radius < height / 2:
            # Decorative border around panel perimeter
            border_path = (f"M {border_inset + corner_radius:.{COORDINATE_PRECISION}f} {border_inset:.{COORDINATE_PRECISION}f} "
                          f"L {width - border_inset - corner_radius:.{COORDINATE_PRECISION}f} {border_inset:.{COORDINATE_PRECISION}f} "
                          f"Q {width - border_inset:.{COORDINATE_PRECISION}f} {border_inset:.{COORDINATE_PRECISION}f} {width - border_inset:.{COORDINATE_PRECISION}f} {border_inset + corner_radius:.{COORDINATE_PRECISION}f} "
                          f"L {width - border_inset:.{COORDINATE_PRECISION}f} {height - border_inset - corner_radius:.{COORDINATE_PRECISION}f} "
                          f"Q {width - border_inset:.{COORDINATE_PRECISION}f} {height - border_inset:.{COORDINATE_PRECISION}f} {width - border_inset - corner_radius:.{COORDINATE_PRECISION}f} {height - border_inset:.{COORDINATE_PRECISION}f} "
                          f"L {border_inset + corner_radius:.{COORDINATE_PRECISION}f} {height - border_inset:.{COORDINATE_PRECISION}f} "
                          f"Q {border_inset:.{COORDINATE_PRECISION}f} {height - border_inset:.{COORDINATE_PRECISION}f} {border_inset:.{COORDINATE_PRECISION}f} {height - border_inset - corner_radius:.{COORDINATE_PRECISION}f} "
                          f"L {border_inset:.{COORDINATE_PRECISION}f} {border_inset + corner_radius:.{COORDINATE_PRECISION}f} "
                          f"Q {border_inset:.{COORDINATE_PRECISION}f} {border_inset:.{COORDINATE_PRECISION}f} {border_inset + corner_radius:.{COORDINATE_PRECISION}f} {border_inset:.{COORDINATE_PRECISION}f} Z")
            
            lines.append(border_path)
        
        return lines
    
    def _generate_festive_swirls(self, width: float, height: float, margin: float, scale: float) -> List[str]:
        """Generate festive swirl decorations for gingerbread houses."""
        lines = []
        
        # Avoid putting decorations too close to edges
        safe_margin = margin + 5 * scale
        safe_width = width - 2 * safe_margin
        safe_height = height - 2 * safe_margin
        
        swirl_size = 4.0 * scale
        if safe_width > swirl_size * 3 and safe_height > swirl_size * 3:
            # Place swirl in corner of safe area
            swirl_x = safe_margin + swirl_size * 1.5
            swirl_y = safe_margin + swirl_size * 1.5
            
            # Generate spiral swirl path
            swirl_path = self._generate_swirl_path(swirl_x, swirl_y, swirl_size)
            lines.append(swirl_path)
        
        return lines
    
    def _generate_star_path(self, cx: float, cy: float, size: float) -> str:
        """Generate SVG path for a 5-pointed star."""
        
        points = []
        for i in range(10):  # 5 outer + 5 inner points
            angle = (i * math.pi) / 5  # 36 degrees between points
            radius = size if i % 2 == 0 else size * 0.4  # Alternate outer/inner radius
            x = cx + radius * math.cos(angle - math.pi/2)  # Start from top
            y = cy + radius * math.sin(angle - math.pi/2)
            points.append((x, y))
        
        path_data = f"M {points[0][0]:.{COORDINATE_PRECISION}f} {points[0][1]:.{COORDINATE_PRECISION}f}"
        for point in points[1:]:
            path_data += f" L {point[0]:.{COORDINATE_PRECISION}f} {point[1]:.{COORDINATE_PRECISION}f}"
        path_data += " Z"
        
        return path_data
    
    def _generate_heart_path(self, cx: float, cy: float, size: float) -> str:
        """Generate SVG path for a heart shape."""
        # Heart shape using bezier curves
        path_data = (f"M {cx:.{COORDINATE_PRECISION}f} {cy + size * 0.3:.{COORDINATE_PRECISION}f} "  # Bottom point
                    f"C {cx - size * 0.6:.{COORDINATE_PRECISION}f} {cy - size * 0.1:.{COORDINATE_PRECISION}f} {cx - size * 0.6:.{COORDINATE_PRECISION}f} {cy - size * 0.6:.{COORDINATE_PRECISION}f} {cx:.{COORDINATE_PRECISION}f} {cy - size * 0.3:.{COORDINATE_PRECISION}f} "  # Left curve
                    f"C {cx + size * 0.6:.{COORDINATE_PRECISION}f} {cy - size * 0.6:.{COORDINATE_PRECISION}f} {cx + size * 0.6:.{COORDINATE_PRECISION}f} {cy - size * 0.1:.{COORDINATE_PRECISION}f} {cx:.{COORDINATE_PRECISION}f} {cy + size * 0.3:.{COORDINATE_PRECISION}f} "  # Right curve
                    f"Z")
        
        return path_data
    
    def _generate_swirl_path(self, cx: float, cy: float, size: float) -> str:
        """Generate SVG path for a decorative swirl."""
        # Spiral swirl using multiple curves
        path_data = (f"M {cx:.{COORDINATE_PRECISION}f} {cy:.{COORDINATE_PRECISION}f} "
                    f"Q {cx + size * 0.5:.{COORDINATE_PRECISION}f} {cy - size * 0.3:.{COORDINATE_PRECISION}f} {cx + size * 0.7:.{COORDINATE_PRECISION}f} {cy:.{COORDINATE_PRECISION}f} "
                    f"Q {cx + size * 0.5:.{COORDINATE_PRECISION}f} {cy + size * 0.5:.{COORDINATE_PRECISION}f} {cx:.{COORDINATE_PRECISION}f} {cy + size * 0.3:.{COORDINATE_PRECISION}f} "
                    f"Q {cx - size * 0.3:.{COORDINATE_PRECISION}f} {cy:.{COORDINATE_PRECISION}f} {cx - size * 0.1:.{COORDINATE_PRECISION}f} {cy - size * 0.2:.{COORDINATE_PRECISION}f}")
        
        return path_data


# ---------------------------------------------------------------------------
# Roof patterns
# ---------------------------------------------------------------------------

def roof_pattern(shingle_type: ShingleType, position: Point, width: float, height: float) -> str:
    """Tile/shingle engraving for a rectangular roof panel."""
    if shingle_type == ShingleType.SPANTILE:
        return _generate_spantile_pattern(position, width, height)
    if shingle_type == ShingleType.SPANISH:
        return _generate_spanish_tile_pattern(position, width, height)
    if shingle_type == ShingleType.SCALLOPS:
        return _generate_scallop_pattern(position, width, height)
    if shingle_type == ShingleType.S_TILE:
        return _generate_s_tile_pattern(position, width, height)
    return _generate_standard_shingles_pattern(position, width, height)


def _generate_standard_shingles_pattern(position: Point, width: float, height: float) -> str:
    """Generate standard rectangular shingles pattern"""
    margin = 0.8
    lines = []

    shingle_height = 4.0
    shingle_width = 8.0
    overlap = 1.5

    y = position.y + margin
    y_end = position.y + height - margin
    row = 0

    while y < y_end:
        next_y = min(y + shingle_height - overlap, y_end)

        row_start_x = position.x + margin
        row_end_x = position.x + width - margin

        # Horizontal line
        lines.append(f"M {row_start_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                    f"L {row_end_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")

        # Vertical lines with offset
        x_offset = (shingle_width / 2) if row % 2 == 1 else 0
        x = row_start_x + x_offset

        while x < row_end_x - 0.1:
            if x > row_start_x + 0.1:
                line_end_y = min(y + shingle_height, y_end)
                lines.append(f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                            f"L {x:.{COORDINATE_PRECISION}f},{line_end_y:.{COORDINATE_PRECISION}f}")
            x += shingle_width

        y = next_y
        row += 1

    return " ".join(lines)

def _generate_spantile_pattern(position: Point, width: float, height: float) -> str:
    """Generate Spanish tile (Spantile) pattern with wavy curves"""
    margin = 0.8
    lines = []

    tile_height = 5.0  # Height of each tile row
    tile_width = 6.0   # Width of individual tiles

    y = position.y + margin
    y_end = position.y + height - margin
    row = 0

    while y < y_end:
        row_start_x = position.x + margin
        row_end_x = position.x + width - margin

        # Wavy horizontal line using quadratic curves
        x = row_start_x
        path_parts = [f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}"]

        while x < row_end_x:
            next_x = min(x + tile_width, row_end_x)
            mid_x = (x + next_x) / 2
            # Create wave with control point above the line
            path_parts.append(f" Q {mid_x:.{COORDINATE_PRECISION}f},{y - 1.5:.{COORDINATE_PRECISION}f} {next_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")
            x = next_x

        lines.append("".join(path_parts))

        y += tile_height
        row += 1

    return " ".join(lines)

def _generate_spanish_tile_pattern(position: Point, width: float, height: float) -> str:
    """Generate Spanish tile pattern with rounded edges"""
    margin = 0.8
    lines = []

    tile_height = 5.0
    tile_width = 7.0

    y = position.y + margin
    y_end = position.y + height - margin
    row = 0

    while y < y_end:
        row_start_x = position.x + margin
        row_end_x = position.x + width - margin

        # Horizontal line
        lines.append(f"M {row_start_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                    f"L {row_end_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")

        # Rounded vertical separators
        x_offset = (tile_width / 2) if row % 2 == 1 else 0
        x = row_start_x + x_offset

        while x < row_end_x - 0.1:
            if x > row_start_x + 0.1:
                # Curved vertical line for tile edge
                curve_y = min(y + tile_height, y_end)
                mid_y = (y + curve_y) / 2
                lines.append(f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                            f"Q {x + 0.5:.{COORDINATE_PRECISION}f},{mid_y:.{COORDINATE_PRECISION}f} "
                            f"{x:.{COORDINATE_PRECISION}f},{curve_y:.{COORDINATE_PRECISION}f}")
            x += tile_width

        y += tile_height
        row += 1

    return " ".join(lines)

def _generate_scallop_pattern(position: Point, width: float, height: float) -> str:
    """Generate scalloped/fish-scale shingles pattern"""
    margin = 0.8
    lines = []

    scale_height = 4.0  # Height of each scallop row
    scale_width = 5.0   # Width of individual scallops
    overlap = 2.0       # Vertical overlap

    y = position.y + margin
    y_end = position.y + height - margin
    row = 0

    while y < y_end:
        row_start_x = position.x + margin
        row_end_x = position.x + width - margin

        # Offset every other row
        x_offset = (scale_width / 2) if row % 2 == 1 else 0
        x = row_start_x + x_offset

        # Draw scalloped bottom edges for each scale
        while x < row_end_x:
            next_x = min(x + scale_width, row_end_x)
            if next_x - x > scale_width * 0.3:  # Only draw if wide enough
                mid_x = (x + next_x) / 2
                curve_y = min(y + scale_height, y_end)
                # Scallop curve pointing down
                lines.append(f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                            f"Q {mid_x:.{COORDINATE_PRECISION}f},{curve_y:.{COORDINATE_PRECISION}f} "
                            f"{next_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")
            x += scale_width

        y += scale_height - overlap
        row += 1

    return " ".join(lines)

def _generate_s_tile_pattern(position: Point, width: float, height: float) -> str:
    """Generate S-shaped tiles pattern with alternating curves"""
    margin = 0.8
    lines = []

    tile_height = 5.0
    tile_width = 6.0

    y = position.y + margin
    y_end = position.y + height - margin
    row = 0

    while y < y_end:
        row_start_x = position.x + margin
        row_end_x = position.x + width - margin

        # S-shaped curves
        x = row_start_x
        while x < row_end_x:
            next_x = min(x + tile_width, row_end_x)
            if next_x - x > tile_width * 0.3:
                mid_x = (x + next_x) / 2
                curve_y = min(y + tile_height, y_end)
                mid_y = (y + curve_y) / 2

                # S-curve: up then down (or down then up for alternating rows)
                if row % 2 == 0:
                    lines.append(f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                                f"Q {x:.{COORDINATE_PRECISION}f},{mid_y:.{COORDINATE_PRECISION}f} "
                                f"{mid_x:.{COORDINATE_PRECISION}f},{mid_y:.{COORDINATE_PRECISION}f} "
                                f"Q {next_x:.{COORDINATE_PRECISION}f},{mid_y:.{COORDINATE_PRECISION}f} "
                                f"{next_x:.{COORDINATE_PRECISION}f},{curve_y:.{COORDINATE_PRECISION}f}")
                else:
                    lines.append(f"M {x:.{COORDINATE_PRECISION}f},{curve_y:.{COORDINATE_PRECISION}f} "
                                f"Q {x:.{COORDINATE_PRECISION}f},{mid_y:.{COORDINATE_PRECISION}f} "
                                f"{mid_x:.{COORDINATE_PRECISION}f},{mid_y:.{COORDINATE_PRECISION}f} "
                                f"Q {next_x:.{COORDINATE_PRECISION}f},{mid_y:.{COORDINATE_PRECISION}f} "
                                f"{next_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")
            x += tile_width

        y += tile_height
        row += 1

    return " ".join(lines)


# ---------------------------------------------------------------------------
# Chimney brick
# ---------------------------------------------------------------------------

def chimney_brick_pattern(wall_name: str, position: Point, width: float, height: float, corners: List[Point]) -> str:
    """
    Generate brick pattern for chimney panels with 0.1mm line width
    Properly fills trapezoid from bottom sloped edge to top, and rectangles completely

    Args:
        position: Base position of the panel
        width: Width of the panel
        height: Height of the panel (for trapezoid, this is the maximum height)
        corners: Corner points of the panel (for trapezoid boundaries)

    Returns:
        SVG path string for brick pattern
    """

    margin = 0.8  # Margin to avoid touching panel edges

    lines = []

    # Brick dimensions
    brick_height = 2.5  # 2.5mm brick height
    brick_width = brick_height * 2.5

    # Determine if this is a trapezoid panel
    # Check if top edge (corners[0] to corners[1]) is diagonal (Y values differ)
    if len(corners) == 4:
        is_trapezoid = abs(corners[0].y - corners[1].y) > 0.01
    else:
        is_trapezoid = False

    if is_trapezoid:
        # Detect if this is a mirrored trapezoid (right panel) by checking if slope goes opposite direction
        # Standard: corners[0].y < corners[1].y (left edge lower, right edge higher)
        # Mirrored: corners[0].y > corners[1].y (left edge higher, right edge lower)
        is_mirrored = corners[0].y > corners[1].y

        # CRITICAL: Use actual corner Y values, NOT the height parameter
        # The height parameter doesn't include height_diff from slope
        y_min = min(c.y for c in corners)  # Top of shape
        y_max = max(c.y for c in corners)  # Bottom of shape - THIS IS THE ACTUAL MAX Y

        if is_mirrored:
            # Mirrored trapezoid (right panel): corners[1].y < corners[0].y
            # Diagonal is on LEFT side, vertical is on RIGHT side
            slope_end_y = corners[0].y  # Where diagonal ends (higher Y)

            def get_bounds_at_y(y_pos):
                """Get left and right X bounds at given Y position for mirrored trapezoid"""
                if y_pos <= slope_end_y:
                    # In sloped region: left edge is diagonal, right edge is vertical
                    # Interpolate left edge from corners[1] to corners[0]
                    if slope_end_y > corners[1].y:
                        t = (y_pos - corners[1].y) / (slope_end_y - corners[1].y)
                    else:
                        t = 0.0
                    left_x = corners[1].x + t * (corners[0].x - corners[1].x)  # Interpolate left
                    right_x = corners[1].x  # Right is always at same X
                else:
                    # In rectangular region: both edges are vertical
                    left_x = corners[3].x  # Bottom-left X
                    right_x = corners[2].x  # Bottom-right X
                return left_x, right_x
        else:
            # Standard trapezoid (left panel): corners[0].y < corners[1].y
            # Diagonal is on RIGHT side, vertical is on LEFT side
            slope_end_y = corners[1].y  # Where diagonal ends

            def get_bounds_at_y(y_pos):
                """Get left and right X bounds at given Y position for standard trapezoid"""
                if y_pos <= slope_end_y:
                    # In sloped region: left edge is vertical, right edge is diagonal
                    # Interpolate right edge from corners[0] to corners[1]
                    if slope_end_y > corners[0].y:
                        t = (y_pos - corners[0].y) / (slope_end_y - corners[0].y)
                    else:
                        t = 0.0
                    left_x = corners[0].x  # Left is always at same X
                    right_x = corners[0].x + t * (corners[1].x - corners[0].x)  # Interpolate right
                else:
                    # In rectangular region: both edges are vertical
                    left_x = corners[3].x  # Bottom-left X
                    right_x = corners[2].x  # Bottom-right X
                return left_x, right_x
    else:
        # Rectangle
        y_min = position.y
        y_max = position.y + height

        def get_bounds_at_y(y_pos):
            """Get left and right X bounds (constant for rectangle)"""
            return position.x, position.x + width

    # Start from top (smallest Y) with margin
    y = y_min + margin
    y_end = y_max - margin
    row = 0


    # Fill entire height from bottom to top
    while y < y_end:
        # Get bounds at current Y
        left_x, right_x = get_bounds_at_y(y)
        row_start_x = left_x + margin
        row_end_x = right_x - margin
        row_width = row_end_x - row_start_x

        # Calculate next row Y first
        next_y = min(y + brick_height, y_end)

        # Skip drawing if too narrow, but always advance Y
        # UNLESS we're very close to y_end (within one brick_height)
        if row_width < brick_width * 0.3:
            if y_end - y > brick_height:  # Still have significant distance to go
                y += brick_height
                row += 1
                continue
            else:  # Close to end, break out to avoid getting stuck
                break

        # Get bounds at next Y for proper clipping
        left_x_next, right_x_next = get_bounds_at_y(next_y)
        row_start_x_next = left_x_next + margin
        row_end_x_next = right_x_next - margin

        # Draw horizontal mortar line at current Y (clipped to current width)
        lines.append(f"M {row_start_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                    f"L {row_end_x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")

        # Offset for brick bond pattern
        x_offset = (brick_width / 2) if row % 2 == 1 else 0
        x = row_start_x + x_offset

        # Draw vertical mortar lines - these may be angled for trapezoids
        first_brick_x = x  # Remember first position
        brick_num = 0
        while x < row_end_x:
            # Draw vertical line for all bricks EXCEPT at the very first position (left edge)
            # AND the very last position (right edge)
            if x > first_brick_x + 0.1 and x < row_end_x - 0.1:
                # For vertical line, clip to bounds at both Y levels
                x_bottom = x  # X at current level

                # Clip to bounds at next level
                if x_bottom < row_start_x_next:
                    x_bottom = row_start_x_next
                if x_bottom > row_end_x_next:
                    x_bottom = row_end_x_next

                # Only draw if within bounds at both levels
                if row_start_x <= x <= row_end_x and row_start_x_next <= x_bottom <= row_end_x_next:
                    lines.append(f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                                f"L {x_bottom:.{COORDINATE_PRECISION}f},{next_y:.{COORDINATE_PRECISION}f}")

            x += brick_width
            brick_num += 1

        y = next_y
        row += 1

    # Add final horizontal line at bottom (clipped)
    if lines:
        left_x_bottom, right_x_bottom = get_bounds_at_y(y_end)
        bottom_start_x = left_x_bottom + margin
        bottom_end_x = right_x_bottom - margin

        if bottom_end_x > bottom_start_x + 0.1:
            lines.append(f"M {bottom_start_x:.{COORDINATE_PRECISION}f},{y_end:.{COORDINATE_PRECISION}f} "
                        f"L {bottom_end_x:.{COORDINATE_PRECISION}f},{y_end:.{COORDINATE_PRECISION}f}")

    return " ".join(lines)


def polygon_shingles_pattern(polygon, margin: float = 0.5, row_height: float = 2.0,
                             tile_length: float = 4.0) -> str:
    """
    Shingle engraving for a convex roof polygon whose *rows run along y* (the ridge direction) and
    stack along x (up the rafter). Rows are clipped to the polygon, inset by `margin`.
    """
    xs = [p.x for p in polygon]
    lines = []
    edges = list(zip(polygon, polygon[1:] + polygon[:1]))

    def y_extent(x):
        ys = []
        for a, b in edges:
            if (a.x - x) * (b.x - x) <= 0 and a.x != b.x:
                ys.append(a.y + (b.y - a.y) * (x - a.x) / (b.x - a.x))
        return (min(ys), max(ys)) if len(ys) >= 2 else None

    x, row = min(xs) + margin, 0
    while x < max(xs) - margin:
        ext = y_extent(x)
        if ext and ext[1] - ext[0] > tile_length + 2 * margin:
            y0, y1 = ext[0] + margin, ext[1] - margin
            lines.append(f"M {x:.{COORDINATE_PRECISION}f},{y0:.{COORDINATE_PRECISION}f} "
                         f"L {x:.{COORDINATE_PRECISION}f},{y1:.{COORDINATE_PRECISION}f}")
            y = y0 + (tile_length / 2 if row % 2 else tile_length)
            while y < y1 - 0.1:
                x_end = min(x + row_height, max(xs) - margin)
                lines.append(f"M {x:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f} "
                             f"L {x_end:.{COORDINATE_PRECISION}f},{y:.{COORDINATE_PRECISION}f}")
                y += tile_length
        x += row_height
        row += 1
    return " ".join(lines)
