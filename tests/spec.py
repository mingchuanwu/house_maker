"""
Independent closed-form specification of the cut panels, written from the documented rules - not
from the library's code - so that errors common to all panels (a wrong kerf sign, a wrong overhang)
cannot cancel out in relative comparisons.

Inputs:  X x Y floor (length x width), Z wall height, theta roof angle, t thickness, k kerf, f finger.
Rules:   every outer dimension is nominal + k (the laser eats k/2 per edge);
         gable wall = Y + 2t wide (it spans both side walls); roof panels overhang 3t each end.
"""

import math


def box_panel_sizes(X, Y, Z, theta, t, k):
    """Drawn (kerf-compensated) nominal width x height of every main panel."""
    gable_w = Y + k + 2 * t
    half = gable_w / 2
    peak = half * math.tan(math.radians(theta))
    rafter = half / math.cos(math.radians(theta))
    return {
        'floor': (X + k, Y + k),
        'side_wall_left': (X + k, Z + k),
        'side_wall_right': (X + k, Z + k),
        'gable_wall_front': (gable_w, Z + k + peak),
        'gable_wall_back': (gable_w, Z + k + peak),
        'roof_panel_left': (X + k + 6 * t, rafter + 4 * t + k),
        'roof_panel_right': (X + k + 6 * t, rafter + 3 * t + k),
    }


def gable_peak(Y, theta, t, k):
    return (Y + k + 2 * t) / 2 * math.tan(math.radians(theta))


CONFIGS = [
    dict(length=100, width=80, height=70, gable_angle=45, material_thickness=3.0, kerf=0.1),
    dict(length=160, width=90, height=120, gable_angle=30, material_thickness=2.0, kerf=0.0),
    dict(length=80, width=60, height=70, gable_angle=35, material_thickness=3.0, kerf=0.2),
    dict(length=200, width=150, height=130, gable_angle=60, material_thickness=4.0, kerf=0.15),
]


def cid(c):
    return f"{c['length']}x{c['width']}x{c['height']}-a{c['gable_angle']}-t{c['material_thickness']}-k{c['kerf']}"
