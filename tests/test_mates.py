"""Declared mates must be physically consistent: fingers coincide when mate edges are laid together."""

import pytest

from house_maker.mates import EDGE, TAB_SLOT, declared_mates
from .conftest import make_house

SCENES = {
    'box': dict(),
    'box_k0': dict(kerf=0.0, gable_angle=60),
    'chimney': dict(chimneys=[('roof_panel_left', 25, 30, 14, 20, 30)]),
    'dormer': dict(length=200, width=160, height=90, dormers=[('roof_panel_right', 40, 20, 70)]),
}


@pytest.fixture(params=SCENES)
def mates_and_panels(request):
    panels = {p.name: p for p in make_house(**SCENES[request.param]).build_panels()}
    return declared_mates(panels), panels, request.param


def length(panel, edge):
    i = panel.edge_names.index(edge)
    a, b = panel.corners[i], panel.corners[(i + 1) % len(panel.corners)]
    return ((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5


def test_edge_mates_line_up_every_finger(mates_and_panels):
    mates, panels, _ = mates_and_panels
    checked = 0
    for m in (m for m in mates if m.kind == EDGE):
        a, b = panels[m.a[0]], panels[m.b[0]]
        fa, fb = a.joints.get(m.a[1]), b.joints.get(m.b[1])
        if fa and fb:
            fa, fb = type('S', (), {'fingers': fa.nominal, 'role': fa.role}), type('S', (), {'fingers': fb.nominal, 'role': fb.role})
        assert (fa is None) == (fb is None), f"{m}: one side has fingers, the other not"
        if not fa:
            continue
        lb = length(b, m.b[1])
        assert len(fa.fingers) == len(fb.fingers)
        # B's point s_b meets A's point shift + lb - s_b: each mirrored B finger equals an A finger
        mapped = sorted((m.shift + lb - e, m.shift + lb - s) for s, e in fb.fingers)
        for (x0, x1), (y0, y1) in zip(mapped, sorted(fa.fingers)):
            assert (x0, x1) == pytest.approx((y0, y1), abs=1e-6), m
        assert {fa.role, fb.role} == {'male', 'female'}
        checked += 1
    assert checked


def test_tab_slot_mates_reference_existing_slots_and_tabs(mates_and_panels):
    mates, panels, scene = mates_and_panels
    slots = [m for m in mates if m.kind == TAB_SLOT]
    for m in slots:
        assert panels[m.a[0]].joints[m.a[1]].role == 'male'
        assert 0 <= m.b[1] < len(panels[m.b[0]].slots)
    if scene == 'box':
        assert len(slots) == 4          # 2 gables × 2 roof edges
    if scene == 'dormer':
        assert any(m.a[0].startswith('additional_gable_front') for m in slots)


def test_every_main_box_seam_is_declared():
    panels = {p.name: p for p in make_house().build_panels()}
    pairs = {(m.a[0], m.b[0]) for m in declared_mates(panels) if m.kind == EDGE}
    assert len(pairs) == 9      # 4 floor seams + 4 corner seams + ridge


# ---------------------------------------------------------------- exact wiring
def edge_set(mates):
    return {(m.a[0], m.a[1], m.b[0], m.b[1]) for m in mates if m.kind == EDGE}


def slot_set(mates):
    return {(m.a[0], m.a[1], m.b[0], m.b[1]) for m in mates if m.kind == TAB_SLOT}


def test_main_box_wiring_is_exactly_this():
    panels = {p.name: p for p in make_house().build_panels()}
    mates = declared_mates(panels)
    assert edge_set(mates) == {
        ('floor', 'bottom', 'side_wall_left', 'bottom'), ('floor', 'top', 'side_wall_right', 'bottom'),
        ('floor', 'right', 'gable_wall_front', 'bottom'), ('floor', 'left', 'gable_wall_back', 'bottom'),
        ('side_wall_left', 'right', 'gable_wall_front', 'left'), ('side_wall_left', 'left', 'gable_wall_back', 'right'),
        ('side_wall_right', 'right', 'gable_wall_back', 'left'), ('side_wall_right', 'left', 'gable_wall_front', 'right'),
        ('roof_panel_right', 'ridge', 'roof_panel_left', 'ridge'),
    }
    # each gable plugs into its own end slot (slot 0 at the start of the roof panel, slot 1 at the end)
    assert slot_set(mates) == {
        ('gable_wall_front', 'roof_left', 'roof_panel_left', 0), ('gable_wall_front', 'roof_right', 'roof_panel_right', 0),
        ('gable_wall_back', 'roof_left', 'roof_panel_left', 1), ('gable_wall_back', 'roof_right', 'roof_panel_right', 1),
    }
    assert len(mates) == 13 and all(m.note for m in mates)


def test_chimney_wiring_is_exactly_this_and_indexed_per_chimney():
    h = make_house(length=200, width=140, height=90,
                   chimneys=[('roof_panel_left', 40, 60, 14, 20, 30), ('roof_panel_right', 100, 60, 14, 20, 30)])
    mates = declared_mates({p.name: p for p in h.build_panels()})
    for i in (0, 1):
        assert {x for x in edge_set(mates) if x[0].endswith(f'_{i}')} == {
            (f'chimney_front_{i}', 'left', f'chimney_left_{i}', 'front_end'),
            (f'chimney_front_{i}', 'right', f'chimney_right_{i}', 'front_end'),
            (f'chimney_back_{i}', 'left', f'chimney_left_{i}', 'back_end'),
            (f'chimney_back_{i}', 'right', f'chimney_right_{i}', 'back_end'),
        }


def test_dormer_wiring_depends_on_whether_tabs_exist():
    big = make_house(length=200, width=160, height=90, dormers=[('roof_panel_right', 40, 20, 70)])
    mates = declared_mates({p.name: p for p in big.build_panels()})
    assert ('additional_gable_roof_right_0', 'ridge', 'additional_gable_roof_left_0', 'ridge') in edge_set(mates)
    assert {x for x in slot_set(mates) if x[0].startswith('additional')} == {
        ('additional_gable_front_0', 'rake_left', 'additional_gable_roof_left_0', 0),
        ('additional_gable_front_0', 'rake_right', 'additional_gable_roof_right_0', 0),
    }
    small = make_house(dormers=[('roof_panel_left', 30, 25, 25)])
    mates = declared_mates({p.name: p for p in small.build_panels()})
    assert not {x for x in slot_set(mates) if x[0].startswith('additional')}       # no tabs, so nothing to plug in
    assert ('additional_gable_roof_right_0', 'ridge', 'additional_gable_roof_left_0', 'ridge') in edge_set(mates)


def test_mates_only_for_panels_that_exist():
    panels = {p.name: p for p in make_house().build_panels() if p.name != 'floor'}
    mates = declared_mates(panels)
    assert all('floor' not in (m.a[0], m.b[0]) for m in mates)
    assert declared_mates({}) == []


def test_edges_without_fingers_are_centred_on_each_other():
    h = make_house(chimneys=[('roof_panel_left', 25, 30, 6, 8, 10)])            # too small for fingers: glued
    panels = {p.name: p for p in h.build_panels()}
    mates = [m for m in declared_mates(panels) if m.kind == EDGE and m.a[0].startswith('chimney')]
    assert len(mates) == 4
    for m in mates:
        assert not panels[m.a[0]].joints and not panels[m.b[0]].joints
        assert m.shift == pytest.approx((length(panels[m.a[0]], m.a[1]) - length(panels[m.b[0]], m.b[1])) / 2)
        if m.a[0].startswith('chimney_front'):
            assert m.shift < 0              # the down-slope end of the side wall is taller than the front wall
        else:
            assert abs(m.shift) <= 0.1            # at the up-slope end wall and side wall have (almost) the same height


def test_edge_mate_requires_both_sides_to_have_the_edge():
    panels = {p.name: p for p in make_house().build_panels()}
    mates = declared_mates(panels)
    for m in mates:
        assert m.a[1] in panels[m.a[0]].edge_names
        if m.kind == EDGE:
            assert m.b[1] in panels[m.b[0]].edge_names
        else:
            assert 0 <= m.b[1] < len(panels[m.b[0]].slots)
