"""actor_critic.py - 共享 ActorCritic 输出头 + 编码器工厂

Actor: 7 维算子选择概率（Categorical 分布）
Critic: 1 维状态价值
"""

import torch
import torch.nn as nn

from gnn_encoder import GNNEncoder, MLPEncoder, TransformerEncoder, EMBED_DIM

N_ACTIONS = 7


class ActorCritic(nn.Module):
    """编码器 + Actor 头 + Critic 头"""

    def __init__(self, encoder_type='gnn', **encoder_kwargs):
        super().__init__()
        if encoder_type == 'gnn':
            self.encoder = GNNEncoder(**encoder_kwargs)
        elif encoder_type == 'mlp':
            self.encoder = MLPEncoder(**encoder_kwargs)
        elif encoder_type == 'transformer':
            self.encoder = TransformerEncoder(**encoder_kwargs)
        else:
            raise ValueError(f"unknown encoder_type: {encoder_type}")

        self.actor = nn.Linear(EMBED_DIM, N_ACTIONS)
        self.critic = nn.Linear(EMBED_DIM, 1)

    def forward(self, data):
        embed = self.encoder(data)
        logits = self.actor(embed)
        value = self.critic(embed)
        return logits, value


def get_action(logits):
    """从 logits 采样动作，返回 (action, log_prob)"""
    dist = torch.distributions.Categorical(logits=logits)
    action = dist.sample()
    log_prob = dist.log_prob(action)
    return action, log_prob


def get_action_probs(logits):
    """返回 7 维概率向量（用于算子选择）"""
    return torch.softmax(logits, dim=-1)
