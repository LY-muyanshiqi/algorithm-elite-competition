# 新型电力系统下抽水蓄能减碳效益优化核算系统

基于 NSLDE 多目标优化算法的火电深度调峰与抽水蓄能协同调度系统，用于评估和优化电力系统的碳减排效益。

[![Run Tests](https://github.com/LY-muyanshiqi/thermal-peak-shaving-pumped-storage/actions/workflows/test.yml/badge.svg)](https://github.com/LY-muyanshiqi/thermal-peak-shaving-pumped-storage/actions/workflows/test.yml)

## 项目结构

```
├── 全年抽蓄减碳效益优化计算/   # MATLAB 优化算法核心
│   ├── main.m                  # 主程序入口
│   ├── nslde.m                 # NSLDE 多目标优化算法
│   ├── evaluate_objective.m    # 目标函数评估
│   ├── process.m               # 抽蓄功率后处理
│   └── *.txt                   # 输入数据 (365×24)
│
├── 前端封装/frontend/          # Python Streamlit 前端
│   ├── app.py                  # 应用主入口
│   ├── config.py               # 集中配置 (参数预设、页面定义)
│   ├── data_loader.py          # 数据加载与计算
│   ├── charts.py               # 图表绘制模块
│   ├── report.py               # 综合报告导出
│   ├── styles.py               # CSS 样式
│   ├── v2_features/            # 高级功能 (可视化/分析)
│   ├── static/images/          # 静态图片资源
│   ├── requirements.txt        # Python 依赖
│   └── test_data_loader.py     # 单元测试 (pytest)
│
├── 建模/                       # Blender 3D 场景建模
├── .github/workflows/          # CI/CD
│   ├── test.yml                # 自动测试
│   └── deploy-frontend.yml     # GitHub Pages 部署
└── README.md
```

## 主要功能

- **多目标优化**：最小化火电调峰深度 & 最小化系统碳排放
- **NSLDE 算法**：基于非支配排序的差分进化，含 Lévy 飞行扰动
- **抽水蓄能调度**：365 天 × 24 小时精细调度策略可视化
- **高级分析**：敏感性分析、情景模拟、决策建议、统计分析
- **A/B 参数对比**：多方案并行计算与指标对比
- **交互式图表**：Plotly 驱动的桑基图、Pareto 前沿、3D 可视化

## 快速开始

### 1. 运行 MATLAB 优化

```matlab
cd('全年抽蓄减碳效益优化计算')
main
```

### 2. 启动 Python 前端

```bash
cd 前端封装/frontend
pip install -r requirements.txt
streamlit run app.py
```

浏览器打开 http://localhost:8501

### 3. 运行测试

```bash
cd 前端封装/frontend
python -m pytest test_data_loader.py -v
```

## 部署

- **Streamlit Cloud**：推送代码后自动部署
- **GitHub Pages**：自动部署项目落地页 [访问](https://LY-muyanshiqi.github.io/thermal-peak-shaving-pumped-storage/)
- **Dev Container**：支持 GitHub Codespaces 一键开发环境

## 技术参数

| 参数 | 默认值 |
|------|--------|
| 抽水蓄能装机容量 | 1400 MW |
| 蓄能时长 | 4 h |
| 抽发效率 | 75% |
| Pareto 解数量 | 100 |
| 碳排放系数 | 0.5 吨CO₂/万kWh |
| 数据粒度 | 365天 × 24小时 = 8760点 |

## 许可证

MIT License

## 更新日期

2026-05-18
