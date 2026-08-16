# 全年抽蓄减碳效益优化计算

NSLDE 多目标优化算法的核心计算模块，包含 MATLAB 实现与 Python 深度学习环境两套。

## 一、目录结构

```
全年抽蓄减碳效益优化计算/
├── *.m                          # MATLAB 核心算法（NSLDE + 对比算法 + 实验）
├── *.txt                        # 输入数据（365天×24小时）
├── python_env/                  # Python 环境（numpy 复刻 MATLAB，用于 RL 训练）
│   ├── evaluate_objective.py    # 目标函数复刻（含 pchip 连续化碳排放）
│   ├── operators.py             # NSGA-II 核心算子（非支配排序/锦标赛/精英保留）
│   ├── genetic_operators.py     # 7 个遗传算子
│   ├── nslde_env.py             # 完整 NSLDE gym-like 环境
│   ├── q_learning_selector.py   # Q-Learning 自适应算子选择（numpy 版）
│   ├── state_features.py        # 6 维状态特征
│   └── data_loader_py.py        # 单日数据加载
├── rl/                          # 深度学习框架（路线 B）
│   ├── graph_builder.py         # 种群状态 → 图结构
│   ├── gnn_encoder.py           # GNN/MLP/Transformer 三编码器
│   ├── actor_critic.py          # Actor(7算子) + Critic(1价值) 输出头
│   ├── ppo_trainer.py           # PPO 训练器
│   ├── simple_env.py            # 简化环境（阶段2验证）;
│   └── config.py                # 超参配置
├── experiments/                 # 实验脚本
│   ├── train_ppo.py             # PPO 训练（简化环境）
│   ├── train_ppo_full.py        # PPO 训练（完整环境，可行性验证）
│   └── evaluate.py              # 三基线对比（均匀/Q-Learning/PPO）
├── tests/                       # 对拍测试
│   ├── test_objective_parity.py # 目标函数 MATLAB 对拍
│   └── test_operators_parity.py # 非支配排序 MATLAB 对拍
└── math_proofs/                 # 数学推导
    └── nslde_mathematical_basis.md
```

## 二、MATLAB 核心算法

### NSLDE 主框架
- `nslde.m` / `nslde_enhanced.m` — NSLDE 基础版 / 增强版（多算子 + 历史记录）
- `genetic_operator.m` / `genetic_operator_multi.m` — 单算子 / 多算子遗传操作
- `q_learning_selector.m` — Q-Learning 自适应算子选择（MATLAB 原生，路线 A）
- `initialize_variables.m` / `initialize_variables_multi.m` — 单/多策略初始化
- `compromise_solution.m` / `compromise_solution_enhanced.m` — 折中解选择（min-max / TOPSIS+VIKOR+GRA）

### 对比算法
- `nsga2_standard.m` / `nsga3_standard.m` — NSGA-II / NSGA-III
- `moead_standard.m` / `moead_de.m` — MOEA/D / MOEA/D-DE

### 实验与验证
- `run_ablation.m` — 消融实验 MATLAB 入口
- `compare_algorithms.m` — 多算法对比
- `experiment_runner.py` — Python 实验自动化 + 统计分析
- `verify_chaos_uniformity.m` / `verify_levy_jump.m` — 混沌/Lévy 验证
- `decision_sensitivity.m` — 决策变量敏感性分析

## 三、Python 深度学习环境（路线 B，经验证收益弱，代码留存）

> 注：路线 A（Q-Learning）和路线 B（GNN+PPO）两个"自适应算子选择"方向，
> 经严谨实验验证均无显著收益（详见外层 `NSLDE算法方向探索结论.md`）。
> 该环境的 numpy 复刻部分（对拍验证）仍有价值，深度学习框架作为探索记录留存。

### 路线 A vs 路线 B

| | 路线 A（已验证） | 路线 B（已验证） |
|---|---|---|
| 自适应方式 | Q-Learning（Q 表） | GNN + PPO 策略网络 |
| 实现语言 | MATLAB 原生 | Python + PyTorch + PyG |
| 状态空间 | 6 维特征离散化 | 图结构 + 6 维标量 |
| 训练 | 在线 ε-greedy | 离线 RL（BC + PPO） |
| 验证结论 | 与固定策略无显著差异(p=0.31) | reward 仅升 3%，MLP≈GNN |

### Python 环境的用途

`python_env/` 用 numpy 精确复刻了 MATLAB 的目标函数和核心算子（经对拍验证），
目的是让 PPO 训练能**高频调用目标函数**（PPO 训练需要几十万次评估，不能走
MATLAB 子进程）。

### 对拍验证

Python 复刻通过两个测试脚本与 MATLAB 对齐：
```bash
cd 全年抽蓄减碳效益优化计算
python tests/test_objective_parity.py    # 目标函数对拍（f1差0, f2差1e-7）
python tests/test_operators_parity.py    # 非支配排序对拍（rank/crowding一致）
```

### 编码器对比

三种编码器（统一接口 `encode(图) -> 128维嵌入`）：
- **GNN**（SAGEConv）：图结构归纳偏置
- **MLP**：6 维标量 baseline
- **Transformer**：29 节点自注意力

## 四、运行

### MATLAB 主程序
```matlab
cd('全年抽蓄减碳效益优化计算')
main
```

### Python 对拍测试
```bash
python tests/test_objective_parity.py
python tests/test_operators_parity.py
```

### PPO 训练（可行性验证）
```bash
python experiments/train_ppo_full.py
```

### 三基线对比
```bash
python experiments/evaluate.py --n_runs 3 --gen 300
```

## 五、依赖

- MATLAB R2024b（生成对拍参考值）
- Python 3.8+，依赖：
  - numpy / scipy（目标函数复刻）
  - torch 2.7+（深度学习）
  - torch-geometric（GNN 编码器）
