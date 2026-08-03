# 智蓄减碳

> 第八届全球校园人工智能算法精英大赛 · 算法创新赛参赛项目
>
> 西安理工大学 | 赛道：AI+创新创业 | 赛制：校赛→省赛→总决赛

## 一句话说清楚

在风电光伏大规模并网、火电机组被迫深度调峰的背景下，用 **NSLDE 多目标进化算法** 求解抽水蓄能调度方案——同时压低火电调峰深度和系统碳排放，这两个天然冲突的目标。

## 跑起来

```bash
# MATLAB 核心（365天×24小时优化）
cd thermal-peak-shaving-pumped-storage/thermal-peak-shaving-pumped-storage/全年抽蓄减碳效益优化计算
main

# Python 前端（8页交互可视化）
cd thermal-peak-shaving-pumped-storage/thermal-peak-shaving-pumped-storage/前端封装/frontend
pip install -r requirements.txt
streamlit run app.py
```

浏览器打开 `localhost:8501`，调整装机容量 / 蓄能时长 / 抽发效率，即时看 Pareto 前沿移动。

## 这东西到底干了什么

```
风电出力 ─┐
光伏出力 ─┤
水电出力 ─┼──→ NSLDE优化引擎 ──→ 8760小时调度方案 ──→ 碳减排效益核算
负荷曲线 ─┘        │
                   ├── Pareto前沿（100组非支配解）
                   ├── TOPSIS折中解（推荐方案）
                   └── 8维度可视化报告
```

一句话：**输入四省电网数据，输出"火电少调峰多少、碳减排多少"的最优答案。**

## 核心看点

**算法层面** — 不是套壳 NSGA-II。在标准差分进化上叠加了三个机制：

| 改进点 | 方法 | 解决的问题 |
|--------|------|-----------|
| 混沌初始化 | Logistic 映射 (μ=4) | 种群初始分布更均匀，避免早熟 |
| Lévy 扰动 | Mantegna 算法 (β=1.5) | 跳出局部最优，保持全局搜索能力 |
| 非支配排序 | 快速 NDS + 拥挤距离 | 保证 Pareto 前沿分布质量 |

**工程层面** — 不是纯 MATLAB 脚本：

- 17 个 pytest 测试用例 + GitHub Actions CI（唯一有真测试的项目）
- GitHub Pages 自动部署落地页
- Dev Container 支持，克隆即用
- Blender 3D 抽水蓄能电站建模

**领域层面** — 不是参数玩具：
- 真实区域电网数据：甘肃 / 青海 / 宁夏 / 四川，365天×24小时
- 碳排放核算链完整：煤耗分档 → 碳氧化率 → CO₂分子量比
- 深度调峰三档分类：常规 (>50%) / 中度 (30-50%) / 深度 (<30%)

## 技术栈

MATLAB · Python (Streamlit, NumPy, SciPy) · GitHub Actions · Blender · Docker

## 目录

```
├── 参赛方案书、答辩大纲、任务清单等    ← 算法精英大赛申报材料
├── thermal-peak-shaving-pumped-storage/
│   └── thermal-peak-shaving-pumped-storage/
│       ├── 全年抽蓄减碳效益优化计算/   ← MATLAB NSLDE 核心
│       ├── 前端封装/frontend/          ← Streamlit 平台
│       ├── 建模/                       ← Blender 3D 场景
│       └── backend/                    ← FastAPI 后端
└── backend/                            ← 外层后端服务（FastAPI）
```

## 许可

MIT
