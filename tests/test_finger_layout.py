"""
Finger-joint layout policy, tested as properties of FingerJointEngine over a sweep of edge lengths,
finger lengths, thicknesses and kerfs - plus a few pinned values that document the policy.
"""

import itertools

import pytest

from house_maker.exceptions import FingerJointError
from house_maker.geometry import Point
from house_maker.joints import FEMALE, MALE, FingerJointEngine
from .geom import flat

EPS = 1e-9
FINGERS = (5.0, 10.0, 15.0, 20.0)
LENGTHS = [x * 0.7 for x in range(20, 700)]            # 14 .. 490 mm


def engines():
    for f, (t, k), single in itertools.product(FINGERS, [(3.0, 0.1), (2.0, 0.0), (4.0, 0.2)], (False, True)):
        yield FingerJointEngine(t, f, k, single_joints=single)


# ------------------------------------------------------------------ the policy, pinned
@pytest.mark.parametrize('length,count', [
    (37.4, 1), (37.5, 1),           # below 2.5 finger lengths: always one finger
    (83.9, 1), (84.0, 3), (100, 3),     # 3 fingers from 5.6 f
    (137.9, 3), (138.0, 5), (180, 5),   # 5 fingers from 9.2 f
    (191.9, 5), (192.0, 7), (400, 7),   # 7 is the maximum
])
def test_joint_count_ladder_for_15mm_fingers(length, count):
    assert FingerJointEngine(3.0, 15.0).joint_count(length) == count


def test_single_joints_mode_always_gives_one_finger():
    e = FingerJointEngine(3.0, 15.0, single_joints=True)
    assert all(e.joint_count(L) == 1 for L in (20, 50, 100, 400))
    assert len(e.plan_edge(400, MALE).fingers) == 1


@pytest.mark.parametrize('L,usable_ok', [(22.49, False), (22.5, True), (22.51, True)])
def test_edge_needs_one_and_a_half_finger_lengths(L, usable_ok):
    e = FingerJointEngine(3.0, 15.0)
    assert (e.plan_edge(L, MALE) is not None) == usable_ok


def test_inset_edges_are_judged_on_the_length_the_fingers_occupy():
    e = FingerJointEngine(3.0, 15.0)
    assert e.plan_edge(22.5 + 6, MALE, inset=3.0) is not None
    assert e.plan_edge(22.5 + 5.99, MALE, inset=3.0) is None


# ------------------------------------------------------------------ properties
def test_layouts_are_valid_symmetric_and_well_spaced():
    for e in engines():
        f = e.finger_length
        previous = 0
        for L in LENGTHS:
            spec = e.plan_edge(L, MALE)
            if L < 1.5 * f:
                assert spec is None
                continue
            n = len(spec.nominal)
            assert n % 2 == 1 and 1 <= n <= 7, (L, n)
            if e.single_joints:
                assert n == 1
            for a, b in spec.nominal:
                assert b - a == pytest.approx(f, abs=EPS)                       # every finger is exactly f long
            assert spec.nominal[0][0] >= e.MIN_GAP_RATIO * f - EPS if n > 1 else spec.nominal[0][0] >= 0.25 * f - EPS
            assert spec.nominal[-1][1] <= L - (e.MIN_GAP_RATIO * f if n > 1 else 0.25 * f) + EPS
            for (a0, a1), (b0, b1) in zip(spec.nominal, spec.nominal[1:]):
                assert b0 - a1 >= e.MIN_GAP_RATIO * f - EPS                     # no cramped gaps
            mirrored = sorted((L - b, L - a) for a, b in spec.nominal)
            assert flat(mirrored) == pytest.approx(flat(sorted(spec.nominal)), abs=1e-7)      # symmetric: mating edges mirror
            if not e.single_joints:
                assert n >= previous, f"finger count decreased at L={L}"        # longer edge never gets fewer fingers
                previous = n


def test_kerf_changes_only_the_width_never_the_centre_or_depth():
    for e in engines():
        male, female = e.plan_edge(150, MALE), e.plan_edge(150, FEMALE)
        assert male.nominal == female.nominal
        assert male.depth == female.depth == e.thickness
        for (m0, m1), (f0, f1), (n0, n1) in zip(male.fingers, female.fingers, male.nominal):
            assert (m0 + m1) / 2 == pytest.approx((n0 + n1) / 2) == pytest.approx((f0 + f1) / 2)
            assert m1 - m0 == pytest.approx(e.finger_length + e.kerf)       # tab: material grows by kerf
            assert f1 - f0 == pytest.approx(e.finger_length - e.kerf)       # notch: void shrinks by kerf


def test_inset_shifts_and_keeps_symmetry():
    e = FingerJointEngine(3.0, 15.0)
    plain = e.plan_edge(100, MALE)                          # fingers laid out over 100
    inset = e.plan_edge(106, MALE, inset=3.0)               # same fingers over the inner 100, shifted by 3
    assert flat((a + 3, b + 3) for a, b in plain.nominal) == pytest.approx(flat(inset.nominal))
    L = 106
    assert flat(sorted((L - b, L - a) for a, b in inset.nominal)) == pytest.approx(flat(sorted(inset.nominal)))


