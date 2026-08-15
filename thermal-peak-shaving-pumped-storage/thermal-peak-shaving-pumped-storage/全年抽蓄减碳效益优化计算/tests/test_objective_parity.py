"""test_objective_parity.py - numpy 复刻 vs MATLAB 原始的对拍测试

流程:
  1. 用 numpy 生成随机解集 X，写入 parity_input.mat
  2. 调 matlab -batch objective_parity_ref 生成参考值 parity_ref.mat
  3. numpy 复刻版 evaluate_objective_np 计算对比，断言 allclose

用法:
  python -m pytest tests/test_objective_parity.py -v
  或直接 python tests/test_objective_parity.py
"""

import os
import sys
import subprocess
import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_CALC_DIR = os.path.dirname(_THIS_DIR)  # 全年抽蓄减碳效益优化计算/

sys.path.insert(0, _CALC_DIR)
sys.path.insert(0, os.path.join(_CALC_DIR, 'python_env'))

from evaluate_objective import evaluate_objective_np
from data_loader_py import load_day


def _write_parity_input(X, day_idx, out_dir):
    from scipy.io import savemat
    Nh, Nw, Np, L = load_day(day_idx)
    savemat(
        os.path.join(out_dir, 'parity_input.mat'),
        {'X': X, 'Nh': Nh, 'Nw': Nw, 'Np': Np, 'L': L, 'Zpump': 1400.0, 'h': 4.0},
    )


def _run_matlab_ref(out_dir):
    result = subprocess.run(
        ['matlab', '-batch', 'objective_parity_ref'],
        cwd=out_dir, capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"MATLAB 出错:\n{result.stdout}\n{result.stderr}")
    return os.path.join(out_dir, 'parity_ref.mat')


def _read_parity_ref(ref_path):
    from scipy.io import loadmat
    return loadmat(ref_path)['F']


def main():
    day_idx = 0  # 用第 1 天数据
    rng = np.random.default_rng(42)
    X = rng.random((100, 23))  # 100 个随机解

    Nh, Nw, Np, L = load_day(day_idx)

    # 写入 input
    _write_parity_input(X, day_idx, _CALC_DIR)

    # 跑 MATLAB 参考
    print('运行 MATLAB 生成参考值...')
    ref_path = _run_matlab_ref(_CALC_DIR)
    F_ref = _read_parity_ref(ref_path)
    print(f'  MATLAB 参考值: {F_ref.shape}')

    # numpy 计算
    F_np = np.empty((X.shape[0], 2))
    for i in range(X.shape[0]):
        F_np[i, 0], F_np[i, 1] = evaluate_objective_np(X[i], Nh, Nw, Np, L)

    # 对比（inf 与 inf 应视为一致）
    def _close(a, b):
        inf_mask = np.isinf(a) & np.isinf(b)
        fin_mask = ~inf_mask
        ok = True
        if np.any(fin_mask):
            ok = ok and np.allclose(a[fin_mask], b[fin_mask], rtol=1e-6, atol=1e-6)
        return ok and np.all(inf_mask | (~np.isinf(a) & ~np.isinf(b)))

    f1_close = _close(F_np[:, 0], F_ref[:, 0])
    f2_close = _close(F_np[:, 1], F_ref[:, 1])

    def _max_diff(a, b):
        fin = ~np.isinf(a) & ~np.isinf(b)
        if np.any(fin):
            return np.max(np.abs(a[fin] - b[fin]))
        return 0.0

    f1_max_diff = _max_diff(F_np[:, 0], F_ref[:, 0])
    f2_max_diff = _max_diff(F_np[:, 1], F_ref[:, 1])

    print('\n=== 对拍结果 ===')
    print(f'  f1 (Zt_f)  一致: {f1_close}  最大差 {f1_max_diff:.2e}')
    print(f'  f2 (EMI)   一致: {f2_close}  最大差 {f2_max_diff:.2e}')

    if f1_close and f2_close:
        print('\n[PASS] 对拍通过：numpy 复刻与 MATLAB 一致')
        return 0
    else:
        print('\n[FAIL] 对拍失败')
        return 1


if __name__ == '__main__':
    sys.exit(main())
