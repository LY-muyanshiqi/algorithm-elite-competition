"""config.py - 超参数 + 编码器开关"""

from dataclasses import dataclass, field


@dataclass
class Config:
    # 编码器
    encoder_type: str = 'gnn'  # 'gnn' | 'mlp' | 'transformer'
    embed_dim: int = 128

    # 环境
    pop: int = 100
    gen: int = 100  # 本轮简化环境用较少代数验证
    day_idx: int = 0
    Zpump: float = 1400.0
    h: float = 4.0

    # 算子（7 个）
    n_actions: int = 7

    # PPO 超参
    lr: float = 3e-4
    gamma: float = 0.99
    lam: float = 0.95  # GAE lambda
    clip_epsilon: float = 0.2
    value_coef: float = 0.5
    entropy_coef: float = 0.01
    ppo_epochs: int = 4
    batch_size: int = 64
    max_steps: int = 2048

    # 行为克隆
    bc_epochs: int = 20
    bc_lr: float = 1e-3

    # 离线数据
    n_trajectories: int = 10
    offline_dir: str = 'offline_data/trajectories'

    seed: int = 42
    device: str = 'cpu'


def get_config(**overrides):
    cfg = Config()
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg
