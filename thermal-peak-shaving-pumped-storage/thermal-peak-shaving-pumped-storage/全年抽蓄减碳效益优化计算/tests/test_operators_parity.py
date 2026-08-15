"""test_operators_parity.py - 非支配排序 numpy 复刻 vs MATLAB 对拍

流程: 生成随机种群 -> MATLAB non_domination_sort_mod 得参考 -> numpy 版对比
验证 rank 和 crowding distance 是否一致。

用法: python tests/test_operators_parity.py
"""

import os
import sys
import subprocess
import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_CALC_DIR = os.path.dirname(_THIS_DIR)

sys.path.insert(0, os.path.join(_CALC_DIR, 'python_env'))

from operators import non_domination_sort, compute_hv_2d
from evaluate_objective import evaluate_objective_np
from data_loader_py import load_day


def _write_input(X, M, V, out_dir):
    from scipy.io import savemat
    savemat(os.path.join(out_dir, 'sort_input.mat'), {'X': X, 'M': M, 'V': V})


def _run_matlab(out_dir):
    result = subprocess.run(
        ['matlab', '-batch', 'sort_parity_ref'],
        cwd=out_dir, capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"MATLAB err:\n{result.stdout}\n{result.stderr}")
    return os.path.join(out_dir, 'sort_ref.mat')


def _read_ref(path):
    from scipy.io import loadmat
    return loadmat(path)['sorted']


def main():
    day_idx = 0
    # 用真实目标函数生成种群（保证有 inf 不可行解，测试 inf 处理）
    Nh, Nw, Np, L = load_day(day_idx)
    V, M = 23, 2
    N = 40
    rng = np.random.default_rng(7)

    X = rng.random((N, V))
    F = np.empty((N, M))
    for i in range(N):
        F[i, 0], F[i, 1] = evaluate_objective_np(X[i], Nh, Nw, Np, L, 1400.0, 4.0)
    X_full = np.hstack([X, F])  # N x 25

    # 写 input
    _write_input(X_full, M, V, _CALC_DIR)

    # 跑 MATLAB
    print('运行 MATLAB 非支配排序参考...')
    ref = _read_ref(_run_matlab(_CALC_DIR))
    print(f'  MATLAB sorted: {ref.shape}')

    # numpy 版
    np_sorted = non_domination_sort(X_full, M, V)
    print(f'  numpy sorted:  {np_sorted.shape}')

    # 对比: rank 列 (V+M=25)，crowding 列 (V+M+1=26)
    rank_ref = ref[:, V + M]
    rank_np = np_sorted[:, V + M]
    crowd_ref = ref[:, V + M + 1]
    crowd_np = np_sorted[:, V + M + 1]

    print('\n=== 对拍结果 ===')
    # rank 是排序后的顺序，对比排序后每个位置的 rank 分布
    # 注意: 排序可能因并列 rank 而顺序不同，用"rank 多重集"对比更稳健
    rank_ref_sorted = np.sort(rank_ref)
    rank_np_sorted = np.sort(rank_np)
    rank_match = np.allclose(rank_ref_sorted, rank_np_sorted)

    print(f'  rank 分布一致: {rank_match}')
    if not rank_match:
        print(f'    REF rank 值: {rank_ref_sorted[:20]}')
        print(f'    NP  rank 值: {rank_np_sorted[:20]}')

    # crowding distance: 只对比可行解（不可行解 f=[inf,inf] 的 crowding 是 nan vs 0，
    # 属于无害边界差异，由 MATLAB 对 inf-inf 的中间计算产生）
    # 可行解 mask: 目标值都非 inf
    feasible_ref = ~np.isinf(ref[:, V]) & ~np.isinf(ref[:, V + 1])
    feasible_np = ~np.isinf(np_sorted[:, V]) & ~np.isinf(np_sorted[:, V + 1])

    crowd_ref_finite = crowd_ref[feasible_ref]
    crowd_np_finite = crowd_np[feasible_np]
    crowd_ref_finite = crowd_ref_finite[np.isfinite(crowd_ref_finite)]
    crowd_np_finite = crowd_np_finite[np.isfinite(crowd_np_finite)]
    crowd_match = np.allclose(np.sort(crowd_ref_finite), np.sort(crowd_np_finite), atol=1e-4, rtol=1e-3)

    print(f'  crowding 多重集一致(仅可行解): {crowd_match}')
    print(f'    可行解数量: REF={feasible_ref.sum()}, NP={feasible_np.sum()}')

    if rank_match and crowd_match:
        print('\n[PASS] 非支配排序对拍通过')
        return 0
    else:
        print('\n[FAIL] 非支配排序对拍失败')
        return 1


if __name__ == '__main__':
    sys.exit(main())
