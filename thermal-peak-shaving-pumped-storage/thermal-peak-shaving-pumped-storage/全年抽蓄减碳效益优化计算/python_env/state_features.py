"""state_features.py - 复刻 nslde_enhanced.m 的 extract_state_features（6 维特征）

权威语义参照 nslde_enhanced.m 第 215-255 行，输出 6 维:
  [entropy_norm, gen_ratio, stag_norm, hv_delta, cv_rate, crowd_var]
"""

import numpy as np


def compute_hv_2d(points, ref_point):
    """2 目标 Hypervolume（复刻 compare_algorithms.m 的 compute_hv）"""
    points = np.asarray(points, dtype=float)
    if points.shape[0] == 0:
        return 0.0
    points = points[np.argsort(points[:, 0])]
    hv = 0.0
    prev_x = ref_point[0]
    for i in range(points.shape[0]):
        if points[i, 1] < ref_point[1]:
            hv += (prev_x - points[i, 0]) * (ref_point[1] - points[i, 1])
            prev_x = points[i, 0]
    return abs(hv)


def extract_state_features(chromosome, M, V, gen, max_gen, stagnation, prev_hv):
    """复刻 extract_state_features，chromosome 为 (N, V+M+3) 的种群矩阵

    注意: chromosome 列布局与 MATLAB 一致:
      [0:V] 决策变量, [V:V+M] 目标值, [V+M] rank, [V+M+1] crowding
    """
    f1 = chromosome[:, V]
    f2 = chromosome[:, V + 1]
    feasible = ~np.isinf(f1) & ~np.isinf(f2)
    n_feasible = int(np.sum(feasible))

    # entropy
    if n_feasible > 2:
        f_all = np.column_stack([f1[feasible], f2[feasible]])
        f_all_norm = (f_all - f_all.min(axis=0)) / (
            f_all.max(axis=0) - f_all.min(axis=0) + 1e-10
        )
        from scipy.spatial.distance import cdist
        dist_matrix = cdist(f_all_norm, f_all_norm)
        alpha = 0.1
        S = np.exp(-dist_matrix ** 2 / (2 * alpha ** 2))
        entropy = -np.mean(np.log(np.mean(S, axis=1) + 1e-10))
    else:
        entropy = 0.0

    entropy_norm = min(max(entropy / 5.0, 0.0), 1.0)
    gen_ratio = gen / max_gen
    stag_norm = min(stagnation / 10.0, 3.0)

    # hv_delta
    hv_delta = 0.0
    if prev_hv > 0 and n_feasible > 0:
        f_all = np.column_stack([f1[feasible], f2[feasible]])
        ref_point = [np.max(f1[feasible]) * 1.2, np.max(f2[feasible]) * 1.2]
        hv_current = compute_hv_2d(f_all, ref_point)
        hv_delta = (hv_current - prev_hv) / max(prev_hv, 1.0)

    cv_rate = 1.0 - n_feasible / chromosome.shape[0]

    crowd_var = 0.0
    if n_feasible > 2:
        crowd_vals = chromosome[feasible, V + M + 1]
        crowd_var = min(max(np.std(crowd_vals) / max(np.mean(crowd_vals), 1e-10), 0.0), 1.0)

    return np.array([entropy_norm, gen_ratio, stag_norm, hv_delta, cv_rate, crowd_var])
