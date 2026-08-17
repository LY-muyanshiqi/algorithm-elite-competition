import os
import sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'python_env'))

from data_loader_py import load_all_days
from evaluate_objective import evaluate_objective_np
from robust_scenarios import (ExperienceArchive, RobustScenarioEvaluator,
                              extract_representative_scenarios, weighted_cvar)
from nslde_env import NSLDEEnv


def test_weighted_cvar_focuses_on_upper_tail():
    values = np.array([1.0, 2.0, 10.0])
    weights = np.array([0.4, 0.4, 0.2])
    assert np.isclose(weighted_cvar(values, weights, alpha=0.8), 10.0)


def test_scenario_extraction_and_robust_evaluation():
    data = load_all_days()
    scenarios = extract_representative_scenarios(*data, n_clusters=4, n_extremes=2)
    assert len(scenarios.indices) == 6
    assert np.isclose(scenarios.weights.sum(), 1.0)
    result = RobustScenarioEvaluator(*data, scenarios, beta=0.2)(np.full(23, 0.5))
    assert len(result) == 2
    assert np.all(np.isfinite(result))


def test_dispatch_details_and_archive_warm_start():
    data = load_all_days()
    _, _, details = evaluate_objective_np(
        np.full(23, 0.5), *(item[0] for item in data), return_details=True)
    assert {'ramp_mw', 'starts', 'mode_switches', 'short_runs'} <= details.keys()
    archive = ExperienceArchive()
    archive.add(np.zeros(9), np.full((2, 23), 0.4))
    warm = archive.warm_start(np.ones(9) * 0.1, 5, np.random.default_rng(1), jitter=0)
    assert warm.shape == (5, 23)
    assert np.allclose(warm, 0.4)


def test_robust_evaluator_runs_through_evolution_step():
    data = load_all_days()
    scenarios = extract_representative_scenarios(*data, n_clusters=2, n_extremes=1)
    evaluator = RobustScenarioEvaluator(*data, scenarios, beta=0.1)
    env = NSLDEEnv(*(item[scenarios.indices[0]] for item in data), pop=8, gen=1,
                   evaluator=evaluator, initial_solutions=np.full((2, 23), 0.5))
    state = env.reset()
    next_state, reward, done = env.step(0)
    assert state.shape == next_state.shape == (6,)
    assert np.isfinite(reward)
    assert done
