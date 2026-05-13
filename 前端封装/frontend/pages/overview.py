"""
系统总览页面模块
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def show_dashboard(data, selected_days=None):
    """显示总览仪表盘"""
    st.title("🏠 总览仪表盘")
    
    stats = calculate_basic_stats(data)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("🌬️ 风电总量", f"{stats['total_wind']:.2f}亿kWh")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("☀️ 光伏总量", f"{stats['total_solar']:.2f}亿kWh")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("💧 水电总量", f"{stats['total_hydro']:.2f}亿kWh")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("🔥 火电总量", f"{stats['total_fh']:.2f}亿kWh")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    fig = make_subplots(rows=2, cols=1, subplot_titles=("全年新能源发电曲线", "抽水蓄能功率分布"))
    
    hours = np.arange(8760)
    wind_flat = data['wind'].flatten()[:8760]
    solar_flat = data['solar'].flatten()[:8760]
    hydro_flat = data['hydro'].flatten()[:8760]
    
    fig.add_trace(go.Scatter(x=hours, y=wind_flat, name='风电', fill='tozeroy', fillcolor='rgba(0, 200, 255, 0.3)'), row=1, col=1)
    fig.add_trace(go.Scatter(x=hours, y=solar_flat, name='光伏', fill='tonexty', fillcolor='rgba(255, 180, 0, 0.3)'), row=1, col=1)
    fig.add_trace(go.Scatter(x=hours, y=hydro_flat, name='水电', fill='tonexty', fillcolor='rgba(0, 255, 136, 0.3)'), row=1, col=1)
    
    fig.add_trace(go.Histogram(x=data['np_raw'].flatten(), name='蓄能功率', nbinsx=50), row=2, col=1)
    
    fig.update_layout(height=800, template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)


def show_overview_v2(data):
    """显示系统总览（高级版）"""
    st.title("📊 系统总览")
    
    stats = calculate_basic_stats(data)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown(f"<div style='font-size: 2rem;'>🌿</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size: 1.5rem; color: #00d4ff;'>{stats['total_renewable']:.2f}亿kWh</div>", unsafe_allow_html=True)
        st.markdown("<div style='color: #8ba4c4;'>新能源合计</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown(f"<div style='font-size: 2rem;'>⚡</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size: 1.5rem; color: #00ff88;'>{stats['renewable_ratio']:.1f}%</div>", unsafe_allow_html=True)
        st.markdown("<div style='color: #8ba4c4;'>新能源占比</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown(f"<div style='font-size: 2rem;'>🔄</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size: 1.5rem; color: #ffcc00;'>{stats['pump_hours']}小时</div>", unsafe_allow_html=True)
        st.markdown("<div style='color: #8ba4c4;'>抽水时长</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    fig_pareto = go.Figure()
    fig_pareto.add_trace(go.Scatter(
        x=data['z_gain'][:, 0],
        y=data['z_gain'][:, 1],
        mode='markers',
        marker=dict(size=10, color=np.arange(len(data['z_gain'])), colorscale='Viridis', showscale=True),
        name='Pareto最优解'
    ))
    fig_pareto.update_layout(
        title='Pareto最优前沿',
        height=500,
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_pareto, use_container_width=True)


def calculate_basic_stats(data):
    """计算基础统计数据"""
    return {
        'total_wind': np.sum(data['wind']) / 10000,
        'total_solar': np.sum(data['solar']) / 10000,
        'total_hydro': np.sum(data['hydro']) / 10000,
        'total_fh': np.sum(data['fh']) / 10000,
        'total_renewable': (np.sum(data['wind']) + np.sum(data['solar']) + np.sum(data['hydro'])) / 10000,
        'renewable_ratio': (np.sum(data['wind']) + np.sum(data['solar']) + np.sum(data['hydro'])) / 
                          (np.sum(data['wind']) + np.sum(data['solar']) + np.sum(data['hydro']) + np.sum(data['fh'])) * 100,
        'pump_hours': int((data['np_raw'] < 0).sum()),
        'gen_hours': int((data['np_raw'] > 0).sum())
    }