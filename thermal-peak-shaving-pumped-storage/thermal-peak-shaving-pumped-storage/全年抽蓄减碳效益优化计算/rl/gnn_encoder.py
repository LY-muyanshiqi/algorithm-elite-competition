"""gnn_encoder.py - 三种编码器: GNN / MLP / Transformer

统一接口 encode() -> graph_embedding (128 维)，通过 config 切换。
三者共享 ActorCritic 输出头（Actor 7 维 + Critic 1 维）。
"""

import torch
import torch.nn as nn
from torch_geometric.nn import SAGEConv, global_mean_pool, global_max_pool

EMBED_DIM = 128


class GNNEncoder(nn.Module):
    """同构图编码器：29 节点(5电源+24时段)，SAGE 消息传递 + readout"""

    def __init__(self, node_dim=8, hidden=64, embed_dim=EMBED_DIM, scalar_dim=6):
        super().__init__()
        self.conv1 = SAGEConv(node_dim, hidden)
        self.conv2 = SAGEConv(hidden, hidden)

        self.readout = nn.Sequential(
            nn.Linear(hidden * 2 + scalar_dim, embed_dim),
            nn.ReLU(),
            nn.Linear(embed_dim, embed_dim),
        )

    def forward(self, data):
        x, edge_index = data.x, data.edge_index

        x = self.conv1(x, edge_index)
        x = torch.relu(x)
        x = self.conv2(x, edge_index)
        x = torch.relu(x)

        # 图级 readout: 节点 mean + max
        pooled = torch.cat([x.mean(dim=0), x.max(dim=0)[0]], dim=0)
        u = data.u.squeeze(0)

        concat = torch.cat([pooled, u], dim=0)
        return self.readout(concat)


class MLPEncoder(nn.Module):
    """仅用 6 维标量特征的 MLP baseline（复用 operator_selector.py 的结构: 6->32->64->32）"""

    def __init__(self, scalar_dim=6, embed_dim=EMBED_DIM):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(scalar_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, embed_dim),
        )

    def forward(self, data):
        u = data.u.squeeze(0)  # (scalar_dim,)
        return self.mlp(u)


class TransformerEncoder(nn.Module):
    """29 节点(5电源+24时段)当 29 token，自注意力建模全局交互"""

    def __init__(self, node_dim=8, d_model=64, nhead=4, n_layers=2, embed_dim=EMBED_DIM, scalar_dim=6):
        super().__init__()
        self.node_proj = nn.Linear(node_dim, d_model)
        n_nodes = 5 + 24
        self.pos = nn.Parameter(torch.randn(1, n_nodes, d_model))

        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)

        self.readout = nn.Sequential(
            nn.Linear(d_model + scalar_dim, embed_dim),
            nn.ReLU(),
            nn.Linear(embed_dim, embed_dim),
        )

    def forward(self, data):
        x = self.node_proj(data.x)  # (29, d_model)
        tokens = x.unsqueeze(0)  # (1, 29, d_model)
        tokens = tokens + self.pos[:, :tokens.shape[1], :]
        out = self.transformer(tokens).squeeze(0)  # (29, d_model)
        pooled = out.mean(dim=0)  # (d_model,)
        u = data.u.squeeze(0)
        return self.readout(torch.cat([pooled, u], dim=0))
