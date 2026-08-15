"""train_ppo.py - 端到端 PPO 训练验证脚本（阶段2验收）

跑通: 简化环境 → 状态→图 → 策略网络 → 动作 → 奖励 → PPO 更新
"""

import os
import sys
import numpy as np
import torch

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
sys.path.insert(0, os.path.join(_THIS_DIR, '..', 'rl'))
sys.path.insert(0, os.path.join(_THIS_DIR, '..', 'python_env'))

from graph_builder import build_graph
from actor_critic import ActorCritic
from ppo_trainer import PPOBuffer, PPOTrainer
from simple_env import SimpleNSLDEEnv
from data_loader_py import load_day
from config import get_config


def state_to_graph(env, state):
    """环境状态 → 图输入。用环境的电源数据和 6 维标量构建图"""
    # 简单起见，用净功率计算一个近似的 Npump/Nt
    Nh = env.Nh
    Nw = env.Nw
    Np = env.Np
    L = env.L
    Npump = np.zeros(24)
    Nt = L - (Nh + Nw + Np + Npump)
    return build_graph(Nh, Nw, Np, Npump, Nt, L, env.Zpump, state)


def main():
    cfg = get_config(encoder_type='mlp', gen=50, pop=30, device='cpu')
    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)

    Nh, Nw, Np, L = load_day(cfg.day_idx)
    env = SimpleNSLDEEnv(Nh, Nw, Np, L, Zpump=cfg.Zpump, h=cfg.h, pop=cfg.pop, gen=cfg.gen)

    model = ActorCritic(encoder_type=cfg.encoder_type)
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    trainer = PPOTrainer(model, optimizer, cfg)

    print(f'编码器: {cfg.encoder_type}，pop={cfg.pop}，gen={cfg.gen}')
    print('开始 PPO 训练...')

    n_episodes = 5
    for ep in range(n_episodes):
        state = env.reset()
        buffer = PPOBuffer()
        ep_reward = 0.0

        for t in range(cfg.gen):
            data = state_to_graph(env, state)
            logits, value = model(data)
            from torch.distributions import Categorical
            dist = Categorical(logits=logits)
            action = dist.sample()
            log_prob = dist.log_prob(action)

            state, reward, done = env.step(action.item())

            buffer.add(data, action.item(), reward, log_prob, value.item(), done)
            ep_reward += reward

            if done:
                break

        loss = trainer.train_one_batch(buffer)
        print(f'  Episode {ep+1}: reward={ep_reward:.4f}, loss={loss:.4f}')

    # 最终策略检查
    data = state_to_graph(env, env.reset())
    logits, _ = model(data)
    probs = torch.softmax(logits, dim=-1).detach().numpy()
    print('\n最终算子选择概率分布:')
    op_names = ['DE/rand/1', 'DE/rand/2', 'DE/c-to-b/1', 'PM', 'SBX', 'Levy', 'Cauchy']
    for i, name in enumerate(op_names):
        print(f'  {name:20s}: {probs[i]:.4f}')

    print('\n[PASS] PPO 训练循环跑通')


if __name__ == '__main__':
    main()
