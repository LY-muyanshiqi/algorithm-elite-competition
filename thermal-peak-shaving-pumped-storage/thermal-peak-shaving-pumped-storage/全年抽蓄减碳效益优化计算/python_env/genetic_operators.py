"""genetic_operators.py - numpy 复刻 genetic_operator_multi.m 的 7 个算子

算子索引与 MATLAB 一致:
  0: DE/rand/1, 1: DE/rand/2, 2: DE/current-to-best/1, 3: PM, 4: SBX, 5: Levy, 6: Cauchy
每个算子返回 (child_1, child_2) 两个子代（未评估）。
"""

import numpy as np
from scipy.special import gamma as _gamma


def clip_bounds(x, l_limit, u_limit):
    return np.clip(x, l_limit, u_limit)


def op_de_rand_1(target, p1, p2, V, l_limit, u_limit, F=0.5, rng=None):
    random = np.random if rng is None else rng
    CR = 0.9
    c1 = target.copy()
    mask = random.random(V) < CR
    c1[mask] = p1[mask] + F * (p2[mask] - target[mask])
    c1 = clip_bounds(c1, l_limit, u_limit)
    c2 = target.copy()
    return c1, c2


def op_de_rand_2(target, p1, p2, pop, V, l_limit, u_limit, F=0.5, rng=None):
    random = np.random if rng is None else rng
    pop_x = pop[:, :V]
    N = pop_x.shape[0]
    if N < 2:
        raise ValueError('DE/rand/2 requires at least two population rows')
    randint = random.randint if rng is None else random.integers
    idx3 = randint(N)
    idx4 = randint(N)
    while idx4 == idx3:
        idx4 = randint(N)
    p3 = pop_x[idx3]
    p4 = pop_x[idx4]
    CR = 0.9
    c1 = target.copy()
    mask = random.random(V) < CR
    c1[mask] = p1[mask] + F * (p2[mask] - p3[mask]) + F * (p4[mask] - target[mask])
    c1 = clip_bounds(c1, l_limit, u_limit)
    c2 = target.copy()
    return c1, c2


def op_de_current_to_best(target, p1, p2, pop, V, l_limit, u_limit, F=0.5, rng=None):
    random = np.random if rng is None else rng
    # ``pop`` is the complete chromosome when called from the dispatcher.
    # The objective is at column V, not at decision-variable column 0.
    if pop.shape[1] >= V + 1:
        objectives = pop[:, V]
        finite = np.isfinite(objectives)
        if np.any(finite):
            candidates = np.flatnonzero(finite)
            best = pop[candidates[np.argmin(objectives[finite])], :V]
        else:
            best = pop[0, :V]
    else:
        best = pop[np.argsort(pop[:, 0])[0], :V]
    # Match the project's MATLAB operator for the attraction term while
    # allowing RLDE-F to adapt the differential term F2.
    F1 = 0.8
    F2 = F
    CR = 0.9
    c1 = target.copy()
    mask = random.random(V) < CR
    c1[mask] = target[mask] + F1 * (best[mask] - target[mask]) + F2 * (p1[mask] - p2[mask])
    c1 = clip_bounds(c1, l_limit, u_limit)
    c2 = target.copy()
    return c1, c2


def op_pm(parent, V, l_limit, u_limit, rng=None):
    random = np.random if rng is None else rng
    eta_m = 20
    pm = 1.0 / V
    c1 = parent.copy()
    c2 = parent.copy()
    for j in range(V):
        if random.random() < pm:
            y = parent[j]
            r = random.random()
            if r <= 0.5:
                delta_q = (2 * r) ** (1 / (eta_m + 1)) - 1
            else:
                delta_q = 1 - (2 * (1 - r)) ** (1 / (eta_m + 1))
            c1[j] = y + delta_q * (u_limit[j] - l_limit[j])

            r2 = random.random()
            if r2 <= 0.5:
                delta_q2 = (2 * r2) ** (1 / (eta_m + 1)) - 1
            else:
                delta_q2 = 1 - (2 * (1 - r2)) ** (1 / (eta_m + 1))
            c2[j] = y + delta_q2 * (u_limit[j] - l_limit[j])
    c1 = clip_bounds(c1, l_limit, u_limit)
    c2 = clip_bounds(c2, l_limit, u_limit)
    return c1, c2


