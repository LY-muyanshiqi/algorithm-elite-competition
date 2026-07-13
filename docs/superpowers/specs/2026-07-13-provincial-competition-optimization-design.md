# 省赛冲刺优化方案 — 智蓄减碳 NSLDE 多目标优化

## 概述

三线并进：对比实验（MATLAB）→ 典型日场景（数据/分析）→ 前端补全（Python/Vue）

---

## 一、NSLDE vs NSGA-II vs MOEA/D 对比实验

### 目标

把前端 `analysis.py` 里的模拟假数据替换为 MATLAB 真实对比实验结果。

### 设计

**新增 MATLAB 文件（3个，放在 `全年抽蓄减碳效益优化计算/`）：**

1. `nsga2_standard.m` — 标准 NSGA-II 实现
   - 与 nslde.m 使用相同的决策变量编码（23维）、目标函数（`evaluate_objective.m`）、约束处理
   - 去除 Lévy 飞行扰动（`genetic_operator.m` 中 child_2 的 Lévy 步长逻辑），保留 SBX+多项式变异
   - 去混沌初始化（`initialize_variables.m` 中用 `rand` 替代 Logistic 混沌映射）
   - 保留 DE/rand/1 差分进化算子 + 快速非支配排序 + 锦标赛选择

2. `moead_standard.m` — 标准 MOEA/D 实现
   - 基于切比雪夫分解的 MOEA/D 算法
   - 与 NSLDE 相同的决策变量编码和目标函数
   - 权重向量生成（simplex-lattice，N=100 个均匀权重）
   - 邻域大小 T=20，交叉变异同标准 DE

3. `compare_algorithms.m` — 对比实验主脚本
   - 对同一数据集运行 NSLDE / NSGA-II / MOEA/D 各 N 天
   - 每算法记录：Pareto 前沿、收敛历史（每 100 代的目标值）、运行时间
   - 计算 HV / IGD / Spacing 指标
   - 输出 `comparison_results.mat` 供 Python 前端加载

**修改 Python 文件：**

4. `data_loader.py` — 新增 `load_comparison_data()` 从 `comparison_results.mat` 加载真实对比结果

5. `v2_features/analysis.py` — 修改 `algorithm_comparison_data()` 优先读取真实数据，文件不存在时降级为模拟数据

### 关键决策

- NSGA-II 通过修改 `nslde.m` 到达（关闭 Lévy + 去掉混沌初始化），而不是从零写完整的 NSGA-II，确保变量编码和目标函数完全一致
- 不需要对全部 365 天运行三个算法——选择有代表性的 3 天（春分/夏至/秋分/冬至各 1 天 + 全年最极端负荷日 1 天 = 5 天），节省计算时间
- 收敛历史每 100 代记录一次，3000 代共 30 个采样点

### 输出文件

- `comparison_results.mat` 结构：
  ```
  z_nslde:  (n_days × 100 × 2) 每天 Pareto 解
  z_nsga2:  (n_days × 100 × 2)
  z_moead:  (n_days × 100 × 2)
  hv:       [n_days × 3]       (三算法)
  igd:      [n_days × 3]
  spacing:  [n_days × 3]
  convergence: struct{nslde, nsga2, moead} 各自 (n_days × n_checkpoints)
  timing:   [n_days × 3]
  days_used: [1×n_days]        选取的天索引
  ```

---

## 二、典型日与极端日场景分析

### 目标

为省赛提供四季典型日 + 极端日的深度对比分析。

### 设计

**新增 MATLAB 文件：**

6. `scenario_extraction.m` — 从 365 天的优化结果中抽取典型日和极端日的数据切片
   - 自动识别：最大负荷日（全年 FH 均值最高日）、最小负荷日、最大风电日、最小风电日、最大光伏日、最大峰谷差日
   - 每年 4 个季度各选 1 个典型日（负荷最接近季度均值日）
   - 每类输出当天的 24 小时详细调度曲线

**修改 Python 文件：**

7. `v2_features/analysis.py` — 新增 `seasonal_comparative_analysis()`
   - 四季对比：四象限图（Spring/Summer/Autumn/Winter 各自的新能源消纳 vs 碳减排）
   - 四季分别的 KPI 汇总表

8. `app.py` — 综合分析报告页新增"四季对比分析"模块
   - 替换现有硬编码的 `before_scores`（1581-1568 行），改为从数据计算的真实优化前后对比
   - 新增极端日调度详情表（6 种极端日的 24h 火电/抽蓄/碳排对比）

9. `config.py` — PAGE_GROUPS 新增"算法对比"页到"高级功能"分组

### 输出

4 张四季对比图 PNG + 4 张极端日分析图（已有 Pareto 四季图，补充调度对比图）

---

## 三、前端展示优化

### 目标

补全前端未完成功能，解决已发现的问题。

### 设计

**10. 历史运行对比页面（新增 Streamlit 页面）**

- 在 `app.py` 新增 `show_history_comparison()` 页面
- 调用 `db.list_runs()` 列出所有历史运行 → 用户点选后调用 `db.load_run_daily()` → 并排对比
- 在 `config.py` PAGE_GROUPS 新增

**11. Vue 前端补全（2 处关键修复）**

- `SchedulingEditor.vue`：将编辑后的抽蓄曲线数据通过 POST `/api/simulate` 发送到后端，后端接收 `Npump` 数组重新计算（目前滑块参数送了但曲线不送）
- `SimulationView.vue`：A/B 对比完成后接入 `db.py` 的保存/加载，用户可保存对比结果并后续加载

**12. 后端新增 History API（2 个端点）**

- `GET /api/history/list` → `db.list_runs()`
- `GET /api/history/load/{run_id}` → `db.load_run_daily(run_id)`

**13. 综合分析报告页改用真实计算**

- 替换 `app.py:1561-1568` 硬编码的 before_scores → 从数据计算真实的"有/无抽蓄"对比
- `data_loader.py` 已有 `F2`（无抽蓄场景）和 `F1`（有抽蓄场景）数据，直接使用

---

## 文件变更总览

| # | 文件 | 操作 |
|---|------|------|
| 1 | `全年抽蓄减碳效益优化计算/nsga2_standard.m` | 新建 |
| 2 | `全年抽蓄减碳效益优化计算/moead_standard.m` | 新建 |
| 3 | `全年抽蓄减碳效益优化计算/compare_algorithms.m` | 新建 |
| 4 | `全年抽蓄减碳效益优化计算/scenario_extraction.m` | 新建 |
| 5 | `前端封装/frontend/data_loader.py` | 修改（+load_comparison_data） |
| 6 | `前端封装/frontend/v2_features/analysis.py` | 修改（真实数据+四季分析） |
| 7 | `前端封装/frontend/app.py` | 修改（历史对比页+真实报告+四季分析） |
| 8 | `前端封装/frontend/config.py` | 修改（加页面分组） |
| 9 | `backend/main.py` | 修改（+history API） |
| 10 | `前端封装/vue-frontend/src/views/SchedulingEditor.vue` | 修改（发送曲线数据） |
| 11 | `前端封装/vue-frontend/src/views/SimulationView.vue` | 修改（接入db） |

## 实施顺序

Phase 1: MATLAB 算法对比（#1-3, #6）
Phase 2: Python 数据层 + 分析更新（#5, #6, #13）
Phase 3: Streamlit 前端（#7, #8, #10）
Phase 4: Vue 前端修复（#11）+ 后端 API（#9）

---

> 设计日期: 2026-07-13 · 赛后冲刺优化
