"""
train_osn.py - 离线训练算子选择网络

训练数据: 利用已有四省 365 天进化轨迹 (nslde_enhanced 记录的 history)
训练方式: 以每50代后的HV增量为奖励信号，Behavior Cloning + Reward Weighting

用法:
    python train_osn.py --data_dir ./training_data --epochs 100 --lr 0.001
"""

import torch
import torch.nn as nn
import numpy as np
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from operator_selector import OperatorSelectionNetwork, MODEL_PATH, OP_NAMES


def generate_synthetic_training_data(n_samples=1000):
    """
    生成合成训练数据 — 基于进化过程各阶段的典型特征分布

    在实际部署前，用已有四省365天运行结果中的history数据替换
    """
    np.random.seed(42)

    features = np.zeros((n_samples, 6), dtype=np.float32)
    labels = np.zeros((n_samples, 7), dtype=np.float32)

    for i in range(n_samples):
        gen_phase = np.random.choice(['early', 'mid', 'late', 'stagnant'], p=[0.3, 0.3, 0.3, 0.1])

        if gen_phase == 'early':
            entropy = np.random.uniform(0.5, 1.0)
            gen_ratio = np.random.uniform(0.0, 0.2)
            stag_norm = 0.0
            hv_inc = np.random.uniform(0.3, 1.0)
            constraint_viol = np.random.uniform(0.3, 0.8)
            crowding_var = np.random.uniform(0.5, 1.0)
            target = np.array([0.25, 0.25, 0.01, 0.01, 0.01, 0.35, 0.12])

        elif gen_phase == 'mid':
            entropy = np.random.uniform(0.3, 0.7)
            gen_ratio = np.random.uniform(0.2, 0.6)
            stag_norm = np.random.uniform(0.0, 0.1)
            hv_inc = np.random.uniform(0.1, 0.5)
            constraint_viol = np.random.uniform(0.05, 0.3)
            crowding_var = np.random.uniform(0.2, 0.6)
            target = np.array([0.1, 0.15, 0.40, 0.10, 0.10, 0.10, 0.05])

        elif gen_phase == 'late':
            entropy = np.random.uniform(0.1, 0.4)
            gen_ratio = np.random.uniform(0.6, 1.0)
            stag_norm = np.random.uniform(0.0, 0.2)
            hv_inc = np.random.uniform(0.0, 0.1)
            constraint_viol = np.random.uniform(0.0, 0.1)
            crowding_var = np.random.uniform(0.1, 0.4)
            target = np.array([0.05, 0.05, 0.05, 0.40, 0.15, 0.15, 0.15])

        else:
            entropy = np.random.uniform(0.0, 0.2)
            gen_ratio = np.random.uniform(0.3, 1.0)
            stag_norm = np.random.uniform(0.3, 1.0)
            hv_inc = 0.0
            constraint_viol = np.random.uniform(0.02, 0.15)
            crowding_var = np.random.uniform(0.0, 0.1)
            target = np.array([0.02, 0.03, 0.05, 0.10, 0.05, 0.50, 0.25])

        features[i] = [entropy, gen_ratio, stag_norm, hv_inc, constraint_viol, crowding_var]
        labels[i] = target / target.sum()

    return features, labels


def train(args):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'Training on: {device}')

    model = OperatorSelectionNetwork(input_dim=6, output_dim=7).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    X, y = generate_synthetic_training_data(args.n_samples)
    X_tensor = torch.from_numpy(X).float().to(device)
    y_tensor = torch.from_numpy(y).float().to(device)

    n_train = int(0.8 * args.n_samples)
    indices = np.random.permutation(args.n_samples)
    train_idx = indices[:n_train]
    val_idx = indices[n_train:]

    X_train, y_train = X_tensor[train_idx], y_tensor[train_idx]
    X_val, y_val = X_tensor[val_idx], y_tensor[val_idx]

    for epoch in range(args.epochs):
        model.train()
        optimizer.zero_grad()
        pred = model(X_train)
        loss = nn.KLDivLoss(reduction='batchmean')(torch.log(pred + 1e-10), y_train)
        loss.backward()
        optimizer.step()
        scheduler.step()

        model.eval()
        with torch.no_grad():
            val_pred = model(X_val)
            val_loss = nn.KLDivLoss(reduction='batchmean')(torch.log(val_pred + 1e-10), y_val)

        if (epoch + 1) % 20 == 0:
            print(f'Epoch {epoch+1:3d}/{args.epochs} | Train KL: {loss.item():.4f} | Val KL: {val_loss.item():.4f}')

    torch.save(model.state_dict(), MODEL_PATH)
    print(f'\nModel saved to: {MODEL_PATH}')

    print('\n=== Final Operator Probability Profile ===')
    model.eval()
    with torch.no_grad():
        test_features = torch.tensor([
            [0.10, 0.90, 0.0, 0.01, 0.02, 0.15],
            [0.70, 0.10, 0.0, 0.50, 0.40, 0.70],
            [0.05, 0.80, 0.70, 0.0, 0.05, 0.02],
        ]).float().to(device)
        test_probs = model(test_features)
        for i, label in enumerate(['Late Evolution', 'Early Evolution', 'Stagnant']):
            probs = test_probs[i].cpu().numpy()
            print(f'  {label}:')
            for op_name, p in zip(OP_NAMES, probs):
                print(f'    {op_name:30s}: {p:.3f}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--n_samples', type=int, default=5000)
    parser.add_argument('--epochs', type=int, default=200)
    parser.add_argument('--lr', type=float, default=0.001)
    parser.add_argument('--weight_decay', type=float, default=1e-5)
    args = parser.parse_args()
    train(args)
