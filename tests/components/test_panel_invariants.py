"""
Every panel of every scene: what is drawn equals what was declared.

For each panel the outline must be a simple counter-clockwise polygon through the nominal corners,
its fingers must be exactly the planned ones (position, width, depth), its area must equal the
nominal area plus tabs minus notches, drawn slots must equal the declared slots, and all cut-outs and
score lines must lie inside the outline without touching it or each other.
"""

import pytest

from ..conftest import make_house
from .. import invariants
from ..spec import CONFIGS, cid

SCENES = {f"box-{cid(c)}": dict(c, auto_add_components=True) for c in CONFIGS}
SCENES.update({
    'no-components': dict(),
    'chimney-l35': dict(gable_angle=35, length=150, width=120, height=90,
                        chimneys=[('roof_panel_left', 25, 30, 10, 12, 30)]),
    'chimney-r60': dict(gable_angle=60, length=150, width=120, height=90,
                        chimneys=[('roof_panel_right', 40, 30, 14, 20, 24)]),
    'chimney-k0': dict(gable_angle=45, kerf=0.0, length=150, width=120, height=90,
                       chimneys=[('roof_panel_left', 25, 30, 12, 16, 40)]),
    'dormer-small': dict(length=140, width=110, height=90, dormers=[('roof_panel_left', 40, 25, 25)]),
    'dormer-large': dict(length=200, width=160, height=90, gable_angle=35,
                         dormers=[('roof_panel_right', 40, 20, 70)]),
    'dormer-a60': dict(length=200, width=160, height=90, gable_angle=60,
                       dormers=[('roof_panel_left', 40, 20, 60)]),
    'everything': dict(auto_add_components=True, length=220, width=150, height=110, gable_angle=40,
                       chimneys=[('roof_panel_right', 40, 30, 12, 14, 20)],
                       dormers=[('roof_panel_left', 40, 25, 40)]),
})


@pytest.fixture(params=list(SCENES), ids=list(SCENES))
def scene(request):
    house = make_house(**SCENES[request.param])
    return house, house.build_panels()


@pytest.mark.parametrize('check', invariants.ALL_CHECKS, ids=lambda f: f.__name__[len('check_'):])
def test_invariant(scene, check):
    house, panels = scene
    check(house, panels)
