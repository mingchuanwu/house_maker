"""
3D export: the assembled model is checked against the independent numpy model (tests/assembly3d.py), and
the three file formats are parsed back and compared with the meshes they were written from.
"""

import io
import json
import math
import random
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pytest

from house_maker import HouseMaker, WindowType, DoorType
from house_maker.formats3d import FORMATS, encode, to_3mf, to_glb, to_stl
from house_maker.mesh import Mesh, extrude, signed_area, triangulate
from house_maker.model3d import build_model, house_frames, panel_rings

from . import assembly3d as ref
from .conftest import make_house

T, K = 3.0, 0.1
BASE = dict(length=150, width=120, height=90, material_thickness=T, kerf=K)


def full_house(angle=35, window=WindowType.RECTANGULAR, door=DoorType.RECTANGULAR, chimney=True, dormer=True, **kw):
    h = HouseMaker(**{**BASE, 'gable_angle': angle, 'window_type': window, 'door_type': door, **kw})
    if chimney:
        h.add_chimney(*(chimney if isinstance(chimney, tuple) else ('roof_panel_left', 25, 30, 10, 12, 30)))
    if dormer:
        h.add_additional_gable(*(dormer if isinstance(dormer, tuple) else ('roof_panel_right', 20, 20, 40)))
    return h


SCENES = {
    'plain': dict(auto_add_components=False, chimney=False, dormer=False),
    '35-features': dict(),
    '45-arched': dict(angle=45, window=WindowType.ARCHED, door=DoorType.ARCHED),
    '60-circular': dict(angle=60, window=WindowType.CIRCULAR),
    # windows cut as separate panes with bars of wall material between them
    '35-multi-pane': dict(window=WindowType.MULTI_PANE, chimney=False, dormer=False),
    '35-cross-pane': dict(window=WindowType.CROSS_PANE, chimney=False, dormer=False),
    '35-double-hung': dict(window=WindowType.DOUBLE_HUNG, chimney=False, dormer=False),
    '25-features': dict(angle=25),
    'cli-default': dict(length=80, width=60, height=70, chimney=False, dormer=False),   # small gable: attic window
    # `house-maker --add-chimney --add-additional-gable` with every default: a small dormer with its own small fingers
    'cli-features': dict(length=80, width=60, height=70, finger_length=10,
                         chimney=('roof_panel_left', 50, 20, 10, 15, 20), dormer=('roof_panel_right', 30, 15, 25)),
    # `--angle 60 --add-chimney --add-additional-gable`: the steep roof gives the dormer side walls
    'cli-steep-walls': dict(angle=60, length=80, width=60, height=70, finger_length=10,
                            chimney=('roof_panel_left', 50, 20, 10, 15, 20), dormer=('roof_panel_right', 30, 15, 25)),
    # `--angle 60 --add-additional-gable --additional-gable-wall-height 15 --additional-gable-pitch 60`: the slot layout
    # that broke the main roof's triangulation (two hole bridges to one corner)
    # `--angle 60 --add-additional-gable --additional-gable-wall-height 0`: single narrow ridge and base tabs
    'cli-steep-no-walls': dict(angle=60, length=80, width=60, height=70, finger_length=10, chimney=False,
                               dormer=('roof_panel_right', 30, 15, 25, None, 3.0, None, 0)),
    'cli-walls-pitch60': dict(angle=60, length=80, width=60, height=70, finger_length=10, chimney=False,
                              dormer=('roof_panel_right', 30, 15, 25, None, 3.0, 60, 15)),
}


_SCENE_CACHE = {}


def _scene(name):
    if name not in _SCENE_CACHE:
        house = full_house(**SCENES[name])
        panels = house.build_panels()
        _SCENE_CACHE[name] = dict(house=house, panels={p.name: p for p in panels},
                                  parts={p.name: p for p in house.build_model()})
    return _SCENE_CACHE[name]


@pytest.fixture(params=list(SCENES), scope='module')
def scene(request):
    return _scene(request.param)


