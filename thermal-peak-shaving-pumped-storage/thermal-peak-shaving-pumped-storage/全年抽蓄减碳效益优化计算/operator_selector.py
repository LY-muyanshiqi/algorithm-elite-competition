"""
operator_selector.py - Operator Selection Network (OSN)

轻量级策略网络: 输入种群状态特征 → 输出7种算子的选择概率
用于 MATLAB NSLDE 调用: MATLAB 通过 Python Engine 获取算子概率

网络结构: Input(6) → FC(32, ReLU) → FC(64, ReLU) → FC(32, ReLU) → Output(7, Softmax)

6维输入特征:
  0: population_entropy    - 种群熵 (多样性指标)
  1: generation_ratio      - 当前代数/总代数
  2: stagnation_count      - 停滞代数 (归一化)
  3: hv_increment          - 最近k代的HV增量 (归一化)
  4: constraint_violation  - 约束违反率
  5: crowding_variance     - 拥挤距离方差 (归一化)

7维输出: [DE/rand/1, DE/rand/2, DE/current-to-best, PM, SBX, Levy, Cauchy]
"""

import torch
import torch.nn as nn
import numpy as np
import json
import os

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'osn_model.pt')

class OperatorSelectionNetwork(nn.Module):
    def __init__(self, input_dim=6, hidden_dims=[32, 64, 32], output_dim=7):
        super().__init__()
        layers = []
        prev_dim = input_dim
        for h_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, h_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.1))
            prev_dim = h_dim
        layers.append(nn.Linear(prev_dim, output_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        logits = self.net(x)
        return torch.softmax(logits, dim=-1)


class FeatureExtractor:
    """从种群状态矩阵中提取6维特征"""

    @staticmethod
    def extract(chromosome, gen_current, gen_max, stagnation, prev_f1=None, prev_f2=None):
        """
        chromosome: numpy array (N x K), 其中:
            col 0..V-1: 决策变量
            col V..V+1: 目标值 [f1, f2]
            col V+2: rank
            col V+3: crowding distance
        """
        N = chromosome.shape[0]
        V_est = 23
        M_est = 2

        f1 = chromosome[:, V_est]
        f2 = chromosome[:, V_est + 1]
        feasible_mask = ~np.isinf(f1) & ~np.isinf(f2)
        n_feasible = np.sum(feasible_mask)

        if n_feasible > 2:
            f_all = np.column_stack([f1[feasible_mask], f2[feasible_mask]])
            f_min = f_all.min(axis=0)
            f_max = f_all.max(axis=0)
            f_range = f_max - f_min
            f_range[f_range == 0] = 1e-10
            f_norm = (f_all - f_min) / f_range
            from scipy.spatial.distance import pdist, squareform
            dists = squareform(pdist(f_norm, 'euclidean'))
            alpha = 0.1
            S = np.exp(-dists**2 / (2 * alpha**2))
            entropy = -np.mean(np.log(np.mean(S, axis=1) + 1e-10))
        else:
            entropy = 0.0

        gen_ratio = gen_current / gen_max

        stag_norm = min(stagnation / 100.0, 1.0)

        hv_inc = 0.0
        if prev_f1 is not None and prev_f2 is not None and n_feasible > 2:
            prev_mask = ~np.isinf(prev_f1) & ~np.isinf(prev_f2)
            if np.sum(prev_mask) > 2:
                prev_min = np.min(prev_f1[prev_mask])
                if f1[feasible_mask].min() < prev_min:
                    hv_inc = (prev_min - f1[feasible_mask].min()) / (abs(prev_min) + 1e-10)
                hv_inc = np.clip(hv_inc, 0, 1)

        constraint_viol = 1.0 - n_feasible / N

        if n_feasible > 1:
            crowding = chromosome[feasible_mask, V_est + M_est + 1]
            crowding_var = np.var(crowding) / (np.mean(crowding)**2 + 1e-10)
            crowding_var = np.clip(crowding_var, 0, 10) / 10
        else:
            crowding_var = 0.0

        features = np.array([
            entropy,
            gen_ratio,
            stag_norm,
            hv_inc,
            constraint_viol,
            crowding_var
        ], dtype=np.float32)

        return features


def predict_operator_probs(features, model=None):
    """
    给定特征向量，返回7维算子概率

    作为 MATLAB Python Engine 调用的入口:
        >> features = py.numpy.array([entropy, gen_ratio, ...]);
        >> probs = py.operator_selector.predict_operator_probs(features);
    """
    if model is None:
        model = _get_or_load_model()

    x = torch.from_numpy(features).float().unsqueeze(0)
    model.eval()
    with torch.no_grad():
        probs = model(x).squeeze(0).numpy()
    return probs


_model_cache = None

def _get_or_load_model():
    global _model_cache
    if _model_cache is not None:
        return _model_cache
    model = OperatorSelectionNetwork()
    if os.path.exists(MODEL_PATH):
        model.load_state_dict(torch.load(MODEL_PATH, map_location='cpu'))
    _model_cache = model
    return model


OP_NAMES = [
    'DE/rand/1',
    'DE/rand/2',
    'DE/current-to-best/1',
    'PM (Polynomial Mutation)',
    'SBX',
    'Levy Flight',
    'Cauchy Mutation'
]
