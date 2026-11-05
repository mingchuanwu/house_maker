"""
Finger-joint engine.

An edge's joint layout is *planned* once (`plan_edge` -> JointSpec) and then *traced* into a path.
The spec is also exported on each Panel, so mating edges can be verified against the plan that
was actually drawn.

Conventions
-----------
* Panel outlines run counter-clockwise (y up); the outward normal is to the right of travel.
* Finger positions are measured along the edge from its start point.

Kerf model
----------
The laser removes `kerf` of material centred on the drawn path, so a cut part ends up `kerf/2` smaller
on every cut edge. To get the *nominal* part, every path is offset outward from its material by `kerf/2`:

* outer dimensions   nominal + kerf            (done in HouseGeometry)
* edge tab           width f + kerf,  protrusion t       (material grows on both sides of the tab)
* edge notch         width f - kerf,  depth t            (the void shrinks, the material around it grows)
* internal slot      (f - kerf) x (t - kerf)             (void shrinks on all sides)

After cutting, every tab is exactly f wide and t long and every notch/slot exactly f wide and t deep,
so mating features fit with zero clearance. `JointSpec.nominal` holds the kerf-free finger positions.
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .constants import COORDINATE_PRECISION
from .exceptions import FingerJointError
from .geometry import Point, edge_shifts, offset_polygon

MALE = 'male'
FEMALE = 'female'

_P = COORDINATE_PRECISION


@dataclass(frozen=True)
class JointSpec:
    role: str                                   # MALE | FEMALE
    length: float                               # full edge length
    fingers: Tuple[Tuple[float, float], ...]    # (start, end) of each finger as DRAWN (kerf-compensated)
    depth: float                                # protrusion (male) / notch depth (female), as drawn
    nominal: Tuple[Tuple[float, float], ...] = ()   # kerf-free (start, end): the physical finger


@dataclass(frozen=True)
class SlotSpec:
    """A through-slot cut inside a panel that receives a tab from another panel."""
    cx: float
    cy: float
    length: float        # extent along the slot's long axis
    thickness: float     # extent across it
    orientation: str     # 'vertical': long axis along y; 'horizontal': long axis along x


class FingerJointEngine:
    """Plans and traces finger joints for one material (thickness / finger length / kerf)."""

    MIN_GAP_RATIO = 0.3

    def __init__(self, thickness: float, finger_length: float, kerf: float = 0.0,
                 single_joints: bool = False):
        self.thickness = thickness
        self.finger_length = finger_length
        self.kerf = kerf
        self.single_joints = single_joints
        # Edge fingers are as deep as the mating material is thick; kerf only changes their width.
        self.depth = thickness
        # Internal slots are voids: they shrink by the kerf on every side
        self.slot_thickness = thickness - kerf
        self.slot_length = finger_length - kerf
        self._min_spacing = finger_length * 0.8

    # ------------------------------------------------------------------ planning
    def joint_count(self, edge_length: float) -> int:
        """Odd number of fingers (1, 3, 5 or 7) that suits the edge length."""
        if self.single_joints:
            return 1
        available = edge_length - self.finger_length
        fit = int((available + self._min_spacing) / (self.finger_length + self._min_spacing))
        for n in (7, 5, 3):
            if fit >= n:
                return n
        return 1

    def finger_positions(self, edge_length: float, count: int,
                         offset: float = 0.0) -> List[Tuple[float, float]]:
        """Evenly distributed (start, end) finger positions; reduces `count` if gaps get too small."""
        f = self.finger_length
        if count == 1:
            start = (edge_length - f) / 2 + offset
            return [(start, start + f)]
        gap = (edge_length - count * f) / (count + 1)
        if gap < f * self.MIN_GAP_RATIO:
            return self.finger_positions(edge_length, max(1, count - 2), offset)
        pos, out = gap + offset, []
        for _ in range(count):
            out.append((pos, pos + f))
            pos += f + gap
        return out

    def plan_edge(self, edge_length: float, role: str, inset: float = 0.0,
                  count: Optional[int] = None, span: Optional[Tuple[float, float]] = None) -> Optional[JointSpec]:
        """
        Plan the fingers of one edge, or None if the edge is too short for any joint.

        Args:
            inset: lay the fingers out over `edge_length - 2*inset`, shifted by `inset`
                   (used where a panel's edge is longer than the edge it mates with).
            count: force the number of fingers instead of choosing by length.
            span:  (lo, hi) lay the fingers out over this part of the edge only (e.g. where the panel
                   is wide enough to carry a notch); the layout is then not symmetric about the edge
                   centre, so the mating edge must use `mirrored(spec, role)`.
        """
        if role not in (MALE, FEMALE):
            raise FingerJointError(f"Invalid joint role: {role!r}")
        lo, hi = span if span is not None else (inset, edge_length - inset)
        usable = hi - lo
        if usable < self.finger_length * 1.5:
            return None
        n = count if count is not None else self.joint_count(usable)
        return self.spec(role, edge_length, self.finger_positions(usable, n, lo))

    def refit(self, spec: JointSpec, start_shift: float, drawn_length: float) -> JointSpec:
        """The same fingers on a kerf-offset edge: its drawn start lies `start_shift` along the edge from the
        nominal start (see geometry.edge_shifts) and its drawn length is `drawn_length`."""
        return self.spec(spec.role, drawn_length, [(a - start_shift, b - start_shift) for a, b in spec.nominal])

    def kerf_outline(self, corners: List[Point], specs: List[Optional[JointSpec]]):
        """
        Kerf-compensate an outline whose edges carry specs planned on the NOMINAL edges: returns the drawn
        corners (nominal offset outward by kerf/2) and the specs refitted onto the drawn edges.
        """
        drawn = offset_polygon(corners, self.kerf / 2)
        shifts = edge_shifts(corners, drawn)
        out = []
        for i, spec in enumerate(specs):
            if spec is None:
                out.append(None)
                continue
            a, b = drawn[i], drawn[(i + 1) % len(drawn)]
            out.append(self.refit(spec, shifts[i], math.hypot(b.x - a.x, b.y - a.y)))
        return drawn, out

    def mirrored(self, spec: JointSpec, role: str) -> JointSpec:
        """The same fingers seen from the other end of the edge, for the panel it mates with."""
        L = spec.length
        return self.spec(role, L, [(L - b, L - a) for a, b in spec.nominal])

    # ------------------------------------------------------------------ tracing
    @staticmethod
    def trace_edge(start: Point, end: Point, spec: Optional[JointSpec]) -> str:
        """Path fragment ("L ..." segments) from `start` to `end` (start itself is not emitted)."""
        if spec is None:
            return f"L {end.x:.{_P}f},{end.y:.{_P}f}"
        ux, uy = (end.x - start.x) / spec.length, (end.y - start.y) / spec.length
        # outward = right of travel; female notches go the other way
        vx, vy = (uy, -ux) if spec.role == MALE else (-uy, ux)
        d = spec.depth
        parts = []
        for s, e in spec.fingers:
            for a, off in ((s, 0.0), (s, d), (e, d), (e, 0.0)):
                parts.append(f"L {start.x + ux * a + vx * off:.{_P}f},{start.y + uy * a + vy * off:.{_P}f}")
        parts.append(f"L {end.x:.{_P}f},{end.y:.{_P}f}")
        return " ".join(parts)

    def with_finger_length(self, finger_length: float) -> 'FingerJointEngine':
        """Same material, different finger length (small components use smaller fingers)."""
        return FingerJointEngine(self.thickness, finger_length, self.kerf, self.single_joints)

    def spec(self, role: str, length: float, nominal_fingers) -> JointSpec:
        """A JointSpec for kerf-free finger positions (also used to mate with an already planned edge)."""
        half = self.kerf / 2
        nominal = tuple(sorted((float(a), float(b)) for a, b in nominal_fingers))
        grow = half if role == MALE else -half          # tabs grow, notches shrink
        drawn = tuple((a - grow, b + grow) for a, b in nominal)
        return JointSpec(role, length, drawn, self.depth, nominal)

    def trace_outline(self, corners: List[Point], specs: List[Optional[JointSpec]]) -> str:
        """Closed outline path; edge i runs corners[i] -> corners[i+1] and carries specs[i]."""
        path = f"M {corners[0].x:.{_P}f},{corners[0].y:.{_P}f}"
        for i, spec in enumerate(specs):
            path += " " + self.trace_edge(corners[i], corners[(i + 1) % len(corners)], spec)
        return path + " Z"

    def slot_path(self, slot: SlotSpec) -> str:
        """Closed rectangle for an internal slot."""
        if slot.orientation == 'horizontal':
            hx, hy = slot.length / 2, slot.thickness / 2
        else:
            hx, hy = slot.thickness / 2, slot.length / 2
        x0, x1, y0, y1 = slot.cx - hx, slot.cx + hx, slot.cy - hy, slot.cy + hy
        return (f"M {x0:.{_P}f},{y0:.{_P}f} L {x1:.{_P}f},{y0:.{_P}f} "
                f"L {x1:.{_P}f},{y1:.{_P}f} L {x0:.{_P}f},{y1:.{_P}f} Z")

    def make_slot(self, cx: float, cy: float, orientation: str = 'vertical') -> SlotSpec:
        return SlotSpec(cx, cy, self.slot_length, self.slot_thickness, orientation)
