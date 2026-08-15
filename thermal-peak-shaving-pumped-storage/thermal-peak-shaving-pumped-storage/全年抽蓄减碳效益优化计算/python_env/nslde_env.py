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


class NSLDEEnv:
    """完整 NSLDE 环境，每代决定一个全局算子"""

    def __init__(self, Nh, Nw, Np, L, Zpump=1400.0, h=4.0, pop=100, gen=3000,
                 init_method='logistic', op_probs=None, seed=42):
        self.Nh = Nh
        self.Nw = Nw
        self.Np = Np
        self.L = L
        self.Zpump = Zpump
        self.h = h
        self.pop = pop
        self.gen = gen
        self.init_method = init_method
        self.op_probs = op_probs if op_probs is not None else np.ones(7) / 7
        self.rng = np.random.default_rng(seed)

        self.M = 2
        self.V = 23
        self.min_range = np.array([0.0] * 21 + [0.125, 0.3125])
        self.max_range = np.array([1.0] * 21 + [1.0, 0.75])

    def _init_population(self):
        """Logistic 混沌初始化（对齐 initialize_variables_multi.m）"""
        pop_x = np.empty((self.pop, self.V))
        if self.init_method == 'logistic':
            for i in range(self.pop):
                y = self.rng.random(self.V)
                y = 4 * y * (1 - y)  # logistic 一次迭代
                pop_x[i] = self.min_range + (self.max_range - self.min_range) * y
        else:  # random
            pop_x = self.rng.random((self.pop, self.V))
            pop_x = self.min_range + (self.max_range - self.min_range) * pop_x
        return self._evaluate_pop(pop_x)

    def _evaluate_pop(self, pop_x):
        """评估种群，返回 (决策变量, 目标值) 拼接矩阵"""
        F = np.empty((self.pop, 2))
        for i in range(self.pop):
            F[i, 0], F[i, 1] = evaluate_objective_np(
                pop_x[i], self.Nh, self.Nw, self.Np, self.L, self.Zpump, self.h)
        return np.hstack([pop_x, F])

    def _hv(self, pop):
        """计算当前种群的 HV（用固定参考点，整个 episode 不变）"""
        obj = pop[:, self.V:self.V + self.M]
        feasible = ~np.isinf(obj[:, 0]) & ~np.isinf(obj[:, 1])
        if feasible.sum() == 0:
            return 0.0
        pts = obj[feasible]
        return compute_hv_2d(pts, self.ref_point)

    def _survival_rate(self, offspring, new_pop):
        """子代存活率：offspring 中有多少个进入 new_pop（按决策变量去重近似）"""
        # 简化：用 fitness 改进衡量，精确去重代价高
        return 0.0

    def reset(self):
        self.generation = 0
        pop_xy = self._init_population()
        self.pop_sorted = non_domination_sort(pop_xy, self.M, self.V)
        # 固定参考点：基于初始种群目标值的上界（整个 episode 不变）
        init_obj = pop_xy[:, self.V:self.V + self.M]
        init_feasible = init_obj[~np.isinf(init_obj[:, 0]) & ~np.isinf(init_obj[:, 1])]
        if init_feasible.shape[0] > 0:
            self.ref_point = [init_feasible[:, 0].max() * 1.2,
                              init_feasible[:, 1].max() * 1.2]
        else:
            self.ref_point = [1e5, 1e10]
        self.prev_hv = self._hv(self.pop_sorted)
        self.stagnation = 0
        self.hv_history = [self.prev_hv]
        return self._state()

    def _state(self):
        """提取 6 维状态特征"""
        # 需要完整染色体矩阵（含 rank/crowding），pop_sorted 已含
        return extract_state_features(
            self.pop_sorted, self.M, self.V,
            self.generation, self.gen, self.stagnation, self.prev_hv,
        )

    def step(self, action, track=False):
        """执行一代进化。action 是算子索引 0..6（本代全局算子偏好）"""
        # 构造 op_probs：选中算子高概率 + 其余均分
        op_probs = np.full(7, 0.1 / 7)
        op_probs[action] = 0.9
        op_probs = op_probs / op_probs.sum()

        # tournament selection
        parent = tournament_selection(self.pop_sorted, self.pop // 2, 2)

        # 遗传操作
        offspring = genetic_operator_multi(
            parent, self.pop_sorted, self.M, self.V,
            self.min_range, self.max_range,
            self.Nh, self.Nw, self.Np, self.L, self.Zpump, self.h, op_probs,
        )

        # 合并 + 非支配排序 + 精英保留
        # pop_sorted 是 (N, V+M+2)，取前 V+M 列（决策+目标）；offspring 是 (N, V+M)
        intermediate = np.vstack([self.pop_sorted[:, :self.V + self.M], offspring])
        inter_sorted = non_domination_sort(intermediate, self.M, self.V)
        self.pop_sorted = replace_chromosome(inter_sorted, self.M, self.V, self.pop)

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
        return self._state(), reward, done
