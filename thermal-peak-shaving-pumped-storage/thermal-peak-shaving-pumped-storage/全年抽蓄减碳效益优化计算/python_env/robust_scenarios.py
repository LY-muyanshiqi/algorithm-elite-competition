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


def daily_features(hydro, wind, solar, load):
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
    weights /= weights.sum()
    return ScenarioSet(np.asarray(indices), weights, labels, features)


def weighted_cvar(values, weights, alpha=0.9):
    """Upper-tail weighted CVaR for a minimization objective."""
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
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
        self.data = (hydro, wind, solar, load)
        self.scenarios = scenarios
        self.Zpump = Zpump
        self.h = h
        self.beta = beta
        self.alpha = alpha

    def __call__(self, x):
        values = np.asarray([
            evaluate_objective_np(x, *(data[day] for data in self.data),
                                  self.Zpump, self.h)
            for day in self.scenarios.indices
        ])
        expected = np.sum(values * self.scenarios.weights[:, None], axis=0)
        tail = np.asarray([
            weighted_cvar(values[:, objective], self.scenarios.weights, self.alpha)
            for objective in range(values.shape[1])
        ])
        return tuple(expected + self.beta * tail)


class ExperienceArchive:
    """Retrieve prior Pareto schedules using normalized scenario features."""

    def __init__(self):
        self._entries = []

    def add(self, feature, solutions):
        self._entries.append((np.asarray(feature), np.asarray(solutions)))

    def warm_start(self, feature, count, rng=None, jitter=0.02):
        if not self._entries or count <= 0:
            return np.empty((0, 23))
        rng = np.random.default_rng() if rng is None else rng
        ordered = sorted(self._entries,
                         key=lambda item: np.linalg.norm(item[0] - feature))
        pool = np.vstack([item[1][:, :23] for item in ordered])
        chosen = pool[np.arange(count) % len(pool)].copy()
        chosen += rng.normal(0.0, jitter, chosen.shape)
        return np.clip(chosen, 0.0, 1.0)
