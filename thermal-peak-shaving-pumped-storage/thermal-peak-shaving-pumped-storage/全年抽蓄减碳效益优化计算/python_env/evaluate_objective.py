"""evaluate_objective.py - numpy 复刻 MATLAB evaluate_objective.m + carbon_intensity_continuous.m

逐行对齐 MATLAB 语义，含 pchip 连续化碳排放模型。

关键对齐点（对拍到 rtol 1e-6 的保证）:
  1. x(22)/x(23)/Cprice 声明但未生效，保持占位行为一致
  2. Npump 循环是顺序依赖，逐时段计算
  3. pchip 输入先 clamp 到 0.30 下界
"""

import numpy as np
from scipy.interpolate import PchipInterpolator

# 预构造 pchip 插值器（模块级，避免每次调用重复构造）
_LOAD_POINTS = np.array([0.30, 0.40, 0.50, 1.00])
_H_POINTS = np.array([370.0, 330.0, 300.0, 300.0])
_E_POINTS = np.array([0.904, 0.920, 0.934, 0.953])
_G_POINTS = np.array([0.401, 0.424, 0.442, 0.458])

_pchip_H = PchipInterpolator(_LOAD_POINTS, _H_POINTS)
_pchip_e = PchipInterpolator(_LOAD_POINTS, _E_POINTS)
_pchip_g = PchipInterpolator(_LOAD_POINTS, _G_POINTS)


def carbon_intensity_continuous(load_ratio):
    """pchip 连续化碳排放模型，返回 (H, e, g, Ce1, Ce2, Ce3)"""
    lr = np.maximum(np.asarray(load_ratio, dtype=float), 0.30)

    H = _pchip_H(lr)
    e = _pchip_e(lr)
    g = _pchip_g(lr)

    OF = 0.99
    Cc = 0.7
    Mco2 = 44.0
    Mc = 12.0
    e_100 = 0.953
    g_100 = 0.458
    Cq = 0.9183
    a = 0.02
    ps = 0.01
    us = 0.95
    Ms = 32.0
    as_val = 0.0148
    ys = 0.00392

    Ce1 = H * OF * Cc * Mco2 / Mc
    Ce2 = H * (1 - e / e_100) * Cq + H * (1 - g / g_100) * Cq + a * H * Cq
    Ce3 = H * ps * us * Mco2 / Ms + H * as_val * Cq + H * ys * Cq

    return H, e, g, Ce1, Ce2, Ce3


def evaluate_objective_np(x, Nh, Nw, Np, L, Zpump=1400.0, h=4.0):
    """复刻 evaluate_objective.m，返回 (f1, f2) = (Zt_f, sum(EMI))"""
    x = np.asarray(x, dtype=float)
    Nh = np.asarray(Nh, dtype=float)
    Nw = np.asarray(Nw, dtype=float)
    Np = np.asarray(Np, dtype=float)
    L = np.asarray(L, dtype=float)

    V = Zpump * h
    N = Nh + Nw + Np

    # C(1)..C(25)，C(1)=C(25)=0.5，C(2..24)=x(1..23)
    C = np.empty(25, dtype=float)
    C[0] = 0.5
    C[24] = 0.5
    C[1:24] = x[:23]

    Npump = np.zeros(24, dtype=float)

    for i in range(24):
        if C[i + 1] <= C[i]:
            Npump[i] = (C[i] - C[i + 1]) * V
            if Npump[i] < Zpump * 0.2:
                Npump[i] = 0.0
                C[i + 1] = C[i]
            if Npump[i] > Zpump:
                Npump[i] = Zpump
                C[i + 1] = C[i] - Npump[i] / V
        if C[i + 1] > C[i]:
            Npump[i] = (C[i] - C[i + 1]) * V / 0.75
            if Npump[i] > -Zpump * 0.2:
                Npump[i] = 0.0
                C[i + 1] = C[i]
            if Npump[i] < -Zpump:
                Npump[i] = -Zpump
                C[i + 1] = C[i] - Npump[i] * 0.75 / V

    Nn = N + Npump
    Nt = L - Nn
    Zt_f = (np.max(Nt) - np.min(Nt)) / 0.7

    if Zt_f > np.max(Nt):
        Nt_b = 0.0
    else:
        Nt_b = np.max(Nt) - Zt_f

    TH = Nt - Nt_b
    THmax = Zt_f
    TH = np.maximum(TH, THmax * 0.3)

    Emi_b = 300.0 * 0.99 * 0.7 * 44.0 / 12.0 * Nt_b
    load_ratio = TH / THmax
    _, _, _, Ce1_vec, Ce2_vec, Ce3_vec = carbon_intensity_continuous(load_ratio)

    Ce = Ce1_vec + Ce2_vec + Ce3_vec
    Emi = Ce * TH
    EMI = Emi + Emi_b

    f1 = Zt_f
    f2 = np.sum(EMI)

    if abs(C[24] - 0.5) > 0.01:
        f1 = np.inf
        f2 = np.inf

    return f1, f2


def evaluate_population_np(X, Nh, Nw, Np, L, Zpump=1400.0, h=4.0):
    """种群级评估。X: (N, 23) -> F: (N, 2)"""
    X = np.asarray(X, dtype=float)
    F = np.empty((X.shape[0], 2), dtype=float)
    for i in range(X.shape[0]):
        F[i, 0], F[i, 1] = evaluate_objective_np(X[i], Nh, Nw, Np, L, Zpump, h)
    return F
