"""state_features.py - 复刻 nslde_enhanced.m 的 extract_state_features（6 维特征）

权威语义参照 nslde_enhanced.m 第 215-255 行，输出 6 维:
  [entropy_norm, gen_ratio, stag_norm, hv_delta, cv_rate, crowd_var]
"""

import numpy as np
from operators import compute_hv_2d


def extract_state_features(chromosome, M, V, gen, max_gen, stagnation, prev_hv,
                           ref_point=None):
    """复刻 extract_state_features，chromosome 为 (N, V+M+3) 的种群矩阵

    注意: chromosome 列布局与 MATLAB 一致:
      [0:V] 决策变量, [V:V+M] 目标值, [V+M] rank, [V+M+1] crowding
    """
    chromosome = np.asarray(chromosome, dtype=float)
    if chromosome.ndim != 2 or chromosome.shape[1] < V + M:
        raise ValueError("chromosome must be a 2-D array containing objectives")
    if M < 2:
        raise ValueError("state features require at least two objectives")

    f1 = chromosome[:, V]
    f2 = chromosome[:, V + 1]
    # NaN is not a feasible objective.  Using ``isinf`` alone lets a NaN
    # enter the entropy/HV calculations and poison the RL state.
    feasible = np.isfinite(f1) & np.isfinite(f2)
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

    entropy_norm = float(np.clip(np.nan_to_num(entropy / 5.0, nan=0.0,
                                               posinf=1.0, neginf=0.0), 0.0, 1.0))
    # State features must remain finite even for a defensive/empty episode.
    # A non-positive horizon has no meaningful progress ratio, so use zero.
    try:
        gen_value = float(gen)
        horizon = float(max_gen)
    except (TypeError, ValueError):
        gen_value, horizon = 0.0, 0.0
    gen_ratio = gen_value / horizon if np.isfinite(gen_value) and np.isfinite(horizon) and horizon > 0 else 0.0
    gen_ratio = float(np.clip(np.nan_to_num(gen_ratio, nan=0.0,
                                             posinf=1.0, neginf=0.0), 0.0, 1.0))
    try:
        stagnation_value = float(stagnation)
    except (TypeError, ValueError):
        stagnation_value = 0.0
    stag_norm = float(np.clip(np.nan_to_num(stagnation_value / 10.0,
                                             nan=0.0, posinf=3.0, neginf=0.0), 0.0, 3.0))

    # hv_delta
    hv_delta = 0.0
    try:
        previous_hv = float(prev_hv)
    except (TypeError, ValueError):
        previous_hv = 0.0
    if np.isfinite(previous_hv) and previous_hv > 0 and n_feasible > 0:
        f_all = np.column_stack([f1[feasible], f2[feasible]])
        if ref_point is None:
            active_ref = [np.max(f1[feasible]) * 1.2,
                          np.max(f2[feasible]) * 1.2]
        else:
            candidate_ref = np.asarray(ref_point, dtype=float).reshape(-1)
            active_ref = (candidate_ref if candidate_ref.shape == (2,)
                          and np.all(np.isfinite(candidate_ref)) else None)
            if active_ref is None:
                active_ref = [np.max(f1[feasible]) * 1.2,
                              np.max(f2[feasible]) * 1.2]
        try:
            hv_current = compute_hv_2d(f_all, active_ref)
            hv_delta = (hv_current - previous_hv) / max(previous_hv, 1.0)
        except (ValueError, FloatingPointError):
            # A malformed reference point should not make the RL state NaN.
            hv_delta = 0.0
    hv_delta = float(np.clip(np.nan_to_num(hv_delta, nan=0.0,
                                           posinf=1.0, neginf=-1.0), -1.0, 1.0))

    population_size = chromosome.shape[0]
    cv_rate = (1.0 - n_feasible / population_size
               if population_size > 0 else 1.0)
    cv_rate = float(np.clip(np.nan_to_num(cv_rate, nan=1.0,
                                           posinf=1.0, neginf=0.0), 0.0, 1.0))

    crowd_var = 0.0
    if n_feasible > 2:
        crowd_vals = chromosome[feasible, V + M + 1]
        crowd_vals = crowd_vals[np.isfinite(crowd_vals)]
        if crowd_vals.size > 1:
            mean_crowd = float(np.mean(crowd_vals))
            scale = max(abs(mean_crowd), 1e-10)
            crowd_var = np.std(crowd_vals) / scale
            crowd_var = float(np.clip(np.nan_to_num(crowd_var, nan=0.0,
                                                     posinf=1.0, neginf=0.0), 0.0, 1.0))

    state = np.array([entropy_norm, gen_ratio, stag_norm, hv_delta, cv_rate, crowd_var],
                     dtype=float)
    return np.nan_to_num(state, nan=0.0, posinf=1.0, neginf=0.0)
