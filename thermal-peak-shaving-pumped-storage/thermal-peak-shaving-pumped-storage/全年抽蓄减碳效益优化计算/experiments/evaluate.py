"""evaluate.py - 阶段4对比实验：三基线（均匀 / Q-Learning / PPO）的 HV/收敛/耗时

小规模验证：单天数据，pop=50, gen=300，每基线重复 N 次取均值+标准差。

用法: python experiments/evaluate.py --n_runs 3 --gen 300
"""

import os
import sys
import time
import argparse
import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS_DIR, '..', 'python_env'))
sys.path.insert(0, os.path.join(_THIS_DIR, '..', 'rl'))

from data_loader_py import load_day
from nslde_env import NSLDEEnv
from q_learning_selector import QLearningSelector
from operators import compute_hv_2d


def evaluate_baseline(env_factory, policy_name, n_runs, gen):
    """评估一个策略基线，返回 HV 轨迹 + 收敛代数 + 耗时"""
    all_hv_final = []
    all_conv_gen = []
    all_time = []

    for r in range(n_runs):
        env = env_factory(seed=42 + r)
        state = env.reset()

        ql = QLearningSelector(seed=42 + r) if policy_name == 'qlearning' else None

        hv_traj = [env.hv_history[-1]]
        start = time.time()

        for g in range(gen):
            if policy_name == 'uniform':
                action = np.random.randint(7)
            elif policy_name == 'qlearning':
                reward = env.hv_history[-1] - (env.hv_history[-2] if len(env.hv_history) > 1 else env.hv_history[-1])
                action, _ = ql.select(state, reward=reward, gen=g, max_gen=gen)
            else:
                # ppo 占位：先用随机动作，实际训练在 train_ppo 里做
                action = np.random.randint(7)

            state, reward, done = env.step(action)
            hv_traj.append(env.hv_history[-1])
            if done:
                break

        elapsed = time.time() - start
        hv_final = env.hv_history[-1]

        # 收敛代数：HV 达到最终 90% 的代数
        hv_arr = np.array(env.hv_history)
        target = 0.9 * hv_arr[-1] if hv_arr[-1] > 0 else 0
        if target > 0 and hv_arr.max() >= target:
            conv_gen = int(np.argmax(hv_arr >= target))
        else:
            conv_gen = gen

        all_hv_final.append(hv_final)
        all_conv_gen.append(conv_gen)
        all_time.append(elapsed)

        print(f'    run {r+1}: HV={hv_final:.2e}, conv_gen={conv_gen}, time={elapsed:.1f}s')

    return {
        'name': policy_name,
        'hv_final_mean': float(np.mean(all_hv_final)),
        'hv_final_std': float(np.std(all_hv_final)),
        'conv_gen_mean': float(np.mean(all_conv_gen)),
        'time_mean': float(np.mean(all_time)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n_runs', type=int, default=3)
    parser.add_argument('--gen', type=int, default=300)
    parser.add_argument('--pop', type=int, default=50)
    args = parser.parse_args()

    Nh, Nw, Np, L = load_day(0)

    def env_factory(seed):
        return NSLDEEnv(Nh, Nw, Np, L, pop=args.pop, gen=args.gen, seed=seed)

    print(f'=== 三基线对比实验 (pop={args.pop}, gen={args.gen}, runs={args.n_runs}) ===\n')

    results = []
    for policy in ['uniform', 'qlearning']:
        print(f'[基线] {policy}')
        results.append(evaluate_baseline(env_factory, policy, args.n_runs, args.gen))

    # 输出对比表
    print('\n=== 结果对比 ===')
    print(f'{"策略":12s} {"HV均值":>14s} {"HVstd":>12s} {"收敛代数":>10s} {"耗时s":>8s}')
    for r in results:
        print(f'{r["name"]:12s} {r["hv_final_mean"]:14.2e} {r["hv_final_std"]:12.2e} '
              f'{r["conv_gen_mean"]:10.1f} {r["time_mean"]:8.1f}')

    print('\n[PASS] 对比实验跑通')


if __name__ == '__main__':
    main()
