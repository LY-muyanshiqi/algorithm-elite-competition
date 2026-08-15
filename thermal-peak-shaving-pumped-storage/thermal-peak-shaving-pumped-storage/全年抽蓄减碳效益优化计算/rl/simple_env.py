"""simple_env.py - 简化 NSLDE 环境（阶段2验证用）

只做单目标式的进化，用真实 numpy 目标函数评估，简化遗传操作。
目的：验证 MDP 转移闭环 + PPO 训练配方，不追求算法性能。

状态：6 维标量特征（extract_state_features 的简化）
动作：7 算子之一
奖励：HV 增量的代理（目标函数改进量 / 可行性改善）
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'python_env'))
from evaluate_objective import evaluate_objective_np
from state_features import compute_hv_2d

N_ACTIONS = 7

# 算子简化实现：每代用选中的算子对种群做变异
# 阶段2只做"算子=变异强度/方向"的抽象，不做完整遗传
def _apply_operator(pop_x, action, l_bound, u_bound):
    """对种群 X (N,23) 应用算子 action，返回新种群"""
    V = pop_x.shape[1]
    N = pop_x.shape[0]
    new_x = pop_x.copy()
    F = 0.5
    for i in range(N):
        # 选两个随机个体做差分
        j = np.random.randint(N)
        k = np.random.randint(N)
        while k == j:
            k = np.random.randint(N)
        diff = pop_x[j] - pop_x[k]
        if action == 0:  # DE/rand/1
            new_x[i] = pop_x[i] + F * diff
        elif action == 1:  # DE/rand/2
            m = np.random.randint(N)
            new_x[i] = pop_x[i] + F * (diff + (pop_x[m] - pop_x[k]))
        elif action == 2:  # DE/current-to-best/1
            best = pop_x[0]  # 简化：当前排序第一
            new_x[i] = pop_x[i] + F * (best - pop_x[i]) + F * diff
        elif action == 3:  # PM
            eta = 20
            u = np.random.random(V)
            delta = np.where(u < 0.5, (2*u)**(1/(eta+1)) - 1, 1 - (2*(1-u))**(1/(eta+1)))
            new_x[i] = pop_x[i] + delta * (u_bound - l_bound)
        elif action == 4:  # SBX
            j2 = np.random.randint(N)
            new_x[i] = 0.5 * (pop_x[j] + pop_x[j2])
        elif action == 5:  # Levy
            u = np.random.normal(0, 0.6966, V)
            v = np.random.normal(0, 1, V)
            step = 0.01 * u / (np.abs(v)**(1/1.5) + 1e-10)
            new_x[i] = pop_x[i] + step * (u_bound - l_bound)
        elif action == 6:  # Cauchy
            cauchy = np.tan(np.pi * (np.random.random(V) - 0.5))
            new_x[i] = pop_x[i] + 0.01 * cauchy * (u_bound - l_bound)
    return np.clip(new_x, l_bound, u_bound)


class SimpleNSLDEEnv:
    """简化环境：每代选算子 → 变异 → 评估 → 得 HV 增量奖励"""

    def __init__(self, Nh, Nw, Np, L, Zpump=1400.0, h=4.0, pop=50, gen=100, seed=42):
        self.Nh = Nh
        self.Nw = Nw
        self.Np = Np
        self.L = L
        self.Zpump = Zpump
        self.h = h
        self.pop = pop
        self.gen = gen
        self.rng = np.random.default_rng(seed)

        self.V = 23
        self.l_bound = np.zeros(self.V)
        self.u_bound = np.ones(self.V)

        self.reset()

    def reset(self):
        self.generation = 0
        self.pop_x = self.rng.random((self.pop, self.V))
        self._evaluate()
        self.prev_hv = self._hv()
        return self._state()

    def _evaluate(self):
        F = np.empty((self.pop, 2))
        for i in range(self.pop):
            F[i, 0], F[i, 1] = evaluate_objective_np(
                self.pop_x[i], self.Nh, self.Nw, self.Np, self.L, self.Zpump, self.h)
        self.F = F
        return F

    def _hv(self):
        feasible = ~np.isinf(self.F[:, 0]) & ~np.isinf(self.F[:, 1])
        if feasible.sum() == 0:
            return 0.0
        pts = self.F[feasible]
        ref = [np.max(pts[:, 0]) * 1.2, np.max(pts[:, 1]) * 1.2]
        return compute_hv_2d(pts, ref)

    def _state(self):
        feasible = ~np.isinf(self.F[:, 0]) & ~np.isinf(self.F[:, 1])
        n_feas = feasible.sum()
        cv_rate = 1.0 - n_feas / self.pop
        gen_ratio = self.generation / self.gen
        return np.array([gen_ratio, cv_rate, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)

    def step(self, action):
        self.pop_x = _apply_operator(self.pop_x, action, self.l_bound, self.u_bound)
        self._evaluate()
        hv_now = self._hv()
        reward = (hv_now - self.prev_hv) / max(abs(hv_now), 1.0)
        # 可行性改善 shaping
        feasible_now = (~np.isinf(self.F[:, 0]) & ~np.isinf(self.F[:, 1])).sum()
        reward += 0.1 * (feasible_now / self.pop - (1.0 - self._state()[1]))
        self.prev_hv = hv_now
        self.generation += 1
        done = self.generation >= self.gen
        return self._state(), reward, done

    def observation_space_dim(self):
        return 6