# every scene gets its automatic windows and door, except those built without components
DOOR_SCENES = [n for n, kw in SCENES.items() if kw.get('auto_add_components', True)]


# ------------------------------------------------------------------ meshes
def test_every_panel_becomes_one_closed_solid(scene):
    assert set(scene['parts']) == set(scene['panels'])
    for name, part in scene['parts'].items():
        assert part.mesh.is_watertight(), name
        assert part.mesh.volume() > 0, f"{name}: inside-out or empty"


def _drawn_nominal_area(panel):
    """Nominal area of a panel worked out from its drawn cut alone: the drawn outline is kerf/2 larger all round and
    every drawn hole kerf/2 smaller, so (to first order) nominal = drawn -/+ kerf/2 x perimeter. The mitred corners
    add a second-order term, at most ~ (kerf/2)^2 per corner; returns (area, tolerance)."""
    from house_maker.svgpath import parse_path
    subs = [sub for d in panel.cut for sub in parse_path(d, 64)]
    h = K / 2

    def area_perimeter(poly):
        pts = [(p.x, p.y) for p in poly]
        a = abs(signed_area(pts))
        per = sum(math.dist(p, q) for p, q in zip(pts, pts[1:] + pts[:1]))
        return a, per
    a0, p0 = area_perimeter(subs[0])
    area, corners = a0 - h * p0, len(subs[0])
    for hole in subs[1:]:
        a, per = area_perimeter(hole)
        area -= a + h * per
        corners += len(hole)
    return area, 4 * h * h * corners + 1e-6 * a0


def test_volume_is_nominal_area_times_thickness(scene):
    """The solid is the nominal panel (outline and every hole, slot and pane) extruded one thickness: checked against
    the drawn cut, independently of the code that builds the solid. A hole missing from the model shows up as at
    least its own area (several mm^2) while the tolerance stays well below 1 mm^2."""
    for name, part in scene['parts'].items():
        area, tol = _drawn_nominal_area(scene['panels'][name])
        assert part.mesh.volume() == pytest.approx(area * T, abs=tol * T), name
        outer, holes = panel_rings(scene['panels'][name], K)
        drawn_holes = sum(len(parse_path_all(d)) for d in scene['panels'][name].cut) - 1
        assert len(holes) == drawn_holes, f"{name}: {drawn_holes} holes drawn, {len(holes)} in the model"


def parse_path_all(d):
    from house_maker.svgpath import parse_path
    return parse_path(d)


def test_nominal_geometry_not_drawn_geometry(scene):
    """The drawn outline carries kerf compensation; the model is back at the specified size."""
    g = scene['house'].geometry
    X, Y = g.x, g.y
    if 'floor' in scene['parts']:                      # floor plus its tabs into the walls: exactly nominal
        lo, hi = scene['parts']['floor'].mesh.bounds()
        assert lo == pytest.approx((-T, -T, 0), abs=1e-6) and hi == pytest.approx((X + T, Y + T, T), abs=1e-6)
    lo, hi = scene['parts']['gable_wall_front'].mesh.bounds()
    assert (lo[0], hi[0]) == pytest.approx((X, X + T), abs=1e-6)          # exactly one thickness thick


def test_house_extent_matches_the_specification(scene):
    parts = scene['parts']
    g = scene['house'].geometry
    lo = [min(p.mesh.bounds()[0][i] for p in parts.values()) for i in range(3)]
    hi = [max(p.mesh.bounds()[1][i] for p in parts.values()) for i in range(3)]
    X, Y, Z = g.x, g.y, g.z
    assert lo[2] == pytest.approx(0, abs=1e-6)
    walls = [parts[n].mesh.bounds() for n in ('gable_wall_front', 'gable_wall_back')]
    assert min(w[0][0] for w in walls) == pytest.approx(-T, abs=1e-6)
    assert max(w[1][0] for w in walls) == pytest.approx(X + T, abs=1e-6)
    assert min(w[0][1] for w in walls) == pytest.approx(-T, abs=1e-6)
    assert max(w[1][1] for w in walls) == pytest.approx(Y + T, abs=1e-6)
    peak = Z + (Y + 2 * T) / 2 * math.tan(math.radians(g.theta))
    top = max(max(v[2] for v in parts[n].mesh.vertices) for n in ('roof_panel_left', 'roof_panel_right'))
    th = math.radians(g.theta)
    assert peak <= top <= peak + T * (math.sin(th) + math.cos(th)) + 1e-6       # the left roof panel sits t above the ridge line
    # gable walls reach the peak (the drawn apex is a few hundredths of a millimetre above the exact mitre offset,
    # see ARCHITECTURE_REVIEW C-29)
    assert max(w[1][2] for w in walls) == pytest.approx(peak, abs=0.05)


