"""ppo_trainer.py - 标准 PPO 训练循环

支持给定环境的 on-policy 训练，也支持离线 buffer 的 behavior cloning 训练。
"""

import torch
import torch.nn as nn
import numpy as np
from torch.distributions import Categorical


class PPOBuffer:
    """存储一集 rollout 的 (s, a, r, log_prob, value)"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.states = []
        self.actions = []
        self.rewards = []
        self.log_probs = []
        self.values = []
        self.dones = []

    def add(self, state, action, reward, log_prob, value, done):
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.log_probs.append(log_prob)
        self.values.append(value)
        self.dones.append(done)

    def size(self):
        return len(self.actions)


def compute_gae(rewards, values, dones, gamma, lam):
    """GAE 优势估计"""
    advantages = np.zeros_like(rewards, dtype=np.float32)
    gae = 0.0
    for t in reversed(range(len(rewards))):
        if t == len(rewards) - 1:
            next_value = 0.0
        else:
            next_value = values[t + 1] * (1 - dones[t + 1])
        delta = rewards[t] + gamma * next_value - values[t]
        gae = delta + gamma * lam * (1 - dones[t]) * gae
        advantages[t] = gae
    returns = advantages + values
    return advantages, returns


class PPOTrainer:
    """PPO 训练器"""

    def __init__(self, model, optimizer, config):
        self.model = model
        self.optimizer = optimizer
        self.config = config

    def train_one_batch(self, buffer):
        """在一个 rollout buffer 上做 PPO 更新"""
        # reward 归一化（稳定训练的关键）
        rewards = np.array(buffer.rewards, dtype=np.float32)
        rewards = np.clip(rewards, -10.0, 10.0)  # clip 极端值
        buffer.rewards = rewards

        advantages, returns = compute_gae(
            buffer.rewards, buffer.values, buffer.dones,
            self.config.gamma, self.config.lam,
        )
        advantages = torch.tensor(advantages, dtype=torch.float32)
        returns = torch.tensor(returns, dtype=torch.float32)

        old_log_probs = torch.stack(buffer.log_probs).detach()
        old_actions = torch.tensor(buffer.actions, dtype=torch.long)

        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        returns = (returns - returns.mean()) / (returns.std() + 1e-8)

        total_loss = 0.0
        count = 0
        for _ in range(self.config.ppo_epochs):
            for i in range(len(buffer.states)):
                data = buffer.states[i]
                logits, value = self.model(data)
                dist = Categorical(logits=logits)
                new_log_prob = dist.log_prob(old_actions[i])
                entropy = dist.entropy()

                ratio = torch.exp(new_log_prob - old_log_probs[i])
                surr1 = ratio * advantages[i]
                surr2 = torch.clamp(ratio, 1 - self.config.clip_epsilon, 1 + self.config.clip_epsilon) * advantages[i]
                actor_loss = -torch.min(surr1, surr2)

                critic_loss = (returns[i] - value) ** 2

                loss = actor_loss + self.config.value_coef * critic_loss - self.config.entropy_coef * entropy
                total_loss += loss.item()
                count += 1

                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 0.5)
                self.optimizer.step()

        buffer.reset()
        return total_loss / max(count, 1)
