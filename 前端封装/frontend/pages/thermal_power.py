"""
火电调峰效果页面模块
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go


def show_thermal_power(data):
    """显示火电调峰效果页面"""
    st.title("🔥 火电调峰效果分析")
    
    # 全年对比
    st.subheader("全年火电出力对比")
    nt_flat = data['Nt'].flatten()[:8760]
    nt2_flat = data['Nt2'].flatten()[:8760]
    
    fig_year = go.Figure()
    fig_year.add_trace(go.Scatter(
        x=np.arange(8760),
        y=nt_flat,
        name='优化后火电出力',
        line_color='#00d4ff',
        opacity=0.8
    ))
    fig_year.add_trace(go.Scatter(
        x=np.arange(8760),
        y=nt2_flat,
        name='优化前火电出力',
        line_color='#ff6b6b',
        opacity=0.6,
        line_dash='dash'
    ))
    
    fig_year.update_layout(
        title='全年火电出力对比曲线',
        height=500,
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_year, use_container_width=True)
    
    # 统计对比
    total_before = np.sum(nt2_flat) / 10000
    total_after = np.sum(nt_flat) / 10000
    peak_before = np.max(nt2_flat)
    peak_after = np.max(nt_flat)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("优化前总量", f"{total_before:.2f}亿kWh")
    col2.metric("优化后总量", f"{total_after:.2f}亿kWh")
    col3.metric("峰值削减", f"{peak_before - peak_after:.1f} MW")
    col4.metric("电量减少", f"{total_before - total_after:.2f}亿kWh")
    
    st.markdown("---")
    
    # 调峰深度分析
    st.subheader("调峰深度分析")
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Histogram(x=nt_flat, name='优化后', nbinsx=50, opacity=0.7))
    fig_hist.add_trace(go.Histogram(x=nt2_flat, name='优化前', nbinsx=50, opacity=0.5))
    
    fig_hist.update_layout(
        title='火电出力直方图',
        barmode='overlay',
        height=400,
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_hist, use_container_width=True)