def test_forced_count_and_cramped_fallback():
    e = FingerJointEngine(3.0, 15.0)
    assert len(e.plan_edge(60, MALE, count=1).nominal) == 1
    assert len(e.plan_edge(150, MALE, count=3).nominal) == 3
    # 7 fingers cannot fit 60 mm with decent gaps: the layout backs off by two until it does
    n = len(e.plan_edge(60, MALE, count=7).nominal)
    assert n in (1, 3) and n % 2 == 1


def test_one_finger_is_centred():
    spec = FingerJointEngine(3.0, 15.0).plan_edge(50, MALE, count=1)
    assert spec.nominal == ((17.5, 32.5),)


# ------------------------------------------------------------------ tracing and slots
def test_trace_edge_orientation_male_out_female_in():
    e = FingerJointEngine(3.0, 10.0, 0.0)
    a, b = Point(0, 0), Point(40, 0)
    male = e.trace_edge(a, b, e.spec(MALE, 40, [(15, 25)]))
    female = e.trace_edge(a, b, e.spec(FEMALE, 40, [(15, 25)]))
    # counter-clockwise outline: the outward normal of a +x edge is -y
    assert male == "L 15.000,0.000 L 15.000,-3.000 L 25.000,-3.000 L 25.000,0.000 L 40.000,0.000"
    assert female == "L 15.000,0.000 L 15.000,3.000 L 25.000,3.000 L 25.000,0.000 L 40.000,0.000"
    assert e.trace_edge(a, b, None) == "L 40.000,0.000"


def test_trace_edge_on_a_rotated_edge():
    e = FingerJointEngine(3.0, 10.0, 0.0)
    path = e.trace_edge(Point(0, 0), Point(0, 40), e.spec(MALE, 40, [(15, 25)]))   # +y edge: outward is +x
    assert path == "L 0.000,15.000 L 3.000,15.000 L 3.000,25.000 L 0.000,25.000 L 0.000,40.000"


def test_trace_outline_closes_the_polygon():
    e = FingerJointEngine(3.0, 10.0, 0.0)
    path = e.trace_outline([Point(0, 0), Point(40, 0), Point(40, 30), Point(0, 30)], [None, None, None, None])
    assert path == "M 0.000,0.000 L 40.000,0.000 L 40.000,30.000 L 0.000,30.000 L 0.000,0.000 Z"


def test_slots_are_rectangles_around_their_centre():
    e = FingerJointEngine(3.0, 15.0, 0.1)
    vertical = e.slot_path(e.make_slot(10, 20, 'vertical'))
    horizontal = e.slot_path(e.make_slot(10, 20, 'horizontal'))
    assert vertical == "M 8.550,12.550 L 11.450,12.550 L 11.450,27.450 L 8.550,27.450 Z"     # 2.9 wide, 14.9 long
    assert horizontal == "M 2.550,18.550 L 17.450,18.550 L 17.450,21.450 L 2.550,21.450 Z"
    slot = e.make_slot(1, 2, 'vertical')
    assert (slot.length, slot.thickness) == (pytest.approx(14.9), pytest.approx(2.9))      # (f - k) x (t - k)


def test_invalid_role_is_rejected():
    with pytest.raises(FingerJointError):
        FingerJointEngine(3.0, 15.0).plan_edge(100, 'sideways')


def test_with_finger_length_keeps_the_material():
    e = FingerJointEngine(3.0, 15.0, 0.1, single_joints=True).with_finger_length(6.0)
    assert (e.thickness, e.finger_length, e.kerf, e.single_joints) == (3.0, 6.0, 0.1, True)


def test_cramped_layouts_back_off_by_exactly_two_fingers():
    e = FingerJointEngine(3.0, 15.0)
    assert len(e.plan_edge(120, MALE, count=7).nominal) == 5        # 7 would leave 1.9 mm gaps, 5 leaves 7.5
    assert len(e.plan_edge(100, MALE, count=7).nominal) == 3
    assert len(e.plan_edge(40, MALE, count=7).nominal) == 1


def test_gap_limit_is_a_third_of_a_finger_and_inclusive():
    e = FingerJointEngine(3.0, 15.0)
    # 7 fingers over 141 mm leave gaps of exactly 4.5 mm = 0.3 f : allowed
    assert len(e.plan_edge(141, MALE, count=7).nominal) == 7
    assert len(e.plan_edge(140.9, MALE, count=7).nominal) == 5
    # 0.4 f gaps are fine, too
    assert len(e.plan_edge(153, MALE, count=7).nominal) == 7


def test_joint_specs_are_immutable():
    import dataclasses
    spec = FingerJointEngine(3.0, 15.0).plan_edge(100, MALE)
    with pytest.raises(dataclasses.FrozenInstanceError):
        spec.depth = 1.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        FingerJointEngine(3.0, 15.0).make_slot(1, 2).cx = 5
