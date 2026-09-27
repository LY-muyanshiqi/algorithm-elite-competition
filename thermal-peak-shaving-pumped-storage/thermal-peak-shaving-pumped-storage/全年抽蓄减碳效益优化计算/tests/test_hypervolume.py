import os
import sys

import numpy as np


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "python_env"))

from operators import compute_hv_2d
from state_features import compute_hv_2d as state_compute_hv_2d


def test_hv_uses_forward_staircase_for_minimization_front():
    # The union is 1*1 + 3*3 = 10, not the signed/absolute result of the old
    # reverse accumulation.
    points = np.array([[1.0, 4.0], [2.0, 2.0]])
    assert np.isclose(compute_hv_2d(points, [5.0, 5.0]), 10.0)


def test_hv_discards_dominated_duplicate_and_outside_points():
    points = np.array([
        [2.0, 2.0],
        [1.0, 4.0],
        [2.0, 2.0],  # duplicate
        [4.0, 4.0],  # dominated by [2, 2]
        [6.0, 1.0],  # outside the reference box
        [1.0, 6.0],  # outside the reference box
    ])
    assert np.isclose(compute_hv_2d(points, [5.0, 5.0]), 10.0)


def test_hv_ignores_nonfinite_points_and_state_features_share_implementation():
    points = np.array([[1.0, 4.0], [2.0, 2.0], [np.inf, 1.0], [np.nan, 2.0]])
    expected = compute_hv_2d(points, [5.0, 5.0])
    assert np.isclose(expected, 10.0)
    assert np.isclose(state_compute_hv_2d(points, [5.0, 5.0]), expected)
