import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'python_env'))

from data_loader_py import load_day
from nslde_env import NSLDEEnv
from rlde_controller import RLDEFController
from operators import non_domination_sort, replace_chromosome


def test_rlde_controller_changes_individual_f_and_updates_q():
    controller = RLDEFController(3, f_init=0.5, f_delta=0.1, seed=3)
    assert np.all(controller.states == controller.FAILURE_STATE)
    before = controller.f.copy()
    controller.q[:, controller.FAILURE_STATE, 2] = 100.0
    actions, values = controller.select(np.arange(3))
    assert actions.shape == (3,)
    assert values.shape == (3,)
    assert np.all((values >= 0.05) & (values <= 1.0))
    controller.update(np.arange(3), actions, np.array([1.0, -0.5, 0.2]), np.array([1, 0, 1]))
    assert not np.allclose(before, controller.f)
    assert np.any(controller.q != 0)
    assert controller.summary()['updates'] == 3


def test_rlde_controller_rejects_non_finite_reward():
    controller = RLDEFController(1, seed=1)
    actions, _ = controller.select([0])
    with np.testing.assert_raises(ValueError):
        controller.update([0], actions, [np.nan], [controller.FAILURE_STATE])


def test_rlde_controller_reset_restores_episode_temperature_and_seeded_state():
    controller = RLDEFController(4, temperature=2.0, temperature_decay=0.5,
                                 seed=12)
    initial_f = controller.f.copy()
    controller.update([0], [1], [1.0], [controller.SUCCESS_STATE])
    assert controller.temperature == 1.0
    controller.reset(seed=12)
    assert controller.temperature == 2.0
    assert np.allclose(controller.f, initial_f)
    assert controller.summary()['updates'] == 0


def test_rlde_f_initialization_uses_reference_scale_and_stays_bounded():
    controller = RLDEFController(4000, seed=19)
    assert np.all(np.isfinite(controller.f))
    assert np.all((controller.f >= controller.f_min) & (controller.f <= controller.f_max))
    assert 0.24 < float(np.std(controller.f)) < 0.29


def test_rlde_env_is_reproducible_and_reports_nfe():
    Nh, Nw, Np, L = load_day(0)
    kwargs = dict(Nh=Nh, Nw=Nw, Np=Np, L=L, pop=8, gen=2,
                  op_probs=np.array([0.4, 0, 0, 0, 0, 0.3, 0.3]),
                  use_rlde=True, seed=17)
    first = NSLDEEnv(**kwargs)
    second = NSLDEEnv(**kwargs)
    first.reset(); second.reset()
    assert np.allclose(first.pop_sorted, second.pop_sorted, equal_nan=True)
    for _ in range(2):
        a = first.step(return_info=True)
        b = second.step(return_info=True)
        assert np.allclose(a[0], b[0], equal_nan=True)
        assert np.isclose(a[1], b[1])
        assert a[3]['nfe'] == b[3]['nfe']
    assert first.nfe == 8 + 2 * 8
    # The configured mix includes non-DE operators; only DE trials update F.
    assert first.rlde.summary()['updates'] <= 8


def test_supported_initializers_are_distinct_and_bounded():
    Nh, Nw, Np, L = load_day(0)
    for method in ('logistic', 'tent', 'sobol', 'random'):
        env = NSLDEEnv(Nh, Nw, Np, L, pop=8, gen=0,
                       init_method=method, seed=7)
        env.reset()
        decisions = env.pop_sorted[:, :23]
        assert decisions.shape == (8, 23)
        assert np.all(decisions >= env.min_range - 1e-12)
        assert np.all(decisions <= env.max_range + 1e-12)


def test_invalid_operator_weights_fail_fast():
    Nh, Nw, Np, L = load_day(0)
    with np.testing.assert_raises(ValueError):
        NSLDEEnv(Nh, Nw, Np, L, pop=8,
                 op_probs=[1, 0, 0, 0, 0, 0, -1])


def test_fixed_operator_probabilities_are_not_overridden_by_step():
    Nh, Nw, Np, L = load_day(0)
    env = NSLDEEnv(Nh, Nw, Np, L, pop=8, gen=1,
                   op_probs=np.array([0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0]), seed=4)
    env.reset()
    _, _, _, info = env.step(return_info=True)
    assert info['op_probs'][4] == 1.0
    assert set(info['operator_ids']) == {4}


def test_rlde_does_not_change_f_when_selected_operator_does_not_use_it():
    Nh, Nw, Np, L = load_day(0)
    env = NSLDEEnv(Nh, Nw, Np, L, pop=8, gen=1,
                   op_probs=np.array([0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0]),
                   use_rlde=True, seed=11)
    env.reset()
    before = env.rlde.f.copy()
    _, _, _, info = env.step(return_info=True)
    assert set(info['operator_ids']) == {4}
    assert np.array_equal(env.rlde.f, before)
    assert env.rlde.summary()['updates'] == 0
    assert env.rlde.action_counts.sum() == 0
    assert info['rlde_reward_mean'] is None
    assert info['rlde_success_rate'] is None


def test_population_lineage_survives_rank_sort_and_duplicate_tournaments():
    Nh, Nw, Np, L = load_day(0)
    env = NSLDEEnv(Nh, Nw, Np, L, pop=8, gen=2,
                   op_probs=np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
                   use_rlde=True, seed=5)
    env.reset()
    initial_ids = set(env.agent_ids.tolist())
    expected_updates = 0
    for _ in range(2):
        _, _, _, info = env.step(return_info=True)
        lineage_ids = np.asarray(info['agent_ids'])
        active = np.asarray(info['rlde_active'], dtype=bool)
        expected_updates += len(np.unique(lineage_ids[active]))
        assert len(env.agent_ids) == env.pop
        assert set(env.agent_ids.tolist()) <= initial_ids
        assert env.rlde.summary()['updates'] == expected_updates
        assert env.rlde.summary()['updates'] == env.rlde.action_counts.sum()


def test_replacement_indices_identify_the_returned_survivor_rows():
    population = np.array([
        [0.0, 1.0, 4.0],
        [1.0, 2.0, 2.0],
        [2.0, 4.0, 1.0],
        [3.0, 3.0, 3.0],
    ])
    ranked, order = non_domination_sort(population, M=2, V=1, return_indices=True)
    survivors, survivor_indices = replace_chromosome(
        ranked, M=2, V=1, pop=3, return_indices=True)
    assert np.array_equal(survivors, ranked[survivor_indices])
    lineage = np.array([10, 11, 12, 13])[order]
    assert len(np.unique(lineage[survivor_indices])) == len(survivors)


def test_reward_uses_actual_trial_not_cloned_second_child_and_handles_inf():
    parent = np.array([[1.0, 2.0], [np.inf, np.inf]])
    # First child is worse; second child is the target clone and must not turn
    # this into a false positive reward.
    children = np.array([
        [[2.0, 3.0], [1.0, 2.0]],
        [[np.inf, np.inf], [np.inf, np.inf]],
    ])
    reward, states = NSLDEEnv._multiobjective_rewards(parent, children)
    assert np.all(np.isfinite(reward))
    assert reward[0] <= 0.0
    assert states[0] == 1
    assert states[1] == 1
