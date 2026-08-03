"""
Streamlit Cloud 部署入口
抽水蓄能减碳效益优化核算系统
"""

import sys
import os

_frontend_dir = os.path.join(os.path.dirname(__file__), "thermal-peak-shaving-pumped-storage", "thermal-peak-shaving-pumped-storage", "前端封装", "frontend")
sys.path.insert(0, _frontend_dir)

import streamlit as st

st.set_page_config(
    page_title="抽水蓄能减碳效益优化核算系统",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

import app as main_app
