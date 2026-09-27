"""nslde_env.py - 完整 NSLDE 环境（gym-like），复刻 nslde_enhanced.m

用 numpy 化算子跑完整进化流程，每代一个 MDP 转移:
  state(6维特征) -> action(算子) -> reward(HV增量+存活率) -> next_state
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluate_objective import evaluate_objective_np
from operators import non_domination_sort, tournament_selection, replace_chromosome, compute_hv_2d
from genetic_operators import genetic_operator_multi, OPERATOR_NAMES
from state_features import extract_state_features
from rlde_controller import RLDEFController


class NSLDEEnv:
    """完整 NSLDE 环境，每代决定一个全局算子"""

    def __init__(self, Nh, Nw, Np, L, Zpump=1400.0, h=4.0, pop=100, gen=3000,
                 init_method='logistic', op_probs=None, seed=42,
                 evaluator=None, initial_solutions=None, use_rlde=False,
                 rlde_options=None, ref_point=None):
        self.Nh = Nh
        self.Nw = Nw
        self.Np = Np
        self.L = L
        self.Zpump = Zpump
        self.h = h
        self.pop = int(pop)
        self.gen = int(gen)
        if self.pop < 2:
            raise ValueError('pop must be at least 2')
        if self.gen < 0:
            raise ValueError('gen must be non-negative')
        self.init_method = str(init_method).lower()
        self.op_probs = np.asarray(
            op_probs if op_probs is not None else np.ones(7) / 7,
            dtype=float,
        )
        if (self.op_probs.shape != (7,) or
                not np.all(np.isfinite(self.op_probs)) or
                np.any(self.op_probs < 0) or self.op_probs.sum() <= 0):
            raise ValueError('op_probs must contain seven finite non-negative weights')
        self.op_probs = self.op_probs / self.op_probs.sum()
        self.seed = int(seed)
        self.rng = np.random.default_rng(seed)
        self.evaluator = evaluator
        self.initial_solutions = initial_solutions
        self.use_rlde = bool(use_rlde)
        if ref_point is None:
            self._ref_point_override = None
        else:
            candidate_ref = np.asarray(ref_point, dtype=float).reshape(-1)
            if candidate_ref.shape != (2,) or not np.all(np.isfinite(candidate_ref)):
                raise ValueError('ref_point must contain two finite values')
            self._ref_point_override = candidate_ref.copy()

        self.M = 2
        self.V = 23
        self.min_range = np.array([0.0] * 21 + [0.125, 0.3125])
        self.max_range = np.array([1.0] * 21 + [1.0, 0.75])
        self.pool_size = max(2, self.pop // 2)
        self.rlde = None
        if self.use_rlde:
            options = dict(rlde_options or {})
            options.setdefault('seed', self.seed + 7919)
            # Keep one controller per population individual, as in RLDE-PV.
            # Tournament selection may reuse an individual in several mating
            # slots; tying Q/F to the slot silently loses that identity.
            self.rlde = RLDEFController(self.pop, **options)

    def _init_population(self):
        """Logistic 混沌初始化（对齐 initialize_variables_multi.m）"""
        pop_x = np.empty((self.pop, self.V))
        if self.init_method == 'logistic':
            y = self.rng.random(self.V)
            for i in range(self.pop):
                y = 4 * y * (1 - y)  # logistic 一次迭代
                pop_x[i] = self.min_range + (self.max_range - self.min_range) * y
        elif self.init_method == 'tent':
            y = self.rng.random(self.V)
            for i in range(self.pop):
                y = np.where(y < 0.5, 2.0 * y, 2.0 * (1.0 - y))
                pop_x[i] = self.min_range + (self.max_range - self.min_range) * y
        elif self.init_method == 'sobol':
            # scipy's Sobol engine gives a reproducible low-discrepancy
            # covering sequence and is available with the project's SciPy
            # dependency.  Scrambling is disabled so common-random-number
            # comparisons remain identical across algorithm variants.
            from scipy.stats import qmc
            y = qmc.Sobol(d=self.V, scramble=False).random(self.pop)
            pop_x = self.min_range + (self.max_range - self.min_range) * y
        elif self.init_method == 'random':
            y = self.rng.random((self.pop, self.V))
            pop_x = self.min_range + (self.max_range - self.min_range) * y
        else:
            raise ValueError(
                "init_method must be one of 'logistic', 'tent', 'sobol', or 'random'"
            )
        if self.initial_solutions is not None:
            warm = np.asarray(self.initial_solutions, dtype=float)
            n_warm = min(len(warm), self.pop)
            pop_x[:n_warm] = np.clip(warm[:n_warm], self.min_range, self.max_range)
        return self._evaluate_pop(pop_x)

    def _evaluate_pop(self, pop_x):
        """评估种群，返回 (决策变量, 目标值) 拼接矩阵"""
        F = np.empty((self.pop, 2))
        for i in range(self.pop):
            if self.evaluator is None:
                F[i, 0], F[i, 1] = evaluate_objective_np(
                    pop_x[i], self.Nh, self.Nw, self.Np, self.L, self.Zpump, self.h)
            else:
                F[i, 0], F[i, 1] = self.evaluator(pop_x[i])
        return np.hstack([pop_x, F])

    def _hv(self, pop):
        """计算当前种群的 HV（用固定参考点，整个 episode 不变）"""
        obj = pop[:, self.V:self.V + self.M]
        # NaN is also infeasible; using ``isinf`` alone would let failed
        # evaluations reach the hypervolume calculation.
        feasible = np.isfinite(obj[:, 0]) & np.isfinite(obj[:, 1])
        if feasible.sum() == 0:
            return 0.0
        pts = obj[feasible]
        return compute_hv_2d(pts, self.ref_point)

    def _survival_rate(self, offspring, new_pop):
        """子代存活率：offspring 中有多少个进入 new_pop（按决策变量去重近似）"""
        # 简化：用 fitness 改进衡量，精确去重代价高
        return 0.0

    def reset(self):
        self.rng = np.random.default_rng(self.seed)
        if self.rlde is not None:
            self.rlde.reset(self.seed + 7919)
        self.generation = 0
        pop_xy = self._init_population()
        self.pop_sorted, initial_order = non_domination_sort(
            pop_xy, self.M, self.V, return_indices=True)
        # ``initial_order`` maps each sorted row back to its original sampled
        # individual.  Keeping this mapping prevents the Q/F controller from
        # being silently reassigned when the first non-dominated sort reorders
        # the population.
        self.agent_ids = initial_order.astype(np.int64, copy=True)
        # Keep a supplied reference point identical across episodes/variants.
        # Standalone environments retain the historical data-driven fallback.
        if self._ref_point_override is not None:
            self.ref_point = self._ref_point_override.copy()
        else:
            init_obj = pop_xy[:, self.V:self.V + self.M]
            init_feasible = init_obj[
                np.isfinite(init_obj[:, 0]) & np.isfinite(init_obj[:, 1])]
            if init_feasible.shape[0] > 0:
                self.ref_point = [init_feasible[:, 0].max() * 1.2,
                                  init_feasible[:, 1].max() * 1.2]
            else:
                self.ref_point = [1e5, 1e10]
        self.prev_hv = self._hv(self.pop_sorted)
        self.stagnation = 0
        self.hv_history = [self.prev_hv]
        self.nfe = self.pop
        self.operator_use_count = np.zeros(7, dtype=int)
        self.rlde_history = []
        return self._state()

    def _state(self):
        """提取 6 维状态特征"""
        # 需要完整染色体矩阵（含 rank/crowding），pop_sorted 已含
        return extract_state_features(
            self.pop_sorted, self.M, self.V,
            self.generation, self.gen, self.stagnation, self.prev_hv,
            ref_point=self.ref_point,
        )

    @staticmethod
    def _multiobjective_rewards(parent_objectives, child_objectives):
        """Return a finite, scale-normalized reward for each parent.

        ``genetic_operator_multi`` emits two rows per parent.  Its second row
        is a clone of the target chromosome, so it is not a trial generated by
        the selected action and must not be used to grant a reward.  The first
        row is the actual trial.  Non-finite objective values are replaced by
        a per-objective dominated penalty before normalization; otherwise an
        ``inf - inf`` operation can poison the Q table with NaN.
        """
        parent = np.asarray(parent_objectives, dtype=float)
        children = np.asarray(child_objectives, dtype=float)
        if parent.ndim != 2 or children.ndim != 3:
            raise ValueError("invalid objective array dimensions")
        if children.shape[0] != parent.shape[0] or children.shape[2] != parent.shape[1]:
            raise ValueError("parent and child objective shapes do not align")

        trial = children[:, 0, :]
        combined = np.vstack([parent, trial])
        safe = combined.copy()
        lower = np.empty(parent.shape[1], dtype=float)
        scale = np.empty(parent.shape[1], dtype=float)
        for objective in range(parent.shape[1]):
            finite = combined[:, objective][np.isfinite(combined[:, objective])]
            if finite.size == 0:
                lower[objective] = 0.0
                scale[objective] = 1.0
                safe[:, objective] = 1.0
                continue
            low = float(np.min(finite))
            high = float(np.max(finite))
            spread = max(high - low, 1.0)
            penalty = high + 10.0 * spread
            safe[~np.isfinite(safe[:, objective]), objective] = penalty
            lower[objective] = low
            scale[objective] = spread

        parent_safe = safe[:parent.shape[0]]
        trial_safe = safe[parent.shape[0]:]
        parent_score = ((parent_safe - lower) / scale).mean(axis=1)
        trial_score = ((trial_safe - lower) / scale).mean(axis=1)
        reward = np.clip(parent_score - trial_score, -1.0, 1.0)
        reward = np.nan_to_num(reward, nan=-1.0, posinf=-1.0, neginf=-1.0)
        success = reward > 0.0
        next_states = np.where(
            success, RLDEFController.SUCCESS_STATE,
            RLDEFController.FAILURE_STATE,
        )
        return reward, next_states.astype(np.int64)

    def step(self, action=None, track=False, return_info=False):
        """执行一代进化。action 是算子索引 0..6（本代全局算子偏好）"""
        if action is None:
            op_probs = self.op_probs.copy()
        else:
            if not 0 <= int(action) < 7:
                raise ValueError('action must be in [0, 6]')
            op_probs = np.full(7, 0.1 / 7)
            op_probs[int(action)] = 0.9
            op_probs = op_probs / op_probs.sum()

        # tournament selection
        parent, selected_indices = tournament_selection(
            self.pop_sorted, self.pool_size, 2, rng=self.rng,
            return_indices=True,
        )

        operator_ids = self.rng.choice(len(op_probs), size=self.pool_size, p=op_probs)
        agent_ids = self.agent_ids[selected_indices]
        rlde_actions = None
        rlde_active = None
        f_values = None
        rlde_agent_ids = None
        rlde_agent_actions = None
        rlde_slot_to_agent = None
        if self.rlde is not None:
            rlde_active = operator_ids < 3
            rlde_actions = np.full(self.pool_size, -1, dtype=np.int64)
            f_values = np.full(self.pool_size, 0.5, dtype=float)
            if np.any(rlde_active):
                active_positions = np.flatnonzero(rlde_active)
                rlde_agent_ids, rlde_slot_to_agent = np.unique(
                    agent_ids[active_positions], return_inverse=True)
                rlde_agent_actions, agent_f = self.rlde.select(rlde_agent_ids)
                rlde_actions[active_positions] = rlde_agent_actions[rlde_slot_to_agent]
                f_values[active_positions] = agent_f[rlde_slot_to_agent]

        # 遗传操作
        offspring, operator_info = genetic_operator_multi(
            parent, self.pop_sorted, self.M, self.V,
            self.min_range, self.max_range,
            self.Nh, self.Nw, self.Np, self.L, self.Zpump, self.h, op_probs,
            evaluator=self.evaluator,
            f_values=f_values, parent_indices=agent_ids, rng=self.rng,
            return_info=True, selected_operator_ids=operator_ids,
        )
        self.nfe += len(offspring)
        used = operator_info['operator_ids']
        self.operator_use_count += np.bincount(used, minlength=7)

        rlde_rewards = None
        if self.rlde is not None:
            parent_objectives = parent[:, self.V:self.V + self.M]
            rlde_rewards, _ = self._multiobjective_rewards(
                parent_objectives, operator_info['child_objectives'])
            # Only DE operators consume F.  Levy/Cauchy/PM/SBX trials should
            # not receive credit for changing the DE scale factor.
            rlde_active = operator_info['f_active']
            if np.any(rlde_active):
                counts = np.bincount(rlde_slot_to_agent, minlength=len(rlde_agent_ids))
                reward_sums = np.bincount(
                    rlde_slot_to_agent, weights=rlde_rewards[rlde_active],
                    minlength=len(rlde_agent_ids))
                agent_rewards = reward_sums / counts
                agent_next_states = np.where(
                    agent_rewards > 0.0, RLDEFController.SUCCESS_STATE,
                    RLDEFController.FAILURE_STATE)
                self.rlde.update(rlde_agent_ids, rlde_agent_actions,
                                 agent_rewards, agent_next_states)
            self.rlde_history.append(self.rlde.summary())

        # 合并 + 非支配排序 + 精英保留
        # pop_sorted 是 (N, V+M+2)，取前 V+M 列（决策+目标）；offspring 是 (N, V+M)
        intermediate = np.vstack([self.pop_sorted[:, :self.V + self.M], offspring])
        child_agent_ids = np.repeat(agent_ids, 2)
        intermediate_agent_ids = np.concatenate([self.agent_ids, child_agent_ids])
        inter_sorted, sort_indices = non_domination_sort(
            intermediate, self.M, self.V, return_indices=True)
        sorted_agent_ids = intermediate_agent_ids[sort_indices]
        self.pop_sorted, survivor_indices = replace_chromosome(
            inter_sorted, self.M, self.V, self.pop, return_indices=True)
        self.agent_ids = sorted_agent_ids[survivor_indices]

        # 奖励
        hv_now = self._hv(self.pop_sorted)
        reward = (hv_now - self.prev_hv) / max(abs(hv_now), 1.0)
        if reward <= 0:
            self.stagnation += 1
        else:
            self.stagnation = 0
        self.prev_hv = hv_now
        self.hv_history.append(hv_now)

        self.generation += 1
        done = self.generation >= self.gen
        result = (self._state(), reward, done)
        if not return_info:
            return result
        info = {
            'op_probs': op_probs.tolist(),
            'operator_ids': used.astype(int).tolist(),
            'agent_ids': agent_ids.astype(int).tolist(),
            'operator_use_count': self.operator_use_count.astype(int).tolist(),
            'nfe': int(self.nfe),
            'hv': float(hv_now),
            'rlde': None if self.rlde is None else self.rlde.summary(),
            'rlde_reward_mean': (None if rlde_rewards is None or not np.any(rlde_active)
                                 else float(np.mean(rlde_rewards[rlde_active]))),
            'rlde_success_rate': (None if rlde_rewards is None or not np.any(rlde_active)
                                  else float(np.mean(rlde_rewards[rlde_active] > 0.0))),
            'rlde_active': (None if rlde_active is None else
                            rlde_active.astype(bool).tolist()),
        }
        return result + (info,)