def op_sbx(p1, p2_parent, p3, V, l_limit, u_limit, rng=None):
    random = np.random if rng is None else rng
    eta_c = 20
    pc = 0.9
    c1 = p1.copy()
    c2 = p1.copy()
    if random.random() < pc:
        for j in range(V):
            if random.random() < 0.5:
                if abs(p2_parent[j] - p3[j]) > 1e-14:
                    y1 = min(p2_parent[j], p3[j])
                    y2 = max(p2_parent[j], p3[j])

                    beta = 1 + 2 * (y1 - l_limit[j]) / max(y2 - y1, 1e-14)
                    alpha = 2 - beta ** (-(eta_c + 1))
                    r = random.random()
                    if r <= 1 / alpha:
                        beta_q = (r * alpha) ** (1 / (eta_c + 1))
                    else:
                        beta_q = (1 / (2 - r * alpha)) ** (1 / (eta_c + 1))
                    c1[j] = 0.5 * ((y1 + y2) - beta_q * (y2 - y1))

                    beta2 = 1 + 2 * (u_limit[j] - y2) / max(y2 - y1, 1e-14)
                    alpha2 = 2 - beta2 ** (-(eta_c + 1))
                    r2 = random.random()
                    if r2 <= 1 / alpha2:
                        beta_q2 = (r2 * alpha2) ** (1 / (eta_c + 1))
                    else:
                        beta_q2 = (1 / (2 - r2 * alpha2)) ** (1 / (eta_c + 1))
                    c2[j] = 0.5 * ((y1 + y2) + beta_q2 * (y2 - y1))
    c1 = clip_bounds(c1, l_limit, u_limit)
    c2 = clip_bounds(c2, l_limit, u_limit)
    return c1, c2


def op_levy(target, V, l_limit, u_limit, rng=None):
    random = np.random if rng is None else rng
    beta = 1.5
    sigma_u = (_gamma(1 + beta) * np.sin(np.pi * beta / 2) /
               (_gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2))) ** (1 / beta)
    u = random.normal(0, sigma_u, V)
    v = random.normal(0, 1, V)
    step = u / (np.abs(v) ** (1 / beta) + 1e-10)
    alpha = 0.01
    c1 = target + alpha * step * (u_limit - l_limit)
    r = -1 + 2 * random.random(V)
    c2 = target + alpha * r * (u_limit - l_limit)
    c1 = clip_bounds(c1, l_limit, u_limit)
    c2 = clip_bounds(c2, l_limit, u_limit)
    return c1, c2


def op_cauchy(target, V, l_limit, u_limit, rng=None):
    random = np.random if rng is None else rng
    alpha = 0.01
    cauchy_noise1 = np.tan(np.pi * (random.random(V) - 0.5))
    c1 = target + alpha * cauchy_noise1 * (u_limit - l_limit)
    cauchy_noise2 = np.tan(np.pi * (random.random(V) - 0.5))
    c2 = target + alpha * cauchy_noise2 * (u_limit - l_limit)
    c1 = clip_bounds(c1, l_limit, u_limit)
    c2 = clip_bounds(c2, l_limit, u_limit)
    return c1, c2