# ------------------------------------------------------------------ placement vs the independent model
def as_ref(frame, k):
    return ref.Frame(np.array(frame.origin), np.array(frame.eu), np.array(frame.ev), np.array(frame.n),
                     frame.thickness, k, frame.shift)


def test_frames_agree_with_the_independent_model(scene):
    h = scene['house']
    g, cfg = h.geometry, h.architectural_config
    frames = house_frames(g, cfg, scene['panels'])
    box = ref.box_frames(g.x, g.y, g.z, g.theta, T, K)
    for name, f in box.items():
        if name == 'gable_wall_back':
            continue                         # the reference mounts it mirrored; checked on its own below
        mine = frames[name]
        for a, b in ((mine.origin, f.O), (mine.eu, f.eu), (mine.ev, f.ev), (mine.n, f.n)):
            assert a == pytest.approx(tuple(b), abs=1e-9), name
    back, rb = frames['gable_wall_back'], box['gable_wall_back']
    assert back.n == pytest.approx(tuple(rb.n))
    assert np.cross(back.eu, back.ev) == pytest.approx(back.n)          # right-handed: no mirrored part
    for i, c in enumerate(cfg.chimneys):
        p = c.position
        want = ref.chimney_frames(box[p.panel], p.x, p.y, p.width, p.height, g.theta, T, K, index=i)
        for name, f in want.items():
            for a, b in ((frames[name].origin, f.O), (frames[name].eu, f.eu), (frames[name].ev, f.ev)):
                assert a == pytest.approx(tuple(b), abs=1e-9), name
    for i, d in enumerate(cfg.additional_gables):
        p = d.position
        want, _ = ref.dormer_frames(box[p.panel], p.x, p.y, p.width, g.theta, d.geometry.phi_deg, T, K, index=i,
                                    wall=d.geometry.wall_height)
        for name, f in want.items():
            for a, b in ((frames[name].origin, f.O), (frames[name].eu, f.eu), (frames[name].ev, f.ev)):
                assert a == pytest.approx(tuple(b), abs=1e-9), name


def test_every_frame_is_right_handed(scene):
    h = scene['house']
    for name, f in house_frames(h.geometry, h.architectural_config, scene['panels']).items():
        assert np.cross(f.eu, f.ev) == pytest.approx(f.n, abs=1e-9), name


def test_panels_do_not_interpenetrate_in_the_exported_model(scene):
    """Run the independent solid-overlap check on exactly the frames the export uses."""
    h = scene['house']
    g = h.geometry
    frames = house_frames(g, h.architectural_config, scene['panels'])
    rf = {n: as_ref(f, K) for n, f in frames.items()}
    tol = 0.5 * K + 0.03
    ridge = tol if g.theta >= 45 else T * abs(math.cos(math.radians(2 * g.theta))) + tol
    worst = ref.worst_penetrations(scene['panels'], rf, step=1.0)
    roof = {'roof_panel_left', 'roof_panel_right'}
    for (a, b), depth in worst.items():
        limit = ridge if {a, b} == roof else tol
        if a.startswith('additional_gable_roof') and b.startswith('additional_gable_roof') and g.theta < 45:
            limit = ridge + T          # dormer ridge: same limitation, relative to the dormer pitch
        assert depth <= limit, f"{a} penetrates {b} by {depth:.3f} mm (limit {limit:.3f})"


