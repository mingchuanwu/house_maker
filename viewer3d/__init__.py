"""
In-house 3D viewer: one self-contained HTML page (WebGL, no server, no network) for visual inspection of the
assembled house - orbit, outliner, exploded view, section plane, X-ray.

* ``build_payload(geometry, config, panels)``  the model as plain JSON-ready data
* ``build_page(payload)``                      the HTML page as a string

``HouseMaker.generate_view()`` and ``house-maker --3d view`` use both.
"""

from .page import build_page
from .payload import build_payload, part_group

__all__ = ['build_page', 'build_payload', 'part_group']