def genetic_operator_multi(parent_chromosome, chromosome, M, V, l_limit, u_limit,
                           Nh, Nw, Np, L, Zpump, h, op_probs, evaluator=None,
                           f_values=None, parent_indices=None, rng=None,
                           return_info=False, selected_operator_ids=None):
    """复刻 genetic_operator_multi.m：按 op_probs 轮盘赌选算子，对每个父代生成 2 子代"""
    from evaluate_objective import evaluate_objective_np

    random = np.random if rng is None else rng
    randint = random.randint if rng is None else random.integers
    op_probs = np.asarray(op_probs, dtype=float)
    if (op_probs.ndim != 1 or op_probs.size == 0 or
            not np.all(np.isfinite(op_probs)) or np.any(op_probs < 0) or
            op_probs.sum() <= 0):
        raise ValueError('op_probs must contain finite non-negative weights')
    op_probs = op_probs / op_probs.sum()
    op_cumsum = np.cumsum(op_probs)

    N = parent_chromosome.shape[0]
    if N < 2:
        raise ValueError('at least two parents are required for genetic operators')
    if f_values is not None:
        f_values = np.asarray(f_values, dtype=float)
        if f_values.shape != (N,) or not np.all(np.isfinite(f_values)):
            raise ValueError('f_values must contain one finite value per parent')
    if selected_operator_ids is not None:
        selected_operator_ids = np.asarray(selected_operator_ids, dtype=int)
        if selected_operator_ids.shape != (N,) or np.any(
                (selected_operator_ids < 0) | (selected_operator_ids >= len(op_probs))):
            raise ValueError('selected_operator_ids must contain one valid operator per parent')
    children = np.empty((N * 2, V + M))
    operator_ids = []
    f_used = []

    p = 0
    for i in range(N):
        # 选两个不同父代
        idx1 = randint(N)
        idx2 = randint(N)
        while idx2 == idx1:
            idx2 = randint(N)

        target = parent_chromosome[i, :V].copy()
        p1 = parent_chromosome[idx1, :V].copy()
        p2 = parent_chromosome[idx2, :V].copy()

        # 轮盘赌选算子
        if selected_operator_ids is None:
            r = random.random()
            op_id = min(int(np.searchsorted(op_cumsum, r)), len(op_probs) - 1)
        else:
            op_id = int(selected_operator_ids[i])
        F = 0.5 if f_values is None else float(f_values[i])
        operator_ids.append(op_id)
        f_used.append(F)

        population = chromosome  # full rows retain objective values for best selection
        parent_population = parent_chromosome

        if op_id == 0:
            c1, c2 = op_de_rand_1(target, p1, p2, V, l_limit, u_limit, F=F, rng=rng)
        elif op_id == 1:
            c1, c2 = op_de_rand_2(target, p1, p2, parent_population, V, l_limit, u_limit, F=F, rng=rng)
        elif op_id == 2:
            c1, c2 = op_de_current_to_best(target, p1, p2, population, V, l_limit, u_limit, F=F, rng=rng)
        elif op_id == 3:
            c1, c2 = op_pm(target, V, l_limit, u_limit, rng=rng)
        elif op_id == 4:
            c1, c2 = op_sbx(target, p1, p2, V, l_limit, u_limit, rng=rng)
        elif op_id == 5:
            c1, c2 = op_levy(target, V, l_limit, u_limit, rng=rng)
        else:
            c1, c2 = op_cauchy(target, V, l_limit, u_limit, rng=rng)

        # 评估两个子代
        if evaluator is None:
            f1a, f2a = evaluate_objective_np(c1, Nh, Nw, Np, L, Zpump, h)
            f1b, f2b = evaluate_objective_np(c2, Nh, Nw, Np, L, Zpump, h)
        else:
            f1a, f2a = evaluator(c1)
            f1b, f2b = evaluator(c2)

        children[p] = np.concatenate([c1, [f1a, f2a]])
        children[p + 1] = np.concatenate([c2, [f1b, f2b]])
        p += 2

    if not return_info:
        return children
    n_parent = len(parent_chromosome)
    target_ids = (np.arange(n_parent) if parent_indices is None
                  else np.asarray(parent_indices, dtype=int))
    return children, {
        'target_indices': target_ids,
        'operator_ids': np.asarray(operator_ids, dtype=int),
        'f_values': np.asarray(f_used, dtype=float),
        'child_objectives': children[:, V:V + M].reshape(n_parent, 2, M),
        'trial_objectives': children[::2, V:V + M],
        'f_active': np.asarray(operator_ids, dtype=int) < 3,
    }


# 算子名（与 config 一致）
OPERATOR_NAMES = ['DE/rand/1', 'DE/rand/2', 'DE/current-to-best/1', 'PM', 'SBX', 'Levy', 'Cauchy']
