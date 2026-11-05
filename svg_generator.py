"""
SVG generation facade for house box panels: build panels -> lay out -> render.
Produces laser-cutting ready SVG with 0.0254mm cut line width.
"""

import math
from typing import Dict, List, Optional

from .config import ArchitecturalConfiguration
from .assembly import build_panels
from .constants import HouseStyle
from .exceptions import HouseMakerError, SVGGenerationError
from .geometry import HouseGeometry
from .layout import pack
from .panel import Panel
from .render import MARGIN, item_size, render_svg


class SVGGenerator:
    """
    Builds all panels of a house, lays them out on the material sheet and renders the SVG.

    Stateless with respect to the configuration: every call re-reads `geometry` and
    `architectural_config`, so changes made after construction are always reflected.
    """

    def __init__(self, geometry: HouseGeometry, style: HouseStyle = HouseStyle.BASIC_HOUSE,
                 material_width: float = 457.2, material_height: float = 304.8,
                 architectural_config: Optional[ArchitecturalConfiguration] = None,
                 single_joints: bool = False):
        self.geometry = geometry
        self.style = style
        self.material_width = material_width     # 18 inches in mm
        self.material_height = material_height   # 12 inches in mm (reference only, height is unbounded)
        self.architectural_config = architectural_config
        self.single_joints = single_joints

    def build_panels(self) -> List[Panel]:
        return build_panels(self.geometry, self.style, self.architectural_config, self.single_joints)

    def layout(self, panels: List[Panel], include_labels: bool = True):
        spacing = max(2 * self.geometry.thickness, 2.0)
        # the renderer adds MARGIN on every side, so the *document* stays within the material width
        return pack([(p.name, *item_size(p, include_labels)) for p in panels],
                    self.material_width - 2 * MARGIN, spacing)

    def render_panels(self, panels: List[Panel], include_labels: bool = True) -> str:
        """Lay out and render any subset of panels (e.g. one component, for inspection)."""
        positions = self.layout(panels, include_labels)
        return render_svg(panels, positions, include_labels)[0]

    def generate_svg(self, include_labels: bool = True) -> str:
        """Complete SVG string ready for laser cutting."""
        try:
            panels = self.build_panels()
            positions = self.layout(panels, include_labels)
            svg, self.svg_width, self.svg_height = render_svg(panels, positions, include_labels)
            return svg
        except HouseMakerError:
            raise
        except Exception as e:
            raise SVGGenerationError("complete_svg", str(e)) from e

    def get_cutting_summary(self) -> Dict[str, any]:
        """Summary of the cutting job, measured from the real cut geometry."""
        panels = self.build_panels()
        positions = self.layout(panels)
        _, width, height = render_svg(panels, positions)
        total = sum(p.cut_length for p in panels)
        details = {}
        for p in panels:
            w, h = p.nominal_size or (p.bbox.width, p.bbox.height)
            details[p.name] = {'width': w, 'height': h, 'area': p.area, 'perimeter': p.cut_length}
        g = self.geometry
        return {
            'total_panels': len(panels),
            'total_cut_length_mm': total,
            'total_cut_length_m': total / 1000,
            'svg_dimensions_mm': (width, height),
            'material_dimensions': {'length': g.x, 'width': g.y, 'height': g.z, 'thickness': g.thickness},
            'panel_details': details,
            'house_geometry': {
                'gable_angle_degrees': g.theta,
                'gable_peak_height': g.gable_peak_height,
                'roof_panel_left_width': g.roof_panel_left_width,
                'roof_panel_right_width': g.roof_panel_right_width,
            },
        }

    def save_svg(self, filename: str, include_labels: bool = True):
        svg_content = self.generate_svg(include_labels)
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(svg_content)
        except OSError as e:
            raise SVGGenerationError("file_save", f"Could not save to {filename}: {e}") from e

    def get_assembly_instructions(self) -> List[str]:
        """Generate human-readable assembly instructions"""
        steps = [
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
        note = self.ridge_finishing_note()
        if note:
            steps += ["", "Finishing the roof ridge:", f"   {note}"]
        return steps

    def ridge_finishing_note(self):
        """
        The roof ridge fits exactly only at 45 degrees (a laser cuts square to the plate, so the panels cannot be
        bevelled). Returns what to finish by hand at other angles, or None at 45.
        """
        theta, t = self.geometry.theta, self.geometry.thickness
        if abs(theta - 45.0) < 0.05 or self.style != HouseStyle.BASIC_HOUSE:
            return None
        if theta < 45:
            return (f"At {theta:g}° the two roof panels overlap along the ridge by up to "
                    f"{t * abs(math.cos(math.radians(2 * theta))):.1f} mm: sand or trim the ridge edge until they seat.")
        return (f"At {theta:g}° a wedge gap of up to {t * abs(math.tan(math.radians(90 - 2 * theta))):.1f} mm remains "
                f"on the outer ridge face and the ridge tabs sit slightly proud: fill with glue/filler or sand a bevel.")