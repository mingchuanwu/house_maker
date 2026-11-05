"""
Invariants that must hold for EVERY generated panel of EVERY house: what is drawn equals what was
declared. Shared by the fixed-scene tests and the randomized sweep.
"""

import itertools

import pytest

from house_maker.svgpath import parse_path, path_bbox
from .geom import dedupe, is_simple, point_in_polygon, signed_area
from .profiles import edge_profile

TOL = 6e-3      # coordinates are written with 3 decimals


def _strictly_inside(p, poly, clearance=0.02):
    """Inside the polygon and more than `clearance` away from its boundary."""
    if not point_in_polygon((p.x, p.y), poly):
        return False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        dx, dy = b.x - a.x, b.y - a.y
        L2 = dx * dx + dy * dy
        s = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p.x - a.x) * dx + (p.y - a.y) * dy) / L2))
        if ((p.x - a.x - s * dx) ** 2 + (p.y - a.y - s * dy) ** 2) ** 0.5 <= clearance:
            return False
    return True


def drawn_polys(panel):
    return [dedupe(sub) for d in panel.cut for sub in parse_path(d)]


def check_outlines_are_simple_polygons(house, panels):
    for panel in panels:
        outline = drawn_polys(panel)[0]
        assert is_simple(outline), f"{panel.name}: outline crosses itself"
        assert abs(signed_area(outline)) > 1, panel.name


def check_engine_panels_are_counter_clockwise_through_their_corners(house, panels):
    for panel in panels:
        if not panel.corners:
            continue
        outline = drawn_polys(panel)[0]
        assert signed_area(outline) > 0, f"{panel.name}: outline must be counter-clockwise"
        # the outline visits every nominal corner, in order
        at = []
        for c in panel.corners:
            idx = [i for i, p in enumerate(outline) if abs(p.x - c.x) < TOL and abs(p.y - c.y) < TOL]
            assert idx, f"{panel.name}: corner {c} missing from outline"
            at.append(idx[0])
        rotated = at[at.index(min(at)):] + at[:at.index(min(at))]
        assert rotated == sorted(rotated), f"{panel.name}: corners visited out of order"


def check_drawn_fingers_are_exactly_the_planned_ones(house, panels):
    for panel in panels:
        for edge in panel.edge_names:
            drawn = edge_profile(panel, edge)
            spec = panel.joints.get(edge)
            if spec is None:
                assert not drawn, f"{panel.name}.{edge}: fingers drawn on an edge without a joint"
                continue
            assert len(drawn) == len(spec.fingers), f"{panel.name}.{edge}"
            for d, (s0, s1) in zip(drawn, spec.fingers):
                assert (d.start, d.end) == pytest.approx((s0, s1), abs=TOL), f"{panel.name}.{edge}"
                expect = spec.depth if spec.role == 'male' else -spec.depth
                assert d.depth == pytest.approx(expect, abs=TOL), f"{panel.name}.{edge}"


def check_area_is_nominal_plus_tabs_minus_notches(house, panels):
    for panel in panels:
        if not panel.corners:
            continue
        outline = drawn_polys(panel)[0]
        nominal = abs(signed_area(panel.corners))
        delta = sum((b - a) * j.depth * (1 if j.role == 'male' else -1)
                    for j in panel.joints.values() for a, b in j.fingers)
        perimeter = sum(((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5 for a, b in zip(outline, outline[1:] + outline[:1]))
        # coordinates are rounded to 0.001: allow that much along the whole perimeter
        assert abs(signed_area(outline)) == pytest.approx(nominal + delta, abs=0.05 + 0.001 * perimeter), panel.name


def check_drawn_slots_are_the_declared_slots(house, panels):
    for panel in panels:
        boxes = [path_bbox(d) for d in panel.cut[1:]]
        for slot in panel.slots:
            hx = (slot.length if slot.orientation == 'horizontal' else slot.thickness) / 2
            hy = (slot.thickness if slot.orientation == 'horizontal' else slot.length) / 2
            want = (slot.cx - hx, slot.cy - hy, slot.cx + hx, slot.cy + hy)
            assert any(b.min_x == pytest.approx(want[0], abs=TOL) and b.min_y == pytest.approx(want[1], abs=TOL)
                       and b.max_x == pytest.approx(want[2], abs=TOL) and b.max_y == pytest.approx(want[3], abs=TOL)
                       for b in boxes), f"{panel.name}: slot {slot} not drawn"


def check_cutouts_and_scores_stay_inside_the_outline(house, panels):
    for panel in panels:
        outline = drawn_polys(panel)[0]
        holes = [h for h in drawn_polys(panel)[1:]]
        for hole in holes:
            assert all(point_in_polygon((p.x, p.y), outline) for p in hole), f"{panel.name}: cut-out leaves the panel"
        for a, b in itertools.combinations(holes, 2):
            # the sub-cuts of one window (e.g. a Palladian) may share an edge; sharing area is the error
            assert not any(_strictly_inside(p, b) for p in a) or panel.name.endswith('casing'), \
                f"{panel.name}: cut-outs overlap"
        for d in panel.score:
            for sub in parse_path(d):
                assert all(point_in_polygon((p.x, p.y), outline) for p in sub), f"{panel.name}: score line leaves the panel"




def check_roof_slot_keepouts_match_the_drawn_slots(house, panels):
    """config avoids HouseGeometry.roof_slot_rects; the builder draws slots from the engine: same place."""
    for panel in panels:
        if not panel.name.startswith('roof_panel'):
            continue
        rects = house.geometry.roof_slot_rects(panel.name)
        boxes = sorted((b.min_x, b.min_y, b.max_x, b.max_y) for b in (path_bbox(d) for d in panel.cut[1:])
                       if (b.max_x - b.min_x) < min(rects[0][2] - rects[0][0] + 0.5, 6))
        assert len(boxes) == len(rects) == 2, panel.name
        for got, want in zip(boxes, sorted(rects)):
            assert got == pytest.approx(want, abs=TOL), panel.name


ALL_CHECKS = [v for k, v in sorted(globals().items()) if k.startswith('check_')]
