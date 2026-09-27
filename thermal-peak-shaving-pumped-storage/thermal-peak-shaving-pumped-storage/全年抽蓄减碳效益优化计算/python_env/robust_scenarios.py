"""Representative scenarios, CVaR objectives, and cross-day warm starts."""

from dataclasses import dataclass
import numpy as np
from scipy.cluster.vq import kmeans2

from evaluate_objective import evaluate_objective_np


@dataclass
class ScenarioSet:
    indices: np.ndarray
    weights: np.ndarray
    labels: list
    features: np.ndarray

    def __post_init__(self):
        indices = np.asarray(self.indices)
        weights = np.asarray(self.weights, dtype=float)
        features = np.asarray(self.features, dtype=float)
        if indices.ndim != 1 or weights.ndim != 1:
            raise ValueError('scenario indices and weights must be one-dimensional')
        if indices.size == 0 or indices.size != weights.size:
            raise ValueError('scenario indices and weights must be non-empty and aligned')
        if not np.all(np.isfinite(indices)) or not np.all(indices == indices.astype(np.int64)):
            raise ValueError('scenario indices must be finite integers')
        if np.any(weights < 0) or not np.all(np.isfinite(weights)):
            raise ValueError('scenario weights must be finite and non-negative')
        total = float(np.sum(weights))
        if not np.isfinite(total) or total <= 0:
            raise ValueError('scenario weights must have a positive finite sum')
        if len(self.labels) != indices.size:
            raise ValueError('scenario labels must align with indices')
        if features.ndim != 2 or not np.all(np.isfinite(features)):
            raise ValueError('scenario features must be a finite 2-D array')
        self.indices = indices.astype(np.int64, copy=False)
        self.weights = weights / total
        self.labels = list(self.labels)
        self.features = features


def _validate_daily_inputs(hydro, wind, solar, load):
    """Normalize and validate annual arrays before feature extraction."""
    arrays = tuple(np.asarray(item, dtype=float)
                   for item in (hydro, wind, solar, load))
    if any(item.ndim != 2 for item in arrays):
        raise ValueError('daily scenario arrays must have shape (days, hours)')
    shape = arrays[0].shape
    if shape[0] == 0 or shape[1] == 0:
        raise ValueError('daily scenario arrays must contain at least one day/hour')
    if any(item.shape != shape for item in arrays[1:]):
        raise ValueError('daily scenario arrays must have identical shapes')
    if not all(np.all(np.isfinite(item)) for item in arrays):
        raise ValueError('daily scenario arrays must contain only finite values')
    return arrays


def daily_features(hydro, wind, solar, load):
    hydro, wind, solar, load = _validate_daily_inputs(hydro, wind, solar, load)
    renewable = hydro + wind + solar
    residual = load - renewable
    raw = np.column_stack([
        load.mean(1), load.max(1), np.ptp(load, axis=1),
        wind.mean(1), solar.mean(1), hydro.mean(1),
        residual.mean(1), residual.max(1), np.ptp(residual, axis=1),
    ])
    return (raw - raw.mean(0)) / (raw.std(0) + 1e-12)


def extract_representative_scenarios(hydro, wind, solar, load, n_clusters=8,
                                     n_extremes=4, seed=42):
    """Select cluster medoids, then add the hardest residual-load days."""
    hydro, wind, solar, load = _validate_daily_inputs(hydro, wind, solar, load)
    days = load.shape[0]
    try:
        n_clusters = int(n_clusters)
        n_extremes = int(n_extremes)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('scenario counts must be finite integers') from exc
    n_clusters = int(np.clip(n_clusters, 1, days))
    n_extremes = max(0, min(n_extremes, days - 1))
    features = daily_features(hydro, wind, solar, load)
    centroids, assignment = kmeans2(features, n_clusters, minit='++', seed=seed)
    indices, weights, labels = [], [], []
    for cluster_id in range(n_clusters):
        members = np.flatnonzero(assignment == cluster_id)
        if members.size == 0:
            continue
        distance = np.linalg.norm(features[members] - centroids[cluster_id], axis=1)
        indices.append(int(members[np.argmin(distance)]))
        weights.append(float(members.size))
        labels.append(f'cluster_{cluster_id + 1}')

    residual = load - hydro - wind - solar
    score = ((residual.max(1) - residual.max(1).mean()) /
             (residual.max(1).std() + 1e-12))
    score += ((np.ptp(residual, axis=1) - np.ptp(residual, axis=1).mean()) /
              (np.ptp(residual, axis=1).std() + 1e-12))
    added = 0
    for day in np.argsort(score)[::-1]:
        if int(day) not in indices:
            indices.append(int(day))
            weights.append(1.0)
            labels.append('extreme_residual_load')
            added += 1
        if added >= n_extremes:
            break
    weights = np.asarray(weights, dtype=float)
    if np.any(weights < 0) or not np.all(np.isfinite(weights)) or weights.sum() <= 0:
        raise ValueError('scenario weights must be finite and non-negative')
    weights /= weights.sum()
    return ScenarioSet(np.asarray(indices), weights, labels, features)


