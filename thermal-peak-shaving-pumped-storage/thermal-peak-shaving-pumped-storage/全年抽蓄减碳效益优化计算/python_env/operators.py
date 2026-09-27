"""operators.py - numpy 复刻 NSGA-II 核心算子

复刻 non_domination_sort_mod.m / tournament_selection.m / replace_chromosome.m
染色体布局与 MATLAB 一致:
  [0:V] 决策变量, [V:V+M] 目标值, [V+M] rank, [V+M+1] crowding distance
"""

import numpy as np


def non_domination_sort(x, M, V, return_indices=False):
    """快速非支配排序 + 拥挤距离，返回排序后的染色体矩阵。

    复刻 non_domination_sort_mod.m。x 形状 (N, V+M) 即只有决策变量+目标值，
    会在末尾追加 rank(V+M) 和 crowding(V+M+1) 两列。
    """
    N = x.shape[0]
    rank_col = V + M
    crowd_col = V + M + 1

    # 目标值矩阵
    obj = x[:, V:V + M].copy()
    # 不可行解（inf）处理：inf 视为被支配
    rank = np.zeros(N, dtype=int)
    dom_count = np.zeros(N, dtype=int)  # n_p: 支配 p 的个体数
    dominated_by = [[] for _ in range(N)]  # S_p: 被 p 支配的个体列表

    front = [[]]

    for i in range(N):
        for j in range(N):
            if i == j:
                continue
            # 判断 i 是否支配 j
            less, equal, more = 0, 0, 0
            for k in range(M):
                vi = obj[i, k]
                vj = obj[j, k]
                # Treat every non-finite objective (including NaN) as an
                # infeasible, worst-case value.  Comparing NaN directly would
                # leave both domination flags unset and can produce rank 0.
                vi_finite = np.isfinite(vi)
                vj_finite = np.isfinite(vj)
                if not vi_finite and not vj_finite:
                    equal += 1
                elif not vi_finite:
                    more += 1
                elif not vj_finite:
                    less += 1
                elif vi < vj:
                    less += 1
                elif abs(vi - vj) < 1e-9:
                    equal += 1
                else:
                    more += 1
            if less == 0 and equal != M:
                # j 支配 i
                dom_count[i] += 1
            elif more == 0 and equal != M:
                # i 支配 j
                dominated_by[i].append(j)
        if dom_count[i] == 0:
            rank[i] = 1
            front[0].append(i)

    # 逐 front 传播
    f = 0
    while len(front[f]) > 0:
        Q = []
        for p in front[f]:
            for q in dominated_by[p]:
                dom_count[q] -= 1
                if dom_count[q] == 0:
                    rank[q] = f + 2
                    Q.append(q)
        f += 1
        front.append(Q)

    # 组装完整染色体（决策+目标+rank）
    full = np.hstack([x, rank.reshape(-1, 1).astype(float)])

    # 拥挤距离（严格对齐 MATLAB: 对 front 内所有个体排序，不跳过 inf）
    crowding = np.zeros(N)
    n_fronts = f
    for fi in range(n_fronts):
        members = np.array(front[fi])
        if len(members) == 0:
            continue
        # 每个目标维度的距离贡献，先存临时，最后求和
        dist_per_obj = np.zeros((len(members), M))
        for k in range(M):
            # ``argsort`` places NaN inconsistently across NumPy versions.
            # Use an explicit worst-case sentinel for crowding calculations;
            # domination above already treats non-finite objectives as
            # infeasible.
            fk = np.where(np.isfinite(obj[members, k]), obj[members, k], np.inf)
            order_in_front = np.argsort(fk)
            f_sorted = fk[order_in_front]
            f_max = f_sorted[-1]
            f_min = f_sorted[0]
            # 首末边界 = inf
            dist_per_obj[order_in_front[0], k] = np.inf
            dist_per_obj[order_in_front[-1], k] = np.inf
            # 若 f_max/f_min 含非有限值（不可行解），该维度只有边界
            # inf，中间个体也给 inf，避免 NaN 传播到拥挤距离。
            if not np.isfinite(f_max) or not np.isfinite(f_min):
                dist_per_obj[order_in_front[1:-1], k] = np.inf
                continue
            for j in range(1, len(order_in_front) - 1):
                if f_max - f_min == 0:
                    dist_per_obj[order_in_front[j], k] = np.inf
                else:
                    dist_per_obj[order_in_front[j], k] = (
                        f_sorted[j + 1] - f_sorted[j - 1]) / (f_max - f_min)
        # 求和（inf + 有限值 = inf，保留 MATLAB 语义）
        crowding[members] = dist_per_obj.sum(axis=1)

    full = np.hstack([full, crowding.reshape(-1, 1)])

    # 按 rank 排序
    idx = np.argsort(full[:, rank_col])
    full = full[idx]
    return (full, idx) if return_indices else full


