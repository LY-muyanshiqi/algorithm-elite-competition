"""data_loader_py.py - 从 txt 文件加载单日调度数据（供 Python 环境使用）

数据文件位于本目录（全年抽蓄减碳效益优化计算/）下的 hydro.txt / wind.txt /
solar.txt / FH.txt，均为 365 行 x 24 列（365 天 x 24 小时）。
"""

import os
import numpy as np

_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据文件在计算目录（python_env 的上级目录）
_CALC_DIR = os.path.dirname(_DIR)

_DATASETS = {
    'hydro': 'hydro.txt',
    'wind': 'wind.txt',
    'solar': 'solar.txt',
    'fh': 'FH.txt',
}

_cache = {}


def load_day(day_idx, data_dir=None):
    """加载第 day_idx 天(0-based)的 (Nh, Nw, Np, L)，各为 24 维向量"""
    base = data_dir if data_dir is not None else _CALC_DIR
    global _cache
    if base not in _cache:
        _cache[base] = {
            key: np.loadtxt(os.path.join(base, fname))
            for key, fname in _DATASETS.items()
        }
    d = _cache[base]
    Nh = d['hydro'][day_idx]
    Nw = d['wind'][day_idx]
    Np = d['solar'][day_idx]
    L = d['fh'][day_idx]
    return Nh, Nw, Np, L


def load_all_days(data_dir=None):
    """加载全部 365 天 (365x24 各一张)"""
    base = data_dir if data_dir is not None else _CALC_DIR
    global _cache
    if base not in _cache:
        _cache[base] = {
            key: np.loadtxt(os.path.join(base, fname))
            for key, fname in _DATASETS.items()
        }
    d = _cache[base]
    return d['hydro'], d['wind'], d['solar'], d['fh']
