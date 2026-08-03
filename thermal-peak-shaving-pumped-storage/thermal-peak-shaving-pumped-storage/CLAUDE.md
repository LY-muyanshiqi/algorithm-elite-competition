# CLAUDE.md — thermal-peak-shaving-pumped-storage：火电调峰抽蓄优化

## 项目简介
基于 NSLDE 多目标优化算法的火电深度调峰与抽水蓄能协同调度系统。MATLAB 算法核心 + Python Streamlit 前端。全仓库中工程化最成熟的项目。

## 技术栈
- MATLAB：NSLDE 多目标优化算法核心
- Python 3.8+：Streamlit 前端 + pytest 测试
- CI/CD：GitHub Actions (pytest + deploy to GitHub Pages)
- Dev：GitHub Codespaces (devcontainer.json)

## 项目结构
```
全年抽蓄减碳效益优化计算/   # MATLAB 核心算法
├── main.m / nslde.m / evaluate_objective.m / process.m
前端封装/frontend/          # Python Streamlit 前端
├── app.py / config.py / data_loader.py / test_data_loader.py
```

## 关键术语
- **NSLDE**: 新型多目标差分进化算法 (Novel Multi-Objective Differential Evolution)
- **深度调峰**: 火电机组大幅降低出力以消纳新能源
- **抽水蓄能**: 利用电力系统低谷电能抽水，高峰时发电的储能方式
- **多目标优化**: 同时优化经济效益和碳减排效益

## 开发命令
```bash
# MATLAB
matlab -r "run('全年抽蓄减碳效益优化计算/main.m')"

# Python
cd 前端封装/frontend
pip install -r requirements.txt
pytest test_data_loader.py -v --tb=short
streamlit run app.py
```

## 注意事项
- 这是唯一有真正常测试套件的仓库 (17 个 pytest 测试)
- 唯一有完整 CI/CD 的仓库 (测试执行 + GitHub Pages 部署)
- .claude/ 在 .gitignore 中，如需项目级 AI 配置请取消忽略
