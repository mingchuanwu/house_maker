"""
3D file formats for an assembled model: binary STL, 3MF and glTF binary (GLB). Pure standard library.

A model is a list of `Part`s (a name, a colour and a closed triangle mesh), all in millimetres with Z up.
STL carries geometry only (parts are merged); 3MF keeps every part as a named object with its colour;
GLB keeps named, coloured nodes too (rotated to glTF's Y-up and scaled to metres, as the format requires).
"""

import io
import json
import math
import struct
import zipfile
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from .mesh import Mesh, Vec

FORMATS = ('stl', '3mf', 'glb')


@dataclass
class Part:
    name: str
    mesh: Mesh
    color: Tuple[int, int, int] = (200, 170, 120)


def _normal(a: Vec, b: Vec, c: Vec) -> Vec:
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    length = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
    return (0.0, 0.0, 0.0) if length == 0 else (n[0] / length, n[1] / length, n[2] / length)


# ------------------------------------------------------------------------------------------------ STL
def to_stl(parts: Iterable[Part]) -> bytes:
    """Binary STL with every part merged into one triangle soup."""
    tris = [tuple(p.mesh.vertices[i] for i in t) for p in parts for t in p.mesh.triangles]
    out = io.BytesIO()
    out.write(b'house_maker'.ljust(80, b'\0'))
    out.write(struct.pack('<I', len(tris)))
    for a, b, c in tris:
        out.write(struct.pack('<12fH', *_normal(a, b, c), *a, *b, *c, 0))
    return out.getvalue()


# ------------------------------------------------------------------------------------------------ 3MF
_CONTENT_TYPES = ('<?xml version="1.0" encoding="UTF-8"?>'
                  '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                  '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                  '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
                  '</Types>')
_RELS = ('<?xml version="1.0" encoding="UTF-8"?>'
         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
         'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')


def _xml_escape(text: str) -> str:
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def to_3mf(parts: Iterable[Part]) -> bytes:
    """3MF package: one named, coloured object per part, in millimetres."""
    parts = list(parts)
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
           '<resources><basematerials id="1">']
    for p in parts:
        xml.append(f'<base name="{_xml_escape(p.name)}" displaycolor="#{p.color[0]:02X}{p.color[1]:02X}{p.color[2]:02X}FF"/>')
    xml.append('</basematerials>')
    for i, p in enumerate(parts):
        xml.append(f'<object id="{i + 2}" type="model" name="{_xml_escape(p.name)}" pid="1" pindex="{i}"><mesh><vertices>')
        xml.extend(f'<vertex x="{x:.5f}" y="{y:.5f}" z="{z:.5f}"/>' for x, y, z in p.mesh.vertices)
        xml.append('</vertices><triangles>')
        xml.extend(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in p.mesh.triangles)
        xml.append('</triangles></mesh></object>')
    xml.append('</resources><build>')
    xml.extend(f'<item objectid="{i + 2}"/>' for i in range(len(parts)))
    xml.append('</build></model>')
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', _CONTENT_TYPES)
        z.writestr('_rels/.rels', _RELS)
        z.writestr('3D/3dmodel.model', ''.join(xml))
    return out.getvalue()


# ------------------------------------------------------------------------------------------------ GLB
_MM_TO_M = 0.001


def to_glb(parts: Iterable[Part]) -> bytes:
    """glTF 2.0 binary: one mesh + node per part, flat-shaded, Y-up, metres."""
    parts = list(parts)
    blob = bytearray()
    views, accessors, meshes, nodes, materials = [], [], [], [], []
    for i, p in enumerate(parts):
        pos, nor = [], []
        for t in p.mesh.triangles:
            v = [p.mesh.vertices[j] for j in t]
            n = _normal(*v)
            for x, y, z in v:                                        # Z-up (mm) -> Y-up (m): (x, y, z) -> (x, z, -y)
                pos.append((x * _MM_TO_M, z * _MM_TO_M, -y * _MM_TO_M))
                nor.append((n[0], n[2], -n[1]))
        lo = [min(c[k] for c in pos) for k in range(3)]
        hi = [max(c[k] for c in pos) for k in range(3)]
        attrs = {}
        for key, data, extra in (('POSITION', pos, {'min': lo, 'max': hi}), ('NORMAL', nor, {})):
            views.append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': 12 * len(data), 'target': 34962})
            for vec in data:
                blob += struct.pack('<3f', *vec)
            accessors.append({'bufferView': len(views) - 1, 'componentType': 5126, 'count': len(data),
                              'type': 'VEC3', **extra})
            attrs[key] = len(accessors) - 1
        meshes.append({'name': p.name, 'primitives': [{'attributes': attrs, 'material': i}]})
        nodes.append({'name': p.name, 'mesh': i})
        r, g, b = (c / 255 for c in p.color)
        materials.append({'name': p.name, 'doubleSided': False,
                          'pbrMetallicRoughness': {'baseColorFactor': [r, g, b, 1.0], 'metallicFactor': 0.0,
                                                   'roughnessFactor': 0.9}})
    doc = {'asset': {'version': '2.0', 'generator': 'house_maker'},
           'scene': 0, 'scenes': [{'nodes': list(range(len(nodes)))}], 'nodes': nodes, 'meshes': meshes,
           'materials': materials, 'accessors': accessors, 'bufferViews': views,
           'buffers': [{'byteLength': len(blob)}]}
    js = json.dumps(doc, separators=(',', ':')).encode()
    js += b' ' * (-len(js) % 4)
    blob += b'\0' * (-len(blob) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    return (struct.pack('<4sII', b'glTF', 2, total) + struct.pack('<I4s', len(js), b'JSON') + js +
            struct.pack('<I4s', len(blob), b'BIN\0') + bytes(blob))


_WRITERS = {'stl': to_stl, '3mf': to_3mf, 'glb': to_glb}


def encode(fmt: str, parts: List[Part]) -> bytes:
    try:
        return _WRITERS[fmt](parts)
    except KeyError:
        raise ValueError(f"unknown 3D format {fmt!r}; choose one of {', '.join(FORMATS)}") from None
