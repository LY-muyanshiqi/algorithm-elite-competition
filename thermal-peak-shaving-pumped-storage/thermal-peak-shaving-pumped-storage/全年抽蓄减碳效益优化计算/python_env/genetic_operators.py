"""genetic_operators.py - numpy 复刻 genetic_operator_multi.m 的 7 个算子

算子索引与 MATLAB 一致:
  0: DE/rand/1, 1: DE/rand/2, 2: DE/current-to-best/1, 3: PM, 4: SBX, 5: Levy, 6: Cauchy
每个算子返回 (child_1, child_2) 两个子代（未评估）。
"""

import numpy as np
from scipy.special import gamma as _gamma


def clip_bounds(x, l_limit, u_limit):
    return np.clip(x, l_limit, u_limit)


def op_de_rand_1(target, p1, p2, V, l_limit, u_limit):
    F = 0.5
    CR = 0.9
    c1 = target.copy()
    mask = np.random.random(V) < CR
    c1[mask] = p1[mask] + F * (p2[mask] - target[mask])
    c1 = clip_bounds(c1, l_limit, u_limit)
    c2 = target.copy()
    return c1, c2


def op_de_rand_2(target, p1, p2, pop, V, l_limit, u_limit):
    N = pop.shape[0]
    idx3 = np.random.randint(N)
    idx4 = np.random.randint(N)
    while idx4 == idx3:
        idx4 = np.random.randint(N)
    p3 = pop[idx3]
    p4 = pop[idx4]
    F = 0.5
    CR = 0.9
    c1 = target.copy()
    mask = np.random.random(V) < CR
    c1[mask] = p1[mask] + F * (p2[mask] - p3[mask]) + F * (p4[mask] - target[mask])
    c1 = clip_bounds(c1, l_limit, u_limit)
    c2 = target.copy()
    return c1, c2


def op_de_current_to_best(target, p1, p2, pop, V, l_limit, u_limit):
    # best = pop 按第 1 个目标排序最小者（对齐 MATLAB: sort(pop(:,V+1))）
    best = pop[np.argsort(pop[:, 0])[0]]
    F1 = 0.8
    F2 = 0.5
    CR = 0.9
    c1 = target.copy()
    mask = np.random.random(V) < CR
    c1[mask] = target[mask] + F1 * (best[mask] - target[mask]) + F2 * (p1[mask] - p2[mask])
    c1 = clip_bounds(c1, l_limit, u_limit)
    c2 = target.copy()
    return c1, c2


def op_pm(parent, V, l_limit, u_limit):
    eta_m = 20
    pm = 1.0 / V
    c1 = parent.copy()
    c2 = parent.copy()
    for j in range(V):
        if np.random.random() < pm:
            y = parent[j]
            r = np.random.random()
            if r <= 0.5:
                delta_q = (2 * r) ** (1 / (eta_m + 1)) - 1
            else:
                delta_q = 1 - (2 * (1 - r)) ** (1 / (eta_m + 1))
            c1[j] = y + delta_q * (u_limit[j] - l_limit[j])

            r2 = np.random.random()
            if r2 <= 0.5:
                delta_q2 = (2 * r2) ** (1 / (eta_m + 1)) - 1
            else:
                delta_q2 = 1 - (2 * (1 - r2)) ** (1 / (eta_m + 1))
            c2[j] = y + delta_q2 * (u_limit[j] - l_limit[j])
    c1 = clip_bounds(c1, l_limit, u_limit)
    c2 = clip_bounds(c2, l_limit, u_limit)
    return c1, c2


def op_sbx(p1, p2_parent, p3, V, l_limit, u_limit):
    eta_c = 20
    pc = 0.9
    c1 = p1.copy()
    c2 = p1.copy()
    if np.random.random() < pc:
        for j in range(V):
            if np.random.random() < 0.5:
                if abs(p2_parent[j] - p3[j]) > 1e-14:
                    y1 = min(p2_parent[j], p3[j])
                    y2 = max(p2_parent[j], p3[j])

                    beta = 1 + 2 * (y1 - l_limit[j]) / max(y2 - y1, 1e-14)
                    alpha = 2 - beta ** (-(eta_c + 1))
                    r = np.random.random()
                    if r <= 1 / alpha:
                        beta_q = (r * alpha) ** (1 / (eta_c + 1))
                    else:
                        beta_q = (1 / (2 - r * alpha)) ** (1 / (eta_c + 1))
                    c1[j] = 0.5 * ((y1 + y2) - beta_q * (y2 - y1))

                    beta2 = 1 + 2 * (u_limit[j] - y2) / max(y2 - y1, 1e-14)
                    alpha2 = 2 - beta2 ** (-(eta_c + 1))
                    r2 = np.random.random()
                    if r2 <= 1 / alpha2:
                        beta_q2 = (r2 * alpha2) ** (1 / (eta_c + 1))
                    else:
                        beta_q2 = (1 / (2 - r2 * alpha2)) ** (1 / (eta_c + 1))
                    c2[j] = 0.5 * ((y1 + y2) + beta_q2 * (y2 - y1))
    c1 = clip_bounds(c1, l_limit, u_limit)
    c2 = clip_bounds(c2, l_limit, u_limit)
    return c1, c2


