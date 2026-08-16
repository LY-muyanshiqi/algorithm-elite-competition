"""train_ppo_full.py - 可行性验证：PPO 在完整 NSLDE 环境上训练

判断 PPO 能否学到"选哪个算子提升 HV"。
完整环境 NSLDEEnv + 状态→图 + 策略网络 + PPO。

成功标准: 训练后策略的 HV 高于均匀随机基线，且 reward 随 episode 上升。
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
from nslde_env import NSLDEEnv
from data_loader_py import load_day
from config import get_config


def state_to_graph(env, state):
    """完整环境状态 → 图输入。用种群信息计算近似的电源时序功率"""
    # 从当前种群提取信息：用当前最优解的决策变量反推 Npump/Nt
    pop_sorted = env.pop_sorted
    # 取 rank=1 的个体（或第一个）作为代表解
    best_idx = np.argmin(pop_sorted[:, env.V + env.M])  # rank 最小
    best_x = pop_sorted[best_idx, :env.V]

    # 复刻 evaluate_objective 的 Npump 计算来得到电源功率
    from evaluate_objective import evaluate_objective_np
    V_phys = env.Zpump * env.h
    N = env.Nh + env.Nw + env.Np
    C = np.empty(25)
    C[0] = 0.5
    C[24] = 0.5
    C[1:24] = best_x[:23]
    Npump = np.zeros(24)
    for i in range(24):
        if C[i+1] <= C[i]:
            Npump[i] = (C[i] - C[i+1]) * V_phys
            if Npump[i] < env.Zpump * 0.2:
                Npump[i] = 0.0
                C[i+1] = C[i]
            if Npump[i] > env.Zpump:
                Npump[i] = env.Zpump
                C[i+1] = C[i] - Npump[i] / V_phys
        if C[i+1] > C[i]:
            Npump[i] = (C[i] - C[i+1]) * V_phys / 0.75
            if Npump[i] > -env.Zpump * 0.2:
                Npump[i] = 0.0
                C[i+1] = C[i]
            if Npump[i] < -env.Zpump:
                Npump[i] = -env.Zpump
                C[i+1] = C[i] - Npump[i] * 0.75 / V_phys
    Nt = env.L - (N + Npump)

    return build_graph(env.Nh, env.Nw, env.Np, Npump, Nt, env.L, env.Zpump, state)


def run_train(encoder_type='mlp', n_episodes=20, gen=500, pop=50, day_idx=0):
    cfg = get_config(encoder_type=encoder_type, gen=gen, pop=pop, device='cpu')
    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)

    Nh, Nw, Np, L = load_day(day_idx)
    env = NSLDEEnv(Nh, Nw, Np, L, Zpump=cfg.Zpump, h=cfg.h, pop=pop, gen=gen, seed=cfg.seed)

    model = ActorCritic(encoder_type=encoder_type)
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    trainer = PPOTrainer(model, optimizer, cfg)

    print(f'编码器={encoder_type}, pop={pop}, gen={gen}, episodes={n_episodes}')
    print('训练中...\n')

    ep_rewards = []
    for ep in range(n_episodes):
        state = env.reset()
        buffer = PPOBuffer()
        ep_reward = 0.0

        for t in range(gen):
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
        final_hv = env.hv_history[-1]
        ep_rewards.append(ep_reward)

        # 每 10 episode 打印进度（含分阶段均值）
        if (ep + 1) % 10 == 0 or ep == 0:
            seg_mean = np.mean(ep_rewards[max(0, ep-9):ep+1])
            print(f'  ep {ep+1:3d}: reward={ep_reward:+8.4f}, HV={final_hv:.2e}, '
                  f'近10均值={seg_mean:+.4f}', flush=True)

    return ep_rewards, env


def main():
    ep_rewards, env = run_train(encoder_type='mlp', n_episodes=20, gen=500, pop=50)

    print('\n=== 可行性判断 ===')
    first5 = np.mean(ep_rewards[:5])
    last5 = np.mean(ep_rewards[-5:])
    print(f'  前5 episode 平均 reward: {first5:+.4f}')
    print(f'  后5 episode 平均 reward: {last5:+.4f}')
    if last5 > first5:
        print('  [倾向可行] reward 随训练上升，PPO 可能在学到东西')
    else:
        print('  [需警惕] reward 未上升，PPO 没学到有效策略，需调参或换 reward')


if __name__ == '__main__':
    main()
