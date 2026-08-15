# 全年抽蓄减碳效益优化计算

NSLDE 多目标优化算法的 MATLAB 核心实现。

## 文件说明

### 核心算法
- `nslde.m` / `nslde_enhanced.m` — NSLDE 主框架（基础版 / 增强版）
- `genetic_operator.m` / `genetic_operator_multi.m` — 单算子 / 多算子遗传操作
- `q_learning_selector.m` — Q-Learning 自适应算子选择（当前已接入的自适应方案）
- `initialize_variables.m` / `initialize_variables_multi.m` — 单 / 多策略初始化
- `compromise_solution.m` / `compromise_solution_enhanced.m` — 折中解选择（min-max / TOPSIS+VIKOR+GRA）

### 实验框架
- `run_ablation.m` — 消融实验 MATLAB 入口
- `experiment_runner.py` — Python 实验自动化与统计分析
- `compare_algorithms.m` — 多算法对比（NSLDE/NSGA-II/NSGA-III/MOEA/D/MOEA/D-DE）

### 对比算法
- `nsga2_standard.m` / `nsga3_standard.m` — NSGA-II / NSGA-III
- `moead_standard.m` / `moead_de.m` — MOEA/D / MOEA/D-DE

### 验证脚本
- `verify_chaos_uniformity.m` — Logistic 混沌映射均匀性验证
- `verify_levy_jump.m` — Lévy 飞行跳跃特性验证
- `decision_sensitivity.m` — 决策变量敏感性分析

### 数学依据
- `math_proofs/nslde_mathematical_basis.md` — 混沌 / DE / Lévy 数学推导

## 关于 OSN（Operator Selection Network）

原先规划用 PyTorch 神经网络（`operator_selector.py`）做算子自适应选择，相关文件
`operator_selector.py`、`train_osn.py`、`osn_model.pt` 已删除。

**当前采用 MATLAB 原生的 Q-Learning 方案**（`q_learning_selector.m`），状态空间
6 维特征 + 7 动作算子，无需跨语言调用。OSN 深度学习方案作为论文"未来工作展望"方向，
如需恢复可查看 git 历史（提交 `131d153`）。
