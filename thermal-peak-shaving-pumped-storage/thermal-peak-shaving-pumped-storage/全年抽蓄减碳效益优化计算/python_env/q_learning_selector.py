"""q_learning_selector.py - Q-Learning 自适应算子选择的 numpy 复刻

复刻 q_learning_selector.m。6 维状态离散化(3*5*3*3*3*3=1215) -> Q表(1215x7)
-> ε-greedy 选算子。相比 MATLAB 版，用类封装避免 persistent 状态污染。
"""

import numpy as np

N_BINS = [3, 5, 3, 3, 3, 3]
N_STATES = int(np.prod(N_BINS))
N_ACTIONS = 7


def discretize_state(features, n_bins=N_BINS):
    """6 维特征离散化为状态索引。复刻 discretize_state.m"""
    idx = 0
    stride = 1

    # 特征1: entropy (0-1) -> 3 bins
    feat = min(max(features[0], 0.0), 1.0 - 1e-10)
    bin_ = int(feat * n_bins[0])
    idx += bin_ * stride
    stride *= n_bins[0]

    # 特征2: gen_ratio (0-1) -> 5 bins
    feat = min(max(features[1], 0.0), 1.0 - 1e-10)
    bin_ = int(feat * n_bins[1])
    idx += bin_ * stride
    stride *= n_bins[1]

    # 特征3: stagnation (0-3) -> 3 bins
    feat = min(features[2], 3.0)
    bin_ = int(feat)
    idx += bin_ * stride
    stride *= n_bins[2]

    # 特征4: hv_delta (-1,1) -> 3 bins
    feat = min(max(features[3], -1.0), 1.0)
    bin_ = int((feat + 1.0) * n_bins[3] / 2.0)
    bin_ = min(max(bin_, 0), n_bins[3] - 1)
    idx += bin_ * stride
    stride *= n_bins[3]

    # 特征5: cv_rate (0-1) -> 3 bins
    feat = min(max(features[4], 0.0), 1.0 - 1e-10)
    bin_ = int(feat * n_bins[4])
    idx += bin_ * stride
    stride *= n_bins[4]

    # 特征6: crowd_var (0-1) -> 3 bins
    feat = min(max(features[5], 0.0), 1.0 - 1e-10)
    bin_ = int(feat * n_bins[5])
    idx += bin_ * stride

    return int(idx)


class QLearningSelector:
    """Q-Learning 算子选择器（类封装，避免 persistent 状态污染）"""

    def __init__(self, alpha=0.1, gamma=0.9, seed=42):
        self.q_table = 0.01 * np.random.default_rng(seed).random((N_STATES, N_ACTIONS))
        self.alpha = alpha
        self.gamma = gamma
        self.prev_state = None
        self.prev_action = None
        self.rng = np.random.default_rng(seed)

    def select(self, state, reward=0.0, gen=0, max_gen=3000):
        """选算子，返回 (action, op_probs)。先更新 Q，再 ε-greedy 选"""
        state_idx = discretize_state(state)

        # 更新 Q（上一状态-动作对）
        if self.prev_state is not None and self.prev_action is not None:
            self.q_table[self.prev_state, self.prev_action] += self.alpha * (
                reward + self.gamma * np.max(self.q_table[state_idx, :])
                - self.q_table[self.prev_state, self.prev_action]
            )

        # ε-greedy
        epsilon = max(0.01, 0.3 * (1.0 - gen / max_gen))
        if self.rng.random() < epsilon:
            action = self.rng.integers(N_ACTIONS)
        else:
            action = int(np.argmax(self.q_table[state_idx, :]))

        self.prev_state = state_idx
        self.prev_action = action

        # 输出 7 维概率（选中算子高概率 + 均分保底）
        op_probs = np.full(N_ACTIONS, 0.1 / N_ACTIONS)
        op_probs[action] = 0.9
        op_probs = op_probs / op_probs.sum()
        return action, op_probs

    def reset(self):
        self.prev_state = None
        self.prev_action = None