def weighted_cvar(values, weights, alpha=0.9):
    """Upper-tail weighted CVaR for a minimization objective."""
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if values.ndim != 1 or weights.ndim != 1 or len(values) != len(weights):
        raise ValueError('values and weights must be one-dimensional and aligned')
    if not np.all(np.isfinite(values)):
        raise ValueError('values must be finite')
    if np.any(weights < 0) or not np.all(np.isfinite(weights)) or weights.sum() <= 0:
        raise ValueError('weights must be finite and non-negative')
    weight_sum = float(np.sum(weights))
    if not np.isfinite(weight_sum) or weight_sum <= 0:
        raise ValueError('weights must have a positive finite sum')
    weights = weights / weight_sum
    try:
        alpha = float(alpha)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('alpha must satisfy 0 <= alpha < 1') from exc
    if not np.isfinite(alpha) or not 0 <= alpha < 1:
        raise ValueError('alpha must satisfy 0 <= alpha < 1')
    tail_mass = max(1.0 - alpha, 1e-12)
    remaining, total = tail_mass, 0.0
    for idx in np.argsort(values)[::-1]:
        take = min(weights[idx], remaining)
        total += take * values[idx]
        remaining -= take
        if remaining <= 1e-12:
            break
    return total / tail_mass


class RobustScenarioEvaluator:
    """Score one daily policy on representative and extreme annual scenarios."""

    def __init__(self, hydro, wind, solar, load, scenarios, Zpump=1400.0,
                 h=4.0, beta=0.3, alpha=0.9):
        self.data = _validate_daily_inputs(hydro, wind, solar, load)
        if not isinstance(scenarios, ScenarioSet):
            raise TypeError('scenarios must be a ScenarioSet')
        if np.any(scenarios.indices < 0) or np.any(scenarios.indices >= self.data[0].shape[0]):
            raise ValueError('scenario indices are outside the supplied data')
        try:
            beta = float(beta)
            alpha = float(alpha)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError('beta and alpha must be finite scalars') from exc
        if not np.isfinite(beta) or beta < 0:
            raise ValueError('beta must be finite and non-negative')
        if not np.isfinite(alpha) or not 0 <= alpha < 1:
            raise ValueError('alpha must satisfy 0 <= alpha < 1')
        self.scenarios = scenarios
        self.Zpump = float(Zpump)
        self.h = float(h)
        self.beta = beta
        self.alpha = alpha

    def evaluate(self, x):
        raw_values = np.asarray([
            evaluate_objective_np(x, *(data[day] for data in self.data),
                                  self.Zpump, self.h)
            for day in self.scenarios.indices
        ], dtype=float)
        if raw_values.ndim != 2 or raw_values.shape[1] != 2:
            raise ValueError('objective evaluator must return exactly two values')
        feasible = bool(np.all(np.isfinite(raw_values)))
        values = raw_values.copy()
        if not np.all(np.isfinite(values)):
            finite_by_objective = [values[:, i][np.isfinite(values[:, i])]
                                   for i in range(values.shape[1])]
            fallback = np.array([1e6, 1e12], dtype=float)[:values.shape[1]]
            max_float = np.finfo(float).max
            penalty = np.array([
                max(float(np.max(item)) * 10.0 if item.size else fallback[i], fallback[i])
                for i, item in enumerate(finite_by_objective)
            ], dtype=float)
            # Keep the penalty finite even if a malformed input produces a
            # very large but finite objective.
            penalty = np.minimum(penalty, max_float / 4.0)
            values = np.where(np.isfinite(values), values, penalty[None, :])
        # A finite objective can still overflow during a weighted sum.  Keep
        # the public robust score finite so it cannot poison NSLDE ranking/RL.
        with np.errstate(over='ignore', invalid='ignore'):
            expected = np.sum(values * self.scenarios.weights[:, None], axis=0)
        expected = np.nan_to_num(expected, nan=np.finfo(float).max / 4.0,
                                 posinf=np.finfo(float).max / 4.0,
                                 neginf=-np.finfo(float).max / 4.0)
        tail = np.asarray([
            weighted_cvar(values[:, objective], self.scenarios.weights, self.alpha)
            for objective in range(values.shape[1])
        ])
        with np.errstate(over='ignore', invalid='ignore'):
            objective = expected + self.beta * tail
        objective = np.nan_to_num(objective, nan=np.finfo(float).max / 4.0,
                                  posinf=np.finfo(float).max / 4.0,
                                  neginf=-np.finfo(float).max / 4.0)
        return {
            'values': values,
            'feasible': feasible,
            'expected': expected,
            'cvar': tail,
            'worst': np.max(values, axis=0),
            'objective': objective,
        }

    def __call__(self, x):
        result = self.evaluate(x)
        return tuple(result['objective'])

    def is_feasible(self, x):
        return bool(self.evaluate(x)['feasible'])


class ExperienceArchive:
    """Retrieve prior Pareto schedules using normalized scenario features."""

    def __init__(self):
        self._entries = []

    def add(self, feature, solutions):
        self._entries.append((np.asarray(feature), np.asarray(solutions)))

    def warm_start(self, feature, count, rng=None, jitter=0.02,
                   lower=None, upper=None):
        if not self._entries or count <= 0:
            return np.empty((0, 23))
        rng = np.random.default_rng() if rng is None else rng
        ordered = sorted(self._entries,
                         key=lambda item: np.linalg.norm(item[0] - feature))
        pool = np.vstack([item[1][:, :23] for item in ordered])
        chosen = pool[np.arange(count) % len(pool)].copy()
        chosen += rng.normal(0.0, jitter, chosen.shape)
        if lower is None:
            lower = np.zeros(chosen.shape[1])
        if upper is None:
            upper = np.ones(chosen.shape[1])
        return np.clip(chosen, np.asarray(lower), np.asarray(upper))
