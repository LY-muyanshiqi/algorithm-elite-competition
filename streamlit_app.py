"""
Streamlit Cloud 部署入口
抽水蓄能减碳效益优化核算系统
"""

import sys
import os

_frontend_dir = os.path.join(os.path.dirname(__file__), "thermal-peak-shaving-pumped-storage", "thermal-peak-shaving-pumped-storage", "前端封装", "frontend")
sys.path.insert(0, _frontend_dir)
os.chdir(_frontend_dir)

# 读取 app.py 并用 streamlit 的 bootstrap 方式执行
with open(os.path.join(_frontend_dir, "app.py"), encoding="utf-8") as f:
    code = f.read()

exec(compile(code, os.path.join(_frontend_dir, "app.py"), "exec"))