def op_levy(target, V, l_limit, u_limit):
    beta = 1.5
    sigma_u = (_gamma(1 + beta) * np.sin(np.pi * beta / 2) /
               (_gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2))) ** (1 / beta)
    u = np.random.normal(0, sigma_u, V)
    v = np.random.normal(0, 1, V)
    step = u / (np.abs(v) ** (1 / beta) + 1e-10)
    alpha = 0.01
    c1 = target + alpha * step * (u_limit - l_limit)
    r = -1 + 2 * np.random.random(V)
    c2 = target + alpha * r * (u_limit - l_limit)
    c1 = clip_bounds(c1, l_limit, u_limit)
    c2 = clip_bounds(c2, l_limit, u_limit)
    return c1, c2


def op_cauchy(target, V, l_limit, u_limit):
    alpha = 0.01
    cauchy_noise1 = np.tan(np.pi * (np.random.random(V) - 0.5))
    c1 = target + alpha * cauchy_noise1 * (u_limit - l_limit)
    cauchy_noise2 = np.tan(np.pi * (np.random.random(V) - 0.5))
    c2 = target + alpha * cauchy_noise2 * (u_limit - l_limit)
    c1 = clip_bounds(c1, l_limit, u_limit)
    c2 = clip_bounds(c2, l_limit, u_limit)
    return c1, c2


def genetic_operator_multi(parent_chromosome, chromosome, M, V, l_limit, u_limit,
                           Nh, Nw, Np, L, Zpump, h, op_probs):
    """复刻 genetic_operator_multi.m：按 op_probs 轮盘赌选算子，对每个父代生成 2 子代"""
    from evaluate_objective import evaluate_objective_np

    op_probs = np.asarray(op_probs, dtype=float)
    op_probs = op_probs / op_probs.sum()
    op_cumsum = np.cumsum(op_probs)

    N = parent_chromosome.shape[0]
    children = np.empty((N * 2, V + M))

    p = 0
    for i in range(N):
        # 选两个不同父代
        idx1 = np.random.randint(N)
        idx2 = np.random.randint(N)
        while idx2 == idx1:
            idx2 = np.random.randint(N)

        target = parent_chromosome[i, :V].copy()
        p1 = parent_chromosome[idx1, :V].copy()
        p2 = parent_chromosome[idx2, :V].copy()

        # 轮盘赌选算子
        r = np.random.random()
        op_id = int(np.searchsorted(op_cumsum, r))

        pop_x = chromosome[:, :V]  # 决策变量矩阵（供 DE/rand/2 等使用）

        if op_id == 0:
            c1, c2 = op_de_rand_1(target, p1, p2, V, l_limit, u_limit)
        elif op_id == 1:
            c1, c2 = op_de_rand_2(target, p1, p2, pop_x, V, l_limit, u_limit)
        elif op_id == 2:
            c1, c2 = op_de_current_to_best(target, p1, p2, pop_x, V, l_limit, u_limit)
        elif op_id == 3:
            c1, c2 = op_pm(target, V, l_limit, u_limit)
        elif op_id == 4:
            c1, c2 = op_sbx(target, p1, p2, V, l_limit, u_limit)
        elif op_id == 5:
            c1, c2 = op_levy(target, V, l_limit, u_limit)
        else:
            c1, c2 = op_cauchy(target, V, l_limit, u_limit)

        # 评估两个子代
        f1a, f2a = evaluate_objective_np(c1, Nh, Nw, Np, L, Zpump, h)
        f1b, f2b = evaluate_objective_np(c2, Nh, Nw, Np, L, Zpump, h)

        children[p] = np.concatenate([c1, [f1a, f2a]])
        children[p + 1] = np.concatenate([c2, [f1b, f2b]])
        p += 2

    return children


# 算子名（与 config 一致）
OPERATOR_NAMES = ['DE/rand/1', 'DE/rand/2', 'DE/current-to-best/1', 'PM', 'SBX', 'Levy', 'Cauchy']
