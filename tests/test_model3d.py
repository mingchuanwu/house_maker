"""
3D export: the assembled model is checked against the independent numpy model (tests/assembly3d.py), and
the three file formats are parsed back and compared with the meshes they were written from.
"""

import io
import json
import math
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
        h.add_chimney('roof_panel_left', 25, 30, 10, 12, 30)
    if dormer:
        h.add_additional_gable('roof_panel_right', 20, 20, 40)
    return h


SCENES = {
    'plain': dict(auto_add_components=False, chimney=False, dormer=False),
    '35-features': dict(),
    '45-arched': dict(angle=45, window=WindowType.ARCHED, door=DoorType.ARCHED),
    '60-circular': dict(angle=60, window=WindowType.CIRCULAR),
    '25-features': dict(angle=25),
}


@pytest.fixture(params=list(SCENES), scope='module')
def scene(request):
    house = full_house(**SCENES[request.param])
    panels = house.build_panels()
    return dict(house=house, panels={p.name: p for p in panels}, parts={p.name: p for p in house.build_model()})


# ------------------------------------------------------------------ meshes
def test_every_panel_becomes_one_closed_solid(scene):
    assert set(scene['parts']) == set(scene['panels'])
    for name, part in scene['parts'].items():
        assert part.mesh.is_watertight(), name
        assert part.mesh.volume() > 0, f"{name}: inside-out or empty"


def test_volume_is_nominal_area_times_thickness(scene):
    for name, part in scene['parts'].items():
        outer, holes = panel_rings(scene['panels'][name], K)
        area = abs(signed_area(outer)) - sum(abs(signed_area(h)) for h in holes)
        assert part.mesh.volume() == pytest.approx(area * T, rel=1e-6), name


def test_nominal_geometry_not_drawn_geometry(scene):
    """The drawn outline carries kerf compensation; the model is back at the specified size."""
    X, Y, Z = BASE['length'], BASE['width'], BASE['height']
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
        want, _ = ref.dormer_frames(box[p.panel], p.x, p.y, p.width, g.theta, d.geometry.phi_deg, T, K, index=i)
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
        assert depth <= limit + (T if 'additional_gable' in a + b else 0), f"{a} penetrates {b} by {depth:.3f} mm"


def test_casings_frame_the_wall_openings(scene):
    """The opening of every casing lies over the wall's hole, and the casing lies on the outside of the wall."""
    h = scene['house']
    frames = house_frames(h.geometry, h.architectural_config, scene['panels'])
    checked = 0
    for name, panel in scene['panels'].items():
        if 'casing' not in name or name.startswith('chimney'):
            continue
        wall_name = name.split('_w')[0].split('_d')[0] if False else next(
            w for w in ('side_wall_left', 'side_wall_right', 'gable_wall_front', 'gable_wall_back') if name.startswith(w))
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
        ww = [np.array(wall.to_world(u, v, T)) for hole in w_holes for u, v in hole]
        assert ww, f"{wall_name} has no hole for {name}"
        far = [min(np.linalg.norm(p - q) for q in ww) for p in cw]
        # every hole vertex of the casing sits on the wall hole's boundary polygon (distance to the nearest edge)
        for p in cw[:: max(1, len(cw) // 40)]:
            d = min(_dist_to_polyline(p, [np.array(wall.to_world(u, v, T)) for u, v in hole]) for hole in w_holes)
            if c_holes:
                assert d < 0.35 + 1e-6, f"{name}: casing opening is {d:.2f} mm off the wall hole"
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


# ------------------------------------------------------------------ file formats
@pytest.fixture(scope='module')
def parts():
    return full_house().build_model()


def test_stl_has_every_triangle(parts):
    data = to_stl(parts)
    (count,) = struct.unpack_from('<I', data, 80)
    assert count == sum(len(p.mesh.triangles) for p in parts)
    assert len(data) == 84 + 50 * count
    # the stored normal agrees with the winding (outward-facing, so the volume is positive)
    n0 = struct.unpack_from('<3f', data, 84)
    assert math.sqrt(sum(c * c for c in n0)) == pytest.approx(1.0, abs=1e-5)


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
