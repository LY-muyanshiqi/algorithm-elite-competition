"""graph_builder.py - 种群状态 → PyG 异构图

每代决策一个图（graph-level 决策）。图结构:
  电源节点(5): hydro/wind/solar/pump/thermal
  时段节点(24): t=0..23
  边(电源->时段): 5x24=120 条，带功率特征
  全局特征 u: 6 维标量

节点的物理含义来自功率平衡约束:
  L(t) = Nh(t) + Nw(t) + Np(t) + Npump(t) + Nt(t)
"""

import numpy as np
import torch
from torch_geometric.data import Data

POWER_SOURCES = ['hydro', 'wind', 'solar', 'pump', 'thermal']
N_SOURCES = 5
N_TIMES = 24

# 统一节点特征维度
SRC_DIM = 8
T_DIM = 6
NODE_DIM = 8  # 电源 8 维，时段填充到 8 维（6 维特征 + 2 维 0）
EDGE_DIM = 3


def build_graph(Nh, Nw, Np, Npump, Nt, L, Zpump, scalar_features):
    """构建单个 generation 状态的同构图。

    节点: 29 个 = 电源 5 个(0..4) + 时段 24 个(5..28)
    边: 电源 -> 时段，120 条
    全局特征 data.u: 6 维标量

    返回 Data 对象（同构图，SAGEConv 可用）
    """
    Nh = np.asarray(Nh, dtype=float)
    Nw = np.asarray(Nw, dtype=float)
    Np = np.asarray(Np, dtype=float)
    Npump = np.asarray(Npump, dtype=float)
    Nt = np.asarray(Nt, dtype=float)
    L = np.asarray(L, dtype=float)

    # ---- 电源节点特征 (5 x 8) ----
    src_power = np.vstack([Nh, Nw, Np, Npump, Nt])
    src_mean = src_power.mean(axis=1)
    src_std = src_power.std(axis=1)
    src_max = src_power.max(axis=1)
    src_min = src_power.min(axis=1)
    src_ptv = (src_max - src_min) / (L.max() + 1e-10)
    src_cap = np.array([
        np.max(np.abs(Nh)), np.max(Nw), np.max(Np), float(Zpump), np.max(Nt),
    ]) / (L.max() + 1e-10)
    src_type = np.array([[1, 0], [0, 1], [0, 0], [0, 0], [0, 0]])

    src_feat = np.column_stack([
        src_mean, src_std, src_max, src_min, src_ptv, src_cap, src_type[:, 0], src_type[:, 1],
    ])  # (5, 8)

    # ---- 时段节点特征 (24 x 6)，填充到 8 维 ----
    new_energy_ratio = (Nw + Np) / (L + 1e-10)
    t_idx = np.arange(N_TIMES)
    sin_t = np.sin(2 * np.pi * t_idx / 24.0)
    cos_t = np.cos(2 * np.pi * t_idx / 24.0)
    t_feat = np.column_stack([
        L, new_energy_ratio, Npump, Nt, sin_t, cos_t,
    ])  # (24, 6)
    t_feat_pad = np.column_stack([t_feat, np.zeros((24, NODE_DIM - T_DIM))])  # (24, 8)

    # 全节点特征: 前 5 电源节点，后 24 时段节点
    node_feat = np.vstack([src_feat, t_feat_pad])  # (29, 8)

    # ---- 边 (电源 -> 时段) ----
    edge_index = []
    edge_feat = []
    for src in range(N_SOURCES):
        for t in range(N_TIMES):
            edge_index.append([src, N_SOURCES + t])
            power = src_power[src, t]
            ratio = power / (L[t] + 1e-10)
            thermal_t = Nt[t]
            edge_feat.append([power, ratio, thermal_t])
    edge_index = np.array(edge_index).T  # (2, 120)
    edge_feat = np.array(edge_feat)  # (120, 3)

    data = Data(
        x=torch.tensor(node_feat, dtype=torch.float32),
        edge_index=torch.tensor(edge_index, dtype=torch.long),
        edge_attr=torch.tensor(edge_feat, dtype=torch.float32),
        u=torch.tensor(np.asarray(scalar_features, dtype=float).reshape(1, -1), dtype=torch.float32),
    )
    return data


def build_batch_graphs(states):
    """批量构建图。states 是 list of (Nh,Nw,Np,Npump,Nt,L,Zpump,scalar_features)"""
    graphs = []
    for s in states:
        graphs.append(build_graph(*s))
    return graphs