def tournament_selection(chromosome, pool_size, tour_size=2, rng=None,
                         return_indices=False):
    """二进制锦标赛选择，返回交配池 (pool_size, V+M+2)"""
    pop = chromosome.shape[0]
    rank_col = chromosome.shape[1] - 2  # V+M，rank
    crowd_col = chromosome.shape[1] - 1  # V+M+1，crowding

    mating_pool = np.empty((pool_size, chromosome.shape[1]))
    selected = np.empty(pool_size, dtype=int)
    for i in range(pool_size):
        # Keep the legacy global RNG when no generator is supplied, but allow
        # callers to own the complete random stream for reproducible runs.
        if rng is None:
            candidates = np.random.choice(pop, size=tour_size, replace=False)
        else:
            candidates = rng.choice(pop, size=tour_size, replace=False)
        ranks = chromosome[candidates, rank_col]
        crowds = chromosome[candidates, crowd_col]
        # Ranked populations produced by ``non_domination_sort`` are finite,
        # but sanitize defensive/custom inputs so a NaN cannot make the
        # tournament winner depend on NumPy's NaN ordering.
        ranks = np.where(np.isfinite(ranks), ranks, np.inf)
        crowds = np.where(np.isnan(crowds), -np.inf, crowds)
        min_rank = ranks.min()
        min_idx = np.where(ranks == min_rank)[0]
        if len(min_idx) > 1:
            # 同 rank 选 crowding 最大
            best_in_min = min_idx[np.argmax(crowds[min_idx])]
        else:
            best_in_min = min_idx[0]
        selected[i] = candidates[best_in_min]
        mating_pool[i] = chromosome[selected[i]]
    return (mating_pool, selected) if return_indices else mating_pool


def replace_chromosome(intermediate, M, V, pop, return_indices=False):
    """精英保留：按 rank + crowding 截断到 pop 大小"""
    N = intermediate.shape[0]
    rank_col = V + M
    crowd_col = V + M + 1

    order = np.argsort(intermediate[:, rank_col])
    sorted_chrom = intermediate[order]

    max_rank = int(np.nanmax(intermediate[:, rank_col])) if N > 0 else 1
    if max_rank < 1 or np.isinf(max_rank):
        max_rank = 1
    max_rank = min(max_rank, N)

    result = []
    selected_indices = []
    previous_index = 0
    for i in range(1, max_rank + 1):
        idx_rank = np.where(sorted_chrom[:, rank_col] == i)[0]
        if len(idx_rank) == 0:
            continue
        current_index = idx_rank[-1] + 1  # 1-based

        if current_index > pop:
            remaining = pop - previous_index
            temp_pop = sorted_chrom[previous_index:min(current_index, N)]
            remaining = min(remaining, temp_pop.shape[0])
            if remaining > 0:
                temp_sort = np.argsort(temp_pop[:, crowd_col])[::-1]  # 降序
                result.append(temp_pop[temp_sort[:remaining]])
                selected_indices.append(
                    order[previous_index:min(current_index, N)][temp_sort[:remaining]])
            break
        else:
            result.append(sorted_chrom[previous_index:current_index])
            selected_indices.append(order[previous_index:current_index])
            previous_index = current_index
            if current_index >= pop:
                break

    if len(result) == 0:
        selected = order[:min(pop, N)]
        rows = sorted_chrom[:min(pop, N)]
        return (rows, selected) if return_indices else rows

    f = np.vstack(result)
    if f.shape[0] < pop:
        take = min(pop, N)
        f = sorted_chrom[:take]
        selected = order[:take]
    else:
        selected = np.concatenate(selected_indices).astype(int, copy=False)
    return (f, selected) if return_indices else f


def compute_hv_2d(points, ref_point):
    """Return the exact 2-D hypervolume for minimisation objectives.

    The dominated region is clipped to the box ending at ``ref_point``.
    Points outside that box, non-finite points, duplicates, and points
    dominated by another point cannot contribute and are discarded first.
    Keeping the Pareto front explicit is important here: the old implementation
    integrated rectangles in the wrong direction and then used ``abs`` to hide
    negative area, which could turn an invalid reference point into a plausible
    but incorrect HV value.
    """
    points = np.asarray(points, dtype=float)
    ref = np.asarray(ref_point, dtype=float).reshape(-1)
    if points.size == 0:
        return 0.0
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("points must have shape (n, 2)")
    if ref.shape != (2,) or not np.all(np.isfinite(ref)):
        raise ValueError("ref_point must contain two finite values")

    # A point with either coordinate at/above the reference has an empty
    # intersection with the dominated box and contributes zero area.
    finite = np.all(np.isfinite(points), axis=1)
    inside = finite & (points[:, 0] < ref[0]) & (points[:, 1] < ref[1])
    points = points[inside]
    if points.shape[0] == 0:
        return 0.0

    # Sort by x and then y.  Scanning in this order keeps only points whose y
    # value improves, which is precisely the non-dominated staircase for two
    # minimisation objectives.
    order = np.lexsort((points[:, 1], points[:, 0]))
    points = points[order]
    front = []
    best_y = np.inf
    for x_value, y_value in points:
        if y_value < best_y:
            front.append((x_value, y_value))
            best_y = y_value
    front = np.asarray(front, dtype=float)

    # Between consecutive x coordinates, the rightmost point dominates the
    # whole vertical strip.  The final strip ends at the reference x value.
    widths = np.diff(np.r_[front[:, 0], ref[0]])
    heights = ref[1] - front[:, 1]
    return float(np.sum(widths * heights))
