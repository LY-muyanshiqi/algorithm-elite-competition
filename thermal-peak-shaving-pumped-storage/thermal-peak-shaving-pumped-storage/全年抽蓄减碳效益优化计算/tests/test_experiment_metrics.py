import os
import sys

import numpy as np


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from experiment_runner import (  # noqa: E402
    _benchmark_records_from_mat,
    compute_metrics,
    compute_spacing_metric,
)


def test_spacing_metric_matches_normalized_nearest_neighbor_definition():
    points = np.array([
        [0.0, 100.0],
        [5.0, 150.0],
        [10.0, 300.0],
        [np.nan, 200.0],
    ])
    finite = points[:3]
    normalized = (finite - finite.min(axis=0)) / (np.ptp(finite, axis=0) + 1e-12)
    distances = np.sqrt(np.sum((normalized[:, None] - normalized[None, :]) ** 2, axis=2))
    np.fill_diagonal(distances, np.inf)
    expected = float(np.std(np.min(distances, axis=1), ddof=1))

    assert np.isclose(compute_spacing_metric(points), expected)
    assert compute_spacing_metric(points[:2]) == 0.0


def test_compute_metrics_uses_spacing_helper_and_rejects_nonfinite_objectives():
    chromosome = np.full((4, 25), 0.0)
    chromosome[:, 23:25] = [
        [0.0, 100.0],
        [5.0, 150.0],
        [10.0, 300.0],
        [np.inf, 200.0],
    ]
    metrics = compute_metrics(chromosome)
    assert metrics['n_feasible'] == 3
    assert np.isclose(metrics['spacing'], compute_spacing_metric(chromosome[:3, 23:25]))


def test_matlab_spacing_mean_is_canonical_spacing_field():
    points = np.array([
        [[0.0, 100.0], [5.0, 150.0], [10.0, 300.0]],
        [[1.0, 110.0], [6.0, 160.0], [11.0, 310.0]],
    ])
    records = _benchmark_records_from_mat({
        'z_nslde': points,
        'spacing': np.array([[0.12], [0.28]]),
    }, source='synthetic.mat')
    assert len(records) == 1
    metrics = records[0]['metrics']
    assert np.isclose(metrics['spacing_mean'], 0.20)
    assert np.isclose(metrics['spacing'], 0.20)

