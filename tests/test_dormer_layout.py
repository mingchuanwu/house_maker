"""
Rows of dormers (`add_dormers`, `--dormers`): over the windows below when the counts match, else in equal bays; one row
as low as they fit; a warning when dormers cover more than half a roof; all or nothing, with proposals when a row fails.
"""

import pathlib
import subprocess
import sys
import warnings

import pytest

from house_maker import PlacementError
from house_maker.placement3d import box_frames
from .conftest import make_house

PKG = pathlib.Path(__file__).resolve().parent.parent


def world_x(house, panel, u, v=0.0):
    return box_frames(house.geometry)[panel].to_world(u, v, 0.0)[0]


def centres(house, panel):
    return sorted(world_x(house, panel, d.position.x + d.position.width / 2, d.position.y)
                  for d in house.architectural_config.get_additional_gables_for_panel(panel))


@pytest.mark.parametrize('count', [1, 2, 3])
def test_evenly_spaced_in_equal_bays(count):
    house = make_house(length=240, width=140, height=100, gable_angle=45)
    house.add_dormers('left', count, width=25)
    want = [240 * (i + 0.5) / count for i in range(count)]
    assert centres(house, 'roof_panel_left') == pytest.approx(want, abs=1e-6)


def test_over_the_windows_when_the_counts_match():
    house = make_house(length=240, width=140, height=100, gable_angle=45)
    for x in (40, 150):                                           # two window columns on the wall below
        house.add_window('side_wall_left', x, 30, 30, 25)
    house.add_dormers('left', 2, width=25)
    wall = box_frames(house.geometry)['side_wall_left']
    windows = sorted(wall.to_world(w.position.x + w.position.width / 2, w.position.y, 0.0)[0]
                     for w in house.architectural_config.get_windows_for_panel('side_wall_left'))
    assert centres(house, 'roof_panel_left') == pytest.approx(windows, abs=1e-6)
    house.add_dormers('right', 3, width=20)                      # right wall has no windows: bays
    assert centres(house, 'roof_panel_right') == pytest.approx([40, 120, 200], abs=1e-6)


def test_one_row_as_low_as_they_all_fit_on_both_sides():
    house = make_house(length=240, width=140, height=100, gable_angle=45)
    dormers = house.add_dormers('both', 3, width=25)
    cfg = house.architectural_config
    for panel in ('roof_panel_left', 'roof_panel_right'):
        row = [d for d in dormers if d.position.panel == panel]
        assert len(row) == 3 and len({round(d.position.y, 9) for d in row}) == 1
        # one step lower and at least one of them would not fit (with the others there it is checked one by one)
        d = row[0]
        others = [g for g in cfg.additional_gables if g is not d]
        cfg.additional_gables[:] = others
        assert not cfg.dormer_fits(panel, d.position.x, d.position.y + 0.1 + 1e-9, 25) or any(
            not cfg.dormer_fits(panel, e.position.x, e.position.y + 0.1 + 1e-9, 25) for e in row[1:])
        cfg.additional_gables[:] = others + [d]


def test_warning_when_dormers_cover_more_than_half_the_roof():
    house = make_house(length=200, width=140, height=100, gable_angle=45)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        house.add_dormers('right', 4, width=30)                  # 120 of 209 mm
    share = 120 / house.geometry.get_panel_dimensions()['roof_panel_right'][0]
    assert share > 0.5
    assert [str(m.message) for m in w if 'dominate' in str(m.message)] == [
        f"dormers cover {share:.0%} of roof_panel_right's width; more than half tends to dominate the roof "
        "(narrower or fewer dormers look better)"]
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        house.add_dormers('left', 3, width=30)                   # 43%: fine
        house.add_additional_gable('roof_panel_left', 160, 10, 25)   # by hand, too: now over half
    assert len([m for m in w if 'dominate' in str(m.message)]) == 1


def test_a_row_that_does_not_fit_adds_nothing_and_proposes_one_that_does():
    house = make_house(length=80, width=60, height=70, gable_angle=35, finger_length=10)      # the CLI's house
    with pytest.raises(PlacementError, match=r'The row would fit with width at most ([\d.]+) for 3 dormers') as err:
        house.add_dormers('left', 3, width=40)
    assert house.architectural_config.additional_gables == []
    width = float(err.value.message.split('width at most ')[1].split(' ')[0])
    with pytest.warns(UserWarning, match='dominate'):          # it fits - though on this small roof it is over half
        house.add_dormers('left', 3, width=width)
    assert len(house.architectural_config.additional_gables) == 3


def test_bad_side_or_count():
    house = make_house()
    with pytest.raises(PlacementError, match='left, right or both'):
        house.add_dormers('top', 2)
    with pytest.raises(PlacementError, match='at least 1'):
        house.add_dormers('left', 0)


def test_cli_dormers(tmp_path):
    out = tmp_path / 'h.svg'
    run = lambda *a: subprocess.run([sys.executable, '-m', 'house_maker.generate_house', '-o', str(out), '--3d', 'none',
                                     *a], capture_output=True, text=True, cwd=PKG.parent)
    r = run('--length', '200', '--width', '140', '--height', '100', '--dormers', 'both:count=3:width=30')
    assert r.returncode == 0, r.stdout + r.stderr
    assert all(f'id="additional_gable_front_{i}"' in out.read_text() for i in range(6))
    r = run('--dormers', 'left:width=30')
    assert r.returncode == 2 and 'count=N' in r.stderr
    r = run('--dormers', 'left:count=3:width=40')
    assert r.returncode == 1 and '--dormers left:count=3:width=40' in r.stdout and 'The row would fit with' in r.stdout
