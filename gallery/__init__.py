"""
House gallery: example houses, each with its command line, a description and a 3D model.

* ``houses.py``   the houses (command line + description) - add one there
* ``build.py``    writes index.html (the table, with inline orbit-only previews) and views/NAME.view.html (full viewers)

    python -m house_maker.gallery        (or: make gallery)
"""

from .build import build_gallery, command
from .houses import HOUSES

__all__ = ['HOUSES', 'build_gallery', 'command']