def test_casings_frame_the_wall_openings(scene):
    """The opening of every casing lies over the wall's hole, and the casing lies on the outside of the wall."""
    h = scene['house']
    frames = house_frames(h.geometry, h.architectural_config, scene['panels'])
    checked = 0
    for name, panel in scene['panels'].items():
        if 'casing' not in name or name.startswith('chimney'):
            continue
        wall_name = next(w for w in ('side_wall_left', 'side_wall_right', 'gable_wall_front', 'gable_wall_back')
                         if name.startswith(w))
        wall, casing = frames[wall_name], frames[name]
        assert casing.n == pytest.approx(wall.n)
        # on the outer face of the wall: the casing's back face is the wall's front face
        probe = np.array(casing.origin) - np.array(wall.origin)
        assert float(np.dot(probe, wall.n)) == pytest.approx(T, abs=1e-9)
        # inner boundary of the casing (nominal) lies on the wall hole boundary
        c_out, c_holes = panel_rings(panel, K)
        w_out, w_holes = panel_rings(scene['panels'][wall_name], K)
        cw = [np.array(casing.to_world(u, v, 0)) for hole in c_holes for u, v in hole]
        if not c_holes:                                    # U-shaped door casing: its inner edges are part of the outline
            cw = [np.array(casing.to_world(u, v, 0)) for u, v in c_out]
        assert w_holes, f"{wall_name} has no hole for {name}"
        world_holes = [[np.array(wall.to_world(u, v, T)) for u, v in hole] for hole in w_holes]
        if c_holes:
            # every vertex of the casing's opening sits on a wall hole's boundary (distance to the nearest edge)
            for p in cw[:: max(1, len(cw) // 40)]:
                d = min(_dist_to_polyline(p, hole) for hole in world_holes)
                assert d < 0.35 + 1e-6, f"{name}: casing opening is {d:.2f} mm off the wall hole"
        else:
            # U-shaped door casing: every corner of the door hole it frames lies on the casing's outline (its legs run
            # down the hole's sides, its top bar along the hole's top)
            centre = np.mean(cw, axis=0)
            door = min(world_holes, key=lambda hole: float(np.linalg.norm(np.mean(hole, axis=0) - centre)))
            for q in door:
                d = _dist_to_polyline(q, cw)
                assert d < 0.35 + 1e-6, f"{name}: door hole corner is {d:.2f} mm off the casing's inner edge"
        checked += 1
    assert checked == len([n for n in scene['panels'] if 'casing' in n and not n.startswith('chimney')])


def _dist_to_polyline(p, pts):
    best = math.inf
    for a, b in zip(pts, pts[1:] + pts[:1]):
        ab = b - a
        L = float(np.dot(ab, ab))
        s = 0.0 if L == 0 else max(0.0, min(1.0, float(np.dot(p - a, ab)) / L))
        best = min(best, float(np.linalg.norm(p - (a + s * ab))))
    return best


def test_only_houses_built_without_components_have_no_door():
    for name in SCENES:
        doors = [n for n in _scene(name)['parts'] if n.endswith('door_casing')]
        assert bool(doors) == (name in DOOR_SCENES), name


@pytest.mark.parametrize('name', DOOR_SCENES)
def test_door_casings_stand_on_the_ground(name):
    """A door casing is open at the bottom; its legs reach down to the underside of the floor (z = 0), level with the
    bottom of the walls, instead of stopping at the door's sill."""
    scene = _scene(name)
    doors = [n for n in scene['parts'] if n.endswith('door_casing')]
    floor = min(v[2] for v in scene['parts']['gable_wall_front'].mesh.vertices)
    assert floor == pytest.approx(0, abs=1e-6)
    for name in doors:
        assert min(v[2] for v in scene['parts'][name].mesh.vertices) == pytest.approx(floor, abs=1e-6), name


# ------------------------------------------------------------------ triangulation
def test_triangulation_covers_exactly_the_polygon_area():
    sq = [(0, 0), (10, 0), (10, 10), (0, 10)]
    holes = [[(2, 2), (4, 2), (4, 4), (2, 4)], [(6, 6), (8, 6), (8, 8), (6, 8)]]
    pts, tris = triangulate(sq, holes)
    area = sum(abs(signed_area([pts[i] for i in t])) for t in tris)
    assert area == pytest.approx(100 - 8)
    m = extrude(sq, holes, 3.0, lambda u, v, w: (u, v, w))
    assert m.is_watertight() and m.volume() == pytest.approx(92 * 3)


def test_triangulation_of_a_comb_with_a_notched_hole():
    comb = [(0, 0), (30, 0), (30, 10), (25, 10), (25, 5), (20, 5), (20, 10), (15, 10), (15, 5), (10, 5),
            (10, 10), (5, 10), (5, 5), (0, 5)]
    hole = [(3, 1), (3, 3), (27, 3), (27, 1)]
    m = extrude(comb, [hole], 2.0, lambda u, v, w: (u, v, w))
    assert m.is_watertight()
    assert m.volume() == pytest.approx((abs(signed_area(comb)) - abs(signed_area(hole))) * 2)


def test_triangulation_when_two_hole_bridges_share_an_outline_corner():
    """Both holes bridge to the outline's top right corner, which then appears three times in the merged polygon;
    an ear at another copy of that corner must not be clipped across the first bridge (regression: the steep-roof
    dormer's main roof panel had overlapping, flipped triangles and was not closed)."""
    rect = lambda x0, y0, x1, y1: [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    outer = rect(0.05, 0.05, 98.05, 75.15)
    holes = [rect(6, 28.05, 9, 38.05), rect(39.5, 51.321, 45.5, 58.017)]
    pts, tris = triangulate(outer, holes)
    assert all(signed_area([pts[i] for i in t]) > 0 for t in tris), "flipped triangle"
    area = sum(signed_area([pts[i] for i in t]) for t in tris)
    assert area == pytest.approx(abs(signed_area(outer)) - sum(abs(signed_area(h)) for h in holes))
    m = extrude(outer, holes, 3.0, lambda u, v, w: (u, v, w))
    assert m.is_watertight()


@pytest.mark.parametrize('seed', range(40))
def test_triangulation_of_random_slotted_panels(seed):
    """Random disjoint slots (half of them on shared rows/columns, so bridges meet at the same outline corners and
    rays run along edges) in a panel with finger notches: the triangles cover exactly the material, none flipped,
    and the extruded solid is closed."""
    rng = random.Random(seed)
    W, H = rng.uniform(40, 120), rng.uniform(30, 90)
    outer = [(0, 0)]
    x = 0.0
    while x + 12 < W:                                   # notches along the bottom edge
        x += rng.uniform(4, 8)
        outer += [(x, 0), (x, -3), (x + 4, -3), (x + 4, 0)]
        x += 4
    outer += [(W, 0), (W, H), (0, H)]
    rows, cols = [rng.uniform(5, H - 10) for _ in range(2)], [rng.uniform(5, W - 10) for _ in range(2)]
    holes, boxes = [], []
    for _ in range(rng.randint(2, 7)):
        w, h = rng.choice([(3, 6), (6, 3), (2.9, 9.9), (5.9, 6.6)])
        x0 = rng.choice(cols) if rng.random() < 0.5 else rng.uniform(3, W - w - 3)
        y0 = rng.choice(rows) if rng.random() < 0.5 else rng.uniform(3, H - h - 3)
        box = (x0, y0, x0 + w, y0 + h)
        if box[2] > W - 2 or box[3] > H - 2 or any(not (box[2] + 1 < b[0] or b[2] + 1 < box[0] or box[3] + 1 < b[1] or b[3] + 1 < box[1]) for b in boxes):
            continue
        boxes.append(box)
        holes.append([(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])])
    pts, tris = triangulate(outer, holes)
    assert all(signed_area([pts[i] for i in t]) > -1e-9 for t in tris), "flipped triangle"
    area = sum(signed_area([pts[i] for i in t]) for t in tris)
    assert area == pytest.approx(abs(signed_area(outer)) - sum(abs(signed_area(h)) for h in holes), rel=1e-9)
    assert extrude(outer, holes, 3.0, lambda u, v, w: (u, v, w)).is_watertight()


# ------------------------------------------------------------------ file formats
@pytest.fixture(scope='module')
def parts():
    return full_house().build_model()


def test_stl_has_every_triangle(parts):
    data = to_stl(parts)
    (count,) = struct.unpack_from('<I', data, 80)
    assert count == sum(len(p.mesh.triangles) for p in parts)
    assert len(data) == 84 + 50 * count
    # every stored normal is the unit normal of its triangle's winding, and the winding faces outward: the triangle
    # soup encloses exactly the parts' volume (a flipped normal or winding fails one or the other)
    volume = 0.0
    for i in range(count):
        rec = struct.unpack_from('<12f', data, 84 + 50 * i)
        n, a, b, c = np.array(rec[0:3]), np.array(rec[3:6]), np.array(rec[6:9]), np.array(rec[9:12])
        face = np.cross(b - a, c - a)
        if np.linalg.norm(face) > 1e-9:
            assert np.dot(n, face / np.linalg.norm(face)) == pytest.approx(1.0, abs=1e-4), f"triangle {i}"
        volume += float(np.dot(a, np.cross(b, c))) / 6
    assert volume == pytest.approx(sum(p.mesh.volume() for p in parts), rel=1e-4)


def test_3mf_package_parses_and_round_trips(parts):
    z = zipfile.ZipFile(io.BytesIO(to_3mf(parts)))
    assert set(z.namelist()) == {'[Content_Types].xml', '_rels/.rels', '3D/3dmodel.model'}
    for name in z.namelist():
        ET.fromstring(z.read(name))                                   # well-formed XML
    ns = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    root = ET.fromstring(z.read('3D/3dmodel.model'))
    assert root.get('unit') == 'millimeter'
    objs = root.findall('.//m:object', ns)
    assert [o.get('name') for o in objs] == [p.name for p in parts]
    assert len(root.findall('.//m:build/m:item', ns)) == len(parts)
    for o, p in zip(objs, parts):
        verts = [(float(v.get('x')), float(v.get('y')), float(v.get('z'))) for v in o.findall('.//m:vertex', ns)]
        tris = [(int(t.get('v1')), int(t.get('v2')), int(t.get('v3'))) for t in o.findall('.//m:triangle', ns)]
        assert Mesh(verts, tris).volume() == pytest.approx(p.mesh.volume(), rel=1e-6)
        assert Mesh(verts, tris).is_watertight()
    colors = [b.get('displaycolor') for b in root.findall('.//m:base', ns)]
    assert all(len(c) == 9 and c.startswith('#') for c in colors)


def test_glb_is_a_valid_glb_with_one_node_per_part(parts):
    data = to_glb(parts)
    magic, version, length = struct.unpack_from('<4sII', data, 0)
    assert (magic, version, length) == (b'glTF', 2, len(data))
    jlen, jtype = struct.unpack_from('<I4s', data, 12)
    assert jtype == b'JSON'
    doc = json.loads(data[20:20 + jlen])
    blen, btype = struct.unpack_from('<I4s', data, 20 + jlen)
    assert btype == b'BIN\0' and 28 + jlen + blen == len(data) and blen % 4 == 0 and jlen % 4 == 0
    assert doc['buffers'][0]['byteLength'] == blen
    assert [n['name'] for n in doc['nodes']] == [p.name for p in parts]
    for acc, view in ((a, doc['bufferViews'][a['bufferView']]) for a in doc['accessors']):
        assert view['byteOffset'] + view['byteLength'] <= blen and view['byteLength'] == 12 * acc['count']
    # Y-up metres: the lowest point of the model is the floor at y = 0, the peak is the roof apex
    pos = [a for m in doc['meshes'] for a in [doc['accessors'][m['primitives'][0]['attributes']['POSITION']]]]
    assert min(a['min'][1] for a in pos) == pytest.approx(0, abs=1e-9)
    zmax = max(v[2] for p in parts for v in p.mesh.vertices) / 1000
    assert max(a['max'][1] for a in pos) == pytest.approx(zmax, abs=1e-6)


def _glb_vec3(data, doc, index):
    jlen = struct.unpack_from('<I', data, 12)[0]
    acc = doc['accessors'][index]
    view = doc['bufferViews'][acc['bufferView']]
    start = 20 + jlen + 8 + view['byteOffset'] + acc.get('byteOffset', 0)
    return acc, [struct.unpack_from('<3f', data, start + 12 * k) for k in range(acc['count'])]


def test_glb_normals_face_outward_and_bounds_match_the_data(parts):
    """Every part: flat normals that are the unit normals of the triangle winding, an outward winding (positive
    enclosed volume, equal to the part's), and POSITION min/max equal to the stored float32 values (glTF requires
    them exact; validators report ACCESSOR_MIN/MAX_MISMATCH otherwise)."""
    data = to_glb(parts)
    doc = json.loads(data[20:20 + struct.unpack_from('<I', data, 12)[0]])
    for mesh, part in zip(doc['meshes'], parts):
        attrs = mesh['primitives'][0]['attributes']
        acc, pos = _glb_vec3(data, doc, attrs['POSITION'])
        _, nor = _glb_vec3(data, doc, attrs['NORMAL'])
        assert acc['min'] == [min(p[k] for p in pos) for k in range(3)], part.name
        assert acc['max'] == [max(p[k] for p in pos) for k in range(3)], part.name
        volume = 0.0
        for t in range(0, len(pos), 3):
            a, b, c = (np.array(pos[t + j]) for j in range(3))
            face = np.cross(b - a, c - a)
            if np.linalg.norm(face) > 1e-12:
                for j in range(3):
                    assert np.dot(nor[t + j], face / np.linalg.norm(face)) == pytest.approx(1.0, abs=1e-3), part.name
            volume += float(np.dot(a, np.cross(b, c))) / 6
        assert volume * 1e9 == pytest.approx(part.mesh.volume(), rel=1e-4), part.name     # m^3 -> mm^3


def test_unknown_format_is_rejected(parts):
    with pytest.raises(ValueError, match='unknown 3D format'):
        encode('obj', parts)
    assert FORMATS == ('stl', '3mf', 'glb')


# ------------------------------------------------------------------ API and CLI
def test_generate_3d_writes_files_by_extension(tmp_path):
    house = full_house()
    for ext in FORMATS:
        path = tmp_path / f'house.{ext}'
        house.generate_3d(str(path))
        assert path.read_bytes() == encode(ext, house.build_model())


def test_generate_3d_returns_bytes_with_explicit_format():
    house = full_house(chimney=False, dormer=False)
    assert house.generate_3d(fmt='stl') == to_stl(house.build_model())
    with pytest.raises(ValueError):
        house.generate_3d()


def test_house_styles_without_floor_or_roof():
    from house_maker.constants import HouseStyle
    for style, missing in ((HouseStyle.HOUSE_NO_ROOF, 'roof_panel_left'), (HouseStyle.WALLS_ONLY, 'floor')):
        house = HouseMaker(**BASE, gable_angle=35, house_style=style)
        names = {p.name for p in house.build_model()}
        assert missing not in names and 'side_wall_left' in names


def test_cli_writes_3mf_by_default_and_honours_the_option(tmp_path):
    svg = tmp_path / 'h.svg'
    run = lambda *a: subprocess.run([sys.executable, '-m', 'house_maker.generate_house', '-o', str(svg), *a],
                                    capture_output=True, text=True, check=True)
    run()
    assert (tmp_path / 'h.3mf').exists() and not (tmp_path / 'h.stl').exists()
    run('--3d', 'all')
    assert all((tmp_path / f'h.{e}').exists() for e in FORMATS)
    for e in FORMATS:
        (tmp_path / f'h.{e}').unlink()
    run('--3d', 'none')
    assert svg.exists() and not any((tmp_path / f'h.{e}').exists() for e in FORMATS)
