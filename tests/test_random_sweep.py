"""
Randomized sweep: many seeded random houses (dimensions, roof angle, material, kerf, finger length,
styles, components, chimneys, dormers) must satisfy EVERY invariant - drawn = declared, document
layout, mate consistency and 3D assembly. Failures print the seed so they can be replayed.

    HOUSE_SWEEP_N=200 pytest tests/test_random_sweep.py     # run a bigger sweep
"""

import math
import os
import random

import numpy as np
import pytest

from house_maker import (ArchitecturalStyle, DoorType, HouseMaker, PlacementError, ShingleType, WindowType)
from house_maker.exceptions import GeometryError
from house_maker.mates import EDGE, TAB_SLOT, declared_mates
from . import invariants
from .assembly3d import PanelSolid, box_frames, chimney_frames, dormer_frames, worst_penetrations
from .svgdoc import parse_svg

N = int(os.environ.get('HOUSE_SWEEP_N', '30'))
MIN_GAP = 1.0


def random_house(seed):
    rng = random.Random(seed)
    for _ in range(50):                                       # draw until the geometry is valid
        kw = dict(length=rng.randint(80, 260), width=rng.randint(70, 180), height=rng.randint(55, 140),
                  gable_angle=rng.choice([20, 25, 30, 35, 40, 45, 50, 55, 60, 65]),
                  material_thickness=rng.choice([2.0, 3.0, 4.0, 5.0]), finger_length=rng.choice([10, 15, 20]),
                  kerf=rng.choice([0.0, 0.1, 0.15, 0.2]), single_joints=rng.random() < 0.15,
                  auto_add_components=rng.random() < 0.5, window_type=rng.choice(list(WindowType)),
                  door_type=rng.choice(list(DoorType)), architectural_style=rng.choice(list(ArchitecturalStyle)),
                  shingle_type=rng.choice(list(ShingleType)))
        try:
            house = HouseMaker(**kw)
            break
        except GeometryError:
            continue
    else:
        pytest.skip('no valid geometry drawn')
    placed = 0
    for _ in range(12):
        panel = rng.choice(['roof_panel_left', 'roof_panel_right'])
        w, h = house.geometry.get_panel_dimensions()[panel]
        x, y = rng.uniform(2, w - 10), rng.uniform(2, h - 10)
        try:
            if rng.random() < 0.5:
                house.add_chimney(panel, x, y, rng.choice([6, 8, 10, 14, 20]), rng.choice([10, 12, 16, 22]), rng.choice([14, 20, 30]))
            else:
                house.add_additional_gable(panel, x, y, rng.choice([16, 25, 40, 60]), roof_overhang=rng.choice([0, 2, 3, 5]))
            placed += 1
        except (PlacementError, GeometryError):
            pass
        if placed >= 3:
            break
    return kw, house


@pytest.mark.parametrize('seed', range(N))
def test_random_house_satisfies_every_invariant(seed):
    kw, house = random_house(seed)
    ctx = f"seed={seed} {kw}"
    panels = house.build_panels()

    # 1. what is drawn equals what was declared, for every panel
    for check in invariants.ALL_CHECKS:
        try:
            check(house, panels)
        except AssertionError as e:
            raise AssertionError(f"{ctx}\n{check.__name__}: {e}") from None

    # 2. the document: everything inside the viewBox, nothing overlapping
    doc = parse_svg(house.generate_svg())
    vb = doc.viewbox
    boxes = {n: p.bbox for n, p in doc.panels.items()}
    assert len(boxes) == len(panels), ctx
    for n, b in boxes.items():
        assert b.min_x >= -1e-6 and b.min_y >= -1e-6 and b.max_x <= vb.max_x + 1e-6 and b.max_y <= vb.max_y + 1e-6, f"{ctx}\n{n} outside viewBox"
    names = list(boxes)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert not boxes[a].inflated(MIN_GAP / 2).intersects(boxes[b].inflated(MIN_GAP / 2)), f"{ctx}\n{a} / {b} too close"

    # 3. declared mates are consistent
    by_name = {p.name: p for p in panels}
    for m in declared_mates(by_name):
        a, b = by_name[m.a[0]], by_name[m.b[0]]
        if m.kind == EDGE:
            ja, jb = a.joints.get(m.a[1]), b.joints.get(m.b[1])
            assert (ja is None) == (jb is None), f"{ctx}\none side of {m} has fingers, the other not"
            if ja:
                assert len(ja.fingers) == len(jb.fingers) and {ja.role, jb.role} == {'male', 'female'}, f"{ctx}\n{m}"
        else:
            assert a.joints[m.a[1]].role == 'male' and m.b[1] < len(b.slots), f"{ctx}\n{m}"
        # tab <-> slot consistency on dormers: a face tab exists exactly when its roof slot does
    for i in range(len(house.architectural_config.additional_gables)):
        face = by_name[f'additional_gable_front_{i}']
        left, right = by_name[f'additional_gable_roof_left_{i}'], by_name[f'additional_gable_roof_right_{i}']
        assert bool(face.joints) == bool(left.slots) == bool(right.slots), f"{ctx}\ndormer {i}: tabs and slots disagree"

    # 4. 3D assembly of the main box: panels never interpenetrate (the ridge is exact only at 45 degrees)
    t, k, th = kw['material_thickness'], kw['kerf'], kw['gable_angle']
    frames = box_frames(kw['length'], kw['width'], kw['height'], th, t, k)
    box_panels = {n: p for n, p in by_name.items() if n in frames}
    tol = 0.5 * k + 0.03
    ridge = tol if th >= 45 else t * abs(math.cos(math.radians(2 * th))) + tol
    for (a, b), depth in worst_penetrations(box_panels, frames, step=1.0).items():
        limit = ridge if {a, b} == {'roof_panel_left', 'roof_panel_right'} else tol + 0.05
        assert depth <= limit, f"{ctx}\n{a} penetrates {b} by {depth:.3f} (limit {limit:.3f})"


    # 5. chimneys and dormers assemble onto their roof panel without interpenetration
    cfg = house.architectural_config
    def check_feature(parts, roof_name, label, extra_limit=None):
        solids = {n: PanelSolid(by_name[n], fr) for n, fr in parts.items() if n in by_name}
        solids[roof_name] = PanelSolid(by_name[roof_name], frames[roof_name])
        samples = {n: sl.sample(step=1.0)[0] for n, sl in solids.items()}
        for a in solids:
            for b in solids:
                if a == b:
                    continue
                d = solids[b].depth(samples[a])
                d = d[~np.isnan(d)]
                if len(d):
                    limit = tol + 0.05
                    if extra_limit and {a, b} == extra_limit[0]:
                        limit += extra_limit[1]
                    assert d.max() <= limit, f"{ctx}\n{label}: {a} penetrates {b} by {d.max():.3f} (limit {limit:.3f})"
    for i, c in enumerate(cfg.chimneys):
        p = c.position
        check_feature(chimney_frames(frames[p.panel], p.x, p.y, p.width, p.height, th, t, k, index=i),
                      p.panel, f'chimney {i}')
    for i, g in enumerate(cfg.additional_gables):
        p, phi = g.position, g.geometry.phi_deg
        df, _ = dormer_frames(frames[p.panel], p.x, p.y, p.width, th, phi, t, k, index=i)
        ridge_extra = t * abs(math.cos(math.radians(2 * phi))) if phi < 45 else 0.0
        check_feature(df, p.panel, f'dormer {i}',
                      ({f'additional_gable_roof_left_{i}', f'additional_gable_roof_right_{i}'}, ridge_extra))
